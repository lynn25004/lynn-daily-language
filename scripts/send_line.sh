#!/bin/bash
# 用法：send_line.sh "訊息內容"
# 從 ~/.claude/line.env 讀取 token & user id，推文字訊息給使用者

set -euo pipefail

if [ $# -lt 1 ]; then
  echo "用法：$0 \"訊息內容\"" >&2
  exit 1
fi

MSG="$1"

# 載入 LINE 憑證
if [ ! -f "$HOME/.claude/line.env" ]; then
  echo "錯誤：找不到 ~/.claude/line.env" >&2
  exit 1
fi
# shellcheck disable=SC1091
source "$HOME/.claude/line.env"

# 以 jq 正確跳脫字串（避免訊息內有雙引號/換行打壞 JSON）
PAYLOAD=$(jq -n \
  --arg to "$LINE_USER_ID" \
  --arg text "$MSG" \
  '{to: $to, messages: [{type: "text", text: $text}]}')

RESP=$(curl -sS -X POST https://api.line.me/v2/bot/message/push \
  -H "Authorization: Bearer $LINE_CHANNEL_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD")

# 成功時 response 含 sentMessages；失敗才會有 "message" 欄位
if echo "$RESP" | jq -e '.message' > /dev/null 2>&1; then
  echo "LINE 推送失敗：$RESP" >&2
  exit 1
fi

echo "✅ 已推送（$(date '+%H:%M:%S')）：$(echo "$MSG" | head -1 | cut -c1-40)..."
