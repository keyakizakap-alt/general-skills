"""check_setup.py のテスト。実リポジトリの管理対象を一時ディレクトリへ複製して検査するので、実設定は変更しない。

    python3 -m unittest discover -s .claude/hooks/tests
"""

import json
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / ".claude/hooks/check_setup.py"
COPY = [".claude/CLAUDE.md", "AGENTS.md", ".gitignore", ".claude/settings.json", ".claude/skills",
        ".claude/agents", ".claude/rules", ".claude/hooks/check_setup.py", ".claude/hooks/check_setup.json", ".claude-plugin",
        "docs/ai"]
HOOK = {"type": "command",
        "command": 'python3 "${CLAUDE_PROJECT_DIR}/.claude/hooks/check_setup.py" --hook',
        "timeout": 20}


def run(root, *args, stdin=None, timeout=20):
    return subprocess.run([sys.executable, str(SCRIPT), "--root", str(root), *args],
                          input=stdin, capture_output=True, text=True, timeout=timeout)


class CheckSetupTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        for rel in COPY:
            src, dst = REPO / rel, self.tmp / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            (shutil.copytree if src.is_dir() else shutil.copy2)(src, dst)
        # 実設定に Hook を登録する前でもテストできるよう、複製側にだけ登録する
        sp = self.tmp / ".claude/settings.json"
        s = json.loads(sp.read_text(encoding="utf-8"))
        if "hooks" not in s:
            s["hooks"] = {"Stop": [{"hooks": [HOOK]}]}
            sp.write_text(json.dumps(s), encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def edit(self, rel, fn):
        p = self.tmp / rel
        p.write_text(fn(p.read_text(encoding="utf-8")), encoding="utf-8")

    # --- 正常 ---
    def test_ok_manual(self):
        res = run(self.tmp)
        self.assertEqual(res.returncode, 0, res.stdout)

    def test_ok_hook_no_output(self):
        res = run(self.tmp, "--hook", stdin=json.dumps({"hook_event_name": "Stop", "stop_hook_active": False}))
        self.assertEqual(res.returncode, 0)
        self.assertEqual(res.stdout.strip(), "")

    # --- 異常 ---
    def test_broken_json_blocks(self):
        self.edit(".claude/settings.json", lambda t: t + "}")
        res = run(self.tmp, "--hook", stdin=json.dumps({"stop_hook_active": False}))
        self.assertEqual(res.returncode, 0)
        out = json.loads(res.stdout)
        self.assertEqual(out["decision"], "block")
        self.assertIn("JSON構文エラー", out["reason"])

    def test_missing_import_target(self):
        (self.tmp / "AGENTS.md").unlink()
        res = run(self.tmp)
        self.assertEqual(res.returncode, 1)
        self.assertIn("import 先がない", res.stdout)

    def test_import_cycle_and_duplicate(self):
        self.edit("AGENTS.md", lambda t: t + "\n@.claude/CLAUDE.md\n")
        self.edit(".claude/CLAUDE.md", lambda t: t + "\n@../AGENTS.md\n")
        res = run(self.tmp)
        self.assertIn("循環", res.stdout)
        self.assertIn("ちょうど1回", res.stdout)

    def test_import_in_code_is_ignored(self):
        self.edit(".claude/CLAUDE.md", lambda t: t + "\n```\n@missing.md\n```\n`@missing2.md`\n")
        self.assertEqual(run(self.tmp).returncode, 0)

    def test_japanese_punctuation_not_part_of_path(self):
        self.edit(".claude/CLAUDE.md", lambda t: t + "\n参照は @../AGENTS.md。以上\n")
        res = run(self.tmp)
        self.assertNotIn("import 先がない", res.stdout)

    def test_reviewer_with_write_tool(self):
        self.edit(".claude/agents/project-reviewer.md",
                  lambda t: t.replace("tools: Read, Grep, Glob", "tools: Read, Grep, Glob, Bash"))
        res = run(self.tmp)
        self.assertIn("Bash", res.stdout)
        self.assertEqual(res.returncode, 1)

    def test_skill_allowed_tools_and_invocation(self):
        self.edit(".claude/skills/project-work/SKILL.md",
                  lambda t: t.replace("disable-model-invocation: true", "allowed-tools: Bash(*)"))
        res = run(self.tmp)
        self.assertIn("disable-model-invocation", res.stdout)
        self.assertIn("allowed-tools", res.stdout)

    def test_broad_bash_and_bypass(self):
        def f(t):
            s = json.loads(t)
            s["permissions"]["allow"] = ["Bash"]
            s["permissions"]["defaultMode"] = "bypassPermissions"
            return json.dumps(s)
        self.edit(".claude/settings.json", f)
        res = run(self.tmp)
        self.assertIn("全許可", res.stdout)
        self.assertIn("bypassPermissions", res.stdout)

    def test_duplicate_stop_hook(self):
        def f(t):
            s = json.loads(t)
            s["hooks"]["Stop"].append(s["hooks"]["Stop"][0])
            return json.dumps(s)
        self.edit(".claude/settings.json", f)
        self.assertIn("ちょうど1件", run(self.tmp).stdout)

    def test_local_settings_content_not_printed(self):
        (self.tmp / ".claude/settings.local.json").write_text('{"token": "SECRET-VALUE",', encoding="utf-8")
        res = run(self.tmp)
        self.assertEqual(res.returncode, 1)
        self.assertNotIn("SECRET-VALUE", res.stdout + res.stderr)

    def test_rule_without_paths_warns(self):
        (self.tmp / ".claude/rules/extra.md").write_text("# no frontmatter\n", encoding="utf-8")
        res = run(self.tmp)
        self.assertEqual(res.returncode, 0)
        self.assertIn("常時読み込まれる", res.stdout)

    # --- 再ブロック防止 ---
    def test_stop_hook_active_never_blocks(self):
        self.edit(".claude/settings.json", lambda t: t + "}")
        res = run(self.tmp, "--hook", stdin=json.dumps({"stop_hook_active": True}))
        self.assertEqual(res.returncode, 0)
        self.assertEqual(res.stdout.strip(), "")

    def test_invalid_stdin_still_checks(self):
        self.edit(".claude/settings.json", lambda t: t + "}")
        res = run(self.tmp, "--hook", stdin="not json")
        self.assertEqual(json.loads(res.stdout)["decision"], "block")

    # --- タイムアウト ---
    def test_runs_well_within_timeout(self):
        start = time.monotonic()
        run(self.tmp, "--hook", stdin="{}", timeout=10)
        self.assertLess(time.monotonic() - start, 5.0)

    def test_killed_by_timeout_is_not_a_pass(self):
        # timeout で打ち切られた場合は終了コードが 0/2 以外 → 公式仕様では非ブロッキングのエラー。
        # 「合格」として扱われない（decision を出力しない）ことを確認する。
        res = subprocess.run(["timeout", "0.001", sys.executable, str(SCRIPT), "--hook", "--root", str(self.tmp)],
                             input="{}", capture_output=True, text=True)
        self.assertNotIn(res.returncode, (0, 2))
        self.assertEqual(res.stdout.strip(), "")

    # --- 汎用版（skills/workspace-setup/assets）との整合 ---
    def test_repo_copy_matches_distributed_asset(self):
        asset = REPO / "skills/workspace-setup/assets/check_setup.py"
        self.assertEqual(asset.read_bytes(), SCRIPT.read_bytes(),
                         "repo の check_setup.py は skills/workspace-setup/assets/ のコピーにする")

    def test_minimal_project_without_config(self):
        root = Path(tempfile.mkdtemp())
        try:
            (root / ".claude/agents").mkdir(parents=True)
            (root / "AGENTS.md").write_text("# rules\n", encoding="utf-8")
            (root / "CLAUDE.md").write_text("@AGENTS.md\n", encoding="utf-8")
            (root / ".claude/settings.json").write_text(json.dumps({"hooks": {"Stop": [{"hooks": [HOOK]}]}}),
                                                        encoding="utf-8")
            (root / ".claude/agents/x-reviewer.md").write_text(
                "---\nname: x-reviewer\ndescription: d\ntools: Read, Edit\n---\n", encoding="utf-8")
            res = run(root)
            self.assertEqual(res.returncode, 1)
            self.assertIn("Edit", res.stdout)  # 既定: 名前に review を含むエージェントは読み取り専用
            (root / ".claude/agents/x-reviewer.md").write_text(
                "---\nname: x-reviewer\ndescription: d\ntools: Read\n---\n", encoding="utf-8")
            res = run(root)
            self.assertEqual(res.returncode, 0, res.stdout)
        finally:
            shutil.rmtree(root)


if __name__ == "__main__":
    unittest.main()
