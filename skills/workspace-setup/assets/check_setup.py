#!/usr/bin/env python3
"""エージェント用設定（CLAUDE.md / AGENTS.md / .claude/）の構造検査。どのプロジェクトにも置ける汎用版。

    python3 .claude/hooks/check_setup.py            # 手動実行: 結果を表示し、エラーがあれば終了コード1
    python3 .claude/hooks/check_setup.py --hook     # Stop hook: stdin のJSONを読み、エラーがあれば decision: block

プロジェクト固有の検査対象は、同じフォルダの check_setup.json に書く（無ければ既定値）。
対象は決まったパスと .claude/ 直下の浅い階層だけ。再帰走査、ネット接続、ファイル変更はしない。
秘密を含み得るファイル（settings.local.json）は構文の可否だけを見て、中身は出力しない。
YAML frontmatter は簡易パーサーで必須キーだけを見る（完全なYAML検証ではない）。

Stop hook の仕様（https://code.claude.com/docs/en/hooks, 参照日 2026-10-05）:
- stdin の stop_hook_active が true なら、すでに hook による継続中なので再ブロックしない
- 終了コード0で {"decision": "block", "reason": ...} を出すと停止を止め、reason を Claude に返す
- 0と2以外の終了コードは非ブロッキングのエラー（停止は続行する）
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

DEFAULT_CONFIG = {
    "required_files": [],          # 追加で必須にするファイル
    "json_files": [".mcp.json"],   # 存在すれば構文を検査するJSON
    "json_globs": [],              # 例: "mods/*/hooks/hooks.json"（浅いglobのみ）
    "manual_skills": [],           # disable-model-invocation: true 必須・allowed-tools 禁止のスキル名
    "readonly_agents": [],         # tools を Read/Grep/Glob に限るエージェント（空なら名前に review を含むもの）
    "gitignore_lines": ["CLAUDE.local.md", ".claude/settings.local.json"],
    "agents_md_max_lines": 100,
}
ENTRIES = [".claude/CLAUDE.md", "CLAUDE.md"]  # どちらか一方を入口にする
SECRET_JSON = [".claude/settings.local.json"]
READONLY_TOOLS = {"Read", "Grep", "Glob"}
HOOK_SCRIPT = "check_setup.py"
MAX_IMPORT_HOPS = 4  # 公式: 再帰importは最大4ホップ
BROAD_BASH = {"Bash", "Bash(*)", "Bash(* *)", "Bash(**)"}


class Report:
    def __init__(self):
        self.errors, self.warnings = [], []

    def error(self, msg):
        self.errors.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)


# ---------- 補助 ----------

def read_text(path):
    return path.read_text(encoding="utf-8")


def load_config(root, r):
    cfg = dict(DEFAULT_CONFIG)
    p = root / ".claude/hooks/check_setup.json"
    if p.is_file():
        try:
            cfg.update(json.loads(read_text(p)))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            r.error(f"check_setup.json を読めない: {e}")
    return cfg


def frontmatter(text):
    """先頭の --- ... --- を簡易解析する。key: value と、続く '- 値' のリストだけを扱う。"""
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end == -1:
        return None
    out, key = {}, None
    for line in text[4:end].splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
        if m:
            key = m.group(1)
            val = m.group(2).strip()
            out[key] = val if val else []
            continue
        m = re.match(r"^\s+-\s+(.*)$", line)
        if m and key is not None and isinstance(out.get(key), list):
            out[key].append(m.group(1).strip().strip("\"'"))
    return out


def strip_code(text):
    """フェンスコードブロックとインラインコードを除く（公式: import 解析はこれらを無視する）。"""
    lines, in_fence = [], False
    for line in text.splitlines():
        if re.match(r"^\s*(```|~~~)", line):
            in_fence = not in_fence
            lines.append("")
            continue
        lines.append("" if in_fence else re.sub(r"`[^`]*`", "", line))
    return lines


IMPORT_RE = re.compile(r"(?:^|\s)@((?:\\ |[^\s`、。，（）「」])+)")  # 日本語の句読点はパスに含めない


def find_imports(text):
    found = []
    for line in strip_code(text):
        for m in IMPORT_RE.finditer(line):
            raw = m.group(1).replace("\\ ", " ").rstrip(".,;:)")
            if "/" in raw or "." in raw:  # メンション等を避け、ファイルらしいものだけ拾う
                found.append(raw)
    return found


def entry_file(root):
    present = [e for e in ENTRIES if (root / e).is_file()]
    return (root / present[0]) if present else None, present


# ---------- 検査 ----------

def check_required(root, cfg, r):
    entry, present = entry_file(root)
    if not present:
        r.error("入口の CLAUDE.md がない（.claude/CLAUDE.md か CLAUDE.md）")
    elif len(present) > 1:
        r.warn("CLAUDE.md と .claude/CLAUDE.md が両方ある（入口が2つ）")
    for rel in ["AGENTS.md", ".claude/settings.json", *cfg["required_files"]]:
        p = root / rel
        if p.is_symlink():
            r.error(f"{rel} がシンボリックリンク（管理対象は実ファイルにする）")
        elif not p.is_file():
            r.error(f"必須ファイルがない: {rel}")


def check_json(root, cfg, r):
    targets = [(rel, True) for rel in [".claude/settings.json", *cfg["json_files"]]]
    targets += [(rel, False) for rel in SECRET_JSON]
    for pattern in cfg["json_globs"]:
        targets += [(str(p.relative_to(root)), True) for p in sorted(root.glob(pattern))]
    for rel, show in targets:
        p = root / rel
        if not p.is_file():
            continue
        try:
            json.loads(read_text(p))
        except json.JSONDecodeError as e:
            detail = f"{e.msg} (行 {e.lineno}, 列 {e.colno})" if show else f"行 {e.lineno}"
            r.error(f"JSON構文エラー: {rel}: {detail}")
        except UnicodeDecodeError:
            r.error(f"UTF-8 で読めない: {rel}")


def walk_imports(root, start, r):
    """入口からの import を辿り、存在・循環・深さ・重複を検査する。"""
    seen = {}

    def visit(path, chain):
        if len(chain) > MAX_IMPORT_HOPS + 1:
            r.error("import が深すぎる（最大4ホップ）: " + " -> ".join(str(c.relative_to(root)) for c in chain))
            return
        try:
            text = read_text(path)
        except (OSError, UnicodeDecodeError):
            return
        here = path.relative_to(root)
        for raw in find_imports(text):
            target = (Path(os.path.expanduser(raw)) if raw.startswith(("~", "/"))
                      else (path.parent / raw)).resolve()
            key = (here, str(target))
            seen[key] = seen.get(key, 0) + 1
            if seen[key] == 2:
                r.error(f"同じ import が重複: {here} 内の @{raw}")
            if target in chain:
                r.error(f"import が循環: {here} -> @{raw}")
                continue
            if not target.is_file():
                r.error(f"import 先がない: {here} 内の @{raw}")
                continue
            try:
                target.relative_to(root)
            except ValueError:
                r.warn(f"プロジェクト外の import（初回に承認ダイアログが出る）: {here} 内の @{raw}")
                continue
            if seen[key] == 1:
                visit(target, chain + [target])

    visit(start, [start])


def check_instructions(root, cfg, r):
    entry, _ = entry_file(root)
    agents = root / "AGENTS.md"
    if entry:
        n = sum(1 for i in find_imports(read_text(entry))
                if (entry.parent / i).resolve() == agents.resolve())
        if agents.is_file() and n != 1:
            r.error(f"{entry.relative_to(root)} は AGENTS.md をちょうど1回 import する（現在 {n} 回）")
        walk_imports(root, entry.resolve(), r)
    if agents.is_file():
        text = read_text(agents)
        lines = len(text.splitlines())
        if lines > cfg["agents_md_max_lines"]:
            r.warn(f"AGENTS.md が {lines} 行（目安 {cfg['agents_md_max_lines']} 行以内）")
        if find_imports(text):
            r.warn("AGENTS.md に @import がある（Claude 専用の記法。他エージェントでは読まれない）")


def check_skills(root, cfg, r):
    d = root / ".claude/skills"
    for p in sorted(d.glob("*/SKILL.md")) if d.is_dir() else []:
        rel, name = p.relative_to(root), p.parent.name
        fm = frontmatter(read_text(p))
        if fm is None:
            r.error(f"frontmatter がない: {rel}")
            continue
        if fm.get("name") and fm["name"] != name:
            r.warn(f"name がフォルダ名と違う（/ メニューには name が出る）: {rel}")
        if not fm.get("description"):
            r.error(f"description が空: {rel}")
        if name in cfg["manual_skills"]:
            if str(fm.get("disable-model-invocation", "")).lower() != "true":
                r.error(f"disable-model-invocation: true がない: {rel}")
            if "allowed-tools" in fm:
                r.error(f"allowed-tools を付けない（承認の省略になる）: {rel}")
    for name in cfg["manual_skills"]:
        if not (d / name / "SKILL.md").is_file():
            r.error(f"スキルがない: .claude/skills/{name}/SKILL.md")


def check_agents(root, cfg, r):
    d = root / ".claude/agents"
    readonly = set(cfg["readonly_agents"])
    for p in sorted(d.glob("*.md")) if d.is_dir() else []:
        rel = str(p.relative_to(root))
        fm = frontmatter(read_text(p))
        if fm is None or not fm.get("name"):
            r.error(f"frontmatter の name がない（読み込まれない）: {rel}")
            continue
        if not fm.get("description"):
            r.error(f"description がない（読み込まれない）: {rel}")
        if rel in readonly or (not readonly and "review" in fm["name"]):
            tools = fm.get("tools") or []
            tools = set(tools) if isinstance(tools, list) else {t.strip() for t in tools.split(",") if t.strip()}
            if not tools:
                r.error(f"確認役に tools の指定がない（全ツールを継承する）: {rel}")
            elif tools - READONLY_TOOLS:
                r.error(f"読み取り専用のはずの tools に {sorted(tools - READONLY_TOOLS)} がある: {rel}")
    for rel in readonly:
        if not (root / rel).is_file():
            r.error(f"エージェントがない: {rel}")


def check_rules(root, cfg, r):
    d = root / ".claude/rules"
    for p in sorted(d.glob("*.md")) if d.is_dir() else []:  # 直下のみ
        fm = frontmatter(read_text(p))
        rel = p.relative_to(root)
        if fm is None or "paths" not in fm:
            r.warn(f"paths が無いルールは常時読み込まれる: {rel}")
        elif not isinstance(fm["paths"], list) or not fm["paths"]:
            r.error(f"paths はリスト形式で1件以上書く: {rel}")


def check_settings(root, cfg, r):
    try:
        s = json.loads(read_text(root / ".claude/settings.json"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return  # 存在・構文は別の検査で報告済み
    perms = s.get("permissions") or {}
    if perms.get("defaultMode") == "bypassPermissions":
        r.error("permissions.defaultMode に bypassPermissions を使わない")
    broad = BROAD_BASH & set(perms.get("allow") or [])
    if broad:
        r.error(f"Bash の全許可がある: {sorted(broad)}")
    if not perms.get("deny"):
        r.warn("permissions.deny が空（秘密ファイルの Read/Edit deny を検討）")
    ours = [h for g in ((s.get("hooks") or {}).get("Stop") or []) for h in (g.get("hooks") or [])
            if HOOK_SCRIPT in str(h.get("command", ""))]
    if len(ours) != 1:
        r.error(f"Stop hook の {HOOK_SCRIPT} 登録はちょうど1件（現在 {len(ours)} 件）")
    for h in ours:
        if h.get("type") != "command":
            r.error("Stop hook の type は command にする")
        if not isinstance(h.get("timeout"), (int, float)):
            r.error("Stop hook に timeout（秒）を付ける")


def check_gitignore(root, cfg, r):
    if not (root / ".git").exists():
        return
    p = root / ".gitignore"
    lines = set(read_text(p).splitlines()) if p.is_file() else set()
    for line in cfg["gitignore_lines"]:
        if line not in lines:
            r.error(f".gitignore に {line} がない")


CHECKS = [check_required, check_json, check_instructions, check_skills,
          check_agents, check_rules, check_settings, check_gitignore]


def run(root):
    r = Report()
    cfg = load_config(root, r)
    for check in CHECKS:
        check(root, cfg, r)
    return r


def default_root():
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    return Path(env) if env else Path(__file__).resolve().parents[2]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--hook", action="store_true", help="Stop hook として動く")
    ap.add_argument("--root", type=Path, help="プロジェクトのルート（既定: CLAUDE_PROJECT_DIR）")
    args = ap.parse_args(argv)
    root = (args.root or default_root()).resolve()

    if args.hook:
        raw = sys.stdin.read(1_000_000)
        try:
            data = json.loads(raw) if raw.strip() else {}
        except json.JSONDecodeError:
            data = {}
        if isinstance(data, dict) and data.get("stop_hook_active") is True:
            return 0  # hook による継続中は再ブロックしない（無限継続の防止）
        r = run(root)
        if r.errors:
            shown = r.errors[:10]
            more = f"\n…ほか {len(r.errors) - 10} 件" if len(r.errors) > 10 else ""
            reason = ("エージェント用設定の構造検査（.claude/hooks/check_setup.py）が失敗しました。"
                      "修正するか、意図した変更なら利用者に報告してください:\n- "
                      + "\n- ".join(shown) + more)
            print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))
        return 0

    r = run(root)
    for w in r.warnings:
        print(f"WARN  {w}")
    for e in r.errors:
        print(f"NG    {e}")
    if r.errors:
        print(f"\n失敗: エラー {len(r.errors)} 件 / 警告 {len(r.warnings)} 件")
        return 1
    print(f"OK    構造検査に合格（警告 {len(r.warnings)} 件）。YAML の完全な検証と実機での読み込みは未検証。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
