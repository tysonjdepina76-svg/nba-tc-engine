PY ?= python3
SCRIPT := leverage_check.py
CONTROLLER := controller.sh

.PHONY: help run test watch controller clean archive status

help:
	@echo "Crypto Leverage Sentinel — make targets"
	@echo "  make run          run one risk check (prints JSON)"
	@echo "  make test         run the unit test suite"
	@echo "  make watch        loop every 60s, print cadence each tick"
	@echo "  make controller   run the controller once"
	@echo "  make status       print the last persisted metrics"
	@echo "  make clean        truncate logs + history (keeps last metrics)"
	@echo "  make archive      snapshot all source files into archive/"

run:
	$(PY) $(SCRIPT)

test:
	$(PY) test_sentinel.py

watch:
	@./$(CONTROLLER) && sleep 60 && $(MAKE) --no-print-directory watch

controller:
	./$(CONTROLLER)

status:
	@cat last_metrics.json | $(PY) -m json.tool | head -20

clean:
	@: > sentinel.log && rm -f run_history.jsonl && echo "log + history cleared"

archive:
	@TS=$$(date -u +%Y-%m-%dT%H-%M-%SZ) && \
	  mkdir -p archive/$$TS && \
	  cp -f *.py *.sh *.json *.md Makefile archive/$$TS/ 2>/dev/null || true && \
	  echo "archived to archive/$$TS/"
