.DEFAULT_GOAL := help
.PHONY: help check zip harness install-harness

help:  ## このメニューを表示する（make だけで出る）
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-16s %s\n", $$1, $$2}'

check:  ## 完了の定義。フック・CI・人間がすべてこれを使う
	python3 tools/check.py

zip:  ## claude.ai 用のスキルZIPを dist/ に作る
	python3 tools/build_skill_zip.py

harness:  ## agent-harness-kit の最新版をこのリポジトリに入れ直す
	python3 skills/agent-harness-kit/scripts/install.py --check "make check" --ci

install-harness:  ## 別のリポジトリにハーネスを入れる（例: make install-harness TARGET=../app ARGS=--dry-run）
	@test -n "$(TARGET)" || { echo "TARGET=<導入先のパス> を指定する"; exit 1; }
	python3 skills/agent-harness-kit/scripts/install.py --target "$(TARGET)" $(ARGS)
