#!/usr/bin/env python3
"""claude.ai にアップロードするスキルZIPを作る（検証つき）。

    python3 tools/build_skill_zip.py                 # skills/ 配下を全部ビルド
    python3 tools/build_skill_zip.py prompt-architect

出力: dist/<skill-name>.zip
ZIPの直下にスキルフォルダが入る形式（claude.ai の要求どおり）:
    prompt-architect/SKILL.md
    prompt-architect/references/...

アップロード先: claude.ai → Settings → Capabilities（Features）→ Skills
前提: Pro / Max / Team / Enterprise プランで、コード実行（ファイルの作成と編集）が有効であること。
"""

import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / "skills"
DIST = ROOT / "dist"
EXCLUDE_DIRS = {"__pycache__", ".git", ".ipynb_checkpoints", "node_modules"}
EXCLUDE_FILES = {".DS_Store", "Thumbs.db"}

# claude.ai / Claude API のフロントマター制約（platform.claude.com, 参照日 2026-09-14）
NAME_RE = re.compile(r"^[a-z0-9-]{1,64}$")
RESERVED = ("anthropic", "claude")
MAX_DESC = 1024


def parse_frontmatter(text):
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    body = text[3:end]
    out, key = {}, None
    for line in body.splitlines():
        m = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
        if m:
            key, out[m.group(1)] = m.group(1), m.group(2).strip()
        elif key and line.strip():
            out[key] += " " + line.strip()
    return out


def validate(skill_dir):
    """アップロードが弾かれる条件を事前に潰す。問題のリストを返す。"""
    problems = []
    md = skill_dir / "SKILL.md"
    if not md.exists():
        return [f"SKILL.md がない: {md}"]

    fm = parse_frontmatter(md.read_text(encoding="utf-8"))
    if fm is None:
        return ["SKILL.md の先頭に --- で囲んだYAMLフロントマターがない"]

    name = fm.get("name", "")
    desc = fm.get("description", "")

    if not name:
        problems.append("name が未設定")
    elif not NAME_RE.match(name):
        problems.append(f"name が不正 (小文字・数字・ハイフンのみ / 64文字以内): {name!r}")
    elif any(w in name.lower() for w in RESERVED):
        problems.append(f"name に予約語 {RESERVED} を含められない: {name!r}")
    if name and name != skill_dir.name:
        problems.append(f"name ({name}) とフォルダ名 ({skill_dir.name}) が不一致")

    if not desc:
        problems.append("description が空")
    elif len(desc) > MAX_DESC:
        problems.append(f"description が長すぎる: {len(desc)} 文字 (上限 {MAX_DESC})")
    if "<" in desc and ">" in desc:
        problems.append("description にXMLタグらしき記述がある（不可）")

    return problems


def build(skill_dir):
    DIST.mkdir(exist_ok=True)
    out = DIST / f"{skill_dir.name}.zip"
    n = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(skill_dir.rglob("*")):
            if not p.is_file():
                continue
            if any(part in EXCLUDE_DIRS for part in p.parts) or p.name in EXCLUDE_FILES:
                continue
            # ZIP直下がスキルフォルダになるように書き込む
            z.write(p, Path(skill_dir.name) / p.relative_to(skill_dir))
            n += 1
    return out, n


def main():
    targets = sys.argv[1:]
    dirs = ([SKILLS_DIR / t for t in targets] if targets
            else sorted(d for d in SKILLS_DIR.iterdir() if (d / "SKILL.md").exists()))

    failed = False
    for d in dirs:
        if not d.exists():
            print(f"NG  {d} が存在しない")
            failed = True
            continue
        problems = validate(d)
        if problems:
            failed = True
            print(f"NG  {d.name}")
            for p in problems:
                print(f"      - {p}")
            continue
        out, n = build(d)
        size = out.stat().st_size / 1024
        print(f"OK  {d.name}: {out.relative_to(ROOT)} ({n} files, {size:.0f} KB)")

    if failed:
        print("\n検証に失敗しました。修正してから再実行してください。")
        return 1
    print("\nclaude.ai → Settings → Capabilities (Features) → Skills からZIPをアップロードします。")
    print("※ コード実行（ファイルの作成と編集）が有効なプラン（Pro / Max / Team / Enterprise）が必要です。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
