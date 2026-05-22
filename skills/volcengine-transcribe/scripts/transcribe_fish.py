#!/usr/bin/env python3
"""Transcribe a local audio file with Fish Audio ASR (direct API), then polish and
summarize with DeepSeek (direct API), and write an Obsidian-ready meeting memo.

ASR:  Fish Audio  POST https://api.fish.audio/v1/asr   (no ElevenLabs, no Doubao)
LLM:  DeepSeek    POST https://api.deepseek.com/chat/completions  (direct, not Ark)

Fish ASR returns timestamped segments but no speaker diarization, so speaker
attribution is best-effort: participant names are used only as hints, and lines
that cannot be attributed stay labeled "Speaker ?".

Environment:
  FISH_API_KEY        Fish Audio API key (from fish.audio/app/api-keys)
  DEEPSEEK_API_KEY    DeepSeek API key
  DEEPSEEK_MODEL      default: deepseek-chat
  DEEPSEEK_BASE_URL   default: https://api.deepseek.com

Usage:
  python3 transcribe_fish.py ./meeting.m4a \
    --language zh \
    --participant "Joe,投资方,法务" \
    --keyword "商业模式,定价,竞争格局" \
    --out-dir "$HOME/Library/Mobile Documents/iCloud~md~obsidian/Documents/Esther Workspace/Meeting Memo"
"""
import argparse
import datetime as dt
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request
import uuid

FISH_ASR_URL = "https://api.fish.audio/v1/asr"


def _multipart(fields, file_field, filename, content, content_type):
    boundary = uuid.uuid4().hex
    body = bytearray()
    for name, value in fields.items():
        if value is None:
            continue
        body += f"--{boundary}\r\n".encode()
        body += f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode()
        body += f"{value}\r\n".encode()
    body += f"--{boundary}\r\n".encode()
    body += (
        f'Content-Disposition: form-data; name="{file_field}"; '
        f'filename="{filename}"\r\n'
    ).encode()
    body += f"Content-Type: {content_type}\r\n\r\n".encode()
    body += content + b"\r\n"
    body += f"--{boundary}--\r\n".encode()
    return boundary, bytes(body)


def fish_asr(audio_path, language=None, ignore_timestamps=False):
    key = os.environ.get("FISH_API_KEY")
    if not key:
        sys.exit("FISH_API_KEY is not set")
    with open(audio_path, "rb") as f:
        content = f.read()
    ctype = mimetypes.guess_type(audio_path)[0] or "application/octet-stream"
    fields = {}
    if language:
        fields["language"] = language
    if ignore_timestamps:
        fields["ignore_timestamps"] = "true"
    boundary, body = _multipart(
        fields, "audio", os.path.basename(audio_path), content, ctype
    )
    req = urllib.request.Request(FISH_ASR_URL, data=body, method="POST")
    req.add_header("Authorization", f"Bearer {key}")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        sys.exit(f"Fish ASR error {e.code}: {detail}")


