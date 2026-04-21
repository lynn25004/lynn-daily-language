# lynn-daily-language

[![Tests](https://github.com/lynn25004/lynn-daily-language/actions/workflows/test.yml/badge.svg)](https://github.com/lynn25004/lynn-daily-language/actions/workflows/test.yml)
[![Morning Lesson](https://github.com/lynn25004/lynn-daily-language/actions/workflows/morning.yml/badge.svg)](https://github.com/lynn25004/lynn-daily-language/actions/workflows/morning.yml)
[![Evening Review](https://github.com/lynn25004/lynn-daily-language/actions/workflows/evening.yml/badge.svg)](https://github.com/lynn25004/lynn-daily-language/actions/workflows/evening.yml)

> 每天自動推播 10 個英文單字（TOEIC 750 程度）、2 個英文文法、10 個日文單字（N5）、2 個日文文法到 LINE。
> 晚上複習當日內容 + 間隔重複（1/3/7 天前的單字），週六附上週單字總結。

## 架構

```
┌────────────────────┐   cron   ┌──────────────────┐    ┌──────────────┐    ┌───────────┐
│  GitHub Actions    │ ───────▶ │  coach.py (Py)   │───▶│  Gemini API  │───▶│  LINE API │
│  (morning/evening) │          │  stdlib only     │    │  2.5-flash   │    │ multicast │
└────────────────────┘          └──────────────────┘    └──────────────┘    └───────────┘
                                          │
                                          ▼
                                  lessons/YYYY-MM-DD.{json,md}
                                  （commit 回 repo 當歷史）
```

## 功能特色

- 🗓️ **全自動排程**：GitHub Actions cron，不用自己的電腦 24/7 開著
- 🤖 **AI 生成內容**：Gemini 2.5-flash，每天主題不同（工程師日常 / 生活 / 美食 / 科技...）
- 📨 **LINE multicast**：一次推多個收件人只算 1 則訊息額度
- 🔁 **間隔重複**：晚課自動帶 1/3/7 天前的單字回顧（符合艾賓浩斯遺忘曲線）
- 📊 **週六總結**：每週日開始前彙整本週 60 個英文 + 60 個日文單字
- 💾 **歷史保存**：每日課程 commit 為 Markdown，可當自己的學習筆記
- ✅ **有測試**：pytest + CI，改 prompt 或格式不怕壞

## 排程

| Workflow | 時間（Asia/Taipei） | UTC cron | 頻率 |
|---|---|---|---|
| `morning.yml` | 09:00 | `0 1 * * 1-6` | 週一到週六 |
| `evening.yml` | 23:00 | `0 15 * * 1-6` | 週一到週六 |
| `test.yml` | — | — | push/PR 時 |

## 需要的 Secrets

到 repo 的 `Settings → Secrets and variables → Actions → New repository secret` 設定：

| Secret Name | 說明 | 取得方式 |
|---|---|---|
| `GEMINI_API_KEY` | Gemini API key | <https://aistudio.google.com/apikey> |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE Messaging API token | LINE Developers Console |
| `LINE_USER_IDS` | 推播目標 user ID（多人用 `,` 分隔） | LINE Developers Console / webhook 取得 |

## 本機測試

```bash
export GEMINI_API_KEY="AIzaSy..."
export LINE_CHANNEL_ACCESS_TOKEN="..."
export LINE_USER_IDS="U123...,U456..."  # 多人用逗號分隔

# 跑早課（會推 LINE + 存 lessons/YYYY-MM-DD.json）
python3 scripts/coach.py morning

# 跑複習（需先有當日早課 JSON）
python3 scripts/coach.py review

# 跑測試
pytest tests/
```

## 使用者設定

目前鎖定為賴皇菘的個人使用：

- 英文：多益目標 750
- 日文：JLPT N5 準備中（已會 50 音）
- 興趣主題：嵌入式 / IoT / 再生能源 / AI 工具 / 日文學習 / 輕鬆日常

如需改風格／程度／主題，編輯 `scripts/coach.py` 中的 `MORNING_PROMPT`。

## 手動觸發

到 `Actions` 頁籤，選 workflow → `Run workflow` 按鈕。

## 技術重點（作品集用）

這個專案展示了以下能力：

- **無伺服器排程系統**：GitHub Actions cron + workflow_dispatch
- **多 API 整合**：Google Gemini + LINE Messaging API（push & multicast）
- **Prompt Engineering**：結構化 JSON response、多語言內容生成
- **錯誤處理**：Gemini 5xx/網路錯誤自動 retry + 指數退避
- **純 stdlib Python**：零第三方依賴，好維護、易部署
- **測試與 CI**：pytest + GitHub Actions CI badge
- **間隔重複學習演算法**：符合記憶曲線的複習邏輯

## 授權

MIT License（內容為個人學習用途）
