#!/usr/bin/env python3
"""Stop: 検証が通るまで終了させない。ただし差し戻しは max_stop_retries 回まで。

ループの安全装置:
- stop_hook_active=false（新しい停止）で回数をリセットする
- 上限に達したら止めてよいことにし、ユーザーに失敗を報告させる
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _harness as h  # noqa: E402


def main():
    event = h.read_event()
    cfg = h.load_config()
    counter = h.state_file(f"stop-{event.get('session_id', 'default')}.count")

    if not event.get("stop_hook_active"):
        counter.unlink(missing_ok=True)

    ok, out = h.run_check(cfg)
    if ok:
        counter.unlink(missing_ok=True)
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
