#!/usr/bin/env bash
# Find recordings in the iCloud Recordings folder, judged by the YYYYMMDD date
# prefix in the filename (iCloud sync rewrites mtime, so the filename date is
# more reliable). mtime is used only as a tie-breaker.
#
# Usage:
#   find_latest_recording.sh            # print the 5 most recent recordings
#   find_latest_recording.sh --latest   # print only the single newest recording path
#   find_latest_recording.sh --today    # print only recordings dated today (by filename)
#
# Override the source folder with MEETING_RECORDINGS_DIR.
set -euo pipefail

REC_DIR="${MEETING_RECORDINGS_DIR:-$HOME/Library/Mobile Documents/com~apple~CloudDocs/Recordings}"

if [[ ! -d "$REC_DIR" ]]; then
  echo "Recordings folder not found: $REC_DIR" >&2
  exit 1
fi

mode="${1:-}"

# Build "<datekey>\t<mtime>\t<path>" rows.
# datekey = leading 8-digit date in the basename, else 00000000 (sorts last).
# Sort by datekey desc, then mtime desc, so the newest by filename date wins.
listing="$(
  find "$REC_DIR" -type f \
    \( -iname '*.m4a' -o -iname '*.qta' -o -iname '*.mp3' -o -iname '*.wav' \
       -o -iname '*.aac' -o -iname '*.caf' -o -iname '*.aiff' -o -iname '*.flac' \) \
    -not -path '*/.*' \
    -exec stat -f '%m	%N' {} + 2>/dev/null \
  | while IFS=$'\t' read -r m p; do
      base="${p##*/}"
      if [[ "$base" =~ ^([0-9]{8}) ]]; then
        datekey="${BASH_REMATCH[1]}"
      else
        datekey="00000000"
      fi
      printf '%s\t%s\t%s\n' "$datekey" "$m" "$p"
    done \
  | sort -t$'\t' -k1,1rn -k2,2rn
)"

if [[ -z "$listing" ]]; then
  echo "No audio recordings found under: $REC_DIR" >&2
  exit 1
fi

case "$mode" in
  --latest)
    printf '%s\n' "$listing" | head -n 1 | cut -f3-
    ;;
  --today)
    today="$(date '+%Y%m%d')"
    out="$(printf '%s\n' "$listing" | awk -F'\t' -v d="$today" '$1 == d')"
    if [[ -z "$out" ]]; then
      echo "No recording dated today ($today) found in: $REC_DIR" >&2
      exit 1
    fi
    printf '%s\n' "$out" | while IFS=$'\t' read -r dk m p; do
      printf '%s\t%s\n' "$(date -r "$m" '+%Y-%m-%d %H:%M:%S')" "$p"
    done
    ;;
  *)
    printf '%s\n' "$listing" | head -n 5 | while IFS=$'\t' read -r dk m p; do
      printf '%s\t%s\n' "$(date -r "$m" '+%Y-%m-%d %H:%M:%S')" "$p"
    done
    ;;
esac
