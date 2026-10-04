#!/usr/bin/env python3
"""Stop: 検証が通るまで終了させない。ただし差し戻しは max_stop_retries 回まで。

ループの安全装置:
- stop_hook_active=false（新しい停止）で回数をリセットする
- 上限に達したら止めてよいことにし、ユーザーに失敗を報告させる

検証が通ったあと、このセッションでファイルを変えたのに進捗ファイルが未更新なら、1回だけ更新を促す。
"""

import sys
from pathlib import Path

sys.dont_write_bytecode = True  # 利用者のリポジトリに __pycache__ を残さない
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _harness as h  # noqa: E402


def progress_reminder(cfg, session):
    """進捗ファイルの更新を促す文を返す。不要なら空文字。セッションにつき1回だけ。"""
    if not cfg.get("remind_progress", True):
        return ""
    done = h.state_file(f"reminded-{session}")
    if done.exists():
        return ""
    start = h.state_file(f"start-{session}")
    changed = h.changed_files(start.read_text().strip() if start.exists() else "")
    progress = cfg["progress_file"]
    if not changed or progress in changed:
        return ""
    done.write_text("1")
    shown = ", ".join(sorted(changed)[:5]) + (" ほか" if len(changed) > 5 else "")
    return (f"このセッションでファイルを変更した（{shown}）が、{progress} が未更新。"
            f"次のセッションが続きから始められるよう、{progress} の「進行中／次にやること／完了」を更新してから終える"
            f"（/handoff で一括実行できる）。更新が不要な軽微な変更なら、そのまま終えてよい。")


def main():
    event = h.read_event()
    cfg = h.load_config()
    if h.disabled_reason():
        return 0
    session = event.get("session_id", "default")
    counter = h.state_file(f"stop-{session}.count")

    if not event.get("stop_hook_active"):
        counter.unlink(missing_ok=True)

    ok, out = h.run_check(cfg)
    if ok:
        counter.unlink(missing_ok=True)
        reminder = progress_reminder(cfg, session)
        if reminder:
            h.emit({"decision": "block", "reason": reminder})
        return 0

    count = int(counter.read_text() or 0) + 1 if counter.exists() else 1
    limit = int(cfg.get("max_stop_retries", 3))
    if count > limit:
        counter.unlink(missing_ok=True)
        h.emit({"systemMessage": f"harness: 検証が {limit} 回の差し戻し後も失敗している。ループを止めた。"})
        return 0

    counter.write_text(str(count))
    h.emit({"decision": "block",
            "reason": (f"完了条件 `{cfg['check']}` が未達（差し戻し {count}/{limit} 回目）。"
                       f"原因を直して再検証すること。直せない場合は理由をユーザーに報告して終える。\n{out}")})
    return 0


if __name__ == "__main__":
    sys.exit(main())
