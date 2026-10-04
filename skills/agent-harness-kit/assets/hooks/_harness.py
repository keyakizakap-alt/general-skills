"""ハーネス用フックの共通処理（標準ライブラリのみ）。

設定は <project>/.claude/harness.json:
    {
      "check": "python3 tools/check.py",   # 完了の定義。終了コード0で合格
      "check_timeout": 120,                # 秒
      "max_stop_retries": 3,               # Stop フックで差し戻す最大回数（無限ループ防止）
      "progress_file": "PROGRESS.md",      # セッション開始時に読ませる外部記憶
      "progress_lines": 40,
      "watch": [".py", ".md", ".json"],    # この拡張子の編集後だけ検証する（空なら全部）
      "remind_progress": true              # 変更があるのに進捗ファイルが未更新なら、終了前に1回だけ促す
    }

一時停止: `/harness off`（この作業コピーだけ）または環境変数 HARNESS_DISABLE=1。
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
    "remind_progress": True,
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


def disabled_reason():
    """無効なら理由を返す。有効なら空文字。"""
    if os.environ.get("HARNESS_DISABLE") == "1":
        return "環境変数 HARNESS_DISABLE=1"
    if (project_dir() / ".claude" / ".harness-state" / "disabled").exists():
        return "/harness off で一時停止中。/harness on で再開"
    return ""


def git(*args):
    try:
        r = subprocess.run(["git", *args], cwd=project_dir(), capture_output=True, text=True, timeout=10)
        return r.stdout.rstrip() if r.returncode == 0 else ""  # 先頭の空白は porcelain の一部
    except (OSError, subprocess.TimeoutExpired):
        return ""


def changed_files(since=""):
    """since（コミット）以降に変わったファイル。コミット済み・未コミット・未追跡を含む。"""
    names = set()
    if since:
        names.update(git("diff", "--name-only", since).splitlines())
    for line in git("status", "--porcelain").splitlines():
        names.add(line[3:].split(" -> ")[-1].strip('"'))
    return {n for n in names if n and not n.startswith(".claude/.harness-state")}


def state_file(name):
    d = project_dir() / ".claude" / ".harness-state"
    d.mkdir(parents=True, exist_ok=True)
    return d / name


def emit(obj):
    print(json.dumps(obj, ensure_ascii=False))
