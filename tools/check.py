#!/usr/bin/env python3
"""リポジトリ全体の検証（完了の定義）。標準ライブラリのみ。

    python3 tools/check.py        # 全チェック。NG が1つでもあれば終了コード1
    make check                    # 同じもの

フック（.claude/hooks/）・CI・人間がすべてこのコマンドを使う。
チェックを足すときは CHECKS に関数を1つ追加する。WARN は失敗にしない。
"""

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
sys.path.insert(0, str(ROOT / "tools"))
from build_skill_zip import validate as validate_skill  # noqa: E402

SKILL_MAX_LINES = 500  # SKILL.md 本体の上限。超える分は references/ に分ける
KIT_HOOKS = SKILLS / "agent-harness-kit" / "assets" / "hooks"
LINT = SKILLS / "prompt-architect" / "scripts" / "lint_prompt.py"
# 回帰テスト: 完成例と雛形はリンターを通り続けること（capability-probe.md は解説文書なので対象外）
LINT_TARGETS = ["prompt-architect/assets/examples/*.md",
                "prompt-architect/assets/universal-template.md",
                "prompt-architect/assets/agent-template.md"]
SECRET_RE = re.compile(
    r"(sk-ant-[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9]{32,}|AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{36,}"
    r"|xox[baprs]-[A-Za-z0-9-]{10,}|-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----)")
PATH_REF_RE = re.compile(r"`((?:references|assets|scripts)/[^`\s<>*]+)`")


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


def rel(p):
    return Path(p).resolve().relative_to(ROOT).as_posix()


def tracked_files():
    try:
        r = subprocess.run(["git", "ls-files", "-co", "--exclude-standard"], cwd=ROOT,
                           capture_output=True, text=True, check=True)
        return [ROOT / f for f in r.stdout.splitlines() if (ROOT / f).is_file()]
    except (OSError, subprocess.CalledProcessError):
        return [p for p in ROOT.rglob("*") if p.is_file() and ".git" not in p.parts]


# ---- チェック本体: (errors, warnings) を返す ----

def check_skill_frontmatter():
    errors = []
    for d in skill_dirs():
        errors += [f"{d.name}: {p}" for p in validate_skill(d)]
    return errors, []


def check_skill_context_budget():
    """コンテキストエンジニアリング: SKILL.md は短く、詳細は参照先へ。参照切れと孤立ファイルを検出する。"""
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
                if r not in text and f"{sub}/" + f.name.rsplit(".", 1)[0] not in text and f"`{sub}/`" not in text:
                    warnings.append(f"{d.name}: {r} が SKILL.md から参照されていない（読まれない可能性）")
    return errors, warnings


def check_manifests():
    errors = []
    plugin = load_json(ROOT / ".claude-plugin" / "plugin.json", errors)
    market = load_json(ROOT / ".claude-plugin" / "marketplace.json", errors)
    if plugin and market:
        for entry in market.get("plugins", []):
            src = ROOT / entry.get("source", "")
            pj = src / ".claude-plugin" / "plugin.json"
            if not pj.exists():
                errors.append(f"marketplace の source {entry.get('source')!r} に plugin.json がない")
            elif entry.get("name") != json.loads(pj.read_text(encoding="utf-8")).get("name"):
                errors.append(f"marketplace の name {entry.get('name')!r} と plugin.json の name が不一致")
    return errors, []


def check_readme_lists_skills():
    """README のスキル一覧表と実際の skills/ が一致すること（説明の腐敗を防ぐ）。"""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    listed = set(re.findall(r"^\|\s*\[`([a-z0-9-]+)`\]\(skills/", readme, re.M))
    actual = {d.name for d in skill_dirs()}
    errors = [f"README のスキル一覧に {s} がない" for s in sorted(actual - listed)]
    errors += [f"README に存在しないスキル {s} が載っている" for s in sorted(listed - actual)]
    return errors, []


def check_python_compiles():
    errors = []
    for f in sorted(ROOT.rglob("*.py")):
        if ".git" in f.parts:
            continue
        try:
            compile(f.read_text(encoding="utf-8"), str(f), "exec")  # .pyc を書かずに構文だけ確認
        except SyntaxError as e:
            errors.append(f"{rel(f)}:{e.lineno}: 構文エラー {e.msg}")
    return errors, []


def check_shell_scripts():
    """sh -n で構文だけ確認する（実行はしない）。"""
    errors = []
    for f in sorted(ROOT.rglob("*.sh")):
        if ".git" in f.parts:
            continue
        r = subprocess.run(["sh", "-n", str(f)], capture_output=True, text=True)
        if r.returncode != 0:
            errors.append(f"{rel(f)}: {r.stderr.strip()}")
    return errors, []


def check_prompt_examples_lint():
    errors = []
    for pattern in LINT_TARGETS:
        for f in sorted(SKILLS.glob(pattern)):
            r = subprocess.run([sys.executable, str(LINT), str(f)], capture_output=True, text=True)
            if r.returncode != 0:
                errors.append(f"{rel(f)} が lint_prompt.py に不合格（例・雛形は合格し続けること）")
    return errors, []


def check_harness_in_sync():
    """このリポジトリの .claude/hooks は agent-harness-kit から入れたもの。中身が一致し続けること。"""
    errors = []
    hooks_dir = ROOT / ".claude" / "hooks"
    for src in sorted(KIT_HOOKS.glob("*.py")):
        dst = hooks_dir / src.name
        if not dst.exists() or dst.read_bytes() != src.read_bytes():
            errors.append(f".claude/hooks/{src.name} がキットと不一致。"
                          f"`python3 skills/agent-harness-kit/scripts/install.py --target . --check \"make check\"` で揃える")
    settings = load_json(ROOT / ".claude" / "settings.json", errors)
    load_json(ROOT / ".claude" / "harness.json", errors)
    for group in (settings or {}).get("hooks", {}).values():
        for g in group:
            for hk in g.get("hooks", []):
                for m in re.findall(r"\$CLAUDE_PROJECT_DIR/([^\"' ]+)", hk.get("command", "")):
                    if not (ROOT / m).exists():
                        errors.append(f".claude/settings.json のフックが存在しないファイルを指す: {m}")
    return errors, []


def check_no_secrets():
    errors = []
    for f in tracked_files():
        if f.suffix in {".zip", ".png", ".jpg", ".pdf"}:
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
    ("プラグイン/マーケットプレイス定義", check_manifests),
    ("README のスキル一覧", check_readme_lists_skills),
    ("Python の構文", check_python_compiles),
    ("シェルスクリプトの構文", check_shell_scripts),
    ("プロンプト例のリンター回帰", check_prompt_examples_lint),
    ("ハーネスの同期", check_harness_in_sync),
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
