#!/usr/bin/env python3
"""Transcribe audio with Fish Audio ASR (direct API) + DeepSeek (direct API) polishing.

ASR:  Fish Audio  POST https://api.fish.audio/v1/asr   — the single ASR path
      (no ElevenLabs, and Fish is called via its own API, not Doubao / Volcengine Ark).
LLM:  DeepSeek     POST https://api.deepseek.com/chat/completions  — direct, not Ark.

Fish Audio has no speaker diarization: every segment comes back without a speaker,
so DeepSeek infers speakers during polishing (guided by any speaker aliases).
Long audio is chunked with ffmpeg because Fish caps uploads at ~22 MB.

Environment:
  FISH_API_KEY / FISH_AUDIO_API_KEY   Fish Audio ASR key
  DEEPSEEK_API_KEY                    DeepSeek key (polishing + summary)
  DEEPSEEK_MODEL                      default: deepseek-chat
  DEEPSEEK_BASE_URL                   default: https://api.deepseek.com
  VOLCENGINE_SPEAKER_ALIASES          optional default speaker map, e.g. "1=Joe;2=Bob"
  VOLCENGINE_OBSIDIAN_MEETING_MEMO_DIR  optional output dir override
"""

from __future__ import annotations

import argparse
import http.client
import json
import mimetypes
import os
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

FISH_ASR_URL = "https://api.fish.audio/v1/asr"
DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com"
FISH_CHUNK_SIZE_SEC = 240  # Fish Audio recommended chunk size
FISH_MAX_UPLOAD_MB = 22  # Fish Audio file size limit
FISH_RETRIES = 4
FISH_TIMEOUT_SEC = 240
DEFAULT_OBSIDIAN_DIR = (
    Path.home()
    / "Library/Mobile Documents/iCloud~md~obsidian/Documents/Esther Workspace/Raw/meeting memo"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Transcribe audio with Fish Audio ASR and polish with DeepSeek.",
    )
    parser.add_argument("audio_source", help="Local audio file path.")
    parser.add_argument("--language", default=None, help="Language code, e.g. zh, en. Auto-detect if omitted.")
    parser.add_argument(
        "--out-dir",
        default=(
            os.environ.get("MEETING_MEMO_DIR")
            or os.environ.get("VOLCENGINE_OBSIDIAN_MEETING_MEMO_DIR")
            or str(DEFAULT_OBSIDIAN_DIR)
        ),
        help="Output directory. Defaults to $MEETING_MEMO_DIR, then the legacy var, then a personal Obsidian path. Set --out-dir or $MEETING_MEMO_DIR for your own setup.",
    )
    parser.add_argument("--speaker-alias", action="append", default=[], help="Speaker mapping like '1=Joe'. Repeatable.")
    parser.add_argument("--participant", default="", help="Comma-separated participant hints.")
    parser.add_argument("--keyword", default="", help="Comma-separated focus keywords / terminology hints.")
    parser.add_argument("--keyterms-file", default=None, help="Path to a text file with one keyterm per line.")
    parser.add_argument("--skip-polish", action="store_true", help="Skip DeepSeek polishing and summarization.")
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Environment helpers
# ---------------------------------------------------------------------------

def require_env(name: str) -> str:
    value = os.environ.get(name)
    if value:
        return value
    raise SystemExit(f"Missing required environment variable: {name}")


def optional_env(name: str, default: str | None = None) -> str | None:
    return os.environ.get(name) or default


# ---------------------------------------------------------------------------
# Speaker aliases
# ---------------------------------------------------------------------------

def canonicalize_speaker_label(label: str) -> str:
    cleaned = str(label).strip()
    match = re.fullmatch(r"(?:Speaker\s*)?(\d+)", cleaned, flags=re.IGNORECASE)
    if match:
        return f"Speaker {match.group(1)}"
    return cleaned


