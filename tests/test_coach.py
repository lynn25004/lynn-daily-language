"""Unit tests for scripts/coach.py (無網路、無 LINE)。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import coach  # noqa: E402


SAMPLE_LESSON = {
    "english_words": [
        {"word": "deploy", "pos": "v.", "meaning": "部署", "example": "We deploy on Monday.", "example_zh": "我們週一部署。"},
        {"word": "debug", "pos": "v.", "meaning": "除錯", "example": "Let's debug it.", "example_zh": "來除錯吧。"},
        {"word": "sensor", "pos": "n.", "meaning": "感測器", "example": "The sensor failed.", "example_zh": "感測器壞了。"},
    ],
    "english_grammar": [
        {"title": "現在完成式", "rule": "have + p.p. 表經驗", "examples": ["I have tried.（我試過了）"]},
    ],
    "japanese_words": [
        {"kana": "べんきょう", "kanji_romaji": "勉強 / benkyou", "meaning": "學習", "example": "日本語を勉強します。", "example_zh": "我學日文。"},
        {"kana": "せんせい", "kanji_romaji": "先生 / sensei", "meaning": "老師", "example": "先生はやさしいです。", "example_zh": "老師很親切。"},
    ],
    "japanese_grammar": [
        {"title": "は（主題助詞）", "structure": "N は ~", "rule": "標示主題", "examples": ["私は学生です。（我是學生）"]},
    ],
}


def test_parse_json_strips_markdown_fence():
    raw = '```json\n{"a": 1}\n```'
    assert coach._parse_json_or_die(raw, "test") == {"a": 1}


def test_parse_json_plain():
    assert coach._parse_json_or_die('{"b": 2}', "test") == {"b": 2}


def test_parse_json_failure_exits(capsys):
    with pytest.raises(SystemExit):
        coach._parse_json_or_die("not json", "test")


def test_weekday_zh():
    # 2026-04-21 是週二
    assert coach.weekday_zh("2026-04-21") == "二"
    # 2026-04-25 是週六
    assert coach.weekday_zh("2026-04-25") == "六"


def test_format_morning_contains_all_sections():
    msgs = coach.format_morning_messages(SAMPLE_LESSON, "2026-04-21", "二")
    combined = "\n".join(msgs)
    assert "英文單字" in combined
    assert "deploy" in combined
    assert "べんきょう" in combined
    assert "現在完成式" in combined


def test_split_for_line_short_message():
    assert coach._split_for_line("hello", limit=100) == ["hello"]


def test_split_for_line_long_message():
    # 每段 100 字 x 100 段 → 10000 字
    para = "a" * 100
    text = "\n\n".join([para] * 100)
    chunks = coach._split_for_line(text, limit=1000)
    assert len(chunks) > 1
    assert all(len(c) <= 1000 for c in chunks)


def test_load_past_lessons(tmp_path, monkeypatch):
    monkeypatch.setattr(coach, "LESSONS_DIR", tmp_path)
    (tmp_path / "2026-04-20.json").write_text(json.dumps(SAMPLE_LESSON), encoding="utf-8")
    (tmp_path / "2026-04-18.json").write_text(json.dumps(SAMPLE_LESSON), encoding="utf-8")

    result = coach.load_past_lessons("2026-04-21", [1, 3, 7])
    assert len(result) == 2
    assert result[0][0] == 1
    assert result[1][0] == 3


def test_load_past_lessons_missing_ok(tmp_path, monkeypatch):
    monkeypatch.setattr(coach, "LESSONS_DIR", tmp_path)
    assert coach.load_past_lessons("2026-04-21", [1, 3, 7]) == []


def test_build_spaced_repetition_deterministic(tmp_path, monkeypatch):
    monkeypatch.setattr(coach, "LESSONS_DIR", tmp_path)
    (tmp_path / "2026-04-20.json").write_text(json.dumps(SAMPLE_LESSON), encoding="utf-8")

    a = coach.build_spaced_repetition("2026-04-21")
    b = coach.build_spaced_repetition("2026-04-21")
    assert a == b  # 同天 seed 相同
    assert "1 天前" in a
    assert "deploy" in a or "debug" in a or "sensor" in a


def test_build_weekly_summary(tmp_path, monkeypatch):
    monkeypatch.setattr(coach, "LESSONS_DIR", tmp_path)
    # 2026-04-25 = 週六; 週一是 04-20
    for d in ["2026-04-20", "2026-04-21", "2026-04-22", "2026-04-23", "2026-04-24", "2026-04-25"]:
        (tmp_path / f"{d}.json").write_text(json.dumps(SAMPLE_LESSON), encoding="utf-8")

    summary = coach.build_weekly_summary("2026-04-25")
    assert "本週單字總結" in summary
    # 6 天 × 3 英 = 18 字
    assert "共 18 字" in summary
    # 6 天 × 2 日 = 12 字
    assert "共 12 字" in summary


def test_format_review_with_extras():
    review = {
        "english_words_quiz": "q1",
        "english_grammar_quiz": "q2",
        "japanese_words_quiz": "q3",
        "japanese_grammar_quiz": "q4",
    }
    msgs = coach.format_review_messages(review, "2026-04-21", extras=["EXTRA_BLOCK"])
    combined = "\n".join(msgs)
    assert "EXTRA_BLOCK" in combined
    assert "早睡" in combined
