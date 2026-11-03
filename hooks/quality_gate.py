#!/usr/bin/env python3
"""Stop フック: プロジェクトが宣言した検査コマンドを、応答の終わりに実行する。

- 対象プロジェクトに `.claude/quality-gate.json` が無ければ何もしない（オプトイン）。
- 前回成功したときから作業ツリーが変わっていなければ実行しない。
- 失敗したら終了コード2で Claude に作業を続けさせる。同じセッションで max_retries 回失敗したら、
  止めずに警告だけ出す（無限ループ防止）。
- 環境変数 QUALITY_GATE_DISABLE=1 で無効にできる。

設定ファイルの例:
    {"command": "python3 -m unittest discover -s tests", "timeout": 600, "max_retries": 3}

標準ライブラリのみ。
"""
import hashlib
import json
import os
import subprocess
import sys
import time

try:
    import fcntl  # POSIX のみ。Windows ではロックせずに動かす
except ImportError:
    fcntl = None
from pathlib import Path

CONFIG = Path('.claude') / 'quality-gate.json'
TAIL_LINES = 60
DEDUP_SECONDS = 3  # 同じ Stop で並列に呼ばれた2つ目だけを拾う。修正後の次の停止までは数秒以上かかる


def project_dir(payload):
    return Path(os.environ.get('CLAUDE_PROJECT_DIR') or payload.get('cwd') or os.getcwd())


def state_dir():
    # プラグインとリポジトリの両方に同じフックがあっても結果を共有できるよう、置き場所を固定する。
    base = os.environ.get('QUALITY_GATE_STATE_DIR') or str(Path.home() / '.cache' / 'quality-gate')
    path = Path(base)
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_config(root):
    path = root / CONFIG
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding='utf-8'))
    command = data.get('command')
    if not isinstance(command, str) or not command.strip():
        raise ValueError(f'{path} に "command"（文字列）がない')
    return {
        'command': command,
        'timeout': int(data.get('timeout', 600)),
        'max_retries': int(data.get('max_retries', 3)),
    }


def git(root, *args):
    r = subprocess.run(['git', *args], cwd=root, capture_output=True, timeout=30)
    return r.stdout if r.returncode == 0 else None


def fingerprint(root, command):
    """作業ツリーの状態を表すハッシュ。Git 管理外なら None（毎回実行する）。"""
    head = git(root, 'rev-parse', 'HEAD')
    if head is None:
        return None
    h = hashlib.sha256(command.encode())
    h.update(head)
    h.update(git(root, 'diff', 'HEAD', '--binary') or b'')
    for name in (git(root, 'ls-files', '-o', '--exclude-standard', '-z') or b'').split(b'\0'):
        if not name:
            continue
        h.update(name)
        try:
            h.update(hashlib.sha256((root / name.decode()).read_bytes()).digest())
        except OSError:
            pass
    return h.hexdigest()


def read_state(path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def main():
    if os.environ.get('QUALITY_GATE_DISABLE') == '1':
        return 0
    try:
        payload = json.loads(sys.stdin.read() or '{}')
    except ValueError:
        payload = {}
    root = project_dir(payload)
    try:
        config = load_config(root)
    except (ValueError, OSError) as e:
        print(f'quality-gate: 設定を読めない: {e}', file=sys.stderr)
        return 1  # 止めない（非ブロッキングのエラー表示）
    if config is None:
        return 0

    key = hashlib.sha256(str(root.resolve()).encode()).hexdigest()[:16]
    state_path = state_dir() / f'{key}.json'
    with open(state_dir() / f'{key}.lock', 'w') as lock:
        if fcntl:
            fcntl.flock(lock, fcntl.LOCK_EX)  # 並列に呼ばれても検査を同時に走らせない
        return evaluate(root, config, payload, state_path)


def evaluate(root, config, payload, state_path):
    state = read_state(state_path)
    fp = fingerprint(root, config['command'])
    if fp is not None and state.get('passed') == fp:
        return 0
    last = state.get('last') or {}
    if fp is not None and last.get('fp') == fp and time.time() - last.get('t', 0) < DEDUP_SECONDS:
        # 同じ Stop で別の場所（プラグインとリポジトリ設定）から2回呼ばれたとき、結果を再利用する。
        if last.get('ok'):
            return 0
        print(last.get('message', 'quality-gate: 検査が失敗した'), file=sys.stderr)
        return last.get('code', 2)

    try:
        r = subprocess.run(config['command'], shell=True, cwd=root, capture_output=True,
                           text=True, timeout=config['timeout'])
        ok, output = r.returncode == 0, (r.stdout + r.stderr)
    except subprocess.TimeoutExpired:
        ok, output = False, f'{config["timeout"]} 秒で終わらなかった'

    session = payload.get('session_id', '')
    if ok:
        state.update(passed=fp, failures={}, last={'fp': fp, 'ok': True, 't': time.time()})
        state_path.write_text(json.dumps(state), encoding='utf-8')
        return 0

    failures = state.get('failures', {})
    failures[session] = failures.get(session, 0) + 1
    state['failures'] = failures
    state_path.write_text(json.dumps(state), encoding='utf-8')
    tail = '\n'.join(output.strip().splitlines()[-TAIL_LINES:])
    if failures[session] > config['max_retries']:
        state['last'] = {'fp': fp, 'ok': True, 't': time.time()}
        state_path.write_text(json.dumps(state), encoding='utf-8')
        print(json.dumps({'systemMessage': f'quality-gate: `{config["command"]}` が'
                          f'{config["max_retries"]}回続けて失敗したため、止めずに終了します。未解決のまま完了と報告しないこと。'},
                         ensure_ascii=False))
        return 0
    message = (f'quality-gate: 検査コマンド `{config["command"]}` が失敗した'
               f'（{failures[session]}/{config["max_retries"]}回目）。原因を直して再実行するまで完了と報告しないこと。\n'
               f'--- 出力の末尾 ---\n{tail}')
    state['last'] = {'fp': fp, 'ok': False, 't': time.time(), 'message': message, 'code': 2}
    state_path.write_text(json.dumps(state), encoding='utf-8')
    print(message, file=sys.stderr)
    return 2


if __name__ == '__main__':
    sys.exit(main())
