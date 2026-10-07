#!/usr/bin/env python3
"""リポジトリ全体の検証（完了の定義）。標準ライブラリのみ。CI と人間とエージェントが同じものを使う。

    python3 tools/check.py        # 全チェック。NG が1つでもあれば終了コード1
    make check                    # 同じもの

チェックを足すときは CHECKS に関数を1つ追加する。WARN は失敗にしない。
claude CLI（plugin validate / plugin test）はCIに無いため、ここには含めない（docs/ai/checks.md 参照）。
元は PR #5（agent harness）の tools/check.py。このリポジトリの構成に合わせて書き直した。
"""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
sys.path.insert(0, str(ROOT / "tools"))
from build_skill_zip import parse_frontmatter, validate as validate_skill  # noqa: E402

SKILL_MAX_LINES = 500  # SKILL.md 本体の上限。超える分は references/ に分ける
LINT = SKILLS / "prompt-architect" / "scripts" / "lint_prompt.py"
# 回帰テスト: 完成例と雛形はリンターを通り続けること（capability-probe.md は解説文書なので対象外）
LINT_TARGETS = ["prompt-architect/assets/examples/*.md",
                "prompt-architect/assets/universal-template.md",
                "prompt-architect/assets/agent-template.md"]
SECRET_RE = re.compile(
    r"(sk-ant-[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9]{32,}|AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{36,}"
    r"|xox[baprs]-[A-Za-z0-9-]{10,}|-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----)")
PATH_REF_RE = re.compile(r"`((?:references|assets|scripts)/[^`\s<>*]+)`")
ANY_CHAT_KEYS = {"name", "description"}  # どのチャットでも動かすため、配布スキルの frontmatter はこの2つだけ
SKIP_DIRS = {".git", "node_modules", "dist", "__pycache__", "setup-backup"}


def rel(p):
    return Path(p).resolve().relative_to(ROOT).as_posix()


def walk(pattern):
    return sorted(p for p in ROOT.rglob(pattern) if not SKIP_DIRS & set(p.parts))


def skill_dirs():
    return sorted(d for d in SKILLS.iterdir() if (d / "SKILL.md").exists())


def load_json(path, errors):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"{rel(path)} がない")
    except ValueError as e:
        errors.append(f"{rel(path)} がJSONとして不正: {e}")
    return None


def tracked_files():
    try:
        r = subprocess.run(["git", "ls-files", "-co", "--exclude-standard"], cwd=ROOT,
                           capture_output=True, text=True, check=True)
        return [ROOT / f for f in r.stdout.splitlines() if (ROOT / f).is_file()]
    except (OSError, subprocess.CalledProcessError):
        return [p for p in walk("*") if p.is_file()]


# ---- チェック本体: (errors, warnings) を返す ----

def check_skill_frontmatter():
    errors, warnings = [], []
    for d in skill_dirs():
        errors += [f"{d.name}: {p}" for p in validate_skill(d)]
        fm = parse_frontmatter((d / "SKILL.md").read_text(encoding="utf-8")) or {}
        extra = set(fm) - ANY_CHAT_KEYS
        if extra:
            errors.append(f"{d.name}: frontmatter に {sorted(extra)}（どのチャットでも動かすため name/description のみにする。claude.ai での扱いは未確認）")
    return errors, warnings


def check_skill_context_budget():
    """SKILL.md は短く、詳細は参照先へ。参照切れと孤立ファイルを検出する。"""
    errors, warnings = [], []
    for d in skill_dirs():
        text = (d / "SKILL.md").read_text(encoding="utf-8")
        n = len(text.splitlines())
        if n > SKILL_MAX_LINES:
            errors.append(f"{d.name}/SKILL.md が {n} 行（上限 {SKILL_MAX_LINES}）。詳細を references/ に分ける")
        for ref in sorted(set(PATH_REF_RE.findall(text))):
            if not (d / ref.rstrip("/")).exists():
                errors.append(f"{d.name}/SKILL.md が存在しないパスを参照: {ref}")
        for sub in ("references", "assets", "scripts"):
            for f in sorted((d / sub).glob("*")) if (d / sub).is_dir() else []:
                r = f"{sub}/{f.name}"
                if r not in text and f"`{sub}/`" not in text:
                    warnings.append(f"{d.name}: {r} が SKILL.md から参照されていない（読まれない可能性）")
    return errors, warnings


def check_agents():
    """プラグインと .claude のサブエージェント: name と description が無いと黙って読み飛ばされる。"""
    errors = []
    for f in walk("agents/*.md"):
        fm = parse_frontmatter(f.read_text(encoding="utf-8"))
        if fm is None or not fm.get("name") or not fm.get("description"):
            errors.append(f"{rel(f)}: frontmatter に name と description が必要")
        elif ":" in fm["name"] or fm["name"].startswith("-"):
            errors.append(f"{rel(f)}: name に ':' を含めない / '-' で始めない")
    return errors, []


def check_manifests():
    errors = []
    plugin = load_json(ROOT / ".claude-plugin" / "plugin.json", errors)
    market = load_json(ROOT / ".claude-plugin" / "marketplace.json", errors)
    if plugin and market:
        for entry in market.get("plugins", []):
            pj = ROOT / entry.get("source", "") / ".claude-plugin" / "plugin.json"
            if not pj.exists():
                errors.append(f"marketplace の source {entry.get('source')!r} に plugin.json がない")
            elif entry.get("name") != json.loads(pj.read_text(encoding="utf-8")).get("name"):
                errors.append(f"marketplace の name {entry.get('name')!r} と plugin.json の name が不一致")
    return errors, []


