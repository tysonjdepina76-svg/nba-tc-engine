PYTHON          ?= python3
LOG_DIR         ?= logs
TIMESTAMP       := $(shell date +%Y%m%d_%H%M%S)
LOG_FILE        := $(LOG_DIR)/tc_pipeline_$(TIMESTAMP).log
DRY_RUN         ?= 0
RETRIES         ?= 2
ALLOW_OFFLINE   ?= 0

MLB_STATUS      := live
WNBA_STATUS     := live
NBA_STATUS      := offseason
NFL_STATUS      := preseason
NHL_STATUS      := offseason

ACTIVE_SPORTS   := $(strip \
	$(if $(filter live preseason,$(MLB_STATUS)),mlb) \
	$(if $(filter live preseason,$(WNBA_STATUS)),wnba) \
	$(if $(filter live preseason,$(NBA_STATUS)),nba) \
	$(if $(filter live preseason,$(NFL_STATUS)),nfl) \
	$(if $(filter live preseason,$(NHL_STATUS)),nhl))

ALL_SPORTS      := mlb wnba nba nfl nhl

.PHONY: all pipeline prepare predict publish evaluate clean help setup force $(ALL_SPORTS)

.DEFAULT_GOAL := pipeline

$(LOG_DIR):
	mkdir -p $(LOG_DIR)

define RUN
	@if [ "$(DRY_RUN)" = "1" ]; then \
		echo "DRY-RUN: $(1)" | tee -a $(LOG_FILE); \
	else \
		echo "▶ $(1)" | tee -a $(LOG_FILE); \
		n=0; \
		until [ $$n -ge $(RETRIES) ]; do \
			$(PYTHON) $(2) 2>&1 | tee -a $(LOG_FILE) && break; \
			n=$$((n+1)); \
			echo "  retry $$n/$(RETRIES)" | tee -a $(LOG_FILE); \
			sleep 2; \
		done; \
		if [ $$n -ge $(RETRIES) ]; then \
			echo "FAILED: $(1)" | tee -a $(LOG_FILE); \
			return 1; \
		fi; \
	fi
endef

setup: $(LOG_DIR)
	@echo "=== TC Pipeline started $$(date) ===" | tee $(LOG_FILE)
	@echo "Active sports: $(ACTIVE_SPORTS)" | tee -a $(LOG_FILE)
	@echo "Dry-run: $(DRY_RUN) | Retries: $(RETRIES) | Offline allowed: $(ALLOW_OFFLINE)" | tee -a $(LOG_FILE)

pipeline: setup prepare predict publish evaluate
	@echo "" | tee -a $(LOG_FILE)
	@echo "Full pipeline finished at $$(date)" | tee -a $(LOG_FILE)

prepare: setup
	@echo "" | tee -a $(LOG_FILE)
	@echo "===== STAGE 1: PREPARE =====" | tee -a $(LOG_FILE)
	$(call RUN,pipeline_audit.py,pipeline_audit.py) || true
	$(call RUN,update_closing_lines.py,update_closing_lines.py) || true
	@echo "Prepare stage done" | tee -a $(LOG_FILE)

predict: setup
	@echo "" | tee -a $(LOG_FILE)
	@echo "===== STAGE 2: PREDICT =====" | tee -a $(LOG_FILE)
	@for sport in $(ACTIVE_SPORTS); do \
		echo "" | tee -a $(LOG_FILE); \
		echo "--- Sport: $$sport ---" | tee -a $(LOG_FILE); \
		$(call RUN,$${sport}_recalibration.py (pre),$${sport}_recalibration.py) || true; \
		$(call RUN,gen_$${sport}_today.py,gen_$${sport}_today.py) || true; \
		$(call RUN,$${sport}_recalibration.py (post),$${sport}_recalibration.py) || true; \
	done
	@echo "Predict stage done" | tee -a $(LOG_FILE)

publish: setup
	@echo "" | tee -a $(LOG_FILE)
	@echo "===== STAGE 3: PUBLISH =====" | tee -a $(LOG_FILE)
	$(call RUN,daily_picks.py --sport all,daily_picks.py --sport all)
	@echo "Publish stage done" | tee -a $(LOG_FILE)

evaluate: setup
	@echo "" | tee -a $(LOG_FILE)
	@echo "===== STAGE 4: EVALUATE =====" | tee -a $(LOG_FILE)
	$(call RUN,run_backtest.py --report,run_backtest.py --report) || true
	@echo "Evaluate stage done" | tee -a $(LOG_FILE)

$(ALL_SPORTS): setup
	@echo "Force single sport: $@" | tee -a $(LOG_FILE)
	$(call RUN,daily_picks.py --sport $@,daily_picks.py --sport $@)

force:
	$(MAKE) -B pipeline

clean:
	rm -rf $(LOG_DIR)/*.log 2>/dev/null || true

help:
	@echo "make                  full pipeline (4 stages)"
	@echo "make prepare          stage 1 only"
	@echo "make predict          stage 2 only"
	@echo "make publish          stage 3 only"
	@echo "make evaluate         stage 4 only"
	@echo "make DRY_RUN=1        preview only"
	@echo "make ALLOW_OFFLINE=1  allow missing API key"
	@echo "make mlb|wnba|nba     force one sport"
	@echo "make force            force full re-run"
	@echo "make clean            clear logs"
