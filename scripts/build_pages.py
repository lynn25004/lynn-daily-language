#!/usr/bin/env python3
"""
把 lessons/*.md 編成可翻閱的靜態網站（GitHub Pages）。
輸出到 site/ 目錄。
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LESSONS_DIR = ROOT / "lessons"
SITE_DIR = ROOT / "site"
SITE_DIR.mkdir(exist_ok=True)


def md_to_html(md: str) -> str:
    """超簡易 Markdown → HTML（只處理 coach.py 產出的格式）。"""
    out = []
    in_list = False
    for line in md.splitlines():
        if line.startswith("# "):
            out.append(f"<h1>{html.escape(line[2:])}</h1>")
        elif line.startswith("## "):
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.startswith("### "):
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<h3>{html.escape(line[4:])}</h3>")
        elif line.startswith("- ") or line.startswith("   - "):
            if not in_list:
                out.append("<ul>")
                in_list = True
            content = line.lstrip(" -")
            out.append(f"<li>{inline_md(content)}</li>")
        elif re.match(r"^\d+\.\s", line):
            if not in_list:
                out.append("<ul>")
                in_list = True
            content = re.sub(r"^\d+\.\s", "", line)
            out.append(f"<li>{inline_md(content)}</li>")
        elif line.strip() == "":
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append("")
        else:
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<p>{inline_md(line)}</p>")
    if in_list:
        out.append("</ul>")
    return "\n".join(out)


def inline_md(text: str) -> str:
    text = html.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
    return text


BASE_CSS = """
* { box-sizing: border-box; }
body {
  font-family: -apple-system, "Noto Sans TC", "PingFang TC", system-ui, sans-serif;
  max-width: 780px; margin: 2rem auto; padding: 0 1rem;
  line-height: 1.7; color: #2c3e50; background: #fafafa;
}
h1 { border-bottom: 3px solid #4a90e2; padding-bottom: .4rem; }
h2 { color: #4a90e2; margin-top: 2rem; border-left: 4px solid #4a90e2; padding-left: .6rem; }
h3 { color: #666; }
ul { padding-left: 1.4rem; }
li { margin: .3rem 0; }
code { background: #eef; padding: 2px 6px; border-radius: 3px; font-size: .95em; }
a { color: #4a90e2; text-decoration: none; }
a:hover { text-decoration: underline; }
.meta { color: #999; font-size: .9rem; margin-bottom: 2rem; }
.lesson-list { list-style: none; padding: 0; }
.lesson-list li {
  background: white; padding: 1rem 1.2rem; margin: .6rem 0;
  border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,.06);
  display: flex; justify-content: space-between; align-items: center;
}
.badge { background: #4a90e2; color: white; padding: 2px 10px; border-radius: 20px; font-size: .8rem; }
footer { margin-top: 3rem; color: #999; font-size: .85rem; text-align: center; }
nav { margin: 1rem 0; }
nav a { margin-right: 1rem; }
"""


def wrap(title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} | lynn-daily-language</title>
<style>{BASE_CSS}</style>
</head>
<body>
<nav><a href="./index.html">← 回首頁</a></nav>
{body}
<footer>
  lynn-daily-language · 每日英日文自學記錄 ·
  <a href="https://github.com/lynn25004/lynn-daily-language">GitHub</a>
</footer>
</body>
</html>"""


def weekday_zh(date_str: str) -> str:
    from datetime import datetime
    wd = datetime.strptime(date_str, "%Y-%m-%d").weekday()
    return ["一", "二", "三", "四", "五", "六", "日"][wd]


def main() -> None:
    lessons = sorted(LESSONS_DIR.glob("*.md"), reverse=True)
    if not lessons:
        print("⚠️  lessons/ 沒有 .md 檔案")

    # 個別課程頁
    for lesson_path in lessons:
        date = lesson_path.stem
        md = lesson_path.read_text(encoding="utf-8")
        body = md_to_html(md)
        out = SITE_DIR / f"{date}.html"
        out.write_text(wrap(f"{date} 每日課程", body), encoding="utf-8")

    # 首頁
    items = []
    for lesson_path in lessons:
        date = lesson_path.stem
        # 嘗試從對應 JSON 抓字數
        json_path = LESSONS_DIR / f"{date}.json"
        word_count = ""
        if json_path.exists():
            try:
                data = json.loads(json_path.read_text(encoding="utf-8"))
                en = len(data.get("english_words", []))
                jp = len(data.get("japanese_words", []))
                word_count = f"{en} 英 + {jp} 日"
            except json.JSONDecodeError:
                pass
        items.append(
            f'<li><a href="./{date}.html">📖 {date}（週{weekday_zh(date)}）</a>'
            f'<span class="badge">{word_count}</span></li>'
        )

    index_body = f"""
<h1>🌏 lynn-daily-language</h1>
<p class="meta">每日自動產生的英日文學習紀錄 · 共 {len(lessons)} 天</p>
<p>每天 09:00 推送英日文單字、文法到 LINE，23:00 睡前複習。所有內容保存於此。</p>

<h2>課程紀錄（由新到舊）</h2>
<ul class="lesson-list">
{chr(10).join(items) if items else '<li>還沒有課程紀錄</li>'}
</ul>

<h2>關於這個專案</h2>
<ul>
  <li>🤖 <strong>AI 生成</strong>：Google Gemini 2.5-flash</li>
  <li>⏰ <strong>自動化</strong>：GitHub Actions cron</li>
  <li>📱 <strong>推播</strong>：LINE Messaging API</li>
  <li>🔁 <strong>間隔重複</strong>：晚課帶 1/3/7 天前的單字</li>
  <li>📊 <strong>週總結</strong>：每週六彙整本週單字</li>
</ul>
<p><a href="https://github.com/lynn25004/lynn-daily-language">→ 查看原始碼</a></p>
"""

    # index 不要有「回首頁」導覽
    index_html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>lynn-daily-language · 每日英日文</title>
<style>{BASE_CSS}</style>
</head>
<body>
{index_body}
<footer>
  lynn-daily-language · 賴皇菘（lynnn）個人學習紀錄 ·
  <a href="https://github.com/lynn25004/lynn-daily-language">GitHub</a>
</footer>
</body>
</html>"""
    (SITE_DIR / "index.html").write_text(index_html, encoding="utf-8")

    print(f"✅ 生成 {len(lessons) + 1} 個 HTML 檔案到 site/")


if __name__ == "__main__":
    main()
