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
import random
import sys
import textwrap
import time
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
LINE_MULTICAST_URL = "https://api.line.me/v2/bot/message/multicast"


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
def gemini_generate(prompt: str, *, json_mode: bool = True, max_retries: int = 3) -> str:
    """Call Gemini generateContent with retry on 5xx / network errors."""
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

    last_err = None
    for attempt in range(1, max_retries + 1):
        req = request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=60) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            break
        except error.HTTPError as e:
            err_body = e.read().decode("utf-8", "ignore")
            if 500 <= e.code < 600 and attempt < max_retries:
                wait = 2 ** attempt
                print(f"⚠️  Gemini HTTP {e.code}，{wait}s 後重試（{attempt}/{max_retries}）", file=sys.stderr)
                time.sleep(wait)
                last_err = f"HTTP {e.code}: {err_body}"
                continue
            sys.exit(f"❌ Gemini HTTP {e.code}: {err_body}")
        except (error.URLError, TimeoutError) as e:
            if attempt < max_retries:
                wait = 2 ** attempt
                print(f"⚠️  網路錯誤 ({e})，{wait}s 後重試（{attempt}/{max_retries}）", file=sys.stderr)
                time.sleep(wait)
                last_err = str(e)
                continue
            sys.exit(f"❌ Gemini 網路錯誤（已重試 {max_retries} 次）：{e}")
    else:
        sys.exit(f"❌ Gemini 失敗：{last_err}")

    try:
        return payload["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        sys.exit(f"❌ Gemini 回應格式異常：{json.dumps(payload)[:500]}")


# --- LINE ---------------------------------------------------------------------
def line_push(text: str) -> None:
    token = env("LINE_CHANNEL_ACCESS_TOKEN")
    ids_raw = os.environ.get("LINE_USER_IDS") or os.environ.get("LINE_USER_ID", "")
    user_ids = [u.strip() for u in ids_raw.split(",") if u.strip()]
    if not user_ids:
        sys.exit("❌ 缺少環境變數：LINE_USER_IDS 或 LINE_USER_ID")

    if len(user_ids) == 1:
        url = LINE_PUSH_URL
        payload = {"to": user_ids[0], "messages": [{"type": "text", "text": text}]}
    else:
        url = LINE_MULTICAST_URL
        payload = {"to": user_ids, "messages": [{"type": "text", "text": text}]}

    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=30) as resp:
            resp_body = resp.read().decode("utf-8")
            if resp.status >= 300:
                sys.exit(f"❌ LINE push failed ({resp.status}): {resp_body}")
    except error.HTTPError as e:
        sys.exit(f"❌ LINE HTTP {e.code}: {e.read().decode('utf-8', 'ignore')}")


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
    return _split_for_line("\n".join(lines).rstrip(), limit=4800)


def format_review_messages(review: dict, date: str, *, extras: list[str] | None = None) -> list[str]:
    """合併成 1 則長訊息（節省 LINE 推播額度）。extras 為額外段落（間隔重複 / 週總結）。"""
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

    for extra in extras or []:
        if extra:
            lines.append(extra)
            lines.append("")

    lines.append("━━━━━━━━━━━")
    lines.append("早睡，明天繼續加油！🌟")

    full = "\n".join(lines).rstrip()
    # LINE 單則上限 5000 字元 → 超過就自動切段
    return _split_for_line(full, limit=4800)


def _split_for_line(text: str, limit: int = 4800) -> list[str]:
    """若超過 LINE 單則字元上限就切段（以空行為切分點）。"""
    if len(text) <= limit:
        return [text]
    chunks, buf = [], []
    size = 0
    for para in text.split("\n\n"):
        plen = len(para) + 2
        if size + plen > limit and buf:
            chunks.append("\n\n".join(buf))
            buf, size = [], 0
        buf.append(para)
        size += plen
    if buf:
        chunks.append("\n\n".join(buf))
    return chunks


def load_past_lessons(today: str, days_back: list[int]) -> list[tuple[int, str, dict]]:
    """Load lessons from N days ago. Returns list of (days_ago, date_str, lesson)."""
    today_date = datetime.strptime(today, "%Y-%m-%d").date()
    out = []
    for d in days_back:
        date_str = (today_date - timedelta(days=d)).strftime("%Y-%m-%d")
        p = LESSONS_DIR / f"{date_str}.json"
        if p.exists():
            try:
                out.append((d, date_str, json.loads(p.read_text(encoding="utf-8"))))
            except json.JSONDecodeError:
                continue
    return out


def build_spaced_repetition(today: str) -> str:
    """間隔重複：抓 1/3/7 天前的課，各抽 3 英 + 3 日單字。"""
    past = load_past_lessons(today, [1, 3, 7])
    if not past:
        return ""
    # 用當天日期當 seed，同一天多次執行會抽到一樣的題目
    rng = random.Random(today)
    lines = ["━━━ 🔁 間隔重複（先想答案再看） ━━━"]
    for days_ago, date_str, lesson in past:
        ew_pool = lesson.get("english_words", [])
        jw_pool = lesson.get("japanese_words", [])
        ew = rng.sample(ew_pool, min(3, len(ew_pool)))
        jw = rng.sample(jw_pool, min(3, len(jw_pool)))
        lines.append(f"")
        lines.append(f"📅 {days_ago} 天前（{date_str[5:]}）")
        for e in ew:
            lines.append(f"  🇬🇧 {e['meaning']}（{e['pos']}）→【{e['word']}】")
        for j in jw:
            lines.append(f"  🇯🇵 {j['meaning']} →【{j['kana']}／{j['kanji_romaji']}】")
    return "\n".join(lines)


def build_weekly_summary(today: str) -> str:
    """週六晚課：彙整本週 Mon-Sat 所有單字。"""
    today_date = datetime.strptime(today, "%Y-%m-%d").date()
    # 週一到今天
    monday_offset = today_date.weekday()  # Mon=0, Sat=5
    days = [monday_offset - i for i in range(monday_offset, -1, -1)]
    lessons = []
    for offset in range(monday_offset + 1):
        d = today_date - timedelta(days=monday_offset - offset)
        p = LESSONS_DIR / f"{d.strftime('%Y-%m-%d')}.json"
        if p.exists():
            try:
                lessons.append((d.strftime("%m-%d"), json.loads(p.read_text(encoding="utf-8"))))
            except json.JSONDecodeError:
                continue
    if not lessons:
        return ""
    lines = ["━━━ 📊 本週單字總結 ━━━"]
    en_all, jp_all = [], []
    for date_str, lesson in lessons:
        en_all.extend([(date_str, w) for w in lesson.get("english_words", [])])
        jp_all.extend([(date_str, w) for w in lesson.get("japanese_words", [])])
    lines.append(f"")
    lines.append(f"🇬🇧 本週英文（共 {len(en_all)} 字）")
    for date_str, w in en_all:
        lines.append(f"  {date_str} {w['word']} — {w['meaning']}")
    lines.append(f"")
    lines.append(f"🇯🇵 本週日文（共 {len(jp_all)} 字）")
    for date_str, w in jp_all:
        lines.append(f"  {date_str} {w['kana']} — {w['meaning']}")
    return "\n".join(lines)


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

    extras = [build_spaced_repetition(date)]
    # 週六（weekday=5）加本週總結
    if datetime.strptime(date, "%Y-%m-%d").weekday() == 5:
        extras.append(build_weekly_summary(date))

    messages = format_review_messages(review, date, extras=extras)
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
