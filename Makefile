.PHONY: check zip harness

check:  ## 完了の定義。フック・CI・人間がすべてこれを使う
	python3 tools/check.py

zip:  ## claude.ai 用のスキルZIPを dist/ に作る
	python3 tools/build_skill_zip.py

harness:  ## agent-harness-kit の最新版をこのリポジトリに入れ直す
	python3 skills/agent-harness-kit/scripts/install.py --target . --check "make check" --ci
