#!/usr/bin/env python3
"""SessionStart: 進捗ファイル・作業ツリー・検証結果を最初のコンテキストに入れる。

前のセッションの記憶はないので、外部ファイルから「どこまで進んだか」を毎回復元する。
"""

import sys
from pathlib import Path

sys.dont_write_bytecode = True  # 利用者のリポジトリに __pycache__ を残さない
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _harness as h  # noqa: E402


def main():
    event = h.read_event()
    cfg = h.load_config()
    off = h.disabled_reason()
    if off:
        h.emit({"hookSpecificOutput": {"hookEventName": "SessionStart",
                                       "additionalContext": f"harness: 無効（{off}）"}})
        return 0

    # 終了前の「進捗ファイル未更新」判定の基準点として、開始時の HEAD を覚えておく
    head = h.git("rev-parse", "HEAD")
    if head:
        h.state_file(f"start-{event.get('session_id', 'default')}").write_text(head)

    parts = []

    progress = h.project_dir() / cfg["progress_file"]
    if progress.exists():
        lines = progress.read_text(encoding="utf-8").splitlines()
        n = cfg["progress_lines"]
        more = f"\n…（残り {len(lines) - n} 行は {cfg['progress_file']} を読む）" if len(lines) > n else ""
        parts.append(f"## {cfg['progress_file']}（先頭 {n} 行）\n" + "\n".join(lines[:n]) + more)

    status = h.git("status", "--short", "--branch")
    if status:
        parts.append("## git status\n" + status)

    if cfg.get("check"):
        ok, out = h.run_check(cfg)
        parts.append(f"## 検証 `{cfg['check']}`: " + ("合格" if ok else "失敗\n" + out))

    parts.append("日々の操作: `/next` で次の作業を1つ進める / `/harness` で状態確認・一時停止 / `/handoff` で引き継ぎ")
    if parts:
        h.emit({"hookSpecificOutput": {"hookEventName": "SessionStart",
                                       "additionalContext": "\n\n".join(parts)}})
    return 0


if __name__ == "__main__":
    sys.exit(main())
