# Skynet — Makefile

.PHONY: setup run clean log

setup:
	@bash setup.sh

run:
	@bash run.sh

log:
	@cat skynet_logs.json 2>/dev/null | python3 -m json.tool || echo "No log file found."

clean:
	rm -f skynet_logs.json
	rm -rf sandbox/*.txt sandbox/*.log
