#!/usr/bin/env python3
"""任意のリポジトリにエージェント用ハーネスを入れる（標準ライブラリのみ）。

    python3 install.py --target <repo> --check "make check" --dry-run   # 何が起きるかだけ表示
    python3 install.py --target <repo> --check "make check"             # 実行
    python3 install.py --target <repo> --check "npm test" --ci          # GitHub Actions も追加

方針（安全側に倒す）:
- 既存ファイルは上書きしない。既にあるものは SKIP と表示するだけ
- 例外は .claude/hooks/*.py（キットの管理物）と .claude/settings.json（既存設定にフックと権限を追記マージ）
- 既存の settings.json が壊れている場合は触らずに中断する
"""

import argparse
import datetime
import json
import shutil
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
HOOKS = KIT / "assets" / "hooks"
TPL = KIT / "assets" / "templates"


class Plan:
    def __init__(self, dry):
        self.dry = dry
        self.failed = False

    def log(self, tag, path, note=""):
        print(f"{tag:<6} {path}" + (f"  ({note})" if note else ""))

    def write(self, dest, text, overwrite=False):
        if dest.exists() and not overwrite:
            self.log("SKIP", dest, "既存")
            return
        self.log("UPDATE" if dest.exists() else "CREATE", dest)
        if not self.dry:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(text, encoding="utf-8")

    def copy(self, src, dest):
        if dest.exists() and dest.read_bytes() == src.read_bytes():
            self.log("OK", dest, "最新")
            return
        self.log("UPDATE" if dest.exists() else "CREATE", dest)
        if not self.dry:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)


def merge_settings(existing, kit):
    """kit のフックと権限を existing に追記する。同じ command は二重に足さない。"""
    out = json.loads(json.dumps(existing))
    out.setdefault("$schema", kit.get("$schema"))
    for event, groups in kit.get("hooks", {}).items():
        cur = out.setdefault("hooks", {}).setdefault(event, [])
        have = {hk.get("command") for g in cur for hk in g.get("hooks", [])}
        for g in groups:
            if not any(hk.get("command") in have for hk in g.get("hooks", [])):
                cur.append(g)
    for key in ("allow", "deny"):
        cur = out.setdefault("permissions", {}).setdefault(key, [])
        cur.extend(r for r in kit.get("permissions", {}).get(key, []) if r not in cur)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target", required=True, help="導入先リポジトリのルート")
    ap.add_argument("--check", required=True, help='完了の定義となる検証コマンド（例: "make check"）')
    ap.add_argument("--ci", action="store_true", help=".github/workflows/check.yml も作る")
    ap.add_argument("--dry-run", action="store_true", help="書き込まずに予定だけ表示する")
    a = ap.parse_args()

    root = Path(a.target).resolve()
    if not root.is_dir():
        print(f"NG  導入先がない: {root}")
        return 1
    p = Plan(a.dry_run)
    sub = lambda s: s.replace("{{CHECK}}", a.check)  # noqa: E731
    today = datetime.date.today().isoformat()

    # 0. 既存の settings.json が壊れていたら、何も書かずに中断する
    settings = root / ".claude" / "settings.json"
    existing = None
    if settings.exists():
        try:
            existing = json.loads(settings.read_text(encoding="utf-8"))
        except ValueError as e:
            print(f"NG  {settings} がJSONとして壊れている（{e}）。手で直してから再実行する。")
            return 1

    # 1. フック本体（キットの管理物なので最新に揃える）
    for src in sorted(HOOKS.glob("*.py")):
        p.copy(src, root / ".claude" / "hooks" / src.name)

    # 2. フック設定（既存設定へ追記マージ）
    kit_settings = json.loads((TPL / "settings.json").read_text(encoding="utf-8"))
    if existing is not None:
        merged = merge_settings(existing, kit_settings)
        if merged == existing:
            p.log("OK", settings, "追記不要")
        else:
            p.write(settings, json.dumps(merged, ensure_ascii=False, indent=2) + "\n", overwrite=True)
    else:
        p.write(settings, (TPL / "settings.json").read_text(encoding="utf-8"))

    # 3. ハーネス設定・指示書・外部記憶（既存は上書きしない）
    harness = json.loads((TPL / "harness.json").read_text(encoding="utf-8"))
    harness["check"] = a.check
    p.write(root / ".claude" / "harness.json", json.dumps(harness, ensure_ascii=False, indent=2) + "\n")
    p.write(root / "AGENTS.md", sub((TPL / "AGENTS.md").read_text(encoding="utf-8")))
    p.write(root / "CLAUDE.md", (TPL / "CLAUDE.md").read_text(encoding="utf-8"))
    p.write(root / "PROGRESS.md", (TPL / "PROGRESS.md").read_text(encoding="utf-8").replace("YYYY-MM-DD", today))
    p.write(root / ".claude" / "agents" / "reviewer.md", (TPL / "agents" / "reviewer.md").read_text(encoding="utf-8"))
    p.write(root / ".claude" / "commands" / "handoff.md", (TPL / "commands" / "handoff.md").read_text(encoding="utf-8"))
    if a.ci:
        p.write(root / ".github" / "workflows" / "check.yml", sub((TPL / "check.yml").read_text(encoding="utf-8")))

    # 4. 状態ファイルは共有しない
    gi = root / ".gitignore"
    line = ".claude/.harness-state/"
    text = gi.read_text(encoding="utf-8") if gi.exists() else ""
    if line in text.splitlines():
        p.log("OK", gi, "追記不要")
    else:
        p.write(gi, text + ("" if not text or text.endswith("\n") else "\n") + line + "\n", overwrite=True)

    print("\n(dry-run: 何も書き込んでいない)" if a.dry_run else
          "\n完了。AGENTS.md の <...> を埋め、`claude` を再起動（または /hooks を開く）するとフックが有効になる。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
