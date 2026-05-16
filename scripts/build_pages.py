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
:root, [data-theme="light"] {
  --bg: #fafafa;
  --card: #ffffff;
  --text: #2c3e50;
  --muted: #999;
  --primary: #4a90e2;
  --code-bg: #eef;
  --border: rgba(0,0,0,.06);
  --shadow: 0 1px 3px rgba(0,0,0,.06);
}
[data-theme="dark"] {
  --bg: #0f172a;
  --card: #1e293b;
  --text: #e2e8f0;
  --muted: #94a3b8;
  --primary: #7dd3fc;
  --code-bg: #25314a;
  --border: rgba(148,163,184,.18);
  --shadow: 0 4px 16px rgba(0,0,0,.35);
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #0f172a;
    --card: #1e293b;
    --text: #e2e8f0;
    --muted: #94a3b8;
    --primary: #7dd3fc;
    --code-bg: #25314a;
    --border: rgba(148,163,184,.18);
    --shadow: 0 4px 16px rgba(0,0,0,.35);
  }
}
* { box-sizing: border-box; }
body {
  font-family: -apple-system, "Noto Sans TC", "PingFang TC", system-ui, sans-serif;
  max-width: 780px; margin: 2rem auto; padding: 0 1rem;
  line-height: 1.7; color: var(--text); background: var(--bg);
  transition: background .2s, color .2s;
}
h1 { border-bottom: 3px solid var(--primary); padding-bottom: .4rem; }
h2 { color: var(--primary); margin-top: 2rem; border-left: 4px solid var(--primary); padding-left: .6rem; }
h3 { color: var(--muted); }
ul { padding-left: 1.4rem; }
li { margin: .3rem 0; }
code { background: var(--code-bg); padding: 2px 6px; border-radius: 3px; font-size: .95em; }
a { color: var(--primary); text-decoration: none; }
a:hover { text-decoration: underline; }
.meta { color: var(--muted); font-size: .9rem; margin-bottom: 2rem; }
.lesson-list { list-style: none; padding: 0; }
.lesson-list li {
  background: var(--card); padding: 1rem 1.2rem; margin: .6rem 0;
  border-radius: 6px; box-shadow: var(--shadow); border: 1px solid var(--border);
  display: flex; justify-content: space-between; align-items: center;
}
.badge { background: var(--primary); color: var(--bg); padding: 2px 10px; border-radius: 20px; font-size: .8rem; font-weight: 600; }
footer { margin-top: 3rem; color: var(--muted); font-size: .85rem; text-align: center; }
nav { margin: 1rem 0; display: flex; align-items: center; gap: 1rem; }
nav a { color: var(--primary); }
.top-bar { display: flex; align-items: center; gap: .6rem; margin: 0 0 1rem; }
.theme-btn {
  margin-left: auto; background: var(--card); border: 1px solid var(--border);
  color: var(--text); width: 34px; height: 34px; border-radius: 50%;
  cursor: pointer; font-size: 15px; transition: transform .2s;
}
.theme-btn:hover { transform: rotate(15deg); }
.search-box {
  width: 100%; padding: 8px 12px; font: inherit;
  background: var(--card); color: var(--text);
  border: 1px solid var(--border); border-radius: 8px; outline: none;
  margin-bottom: .8rem;
}
.search-box:focus { border-color: var(--primary); }
.filter-chips { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 1rem; }
.filter-chip {
  background: transparent; border: 1px solid var(--border); color: var(--muted);
  padding: 4px 12px; border-radius: 999px; font-size: 12px;
  cursor: pointer; font-family: inherit; transition: all .2s;
}
.filter-chip.on { background: var(--primary); color: var(--bg); border-color: var(--primary); font-weight: 600; }
.hidden { display: none !important; }
"""

FAVICON_LINK = '<link rel="icon" type="image/svg+xml" href=\'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="%234a90e2"/><text x="50%25" y="56%25" font-size="34" text-anchor="middle" dominant-baseline="middle" fill="white" font-family="Arial">A</text></svg>\'>'
THEME_META = '<meta name="theme-color" content="#fafafa" media="(prefers-color-scheme: light)"><meta name="theme-color" content="#0f172a" media="(prefers-color-scheme: dark)">'
EARLY_THEME = """<script>(function(){try{var t=localStorage.getItem('ldl-theme');if(t)document.documentElement.dataset.theme=t;}catch(e){}})();</script>"""
THEME_BTN_SCRIPT = """<script>(function(){var b=document.getElementById('theme-btn');if(!b)return;var r=document.documentElement;function sys(){return matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';}function sync(){var t=r.dataset.theme||sys();b.textContent=t==='dark'?'☀️':'🌙';b.setAttribute('aria-label',t==='dark'?'切換淺色':'切換深色');}sync();b.addEventListener('click',function(){var t=(r.dataset.theme||sys())==='dark'?'light':'dark';r.dataset.theme=t;try{localStorage.setItem('ldl-theme',t);}catch(e){}sync();});})();</script>"""


def wrap(title: str, body: str, desc: str = "") -> str:
    desc = desc or "賴皇菘（lynnn）每日英日文自學紀錄，由 Gemini 自動生成，推播到 LINE。"
    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} | lynn-daily-language</title>
<meta name="description" content="{html.escape(desc)}">
<meta property="og:title" content="{html.escape(title)} | lynn-daily-language">
<meta property="og:description" content="{html.escape(desc)}">
{THEME_META}
{FAVICON_LINK}
{EARLY_THEME}
<style>{BASE_CSS}</style>
</head>
<body>
<nav>
  <a href="./index.html">← 回首頁</a>
  <button id="theme-btn" class="theme-btn" type="button" title="切換主題" aria-label="切換主題">🌙</button>
</nav>
{body}
<footer>
  lynn-daily-language · 每日英日文自學記錄 ·
  <a href="https://github.com/lynn25004/lynn-daily-language">GitHub</a>
</footer>
{THEME_BTN_SCRIPT}
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
            f'<li data-date="{date}"><a href="./{date}.html">📖 {date}（週{weekday_zh(date)}）</a>'
            f'<span class="badge">{word_count}</span></li>'
        )

    index_body = f"""
<div class="top-bar">
  <h1 style="border:none;padding:0;margin:0;flex:1">🌏 lynn-daily-language</h1>
  <button id="theme-btn" class="theme-btn" type="button" title="切換主題" aria-label="切換主題">🌙</button>
</div>
<p class="meta">每日自動產生的英日文學習紀錄 · 共 {len(lessons)} 天</p>
<p>每天 09:00 推送英日文單字、文法到 LINE，23:00 睡前複習。所有內容保存於此。</p>

<h2>課程紀錄（由新到舊）</h2>
<input id="lesson-search" class="search-box" type="search" placeholder="🔍 搜尋日期（例：2026-04）" aria-label="搜尋課程">
<div class="filter-chips" id="filter-chips">
  <button class="filter-chip on" type="button" data-range="all">全部</button>
  <button class="filter-chip" type="button" data-range="7">最近 7 天</button>
  <button class="filter-chip" type="button" data-range="30">最近 30 天</button>
</div>
<ul class="lesson-list" id="lesson-list">
{chr(10).join(items) if items else '<li>還沒有課程紀錄</li>'}
</ul>
<p id="empty-msg" class="meta hidden">沒有符合條件的課程。</p>

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

    INDEX_FILTER_SCRIPT = """<script>(function(){
  var list=document.getElementById('lesson-list');
  if(!list)return;
  var items=[].slice.call(list.querySelectorAll('li[data-date]'));
  var search=document.getElementById('lesson-search');
  var chips=document.querySelectorAll('#filter-chips .filter-chip');
  var empty=document.getElementById('empty-msg');
  var state={range:'all',q:''};
  function apply(){
    var today=new Date(); today.setHours(0,0,0,0);
    var cutoff=null;
    if(state.range!=='all'){
      cutoff=new Date(today.getTime()-parseInt(state.range,10)*86400000);
    }
    var shown=0;
    items.forEach(function(li){
      var d=li.getAttribute('data-date');
      var ok=true;
      if(state.q){ok=d.indexOf(state.q)!==-1;}
      if(ok&&cutoff){ok=new Date(d)>=cutoff;}
      li.classList.toggle('hidden',!ok);
      if(ok)shown++;
    });
    empty.classList.toggle('hidden',shown>0);
  }
  if(search)search.addEventListener('input',function(e){state.q=e.target.value.trim();apply();});
  chips.forEach(function(c){c.addEventListener('click',function(){
    chips.forEach(function(x){x.classList.remove('on');});
    c.classList.add('on');
    state.range=c.getAttribute('data-range');
    apply();
  });});
})();</script>"""

    # index 不要有「回首頁」導覽
    index_html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>lynn-daily-language · 每日英日文</title>
<meta name="description" content="賴皇菘（lynnn）每日英日文自學紀錄，Gemini AI 生成 + LINE 推播，共 {len(lessons)} 天記錄。">
<meta property="og:title" content="lynn-daily-language · 每日英日文">
<meta property="og:description" content="賴皇菘的每日英日文自學紀錄，每天 09:00 / 23:00 自動推播。">
{THEME_META}
{FAVICON_LINK}
{EARLY_THEME}
<style>{BASE_CSS}</style>
</head>
<body>
{index_body}
<footer>
  lynn-daily-language · 賴皇菘（lynnn）個人學習紀錄 ·
  <a href="https://github.com/lynn25004/lynn-daily-language">GitHub</a>
</footer>
{THEME_BTN_SCRIPT}
{INDEX_FILTER_SCRIPT}
</body>
</html>"""
    (SITE_DIR / "index.html").write_text(index_html, encoding="utf-8")

    print(f"✅ 生成 {len(lessons) + 1} 個 HTML 檔案到 site/")


if __name__ == "__main__":
    main()
