ifdef CHECK
  CHECK_C := --check --diff
else
  CHECK_C :=
endif

help:
	@echo "Run 'make main.yml' to (re-)run ansible for that machine."
	@echo ""
	@echo "Make Variables: (make ... VAR=VALUE)"
	@echo "  CHECK=1      run in --check mode (implies DIFF=1)"

deps:
	ansible-galaxy install -r requirements.yml

%.yml: deps
	ansible-playbook $@ $(CHECK_C)

.PHONY: deps help