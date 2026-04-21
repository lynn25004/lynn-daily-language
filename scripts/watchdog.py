#!/usr/bin/env python3
"""
Watchdog：檢查今日 morning / review 有沒有跑過。
如果該跑但沒跑，自動補跑 coach.py，並透過 Telegram 告警。

判斷邏輯（以 Asia/Taipei 為準）：
- 週日完全跳過（morning/evening 本來就不跑週日）
- 早課應在 09:00 完成 → 給 30 分鐘 buffer，09:30 後若 lessons/<today>.json 不存在 → 補跑 morning
- 晚課應在 23:00 完成 → 給 30 分鐘 buffer，23:30 後若 lessons/<today>.json 存在
  且 lessons/<today>.reviewed.txt 不存在 → 補跑 review
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib import request, error

TAIPEI = timezone(timedelta(hours=8))
ROOT = Path(__file__).resolve().parent.parent
LESSONS_DIR = ROOT / "lessons"


def telegram_notify(text: str) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print(f"[notify skipped, no telegram env] {text}")
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    body = json.dumps({"chat_id": chat_id, "text": text}).encode("utf-8")
    req = request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with request.urlopen(req, timeout=20) as resp:
            if resp.status >= 300:
                print(f"telegram notify failed: HTTP {resp.status}", file=sys.stderr)
    except (error.HTTPError, error.URLError, TimeoutError) as e:
        print(f"telegram notify error: {e}", file=sys.stderr)


def run_coach(subcmd: str) -> tuple[bool, str]:
    """執行 coach.py morning/review，回傳 (成功?, 輸出尾段)。"""
    try:
        result = subprocess.run(
            ["python", "scripts/coach.py", subcmd],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=300,
        )
        tail = (result.stdout + "\n" + result.stderr)[-600:]
        return result.returncode == 0, tail
    except subprocess.TimeoutExpired:
        return False, "⏱️ 超過 5 分鐘逾時"
    except Exception as e:
        return False, f"subprocess error: {e}"


def main() -> None:
    now = datetime.now(TAIPEI)
    today = now.strftime("%Y-%m-%d")
    weekday = now.weekday()  # Mon=0 ... Sun=6
    hm = now.hour * 60 + now.minute

    if weekday == 6:
        print(f"[{today} {now.strftime('%H:%M')}] 週日不推播，跳過。")
        return

    actions: list[str] = []

    # --- 早課檢查 ---
    morning_expected = hm >= 9 * 60 + 30  # 09:30 以後
    morning_file = LESSONS_DIR / f"{today}.json"
    if morning_expected and not morning_file.exists():
        print(f"⚠️  {today} 早課未完成，補跑中...")
        ok, tail = run_coach("morning")
        if ok:
            actions.append(f"✅ 早課補推成功")
            telegram_notify(
                f"🐕 watchdog 補推\n日期：{today}\n補推項目：早課\n狀態：✅ 成功"
            )
        else:
            actions.append(f"❌ 早課補推失敗")
            telegram_notify(
                f"🚨 watchdog 補推失敗\n日期：{today}\n項目：早課\n\n日誌末段：\n{tail}"
            )
    else:
        print(f"[{today} {now.strftime('%H:%M')}] 早課 OK（file exists={morning_file.exists()}）")

    # --- 晚課檢查 ---
    evening_expected = hm >= 23 * 60 + 30  # 23:30 以後（接近跨日）
    reviewed_file = LESSONS_DIR / f"{today}.reviewed.txt"
    if evening_expected and morning_file.exists() and not reviewed_file.exists():
        print(f"⚠️  {today} 晚課未完成，補跑中...")
        ok, tail = run_coach("review")
        if ok:
            actions.append(f"✅ 晚課補推成功")
            telegram_notify(
                f"🐕 watchdog 補推\n日期：{today}\n補推項目：晚課\n狀態：✅ 成功"
            )
        else:
            actions.append(f"❌ 晚課補推失敗")
            telegram_notify(
                f"🚨 watchdog 補推失敗\n日期：{today}\n項目：晚課\n\n日誌末段：\n{tail}"
            )
    else:
        print(f"[{today} {now.strftime('%H:%M')}] 晚課 OK（reviewed={reviewed_file.exists()}）")

    if not actions:
        print("watchdog: 沒有需要補的項目。")


if __name__ == "__main__":
    main()
