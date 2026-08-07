build:
	../../scripts/build.sh $(APP)

lint-default:
	@echo "Linting not implemented for $(APP)"

# Per-service verification stage. The pipeline runs `make extra-tests` for
# every service, so every service must have the target. A service opts in by
# setting EXTRA_TESTS to the command(s) to run *before* including this file;
# anything that sets nothing inherits the no-op below and the pipeline line
# stays uniform.
#
# Set the variable rather than defining your own `extra-tests:` recipe — a
# second recipe for the same target makes GNU make warn on every invocation.
EXTRA_TESTS ?= echo "$(APP): no extra tests"

.PHONY: extra-tests
extra-tests:
	@$(EXTRA_TESTS)
