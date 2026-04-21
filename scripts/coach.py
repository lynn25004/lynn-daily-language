#!/usr/bin/env python3
"""
Daily English/Japanese language coach for 賴皇菘 (lynnn).
Generates daily lessons via Gemini API and pushes to LINE.

Usage:
    python coach.py morning   # Generate today's lesson, save to lessons/, push 4 LINE messages
    python coach.py review    # Load today's lesson, build review quiz, push 4 LINE messages
"""

from __future__ import annotations

import json
import os
import sys
import textwrap
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib import request, parse, error

# --- Paths --------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
LESSONS_DIR = ROOT / "lessons"
LESSONS_DIR.mkdir(exist_ok=True)

# --- Config -------------------------------------------------------------------
TAIPEI = timezone(timedelta(hours=8))
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_API_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
)
LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"


def today_taipei() -> str:
    return datetime.now(TAIPEI).strftime("%Y-%m-%d")


def weekday_zh(date_str: str) -> str:
    wd = datetime.strptime(date_str, "%Y-%m-%d").weekday()
    return ["一", "二", "三", "四", "五", "六", "日"][wd]


def env(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        sys.exit(f"❌ 缺少環境變數：{name}")
    return val


# --- Gemini -------------------------------------------------------------------
def gemini_generate(prompt: str, *, json_mode: bool = True) -> str:
    """Call Gemini generateContent; return raw text."""
    api_key = env("GEMINI_API_KEY")
    body: dict = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.9,
            "maxOutputTokens": 16384,
        },
    }
    if json_mode:
        body["generationConfig"]["responseMimeType"] = "application/json"

    data = json.dumps(body).encode("utf-8")
    url = f"{GEMINI_API_URL}?key={parse.quote(api_key)}"
    req = request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=60) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as e:
        sys.exit(f"❌ Gemini HTTP {e.code}: {e.read().decode('utf-8', 'ignore')}")

    try:
        return payload["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        sys.exit(f"❌ Gemini 回應格式異常：{json.dumps(payload)[:500]}")


# --- LINE ---------------------------------------------------------------------
def line_push(text: str) -> None:
    token = env("LINE_CHANNEL_ACCESS_TOKEN")
    user_id = env("LINE_USER_ID")
    body = json.dumps(
        {"to": user_id, "messages": [{"type": "text", "text": text}]}
    ).encode("utf-8")
    req = request.Request(
        LINE_PUSH_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with request.urlopen(req, timeout=30) as resp:
        resp_body = resp.read().decode("utf-8")
        if resp.status >= 300:
            sys.exit(f"❌ LINE push failed ({resp.status}): {resp_body}")


# --- Prompts ------------------------------------------------------------------
MORNING_PROMPT = textwrap.dedent("""
    你是一位輕鬆友善的英日文老師。
    今天是 {date}（星期{weekday}），為一位台灣工程師求職者設計今日課程。

    使用者背景：
    - 英文程度：多益目標 750（中上）
    - 日文程度：N5（50 音已會），目標 JLPT N5
    - 興趣：嵌入式系統、IoT、再生能源安全、AI 工具、日文學習
    - 希望主題：輕鬆日常會話為主，可帶一點工程師日常情境

    請輸出以下 JSON 結構（**只輸出 JSON，不要任何說明文字**）：

    {{
      "english_words": [
        {{
          "word": "英文單字（原形）",
          "pos": "詞性縮寫，例如 v./n./adj.",
          "meaning": "中文意思（5-12 字）",
          "example": "英文例句（8-15 字，要口語、輕鬆）",
          "example_zh": "中文翻譯"
        }}
        // 共 10 個
      ],
      "english_grammar": [
        {{
          "title": "文法名稱（中文）",
          "rule": "一句話說明用法（20-40 字）",
          "examples": [
            "英文例句 1（中文翻譯）",
            "英文例句 2（中文翻譯）",
            "英文例句 3（中文翻譯）"
          ]
        }}
        // 共 2 個
      ],
      "japanese_words": [
        {{
          "kana": "平假名",
          "kanji_romaji": "漢字 / 羅馬拼音（例：勉強 / benkyou）。若無漢字只寫 romaji",
          "meaning": "中文意思",
          "example": "日文例句（平假名為主）",
          "example_zh": "中文翻譯"
        }}
        // 共 10 個
      ],
      "japanese_grammar": [
        {{
          "title": "文法名稱",
          "structure": "結構公式，例如「名詞 + を + 動詞(ます)」",
          "rule": "白話說明（20-40 字）",
          "examples": [
            "日文例句 1（中文翻譯）",
            "日文例句 2（中文翻譯）"
          ]
        }}
        // 共 2 個
      ]
    }}

    要求：
    - 英文單字混和技術/日常，難度 TOEIC 600-800 之間
    - 日文單字全部 N5 範圍，含常用漢字
    - 例句要自然、有場景感，避免教科書語氣
    - 主題每天換一種（職場、家庭、旅行、美食、科技、運動...）
""").strip()


REVIEW_PROMPT = textwrap.dedent("""
    你是今早教課的英日文老師，現在要做睡前快速複習（不出新內容）。
    以下是今天早上的課程 JSON：

    {lesson_json}

    請根據這份內容，設計睡前複習題，輸出以下 JSON 結構（**只輸出 JSON**）：

    {{
      "english_words_quiz": "用『中文 → 英文？』的格式列出 10 個單字，讓使用者先回想再看答案。格式：『1. 中文（詞性） → 英文單字』，每個一行",
      "english_grammar_quiz": "兩個文法點各出 1 題英文造句填空，附解答",
      "japanese_words_quiz": "用『中文 → 日文？』的格式列出 10 個單字，每個一行，附平假名答案",
      "japanese_grammar_quiz": "兩個文法點各出 1 題，讓使用者填空或翻譯，附解答"
    }}

    要求：
    - 使用清楚的表情符號輔助排版（例：✅ ❓）
    - 答案可以用『【答】...』格式標示，讓使用者可以先想再看
    - 全部用繁體中文說明
""").strip()


# --- Formatters ---------------------------------------------------------------
def format_morning_messages(lesson: dict, date: str, weekday: str) -> list[str]:
    """合併成 1 則長訊息（節省 LINE 推播額度）"""
    w = lesson["english_words"]
    eg = lesson["english_grammar"]
    jw = lesson["japanese_words"]
    jg = lesson["japanese_grammar"]

    lines = [f"🌅 {date[5:]}（{weekday}）英日文早課", ""]

    # 英文單字
    lines.append("━━━ 🇬🇧 英文單字 ━━━")
    for i, e in enumerate(w, 1):
        lines.append(f"{i}. {e['word']} ({e['pos']}) {e['meaning']}")
        lines.append(f"   {e['example']}")
        lines.append(f"   → {e['example_zh']}")
    lines.append("")

    # 英文文法
    lines.append("━━━ 📘 英文文法 ━━━")
    for i, g in enumerate(eg, 1):
        lines.append(f"【{i}】{g['title']}")
        lines.append(g["rule"])
        for ex in g["examples"]:
            lines.append(f"• {ex}")
        lines.append("")

    # 日文單字
    lines.append("━━━ 🇯🇵 日文單字（N5）━━━")
    for i, j in enumerate(jw, 1):
        lines.append(f"{i}. {j['kana']} / {j['kanji_romaji']}  {j['meaning']}")
        lines.append(f"   {j['example']}")
        lines.append(f"   → {j['example_zh']}")
    lines.append("")

    # 日文文法
    lines.append("━━━ 🗾 日文文法（N5）━━━")
    for i, g in enumerate(jg, 1):
        lines.append(f"【{i}】{g['title']}")
        lines.append(f"結構：{g['structure']}")
        lines.append(g["rule"])
        for ex in g["examples"]:
            lines.append(f"• {ex}")
        lines.append("")

    lines.append("━━━━━━━━━━━")
    lines.append("📝 晚上 23:00 睡前複習見 💪")
    return ["\n".join(lines).rstrip()]


def format_review_messages(review: dict, date: str) -> list[str]:
    """合併成 1 則長訊息（節省 LINE 推播額度）"""
    lines = [f"🌙 {date[5:]} 睡前複習時間", ""]

    lines.append("━━━ 🇬🇧 英文單字小卡 ━━━")
    lines.append(review["english_words_quiz"])
    lines.append("")

    lines.append("━━━ 📘 英文文法小測 ━━━")
    lines.append(review["english_grammar_quiz"])
    lines.append("")

    lines.append("━━━ 🇯🇵 日文單字小卡 ━━━")
    lines.append(review["japanese_words_quiz"])
    lines.append("")

    lines.append("━━━ 🗾 日文文法小測 ━━━")
    lines.append(review["japanese_grammar_quiz"])
    lines.append("")

    lines.append("━━━━━━━━━━━")
    lines.append("早睡，明天繼續加油！🌟")
    return ["\n".join(lines).rstrip()]


def lesson_to_markdown(lesson: dict, date: str, weekday: str) -> str:
    md = [f"# {date}（週{weekday}）英日文每日課程", ""]
    md.append("## 🇬🇧 英文單字（TOEIC 600-800）")
    for i, e in enumerate(lesson["english_words"], 1):
        md.append(f"{i}. **{e['word']}** ({e['pos']}) — {e['meaning']}")
        md.append(f"   - *{e['example']}*")
        md.append(f"   - {e['example_zh']}")
    md.append("")
    md.append("## 📘 英文文法")
    for g in lesson["english_grammar"]:
        md.append(f"### {g['title']}")
        md.append(g["rule"])
        for ex in g["examples"]:
            md.append(f"- {ex}")
    md.append("")
    md.append("## 🇯🇵 日文單字（N5）")
    for i, j in enumerate(lesson["japanese_words"], 1):
        md.append(f"{i}. **{j['kana']}** / {j['kanji_romaji']} — {j['meaning']}")
        md.append(f"   - {j['example']}")
        md.append(f"   - {j['example_zh']}")
    md.append("")
    md.append("## 🗾 日文文法（N5）")
    for g in lesson["japanese_grammar"]:
        md.append(f"### {g['title']}")
        md.append(f"**結構**：{g['structure']}")
        md.append(g["rule"])
        for ex in g["examples"]:
            md.append(f"- {ex}")
    md.append("")
    return "\n".join(md)


# --- Commands -----------------------------------------------------------------
def _parse_json_or_die(raw: str, context: str) -> dict:
    """Parse JSON, stripping markdown fences; print raw on failure for debugging."""
    text = raw.strip()
    if text.startswith("```"):
        # Strip ```json ... ``` fences
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析失敗 ({context}): {e}", file=sys.stderr)
        print(f"--- Raw response (first 1000 chars) ---", file=sys.stderr)
        print(raw[:1000], file=sys.stderr)
        print(f"--- Raw response (last 500 chars) ---", file=sys.stderr)
        print(raw[-500:], file=sys.stderr)
        sys.exit(1)


def cmd_morning() -> None:
    date = today_taipei()
    weekday = weekday_zh(date)
    prompt = MORNING_PROMPT.format(date=date, weekday=weekday)
    raw = gemini_generate(prompt)
    lesson = _parse_json_or_die(raw, "morning")

    # Save lesson as JSON (for review to read later) and Markdown (for humans)
    (LESSONS_DIR / f"{date}.json").write_text(json.dumps(lesson, ensure_ascii=False, indent=2), encoding="utf-8")
    (LESSONS_DIR / f"{date}.md").write_text(lesson_to_markdown(lesson, date, weekday), encoding="utf-8")

    messages = format_morning_messages(lesson, date, weekday)
    for m in messages:
        line_push(m)
    print(f"✅ Morning lesson for {date} pushed ({len(messages)} messages).")


def cmd_review() -> None:
    date = today_taipei()
    lesson_path = LESSONS_DIR / f"{date}.json"
    if not lesson_path.exists():
        sys.exit(f"❌ 找不到 {lesson_path}，今日早課沒跑成功？")
    lesson_json = lesson_path.read_text(encoding="utf-8")
    prompt = REVIEW_PROMPT.format(lesson_json=lesson_json)
    raw = gemini_generate(prompt)
    review = _parse_json_or_die(raw, "review")

    messages = format_review_messages(review, date)
    for m in messages:
        line_push(m)
    print(f"✅ Evening review for {date} pushed ({len(messages)} messages).")


# --- Entry --------------------------------------------------------------------
def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in {"morning", "review"}:
        sys.exit("用法：python coach.py [morning|review]")
    cmd = sys.argv[1]
    if cmd == "morning":
        cmd_morning()
    else:
        cmd_review()


if __name__ == "__main__":
    main()
