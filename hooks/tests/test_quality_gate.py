"""hooks/quality_gate.py のテスト。一時ディレクトリだけを使う。

失敗メッセージには「直し方」を書く。
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'quality_gate.py'


class QualityGateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / 'proj'
        self.root.mkdir()
        self.data = Path(self.tmp.name) / 'data'
        subprocess.run(['git', 'init', '-q'], cwd=self.root, check=True)
        subprocess.run(['git', '-c', 'user.email=t@example.com', '-c', 'user.name=t', 'commit', '-q',
                        '--allow-empty', '-m', 'init'], cwd=self.root, check=True)

    def tearDown(self):
        self.tmp.cleanup()

    def config(self, **kw):
        (self.root / '.claude').mkdir(exist_ok=True)
        (self.root / '.claude' / 'quality-gate.json').write_text(json.dumps(kw), encoding='utf-8')

    def run_gate(self, session='s1', **env):
        e = dict(os.environ, CLAUDE_PROJECT_DIR=str(self.root), QUALITY_GATE_STATE_DIR=str(self.data), **env)
        payload = json.dumps({'session_id': session, 'cwd': str(self.root)})
        return subprocess.run([sys.executable, str(SCRIPT)], input=payload, capture_output=True,
                              text=True, env=e, timeout=60)

    def test_without_config_does_nothing(self):
        r = self.run_gate()
        self.assertEqual(r.returncode, 0, f'設定ファイルが無いのに終了コード{r.returncode}。'
                         '直し方: load_config が None のとき 0 を返す')

    def test_passing_command_allows_stop(self):
        self.config(command='true')
        self.assertEqual(self.run_gate().returncode, 0, '成功するコマンドで止まらなかった。直し方: returncode 0 で 0 を返す')

    def test_failing_command_blocks_with_output(self):
        self.config(command='echo boom-detail; exit 1')
        r = self.run_gate()
        self.assertEqual(r.returncode, 2, '失敗時に終了コード2でない。直し方: 失敗時は 2 を返して Claude に作業を続けさせる')
        self.assertIn('boom-detail', r.stderr, '失敗の出力が stderr に無い。直し方: 出力の末尾を stderr に書く')

    def test_stops_blocking_after_max_retries(self):
        self.config(command='exit 1', max_retries=2)
        codes = []
        for i in range(3):
            (self.root / f'edit{i}.txt').write_text('x', encoding='utf-8')  # 修正を試みた想定で作業ツリーを変える
            codes.append(self.run_gate().returncode)
        self.assertEqual(codes, [2, 2, 0], f'再試行上限の扱いが違う: {codes}。'
                         '直し方: 同じセッションで max_retries 回を超えたら 0 を返し systemMessage で警告する')

    def test_skips_when_tree_unchanged_after_pass(self):
        marker = self.root / 'count.txt'
        self.config(command=f'echo x >> "{marker}"')
        subprocess.run(['git', 'add', '.claude'], cwd=self.root, check=True)
        subprocess.run(['git', '-c', 'user.email=t@example.com', '-c', 'user.name=t', 'commit', '-q', '-m', 'c'],
                       cwd=self.root, check=True)
        (self.root / '.gitignore').write_text('count.txt\n', encoding='utf-8')
        self.run_gate()
        self.run_gate()
        runs = marker.read_text().count('x')
        self.assertEqual(runs, 1, f'変更が無いのに {runs} 回実行した。直し方: 前回成功時の fingerprint と同じなら実行しない')

    def test_second_call_in_same_stop_reuses_result(self):
        marker = self.root / 'count.txt'
        (self.root / '.gitignore').write_text('count.txt\n', encoding='utf-8')
        self.config(command=f'echo x >> "{marker}"; exit 1')
        first, second = self.run_gate(), self.run_gate()
        self.assertEqual((first.returncode, second.returncode), (2, 2),
                         '2回目の呼び出しでも失敗を返すべき。直し方: last の結果を再利用して同じ終了コードを返す')
        runs = marker.read_text().count('x')
        self.assertEqual(runs, 1, f'同じ状態で {runs} 回実行した。直し方: DEDUP_SECONDS 以内の同じ fingerprint は再実行しない')

    def test_disable_env(self):
        self.config(command='exit 1')
        r = self.run_gate(QUALITY_GATE_DISABLE='1')
        self.assertEqual(r.returncode, 0, 'QUALITY_GATE_DISABLE=1 で無効にならない。直し方: main の先頭で環境変数を見る')


if __name__ == '__main__':
    unittest.main()
