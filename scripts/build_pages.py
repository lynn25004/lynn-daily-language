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

<p><a href="./quiz.html" style="display:inline-block;background:var(--primary);color:var(--bg);padding:10px 22px;border-radius:8px;font-weight:600;text-decoration:none;">📝 開始單字測驗</a></p>

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

    # 測驗頁
    build_quiz(lessons)

    print(f"✅ 生成 {len(lessons) + 2} 個 HTML 檔案到 site/（含 index 與 quiz）")


def build_quiz(lessons):
    """從所有 lessons/*.json 聚合單字，產生 site/quiz.html 4 選 1 測驗。"""
    en_words = []
    jp_words = []
    for p in lessons:
        date = p.stem
        json_path = LESSONS_DIR / f"{date}.json"
        if not json_path.exists():
            continue
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        for w in data.get("english_words", []):
            if w.get("word") and w.get("meaning"):
                en_words.append({
                    "id": f"en:{date}:{w['word']}",
                    "date": date,
                    "word": w["word"],
                    "pos": w.get("pos", ""),
                    "meaning": w["meaning"],
                })
        for w in data.get("japanese_words", []):
            if w.get("kana") and w.get("meaning"):
                jp_words.append({
                    "id": f"jp:{date}:{w['kana']}",
                    "date": date,
                    "kana": w["kana"],
                    "kanji_romaji": w.get("kanji_romaji", ""),
                    "meaning": w["meaning"],
                })

    quiz_html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>單字測驗 | lynn-daily-language</title>
