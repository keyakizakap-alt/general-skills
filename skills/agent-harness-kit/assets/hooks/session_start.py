#!/usr/bin/env python3
"""SessionStart: 進捗ファイル・作業ツリー・検証結果を最初のコンテキストに入れる。

前のセッションの記憶はないので、外部ファイルから「どこまで進んだか」を毎回復元する。
"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _harness as h  # noqa: E402


def git_status():
    try:
        r = subprocess.run(["git", "status", "--short", "--branch"], cwd=h.project_dir(),
                           capture_output=True, text=True, timeout=10)
        return r.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""


def main():
    h.read_event()
    cfg = h.load_config()
    parts = []

    progress = h.project_dir() / cfg["progress_file"]
    if progress.exists():
        lines = progress.read_text(encoding="utf-8").splitlines()
        n = cfg["progress_lines"]
        more = f"\n…（残り {len(lines) - n} 行は {cfg['progress_file']} を読む）" if len(lines) > n else ""
        parts.append(f"## {cfg['progress_file']}（先頭 {n} 行）\n" + "\n".join(lines[:n]) + more)

    status = git_status()
    if status:
        parts.append("## git status\n" + status)

    if cfg.get("check"):
        ok, out = h.run_check(cfg)
        parts.append(f"## 検証 `{cfg['check']}`: " + ("合格" if ok else "失敗\n" + out))

    if parts:
        h.emit({"hookSpecificOutput": {"hookEventName": "SessionStart",
                                       "additionalContext": "\n\n".join(parts)}})
    return 0


if __name__ == "__main__":
    sys.exit(main())
