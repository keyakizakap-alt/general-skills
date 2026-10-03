#!/usr/bin/env python3
"""PostToolUse (Edit|Write): 編集直後に検証し、失敗ならその場でモデルに差し戻す。

最後にまとめて直すより、壊した直後に気づかせるほうが修正が小さく済む。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _harness as h  # noqa: E402


def main():
    event = h.read_event()
    cfg = h.load_config()
    path = (event.get("tool_input") or {}).get("file_path", "")

    watch = cfg.get("watch") or []
    if path and watch and not any(path.endswith(ext) for ext in watch):
        return 0

    ok, out = h.run_check(cfg)
    if not ok:
        h.emit({"decision": "block",
                "reason": f"編集後の検証 `{cfg['check']}` が失敗した。次に進む前に直すこと。\n{out}"})
    return 0


if __name__ == "__main__":
    sys.exit(main())
