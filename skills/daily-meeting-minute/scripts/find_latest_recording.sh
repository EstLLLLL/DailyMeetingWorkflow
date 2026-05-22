#!/usr/bin/env bash
# Find the most recently modified recording(s) in the iCloud Recordings folder.
#
# Usage:
#   find_latest_recording.sh            # print the 5 newest recordings (mtime + path)
#   find_latest_recording.sh --latest   # print only the single newest recording path
#   find_latest_recording.sh --today     # print only recordings modified today
#
# Override the source folder with MEETING_RECORDINGS_DIR.
set -euo pipefail

REC_DIR="${MEETING_RECORDINGS_DIR:-$HOME/Library/Mobile Documents/com~apple~CloudDocs/Recordings}"

if [[ ! -d "$REC_DIR" ]]; then
  echo "Recordings folder not found: $REC_DIR" >&2
  exit 1
fi

mode="${1:-}"

# Collect audio files with their modification time (epoch seconds), newest first.
# `stat -f` is the BSD/macOS form.
listing="$(
  find "$REC_DIR" -type f \
    \( -iname '*.m4a' -o -iname '*.qta' -o -iname '*.mp3' -o -iname '*.wav' \
       -o -iname '*.aac' -o -iname '*.caf' -o -iname '*.aiff' -o -iname '*.flac' \) \
    -not -path '*/.*' \
    -exec stat -f '%m	%N' {} + 2>/dev/null | sort -rn
)"

if [[ -z "$listing" ]]; then
  echo "No audio recordings found under: $REC_DIR" >&2
  exit 1
fi

case "$mode" in
  --latest)
    printf '%s\n' "$listing" | head -n 1 | cut -f2-
    ;;
  --today)
    today_start="$(date -j -f '%Y-%m-%d %H:%M:%S' "$(date '+%Y-%m-%d') 00:00:00" '+%s')"
    printf '%s\n' "$listing" | awk -F'\t' -v t="$today_start" '$1 >= t' | while IFS=$'\t' read -r m p; do
      printf '%s\t%s\n' "$(date -r "$m" '+%Y-%m-%d %H:%M:%S')" "$p"
    done
    ;;
  *)
    printf '%s\n' "$listing" | head -n 5 | while IFS=$'\t' read -r m p; do
      printf '%s\t%s\n' "$(date -r "$m" '+%Y-%m-%d %H:%M:%S')" "$p"
    done
    ;;
esac