def deepseek_chat(messages, temperature=0.3):
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        sys.exit("DEEPSEEK_API_KEY is not set")
    base = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
    model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "stream": False,
    }
    req = urllib.request.Request(
        f"{base}/chat/completions", data=json.dumps(payload).encode(), method="POST"
    )
    req.add_header("Authorization", f"Bearer {key}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        sys.exit(f"DeepSeek error {e.code}: {detail}")
    return data["choices"][0]["message"]["content"].strip()


def _fmt_ts(seconds):
    seconds = float(seconds or 0)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def build_srt(segments):
    lines = []
    for i, seg in enumerate(segments, 1):
        start = _fmt_ts(seg.get("start")).replace(".", ",")
        end = _fmt_ts(seg.get("end")).replace(".", ",")
        lines.append(str(i))
        lines.append(f"{start} --> {end}")
        lines.append((seg.get("text") or "").strip())
        lines.append("")
    return "\n".join(lines)


def build_raw_transcript(segments):
    out = []
    for seg in segments:
        out.append(f"[{_fmt_ts(seg.get('start'))}] {(seg.get('text') or '').strip()}")
    return "\n".join(out)


def polish_and_summarize(raw_transcript, participants, keywords):
    hints = []
    if participants:
        hints.append(f"参会人（仅作提示，不要强行套到不确定的句子上）：{participants}")
    if keywords:
        hints.append(f"关键词（帮助识别专有名词）：{keywords}")
    hint_block = ("\n".join(hints) + "\n\n") if hints else ""

    polish_prompt = (
        "下面是一段带时间戳的会议转录，来自语音识别，没有说话人分离。\n"
        "请整理成可读的问答（Q&A）风格记录：\n"
        "- 保持原始对话顺序，不要合并多轮问答成一句总结。\n"
        "- 只合并破碎、重复的措辞，纠正明显的识别错误。\n"
        "- 没有把握归属时用 `Speaker ?`，不要凭空编造说话人。\n"
        "- 参会人名字只作提示，不确定就不要硬套。\n\n"
        f"{hint_block}转录：\n{raw_transcript}"
    )
    polished = deepseek_chat(
        [
            {"role": "system", "content": "你是严谨的会议记录整理助手，不编造内容。"},
            {"role": "user", "content": polish_prompt},
        ]
    )

    summary_prompt = (
        "根据下面整理后的会议记录，写一份详细的中文总结：\n"
        "- 重点呈现每位参会人的主要观点。\n"
        "- 保留关键数字、日期、承诺等具体信息。\n"
        "- 直接、少套话。\n\n"
        f"{hint_block}会议记录：\n{polished}"
    )
    summary = deepseek_chat(
        [
            {"role": "system", "content": "你是严谨的会议总结助手，不编造内容。"},
            {"role": "user", "content": summary_prompt},
        ]
    )
    return polished, summary


def write_memo(out_dir, audio_path, summary, polished, no_speakers):
    os.makedirs(out_dir, exist_ok=True)
    now = dt.datetime.now()
    stamp = now.strftime("%Y%m%d-%H%M%S")
    base = os.path.splitext(os.path.basename(audio_path))[0]
    memo_path = os.path.join(out_dir, f"{stamp} {base}.md")
    parts = [
        f"Date: {now.strftime('%Y-%m-%d')}",
        f"Original file: {os.path.basename(audio_path)}",
        "",
        "## 总结",
        "",
        summary,
        "",
        "## 转录（Q&A）",
        "",
        polished,
        "",
    ]
    if no_speakers:
        parts.insert(
            2, "\n> 注：Fish ASR 未返回说话人分离，发言人标注为最佳猜测。\n"
        )
    with open(memo_path, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))
    return memo_path


def main():
    ap = argparse.ArgumentParser(description="Fish ASR -> DeepSeek -> Obsidian memo")
    ap.add_argument("audio", help="local audio file path")
    ap.add_argument("--language", default=None, help="e.g. zh, en (leave unset if unknown)")
    ap.add_argument("--participant", default="", help="comma-separated participant hints")
    ap.add_argument("--keyword", default="", help="comma-separated focus keywords")
    ap.add_argument(
        "--out-dir",
        default=os.environ.get(
            "VOLCENGINE_OBSIDIAN_MEETING_MEMO_DIR",
            os.path.expanduser(
                "~/Library/Mobile Documents/iCloud~md~obsidian/Documents/"
                "Esther Workspace/Meeting Memo"
            ),
        ),
        help="output directory for memo, result.json, transcript.srt",
    )
    args = ap.parse_args()

    if not os.path.isfile(args.audio):
        sys.exit(f"Audio file not found: {args.audio}")

    print(f"[1/3] Fish ASR: {args.audio}", file=sys.stderr)
    result = fish_asr(args.audio, language=args.language)
    segments = result.get("segments") or []
    if not segments and result.get("text"):
        segments = [{"start": 0, "end": result.get("duration", 0), "text": result["text"]}]
    if not segments:
        sys.exit("Fish ASR returned no transcript text.")

    os.makedirs(args.out_dir, exist_ok=True)
    with open(os.path.join(args.out_dir, "result.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    with open(os.path.join(args.out_dir, "transcript.srt"), "w", encoding="utf-8") as f:
        f.write(build_srt(segments))

    raw = build_raw_transcript(segments)
    print("[2/3] DeepSeek polish + summary", file=sys.stderr)
    polished, summary = polish_and_summarize(raw, args.participant, args.keyword)

    print("[3/3] Write Obsidian memo", file=sys.stderr)
    memo = write_memo(args.out_dir, args.audio, summary, polished, no_speakers=True)
    print(memo)


if __name__ == "__main__":
    main()