def check_readme_lists():
    """README の一覧と実際の skills/ ・workflows/ が一致すること（説明の腐敗を防ぐ）。"""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    errors = []
    listed = set(re.findall(r"^\|\s*\[`([a-z0-9-]+)`\]\(skills/", readme, re.M))
    actual = {d.name for d in skill_dirs()}
    errors += [f"README のスキル一覧に {s} がない" for s in sorted(actual - listed)]
    errors += [f"README に存在しないスキル {s} が載っている" for s in sorted(listed - actual)]
    wf_listed = set(re.findall(r"^\|\s*\[`([a-z0-9-]+)`\]\(workflows/", readme, re.M))
    wf_actual = {p.stem for p in (ROOT / "workflows").glob("*.js")}
    errors += [f"README のワークフロー一覧に {s} がない" for s in sorted(wf_actual - wf_listed)]
    errors += [f"README に存在しないワークフロー {s} が載っている" for s in sorted(wf_listed - wf_actual)]
    return errors, []


def check_python_compiles():
    errors = []
    for f in walk("*.py"):
        try:
            compile(f.read_text(encoding="utf-8"), str(f), "exec")  # .pyc を書かずに構文だけ確認
        except SyntaxError as e:
            errors.append(f"{rel(f)}:{e.lineno}: 構文エラー {e.msg}")
    return errors, []


def check_workflows():
    """workflows/*.js: meta が先頭の純粋なリテラルであること、node での構文と模擬実行（tools/test_workflows.mjs）。"""
    errors, warnings = [], []
    files = sorted((ROOT / "workflows").glob("*.js"))
    for f in files:
        text = f.read_text(encoding="utf-8")
        if not re.match(r"\s*(//[^\n]*\n\s*)*export const meta = \{", text):
            errors.append(f"{rel(f)}: 先頭の文が `export const meta = {{` ではない")
        m = re.search(r"name:\s*'([a-z0-9-]+)'", text)
        if not m or m.group(1) != f.stem:
            errors.append(f"{rel(f)}: meta.name とファイル名が不一致")
        for bad in ("Date.now(", "Math.random(", "new Date()", "import("):
            if bad in text:
                errors.append(f"{rel(f)}: {bad} はワークフロー内で使えない（再開を壊す / 読み込み不可）")
    kit = ROOT / "skills" / "workspace-setup" / "assets" / "workflows"
    for f in files:
        copy = kit / f.name
        if not copy.exists() or copy.read_bytes() != f.read_bytes():
            errors.append(f"skills/workspace-setup/assets/workflows/{f.name} が workflows/{f.name} と不一致（cp でそろえる）")
    for copy in sorted(kit.glob("*.js")):
        if not (ROOT / "workflows" / copy.name).exists():
            errors.append(f"{rel(copy)} に対応する workflows/{copy.name} がない")
    node = shutil.which("node")
    if not files:
        return errors, warnings
    if not node:
        warnings.append("node が無いため workflows の構文検査と模擬実行は未実行")
        return errors, warnings
    r = subprocess.run([node, str(ROOT / "tools" / "test_workflows.mjs")], capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        errors.append("tools/test_workflows.mjs が失敗:\n       " + (r.stdout + r.stderr).strip().replace("\n", "\n       "))
    return errors, warnings


def check_agent_setup():
    """.claude/ のエージェント用設定の構造検査とそのテスト（.claude/hooks/check_setup.py）。"""
    errors = []
    r = subprocess.run([sys.executable, str(ROOT / ".claude/hooks/check_setup.py"), "--root", str(ROOT)],
                       capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        errors.append("check_setup.py: " + r.stdout.strip().replace("\n", " / "))
    r = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", str(ROOT / ".claude/hooks/tests")],
                       capture_output=True, text=True, timeout=120, cwd=ROOT)
    if r.returncode != 0:
        errors.append("check_setup のテストが失敗: " + r.stderr.strip().splitlines()[-1])
    return errors, []


def check_prompt_examples_lint():
    errors = []
    for pattern in LINT_TARGETS:
        for f in sorted(SKILLS.glob(pattern)):
            r = subprocess.run([sys.executable, str(LINT), str(f)], capture_output=True, text=True)
            if r.returncode != 0:
                errors.append(f"{rel(f)} が lint_prompt.py に不合格（例・雛形は合格し続けること）")
    return errors, []


def check_no_secrets():
    errors = []
    for f in tracked_files():
        if f.suffix in {".zip", ".png", ".jpg", ".pdf"} or f == Path(__file__).resolve():
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if SECRET_RE.search(line):
                errors.append(f"{rel(f)}:{i} に秘密情報らしき文字列がある")
    return errors, []


CHECKS = [
    ("スキルのフロントマター", check_skill_frontmatter),
    ("SKILL.md の長さと参照", check_skill_context_budget),
    ("サブエージェント定義", check_agents),
    ("プラグイン/マーケットプレイス定義", check_manifests),
    ("README の一覧", check_readme_lists),
    ("Python の構文", check_python_compiles),
    ("ワークフロー（構文・模擬実行）", check_workflows),
    ("エージェント用設定", check_agent_setup),
    ("プロンプト例のリンター回帰", check_prompt_examples_lint),
    ("秘密情報", check_no_secrets),
]


def main():
    failed = 0
    for label, fn in CHECKS:
        errors, warnings = fn()
        print(f"{'NG ' if errors else 'OK '} {label}")
        for e in errors:
            print(f"     - {e}")
        for w in warnings:
            print(f"     ~ WARN {w}")
        failed += bool(errors)
    print(f"\n{len(CHECKS) - failed}/{len(CHECKS)} 合格")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