def parse_speaker_aliases(raw_items: list[str] | None = None) -> dict[str, str]:
    aliases: dict[str, str] = {}
    items: list[str] = []
    env_value = optional_env("VOLCENGINE_SPEAKER_ALIASES", "")
    if env_value:
        if env_value.lstrip().startswith("{"):
            try:
                payload = json.loads(env_value)
            except json.JSONDecodeError as exc:
                raise SystemExit("VOLCENGINE_SPEAKER_ALIASES is not valid JSON.") from exc
            if not isinstance(payload, dict):
                raise SystemExit("VOLCENGINE_SPEAKER_ALIASES JSON must be an object.")
            for key, value in payload.items():
                aliases[canonicalize_speaker_label(str(key))] = str(value).strip()
        else:
            items.extend(part.strip() for part in re.split(r"[\n;,]+", env_value) if part.strip())
    if raw_items:
        items.extend(raw_items)
    for item in items:
        if "=" not in item:
            raise SystemExit(f"Invalid --speaker-alias entry: {item}")
        key, value = item.split("=", 1)
        aliases[canonicalize_speaker_label(key)] = value.strip()
    return {key: value for key, value in aliases.items() if value}


def apply_speaker_aliases(text: str, speaker_aliases: dict[str, str]) -> str:
    for source, target in speaker_aliases.items():
        pattern = re.compile(rf"(?<!\w){re.escape(source)}(?!\w)", flags=re.IGNORECASE)
        text = pattern.sub(target, text)
    return text


def speaker_alias_instructions(speaker_aliases: dict[str, str]) -> str:
    if not speaker_aliases:
        return "不要猜测或发明任何具体人名；如果没有明确映射，就保留通用 speaker 标签。"
    lines = ["已知说话人映射如下，只能使用这些名字或角色名："]
    for source, target in sorted(speaker_aliases.items()):
        lines.append(f"- {source} = {target}")
    lines.append("除这些映射外，不要自行猜测、补充或替换其他真实姓名。")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Keyterms / participant hints
# ---------------------------------------------------------------------------

def load_keyterms(keyterms_file: str | None, keyword_arg: str) -> list[str]:
    terms: list[str] = []
    if keyterms_file:
        path = Path(keyterms_file).expanduser()
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                term = line.strip()
                if term and not term.startswith("#"):
                    terms.append(term)
    terms.extend(t.strip() for t in keyword_arg.split(",") if t.strip())
    return terms


# ---------------------------------------------------------------------------
# ffmpeg helpers (duration + chunk export)
# ---------------------------------------------------------------------------

def get_duration_seconds(audio_file: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_file),
        ],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())


def export_chunk(audio_file: Path, output_file: Path, start_sec: int, duration_sec: int) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error",
            "-ss", str(start_sec), "-t", str(duration_sec),
            "-i", str(audio_file),
            "-c", "copy", str(output_file),
        ],
        check=True, capture_output=True, text=True,
    )


# ---------------------------------------------------------------------------
# Fish Audio ASR (no diarization)
# ---------------------------------------------------------------------------

class FishAsrError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None, detail: str = "") -> None:
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail

    @property
    def is_file_too_large(self) -> bool:
        return self.status_code == 500 and "maximum file size exceeded" in self.detail.lower()

    @property
    def is_retryable(self) -> bool:
        d = self.detail.lower()
        return (
            self.status_code in {408, 409, 425, 429, 500, 502, 503, 504}
            or "broken pipe" in d
            or "remote disconnected" in d
            or "timed out" in d
            or "timeout" in d
            or "connection reset" in d
            or "temporarily unavailable" in d
        )


def load_fish_api_key() -> str:
    key = os.environ.get("FISH_API_KEY") or os.environ.get("FISH_AUDIO_API_KEY")
    if not key:
        raise SystemExit("Set FISH_API_KEY (or FISH_AUDIO_API_KEY) for Fish Audio ASR.")
    return key


