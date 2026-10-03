#!/bin/sh
# agent-harness-kit を、このリポジトリを clone せずに任意のリポジトリへ入れる。
#
#   cd <導入したいリポジトリ>
#   curl -fsSL https://raw.githubusercontent.com/keyakizakap-alt/general-skills/main/tools/install-harness.sh | sh -s -- --dry-run
#   curl -fsSL https://raw.githubusercontent.com/keyakizakap-alt/general-skills/main/tools/install-harness.sh | sh
#
# 引数は install.py にそのまま渡る（--dry-run / --ci / --check "npm test" / --target DIR）。
# 環境変数: HARNESS_REF（取得するブランチ・タグ。既定 main）、HARNESS_REPO（取得元 git URL）
set -eu

REPO="${HARNESS_REPO:-https://github.com/keyakizakap-alt/general-skills.git}"
REF="${HARNESS_REF:-main}"

if ! command -v python3 >/dev/null 2>&1; then
  echo "NG  python3 が見つからない。Python 3 を入れてから再実行する。" >&2
  exit 1
fi

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT INT TERM

if command -v git >/dev/null 2>&1; then
  git clone --quiet --depth 1 --branch "$REF" "$REPO" "$tmp/kit"
else
  # git がない環境は GitHub のアーカイブを使う
  url="$(printf '%s' "$REPO" | sed -e 's#\.git$##' -e 's#https://github.com/#https://codeload.github.com/#')/tar.gz/$REF"
  mkdir -p "$tmp/kit"
  curl -fsSL "$url" | tar -xz -C "$tmp/kit" --strip-components 1
fi

python3 "$tmp/kit/skills/agent-harness-kit/scripts/install.py" "$@"
