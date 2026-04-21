# lynn-daily-language

> 每天 09:00 自動推播 10 個英文單字（TOEIC 750 程度）、2 個英文文法、10 個日文單字（N5 程度）、2 個日文文法到 LINE；23:00 自動複習當日內容。

## 架構

```
GitHub Actions cron  →  Python (coach.py)  →  Gemini API  →  LINE Messaging API
                                           ↓
                                   lessons/YYYY-MM-DD.{md,json}
                                   （commit 回 repo 當歷史）
```

## 排程

| Workflow | 時間（Asia/Taipei） | UTC cron | 頻率 |
|---|---|---|---|
| `morning.yml` | 09:00 | `0 1 * * 1-6` | 週一到週六 |
| `evening.yml` | 23:00 | `0 15 * * 1-6` | 週一到週六 |

## 需要的 Secrets

到 repo 的 `Settings → Secrets and variables → Actions → New repository secret` 設定：

| Secret Name | 說明 | 取得方式 |
|---|---|---|
| `GEMINI_API_KEY` | Gemini 2.0 Flash API key | https://aistudio.google.com/apikey |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE Messaging API channel access token | LINE Developers Console |
| `LINE_USER_ID` | 推播目標 user ID | LINE Developers Console |

## 本機測試

```bash
# 設定環境變數
export GEMINI_API_KEY="AIzaSy..."
export LINE_CHANNEL_ACCESS_TOKEN="..."
export LINE_USER_ID="U..."

# 跑早課（會推 4 則 LINE + 存 lessons/YYYY-MM-DD.json 和 .md）
python3 scripts/coach.py morning

# 跑複習（需先有當日早課 JSON）
python3 scripts/coach.py review
```

## 課程歷史

所有課程會以 Markdown 格式保存在 `lessons/YYYY-MM-DD.md`，可作為自己的學習紀錄翻閱。

## 使用者設定

目前鎖定為賴皇菘（lynnn）的個人使用：

- 英文：多益目標 750
- 日文：JLPT N5 準備中（已會 50 音）
- 興趣主題：嵌入式 / IoT / 再生能源 / AI 工具 / 日文學習 / 輕鬆日常

如需改風格／程度／主題，編輯 `scripts/coach.py` 中的 `MORNING_PROMPT`。

## 手動觸發

到 `Actions` 頁籤，選 workflow → `Run workflow` 按鈕。