def _build_fish_multipart(audio_path: Path, language: str | None) -> tuple[str, bytes]:
    boundary = f"----CodexBoundary{uuid.uuid4().hex}"
    parts: list[bytes] = []

    def _field(name: str, value: str) -> None:
        parts.append(f"--{boundary}\r\n".encode())
        parts.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        parts.append(value.encode())
        parts.append(b"\r\n")

    _field("ignore_timestamps", "false")
    if language:
        _field("language", language)

    mime = mimetypes.guess_type(audio_path.name)[0] or "application/octet-stream"
    parts.append(f"--{boundary}\r\n".encode())
    parts.append(
        f'Content-Disposition: form-data; name="audio"; filename="{audio_path.name}"\r\n'
        f"Content-Type: {mime}\r\n\r\n".encode()
    )
    parts.append(audio_path.read_bytes())
    parts.append(b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    return boundary, b"".join(parts)


def call_fish_asr(audio_path: Path, language: str | None) -> dict[str, Any]:
    api_key = load_fish_api_key()
    last_error: FishAsrError | None = None
    for attempt in range(1, FISH_RETRIES + 1):
        boundary, body = _build_fish_multipart(audio_path, language)
        req = urllib.request.Request(
            FISH_ASR_URL,
            data=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=FISH_TIMEOUT_SEC) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            error = FishAsrError(f"Fish Audio ASR HTTP {exc.code}: {detail}", status_code=exc.code, detail=detail)
        except urllib.error.URLError as exc:
            error = FishAsrError(f"Could not reach Fish Audio: {exc}", detail=str(exc))
        except socket.timeout as exc:
            error = FishAsrError(f"Fish Audio timed out: {exc}", detail=str(exc) or "timeout")
        except http.client.RemoteDisconnected as exc:
            error = FishAsrError(f"Fish Audio disconnected: {exc}", detail=str(exc) or "remote disconnected")

        last_error = error
        if error.is_file_too_large or not error.is_retryable or attempt >= FISH_RETRIES:
            raise error
        sleep_sec = min(12, attempt * 3)
        print(f"[fish] request failed ({error.detail or error}); retry {attempt + 1}/{FISH_RETRIES} in {sleep_sec}s", flush=True)
        time.sleep(sleep_sec)

    raise last_error or SystemExit("Fish Audio ASR request failed.")


def fish_response_to_utterances(response: dict[str, Any], offset_sec: float = 0.0) -> list[dict[str, Any]]:
    segments = response.get("segments") or []
    utterances: list[dict[str, Any]] = []
    for seg in segments:
        text = str(seg.get("text", "")).strip()
        if not text:
            continue
        utterances.append({
            "speaker": "(unknown)",
            "text": text,
            "start_time": float(seg.get("start", 0.0)) + offset_sec,
            "end_time": float(seg.get("end", 0.0)) + offset_sec,
        })
    if not utterances:
        full = str(response.get("text", "")).strip()
        dur = float(response.get("duration", 0.0) or 0.0)
        if full:
            utterances.append({"speaker": "(unknown)", "text": full, "start_time": offset_sec, "end_time": offset_sec + dur})
    return utterances


def transcribe_fish_chunked(audio_path: Path, duration: float, language: str | None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    file_mb = audio_path.stat().st_size / (1024 * 1024)
    if file_mb > FISH_MAX_UPLOAD_MB:
        safe_sec = duration * (FISH_MAX_UPLOAD_MB * 0.8) / file_mb
        chunk_sec = max(30, min(FISH_CHUNK_SIZE_SEC, safe_sec))
    else:
        chunk_sec = FISH_CHUNK_SIZE_SEC
    chunk_sec_int = int(chunk_sec)

    work_dir = audio_path.parent / f".fish-chunks-{audio_path.stem}"
    work_dir.mkdir(parents=True, exist_ok=True)

    total_chunks = int((duration + chunk_sec - 1) // chunk_sec)
    all_utterances: list[dict[str, Any]] = []

    for idx in range(total_chunks):
        start_sec = int(idx * chunk_sec)
        chunk_file = work_dir / f"chunk_{idx:03d}.m4a"
        cache_file = work_dir / f"chunk_{idx:03d}_result.json"

        if cache_file.exists():
            print(f"[fish-chunk {idx + 1}/{total_chunks}] reuse cached result", flush=True)
            cached = json.loads(cache_file.read_text())
            all_utterances.extend(fish_response_to_utterances(cached, offset_sec=start_sec))
            continue

        if not chunk_file.exists():
            print(f"[fish-chunk {idx + 1}/{total_chunks}] exporting {start_sec}s...", flush=True)
            export_chunk(audio_path, chunk_file, start_sec, chunk_sec_int)

        print(f"[fish-chunk {idx + 1}/{total_chunks}] transcribing with Fish Audio...", flush=True)
        try:
            chunk_response = call_fish_asr(chunk_file, language)
        except FishAsrError as exc:
            if exc.is_file_too_large:
                print(f"[fish-chunk {idx + 1}/{total_chunks}] chunk too large, halving...", flush=True)
                half = max(15, chunk_sec_int // 2)
                for sub_idx, sub_start in enumerate([start_sec, start_sec + half]):
                    sub_file = work_dir / f"chunk_{idx:03d}_sub{sub_idx}.m4a"
                    if not sub_file.exists():
                        export_chunk(audio_path, sub_file, sub_start, half)
                    sub_resp = call_fish_asr(sub_file, language)
                    all_utterances.extend(fish_response_to_utterances(sub_resp, offset_sec=sub_start))
                continue
            raise

        cache_file.write_text(json.dumps(chunk_response, ensure_ascii=False, indent=2), encoding="utf-8")
        all_utterances.extend(fish_response_to_utterances(chunk_response, offset_sec=start_sec))

    merged_response = {"text": " ".join(u["text"] for u in all_utterances), "segments": []}
    return merged_response, all_utterances


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def sec_to_clock(sec: float) -> str:
    sec = max(0.0, sec)
    total_ms = int(sec * 1000)
    hours, rem = divmod(total_ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    seconds, millis = divmod(rem, 1_000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"


def transcript_plain_text(utterances: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for u in utterances:
        start = sec_to_clock(u["start_time"])
        end = sec_to_clock(u["end_time"])
        lines.append(f"[{start} --> {end}] {u['speaker']}: {u['text']}")
    return "\n".join(lines).strip()


# ---------------------------------------------------------------------------
# DeepSeek (direct) API for polishing
# ---------------------------------------------------------------------------

def deepseek_chat(messages: list[dict[str, str]], timeout_sec: int = 300) -> str:
    api_key = require_env("DEEPSEEK_API_KEY")
    model = optional_env("DEEPSEEK_MODEL", "deepseek-chat")
    base_url = optional_env("DEEPSEEK_BASE_URL", DEFAULT_DEEPSEEK_BASE_URL).rstrip("/")
    url = f"{base_url}/chat/completions"
    payload = json.dumps({"model": model, "messages": messages, "temperature": 0.2, "stream": False})

    last_error = ""
    result: Any = None
    for attempt in range(1, 4):
        cmd = [
            "curl", "-s", "-S", "--http1.1", "--noproxy", "*",
            "--max-time", str(timeout_sec),
            "-X", "POST", url,
            "-H", "Content-Type: application/json",
            "-H", f"Authorization: Bearer {api_key}",
            "-d", payload,
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec + 30)
        stdout = proc.stdout.strip()
        if not stdout:
            last_error = proc.stderr or f"curl exit {proc.returncode}"
            if attempt < 3:
                print(f"[deepseek] request failed (attempt {attempt}), retrying in 3s...", flush=True)
                time.sleep(3)
                continue
            raise SystemExit(f"DeepSeek API failed after 3 attempts: {last_error}")
        try:
            result = json.loads(stdout)
        except json.JSONDecodeError:
            raise SystemExit(f"DeepSeek returned non-JSON: {stdout[:500]}")
        break

    if not isinstance(result, dict):
        raise SystemExit("DeepSeek returned a non-JSON response.")
    choices = result.get("choices") or []
    if not choices:
        raise SystemExit(f"DeepSeek returned no choices: {json.dumps(result, ensure_ascii=False)[:500]}")
    content = (choices[0].get("message") or {}).get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = [str(item.get("text", "")) for item in content if isinstance(item, dict) and item.get("type") == "text"]
        return "\n".join(parts).strip()
    raise SystemExit("DeepSeek returned an unsupported content format.")


# ---------------------------------------------------------------------------
# Prompts (carried over from the proven transcribe_elevenlabs flow)
# ---------------------------------------------------------------------------

def _terms_block(keyterms: list[str]) -> str:
    if not keyterms:
        return ""
    return "\n专有名词参考（用于纠正同音字/术语识别错误）：" + "、".join(keyterms[:200]) + "\n"


def _participant_block(participants: str) -> str:
    names = [p.strip() for p in (participants or "").split(",") if p.strip()]
    if not names:
        return ""
    return (
        "\n本次会议参会人可能包括：" + "、".join(names)
        + "（仅作说话人识别提示，不确定时不要硬套到具体句子上）。\n"
    )


def build_polish_prompt(transcript: str, speaker_aliases: dict[str, str] | None, keyterms: list[str], participants: str = "") -> list[dict[str, str]]:
    alias_rules = speaker_alias_instructions(speaker_aliases or {})
    diarize_instruction = (
        "转写来自没有说话人区分的 ASR，所有内容都没有 speaker 标签。"
        "你需要根据对话的语义、问答结构、话题转换来判断每段话是谁说的，"
        "然后在输出中为每段话标注正确的说话人。\n"
    )
    return [
        {
            "role": "system",
            "content": (
                "你是专业会议纪要编辑。把自动语音识别转写整理成流畅、完整、便于阅读的讨论记录。"
                f"{diarize_instruction}"
                "整合方式：把同一话题下来回的计算、数字推演、反复确认整理成一段连贯的叙述；"
                "把同一 speaker 在同一论点上碎片化的多轮发言合并成完整的段落；"
                "去掉口头禅、重复、停顿填充词。"
                "但要保留不同人之间真实的观点分歧和互动问答结构，不要把多人讨论压成单人独白。"
                "**语义修正**：ASR 转写常因同音字、专业术语识别错误产生明显与上下文不符、不通顺、或语义不通的字句。"
                "你需要主动综合上下文意思，对这类明显的转写错误做语义层面的修正，确保最终文本中不出现明显无意义、违反常识或难以理解的句子。"
                "修正应基于上下文推断的高置信判断，不得借机改变发言者的实际观点、数字或结论。"
                "**不确定标注**：如果某处错得明显但你对正确版本把握不足（多种合理猜测、专有名词无法确认、关键数字含糊等），"
                "保留你认为最可能的版本，并在该处用 `[?: 原转写=\"xxx\"，不确定]` 形式行内标注，提示用户人工核对，不要静默猜测。"
                "不新增原文没有的结论，不遗漏关键数字和论点。输出 Markdown。\n"
                f"{alias_rules}{_participant_block(participants)}{_terms_block(keyterms)}"
            ),
        },
        {
            "role": "user",
            "content": (
                "请把下面的会议转写整理成清晰的讨论记录。"
                "要求："
                "1. 大幅整合：把同一人在同一论点上的碎片发言合并成完整段落；"
                "2. 计算和数字推演部分（如估值倍数、仓位比例、IRR 等），整理成一段连贯叙述，不要逐句罗列；"
                "3. 保留不同参与者之间的观点交锋和问答结构；"
                "4. 去掉所有口头禅、重复和无意义填充；"
                "5. 主动结合上下文修正 ASR 明显的同音字/术语转写错误，确保不出现上下文无意义或难以理解的句子；"
                "   把握不足时保留最可能版本并用 `[?: 原转写=\"xxx\"，不确定]` 行内标注，不要静默猜测；"
                "6. 如已给出人名映射就用该映射，否则保留通用标签；"
                "7. 输出格式：`**姓名：** <整理后内容>`，每位说话人一个段落。\n\n"
                f"{transcript}"
            ),
        },
    ]


def build_summary_prompt(transcript: str, source_label: str, speaker_aliases: dict[str, str] | None, participants: str = "") -> list[dict[str, str]]:
    alias_rules = speaker_alias_instructions(speaker_aliases or {})
    return [
        {
            "role": "system",
            "content": (
                "你是资深会议分析助手。请基于转写生成详尽、结构化的会议摘要。\n"
                "首先判断录音类型：\n"
                "- **Discussion（讨论/会议）**：多位参与者围绕议题讨论，各自发表观点。\n"
                "- **Interview（访谈/尽调）**：有明确的提问方和回答方，呈问答结构。\n"
                "根据类型选择对应的输出框架（见 user message）。\n"
                "禁止编造未提及的信息。"
                "语言要直接、克制、像正式 memo，不要写客套话、免责声明、过程说明或'根据转写生成'等套话。"
                f"\n{alias_rules}{_participant_block(participants)}"
            ),
        },
        {
            "role": "user",
            "content": (
                f"请为录音文件《{source_label}》生成会议纪要摘要。使用 Markdown。\n\n"
                "---\n"
                "## 框架 A：Discussion（讨论/会议）\n"
                "如果录音是多人讨论，使用以下结构：\n\n"
                "### 各方观点\n"
                "按说话人逐个总结，每位说话人的内容要**详细**：\n"
                "- 核心论点是什么\n"
                "- 用了什么论据、数据、案例来支撑\n"
                "- 有什么保留意见或附加条件\n\n"
                "### 共识\n大家在哪些问题上达成了一致，具体结论是什么。\n\n"
                "### 分歧\n大家在哪些问题上没有达成一致，各方立场分别是什么。\n\n"
                "### 待办事项\n明确的 action items，标注负责人（如果转写中提到）。\n\n"
                "### 未解答的问题\n讨论中提出但未得到解答、或需要后续跟进的问题。\n\n"
                "---\n"
                "## 框架 B：Interview（访谈/尽调）\n"
                "如果录音是访谈或尽调，使用以下结构：\n\n"
                "### 核心 QA\n"
                "沿着提问方的问题顺序组织，每个问题块写清楚：\n"
                "- 提问方真正关心什么\n"
                "- 被访者的直接回答\n"
                "- 被访者如何展开论证，用了哪些例子/数据/比较\n"
                "- 如果涉及较多数字、比例、时间线或结构化事实，**用表格呈现**\n\n"
                "### 被访者主要观点\n按说话人逐个展开，详尽提炼核心判断、依据、分歧和保留意见。\n\n"
                "### 待办事项\n明确的 action items。\n\n"
                "### 未解答的问题\n访谈中提出但未充分回答、或需要后续跟进的问题。\n\n"
                "---\n"
                "要求：\n"
                "1. 先判断录音类型，选择框架 A 或 B，不要混用。\n"
                "2. 内容必须详细、有论点有论据，不要写空泛概括。\n"
                "3. 涉及数字、比例、估值、时间线等结构化信息时，优先用 Markdown 表格输出。\n"
                "4. 如果某一小节信息不足，直接写'本片段未涉及'。\n\n"
                f"会议转写如下：\n{transcript}"
            ),
        },
    ]


def build_meeting_memo(source_label: str, stamp: str, polished_transcript: str, summary: str) -> str:
    lines = [
        f"- Date: {stamp}",
        f"- Original file: {source_label}",
        "",
        "## Summary",
        "",
        summary.strip(),
        "",
        "## Polished Transcript",
        "",
        polished_transcript.strip(),
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Chunked polishing for long transcripts
# ---------------------------------------------------------------------------

def chunk_transcript_text(transcript: str, max_chars: int = 12000) -> list[str]:
    lines = [line for line in transcript.splitlines() if line.strip()]
    if not lines:
        return []
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for line in lines:
        line_len = len(line) + 1
        if current and current_len + line_len > max_chars:
            chunks.append("\n".join(current))
            current = [line]
            current_len = line_len
        else:
            current.append(line)
            current_len += line_len
    if current:
        chunks.append("\n".join(current))
    return chunks


def build_polished_transcript(transcript: str, speaker_aliases: dict[str, str] | None, keyterms: list[str], participants: str = "") -> str:
    chunks = chunk_transcript_text(transcript)
    if not chunks:
        return ""
    if len(chunks) == 1:
        return deepseek_chat(build_polish_prompt(chunks[0], speaker_aliases, keyterms, participants))

    parts: list[str] = []
    total = len(chunks)
    for index, chunk in enumerate(chunks, start=1):
        prompt = build_polish_prompt(chunk, speaker_aliases, keyterms, participants)
        prompt[1]["content"] = (
            f"这是整场会议转写的第 {index}/{total} 段。"
            "请只整理这一段，不要补写前后内容，也不要写总结性过渡语。\n\n"
            f"{chunk}"
        )
        parts.append(deepseek_chat(prompt).strip())
    return "\n\n".join(part for part in parts if part)


def normalize_generated_text(text: str, speaker_aliases: dict[str, str] | None = None) -> str:
    normalized = text.strip()
    if speaker_aliases:
        normalized = apply_speaker_aliases(normalized, speaker_aliases)
    return re.sub(r"\n{3,}", "\n\n", normalized)


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def save_outputs(
    out_dir: Path,
    response: dict[str, Any],
    utterances: list[dict[str, Any]],
    source_label: str,
    skip_polish: bool,
    speaker_aliases: dict[str, str],
    keyterms: list[str],
    participants: str = "",
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d")
    file_prefix = f"{stamp}-{Path(source_label).stem}"

    transcript_text = transcript_plain_text(utterances)
    if speaker_aliases:
        transcript_text = apply_speaker_aliases(transcript_text, speaker_aliases)

    if skip_polish:
        polished_transcript = transcript_text
        summary = "Polishing skipped."
    else:
        print("[polish] generating polished transcript with DeepSeek...", flush=True)
        polished_transcript = build_polished_transcript(transcript_text, speaker_aliases, keyterms, participants)
        print("[summary] generating summary with DeepSeek...", flush=True)
        summary = deepseek_chat(build_summary_prompt(transcript_text, source_label, speaker_aliases, participants))

    polished_transcript = normalize_generated_text(polished_transcript, speaker_aliases)
    summary = normalize_generated_text(summary, speaker_aliases)

    (out_dir / f"{file_prefix}_result.json").write_text(
        json.dumps(response, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    memo_path = out_dir / f"{file_prefix}_meeting-memo.md"
    memo_path.write_text(build_meeting_memo(source_label, stamp, polished_transcript, summary), encoding="utf-8")
    print(str(memo_path.resolve()), flush=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    args = parse_args()
    speaker_aliases = parse_speaker_aliases(args.speaker_alias)
    keyterms = load_keyterms(args.keyterms_file, args.keyword)

    audio_path = Path(args.audio_source).expanduser().resolve()
    if not audio_path.exists():
        raise SystemExit(f"Audio file not found: {audio_path}")
    source_label = audio_path.name

    print(f"[transcribe] checking duration of {source_label}...", flush=True)
    duration = get_duration_seconds(audio_path)
    print(f"[transcribe] duration: {int(duration)}s ({int(duration / 60)}m{int(duration % 60)}s)", flush=True)

    file_mb = audio_path.stat().st_size / (1024 * 1024)
    if duration > FISH_CHUNK_SIZE_SEC or file_mb > FISH_MAX_UPLOAD_MB:
        print(f"[transcribe] chunking with ffmpeg (~{FISH_CHUNK_SIZE_SEC}s) for Fish Audio...", flush=True)
        response, utterances = transcribe_fish_chunked(audio_path, duration, args.language)
    else:
        print("[transcribe] sending to Fish Audio ASR...", flush=True)
        response = call_fish_asr(audio_path, args.language)
        utterances = fish_response_to_utterances(response)

    if not utterances:
        raise SystemExit("Fish Audio returned no transcript text.")
    print(f"[transcribe] got {len(utterances)} utterances", flush=True)

    save_outputs(Path(args.out_dir), response, utterances, source_label, args.skip_polish, speaker_aliases, keyterms, args.participant)
    print("Done.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
