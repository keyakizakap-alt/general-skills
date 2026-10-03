"""ハーネス用フックの共通処理（標準ライブラリのみ）。

設定は <project>/.claude/harness.json:
    {
      "check": "python3 tools/check.py",   # 完了の定義。終了コード0で合格
      "check_timeout": 120,                # 秒
      "max_stop_retries": 3,               # Stop フックで差し戻す最大回数（無限ループ防止）
      "progress_file": "PROGRESS.md",      # セッション開始時に読ませる外部記憶
      "progress_lines": 40,
      "watch": [".py", ".md", ".json"]     # この拡張子の編集後だけ検証する（空なら全部）
    }
"""

import json
import os
import subprocess
import sys
from pathlib import Path

DEFAULTS = {
    "check": "",
    "check_timeout": 120,
    "max_stop_retries": 3,
    "progress_file": "PROGRESS.md",
    "progress_lines": 40,
    "watch": [],
}
OUTPUT_TAIL = 60  # 失敗時にモデルへ返す行数。長いログでコンテキストを汚さない


def project_dir():
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()


def load_config():
    cfg = dict(DEFAULTS)
    path = project_dir() / ".claude" / "harness.json"
    try:
        cfg.update(json.loads(path.read_text(encoding="utf-8")))
    except FileNotFoundError:
        pass
    except (OSError, ValueError) as e:
        print(f"harness: {path} を読めない: {e}", file=sys.stderr)
    return cfg


def read_event():
    try:
        return json.load(sys.stdin)
    except (ValueError, OSError):
        return {}


def run_check(cfg):
    """(passed, 出力の末尾) を返す。check 未設定なら合格扱い。"""
    cmd = cfg.get("check")
    if not cmd:
        return True, ""
    try:
        r = subprocess.run(cmd, shell=True, cwd=project_dir(), capture_output=True,
                           text=True, timeout=cfg.get("check_timeout", 120))
    except subprocess.TimeoutExpired:
        return False, f"`{cmd}` がタイムアウトした"
    lines = (r.stdout + r.stderr).strip().splitlines()
    return r.returncode == 0, "\n".join(lines[-OUTPUT_TAIL:])


def state_file(name):
    d = project_dir() / ".claude" / ".harness-state"
    d.mkdir(parents=True, exist_ok=True)
    return d / name


def emit(obj):
    print(json.dumps(obj, ensure_ascii=False))
