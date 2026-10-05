.DEFAULT_GOAL := help
.PHONY: help check test zip validate

help:  ## このメニューを表示する
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-10s %s\n", $$1, $$2}'

check:  ## 完了の定義（CI と同じ）。NG があれば失敗
	python3 tools/check.py

test:  ## ワークフローの模擬実行と設定検査のテストだけ
	node tools/test_workflows.mjs
	python3 -m unittest discover -s .claude/hooks/tests

zip:  ## claude.ai 用のスキルZIPを dist/ に作る
	python3 tools/build_skill_zip.py

validate:  ## claude CLI での検証（CI には無い。手元・クラウドセッション用）
	claude plugin validate --strict .claude-plugin/marketplace.json
	claude plugin validate --strict .claude-plugin/plugin.json
	claude plugin validate --strict skills/
	claude plugin validate --strict agents/
	claude plugin validate --strict .claude/skills
	claude plugin validate --strict .claude/agents
