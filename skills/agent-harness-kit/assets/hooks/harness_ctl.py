#!/usr/bin/env python3
"""ハーネスの操作をまとめた入口。Claude Code では /harness から、それ以外ではターミナルから使う。

    python3 .claude/hooks/harness_ctl.py            # = status
    python3 .claude/hooks/harness_ctl.py status     # 状態（有効/無効・検証結果・次にやること・フック登録）
    python3 .claude/hooks/harness_ctl.py off        # この作業コピーだけ一時停止（コミットされない）
    python3 .claude/hooks/harness_ctl.py on         # 再開
    python3 .claude/hooks/harness_ctl.py update     # ハーネスを最新版に更新（既存の設定・文書は上書きしない）
"""

import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # 利用者のリポジトリに __pycache__ を残さない
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _harness as h  # noqa: E402

REMOTE = "https://raw.githubusercontent.com/keyakizakap-alt/general-skills/main/tools/install-harness.sh"
HOOK_FILES = ("session_start.py", "post_edit.py", "stop_gate.py")


def section(text, title):
    """Markdown の `## title` 節の箇条書きを返す。"""
    m = re.search(rf"^##\s*{re.escape(title)}\s*$(.*?)(?=^##\s|\Z)", text, re.M | re.S)
    if not m:
        return []
    return [ln.strip()[2:] for ln in m.group(1).splitlines() if ln.strip().startswith("- ")]


def registered_hooks():
    try:
        settings = json.loads((h.project_dir() / ".claude" / "settings.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    cmds = " ".join(hk.get("command", "") for groups in settings.get("hooks", {}).values()
                    for g in groups for hk in g.get("hooks", []))
    return {f for f in HOOK_FILES if f in cmds}


def status():
    cfg = h.load_config()
    off = h.disabled_reason()
    print(f"ハーネス: {'無効（' + off + '）' if off else '有効'}")

    missing = set(HOOK_FILES) - registered_hooks()
    print("フック登録: " + ("OK（開始時・編集後・終了前）" if not missing else
                         f"不足 {sorted(missing)}。`update` で入れ直す"))

    if cfg.get("check"):
        ok, out = h.run_check(cfg)
        print(f"検証 `{cfg['check']}`: {'合格' if ok else '失敗'}")
        if not ok:
            print("\n".join("  " + ln for ln in out.splitlines()[-15:]))
    else:
        print("検証コマンド: 未設定（.claude/harness.json の \"check\" に書く）")

    progress = h.project_dir() / cfg["progress_file"]
    if progress.exists():
        text = progress.read_text(encoding="utf-8")
        for title in ("進行中", "次にやること"):
            items = [i for i in section(text, title) if i not in ("（なし）", "(なし)")]
            print(f"{title}: " + ("なし" if not items else ""))
            for i in items[:3]:
                print(f"  - {i}")
    else:
        print(f"{cfg['progress_file']}: なし")

    branch = h.git("rev-parse", "--abbrev-ref", "HEAD")
    dirty = len(h.git("status", "--porcelain").splitlines())
    if branch:
        print(f"git: {branch}（未コミット {dirty} 件）")
    return 0


def set_enabled(enabled):
    flag = h.project_dir() / ".claude" / ".harness-state" / "disabled"
    if enabled:
        flag.unlink(missing_ok=True)
        print("ハーネスを再開した。")
    else:
        flag.parent.mkdir(parents=True, exist_ok=True)
        flag.write_text("1")
        print("ハーネスを一時停止した（この作業コピーだけ。コミットされない）。`on` で再開する。")
    return 0


def update():
    cfg = h.load_config()
    args = ["--check", cfg["check"]] if cfg.get("check") else []
    local = h.project_dir() / "skills" / "agent-harness-kit" / "scripts" / "install.py"
    if local.exists():  # キット本体を持つリポジトリ（general-skills 自身）
        cmd = [sys.executable, str(local), "--target", str(h.project_dir()), *args]
        return subprocess.call(cmd, cwd=h.project_dir())
    quoted = " ".join(shlex.quote(a) for a in args)
    script = f"curl -fsSL {REMOTE} | sh -s -- {quoted}"
    print(f"実行: {script}")
    return subprocess.call(script, shell=True, cwd=h.project_dir(), env=os.environ)


def main():
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").lower()
    actions = {"status": status, "on": lambda: set_enabled(True), "off": lambda: set_enabled(False),
               "update": update}
    if cmd not in actions:
        print(__doc__)
        return 2
    return actions[cmd]()


if __name__ == "__main__":
    sys.exit(main())