<meta name="description" content="從每日學習單字隨機抽 4 選 1 測驗，掌握度記憶在你的瀏覽器。">
{THEME_META}
{FAVICON_LINK}
{EARLY_THEME}
<style>{BASE_CSS}
.quiz-wrap{{max-width:560px;margin:0 auto;}}
.quiz-card{{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:22px 18px;box-shadow:var(--shadow);}}
.quiz-q{{font-size:32px;font-weight:700;text-align:center;margin:10px 0 4px;}}
.quiz-sub{{text-align:center;font-size:13px;color:var(--muted);margin-bottom:18px;}}
.quiz-opts{{display:grid;gap:8px;}}
.quiz-opt{{background:var(--card);border:1.5px solid var(--border);color:var(--text);padding:11px 14px;border-radius:10px;font:inherit;font-size:14px;cursor:pointer;text-align:left;transition:all .15s;}}
.quiz-opt:hover:not(:disabled){{border-color:var(--primary);}}
.quiz-opt.correct{{background:rgba(34,197,94,.15);border-color:#22c55e;color:#16a34a;font-weight:600;}}
.quiz-opt.wrong{{background:rgba(239,68,68,.12);border-color:#ef4444;color:#dc2626;}}
.quiz-opt:disabled{{cursor:default;}}
.quiz-bar{{height:6px;background:var(--border);border-radius:3px;overflow:hidden;margin-bottom:18px;}}
.quiz-bar-fill{{height:100%;background:var(--primary);transition:width .3s;}}
.quiz-stats{{display:flex;justify-content:space-between;font-size:12px;color:var(--muted);margin-bottom:8px;}}
.quiz-next{{margin-top:14px;background:var(--primary);color:var(--bg);border:none;padding:10px 20px;border-radius:8px;font:inherit;font-size:14px;font-weight:600;cursor:pointer;width:100%;}}
.quiz-mode{{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:14px;}}
.quiz-mode button{{background:transparent;border:1px solid var(--border);color:var(--muted);padding:6px 14px;border-radius:999px;cursor:pointer;font:inherit;font-size:12px;}}
.quiz-mode button.on{{background:var(--primary);color:var(--bg);border-color:var(--primary);font-weight:600;}}
.quiz-final{{text-align:center;padding:14px 0;}}
.quiz-final h2{{font-size:24px;color:var(--text);margin-bottom:8px;}}
.quiz-final .score{{font-size:48px;font-weight:800;color:var(--primary);margin:8px 0;}}
.master{{display:flex;gap:10px;font-size:12px;color:var(--muted);margin:14px 0;flex-wrap:wrap;}}
.master b{{color:var(--text);}}
</style>
</head>
<body>
<nav>
  <a href="./index.html">← 回首頁</a>
  <button id="theme-btn" class="theme-btn" type="button" title="切換主題" aria-label="切換主題">🌙</button>
</nav>

<h1>📝 單字測驗</h1>
<p class="meta">從累積的單字隨機抽 4 選 1。答對 / 答錯紀錄存在你的瀏覽器（localStorage）。</p>

<div id="setup" class="quiz-wrap">
  <div class="master" id="master-stats"></div>
  <div class="quiz-card">
    <div class="quiz-mode" id="mode-chips">
      <button class="on" type="button" data-mode="all">🌐 混合</button>
      <button type="button" data-mode="en">🇬🇧 英文</button>
      <button type="button" data-mode="jp">🇯🇵 日文</button>
    </div>
    <div class="quiz-mode" id="size-chips">
      <button type="button" data-size="10">10 題</button>
      <button class="on" type="button" data-size="20">20 題</button>
      <button type="button" data-size="30">30 題</button>
    </div>
    <button id="start-btn" class="quiz-next" type="button">開始測驗</button>
  </div>
</div>

<div id="quiz" class="quiz-wrap" style="display:none">
  <div class="quiz-stats">
    <span id="q-counter">1 / 10</span>
    <span id="q-score">答對 0</span>
  </div>
  <div class="quiz-bar"><div id="q-bar" class="quiz-bar-fill" style="width:0%"></div></div>
  <div class="quiz-card">
    <div id="q-tag" class="quiz-sub"></div>
    <div id="q-word" class="quiz-q"></div>
    <div id="q-extra" class="quiz-sub"></div>
    <div id="q-opts" class="quiz-opts"></div>
    <button id="q-next" class="quiz-next" type="button" style="display:none">下一題</button>
  </div>
</div>

<div id="final" class="quiz-wrap" style="display:none">
  <div class="quiz-card quiz-final">
    <h2 id="final-title">🎉 完成！</h2>
    <div class="score"><span id="final-score">0</span> / <span id="final-total">0</span></div>
    <div id="final-msg" class="quiz-sub"></div>
    <button id="again-btn" class="quiz-next" type="button">再來一輪</button>
  </div>
</div>

<footer>lynn-daily-language · 測驗 · <a href="https://github.com/lynn25004/lynn-daily-language">GitHub</a></footer>

{THEME_BTN_SCRIPT}
<script>
const EN_WORDS = {json.dumps(en_words, ensure_ascii=False)};
const JP_WORDS = {json.dumps(jp_words, ensure_ascii=False)};
const ALL_WORDS = [...EN_WORDS, ...JP_WORDS];

const MASTERY_KEY = 'ldl-mastery';
function loadMastery(){{ try{{return JSON.parse(localStorage.getItem(MASTERY_KEY)||'{{}}');}}catch{{return {{}};}} }}
function saveMastery(m){{ try{{localStorage.setItem(MASTERY_KEY,JSON.stringify(m));}}catch{{}} }}
function markAnswer(id,ok){{
  const m=loadMastery();
  const e=m[id]||{{right:0,wrong:0}};
  if(ok)e.right++;else e.wrong++;
  e.last=new Date().toISOString();
  m[id]=e;
  saveMastery(m);
}}

function renderMasterStats(){{
  const m=loadMastery();
  const ids=Object.keys(m);
  const mastered=ids.filter(k=>{{const e=m[k];return e.right>=2&&e.right>e.wrong;}}).length;
  const seen=ids.length;
  const total=ALL_WORDS.length;
  document.getElementById('master-stats').innerHTML=
    `📚 已收錄 <b>${{total}}</b> 個單字 · 看過 <b>${{seen}}</b> · 掌握 <b>${{mastered}}</b>` +
    (seen>0?` <a href="#" id="reset-mastery" style="margin-left:auto">重置紀錄</a>`:'');
  const r=document.getElementById('reset-mastery');
  if(r)r.addEventListener('click',e=>{{
    e.preventDefault();
    if(confirm('確定要清掉所有測驗紀錄嗎？')){{
      localStorage.removeItem(MASTERY_KEY);
      renderMasterStats();
    }}
  }});
}}

let mode='all', size=20, queue=[], idx=0, score=0;

function buildQuestion(w){{
  const isEn=!!w.word;
  const correct=w.meaning;
  // 抽 3 個不同 meaning 當干擾項
  const pool=ALL_WORDS.filter(x=>x.id!==w.id&&x.meaning!==correct);
  const wrongs=[];
  while(wrongs.length<3&&pool.length){{
    const i=Math.floor(Math.random()*pool.length);
    const cand=pool.splice(i,1)[0];
    if(!wrongs.find(x=>x.meaning===cand.meaning))wrongs.push(cand);
  }}
  const opts=[correct, ...wrongs.map(x=>x.meaning)];
  // 洗牌
  for(let i=opts.length-1;i>0;i--){{
    const j=Math.floor(Math.random()*(i+1));
    [opts[i],opts[j]]=[opts[j],opts[i]];
  }}
  return {{
    id:w.id,
    tag:isEn?'🇬🇧 ENGLISH':'🇯🇵 JAPANESE',
    word:isEn?w.word:w.kana,
    extra:isEn?w.pos:(w.kanji_romaji||''),
    correct,
    options:opts,
  }};
}}

function pickSource(){{
  let src=ALL_WORDS;
  if(mode==='en')src=EN_WORDS;
  else if(mode==='jp')src=JP_WORDS;
  return src;
}}

function startQuiz(){{
  const src=pickSource();
  if(src.length<4){{alert('單字數太少（< 4）無法出題，請等更多日子的資料');return;}}
  // 隨機抽 size 個（不夠就重複用）
  const shuffled=[...src].sort(()=>Math.random()-0.5);
  queue=shuffled.slice(0,Math.min(size,shuffled.length)).map(buildQuestion);
  idx=0;score=0;
  document.getElementById('setup').style.display='none';
  document.getElementById('final').style.display='none';
  document.getElementById('quiz').style.display='';
  renderQuestion();
}}

function renderQuestion(){{
  const q=queue[idx];
  document.getElementById('q-counter').textContent=`${{idx+1}} / ${{queue.length}}`;
  document.getElementById('q-score').textContent=`答對 ${{score}}`;
  document.getElementById('q-bar').style.width=`${{(idx/queue.length)*100}}%`;
  document.getElementById('q-tag').textContent=q.tag;
  document.getElementById('q-word').textContent=q.word;
  document.getElementById('q-extra').textContent=q.extra||'';
  const opts=document.getElementById('q-opts');
  opts.innerHTML='';
  q.options.forEach(text=>{{
    const b=document.createElement('button');
    b.type='button';
    b.className='quiz-opt';
    b.textContent=text;
    b.addEventListener('click',()=>chooseAnswer(b,text,q));
    opts.appendChild(b);
  }});
  document.getElementById('q-next').style.display='none';
}}

function chooseAnswer(btn,text,q){{
  const opts=document.querySelectorAll('.quiz-opt');
  opts.forEach(o=>o.disabled=true);
  const isCorrect=(text===q.correct);
  if(isCorrect){{
    btn.classList.add('correct');
    score++;
  }}else{{
    btn.classList.add('wrong');
    opts.forEach(o=>{{if(o.textContent===q.correct)o.classList.add('correct');}});
  }}
  markAnswer(q.id,isCorrect);
  document.getElementById('q-score').textContent=`答對 ${{score}}`;
  document.getElementById('q-next').style.display='';
}}

document.getElementById('q-next').addEventListener('click',()=>{{
  idx++;
  if(idx>=queue.length){{
    showFinal();
  }}else{{
    renderQuestion();
  }}
}});

function showFinal(){{
  document.getElementById('quiz').style.display='none';
  document.getElementById('final').style.display='';
  document.getElementById('final-score').textContent=score;
  document.getElementById('final-total').textContent=queue.length;
  const pct=Math.round((score/queue.length)*100);
  let msg;
  if(pct===100)msg='滿分！🎯';
  else if(pct>=80)msg='很穩，繼續保持 💪';
  else if(pct>=60)msg='不錯！再練幾次就掌握了';
  else msg='答錯沒關係，這樣才會記得更牢 📖';
  document.getElementById('final-msg').textContent=msg;
}}

document.getElementById('again-btn').addEventListener('click',()=>{{
  document.getElementById('final').style.display='none';
  document.getElementById('setup').style.display='';
  renderMasterStats();
}});

document.querySelectorAll('#mode-chips button').forEach(b=>{{
  b.addEventListener('click',()=>{{
    document.querySelectorAll('#mode-chips button').forEach(x=>x.classList.remove('on'));
    b.classList.add('on');
    mode=b.dataset.mode;
  }});
}});
document.querySelectorAll('#size-chips button').forEach(b=>{{
  b.addEventListener('click',()=>{{
    document.querySelectorAll('#size-chips button').forEach(x=>x.classList.remove('on'));
    b.classList.add('on');
    size=parseInt(b.dataset.size,10);
  }});
}});
document.getElementById('start-btn').addEventListener('click',startQuiz);

renderMasterStats();
</script>
</body>
</html>"""
    (SITE_DIR / "quiz.html").write_text(quiz_html, encoding="utf-8")


if __name__ == "__main__":
    main()
