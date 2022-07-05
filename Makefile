LOCAL_SPEC_FILE=./DigitalOcean-public.v2.yaml

PYTEST_CMD = poetry run pytest

.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'; \
	printf "\nNOTE: Run 'SPEC_FILE=path/to/local/spec make generate' to skip the download and use a local spec file.\n"

.PHONY: gen-dependencies
gen-dependencies: ## Install client generation tooling
ifeq (, $(shell which npm))
	@(echo "npm is not installed. See https://docs.npmjs.com/downloading-and-installing-node-js-and-npm for more info"; exit 1)
endif
ifeq (, $(shell which autorest))
	npm install -g autorest
else
	@echo "autorest already installed"
endif

.PHONY: clean
clean: ## Removes all generated code (except _patch.py files)
	@printf "=== Cleaning src directory\n"
	@find src/digitalocean -type f ! -name "_patch.py" -exec rm -rf {} + -depth

.PHONY: download-spec
download-spec: ## Download Latest DO Spec
	@echo Downloading published spec; \
	touch DigitalOcean-public.v2.yaml && \
	curl https://api-engineering.nyc3.digitaloceanspaces.com/spec-ci/DigitalOcean-public.v2.yaml -o $(LOCAL_SPEC_FILE)

.PHONY: generate
ifndef SPEC_FILE
generate: SPEC_FILE = $(LOCAL_SPEC_FILE)
generate: gen-dependencies download-spec ## Generates the python client using the latest published spec first.
endif 
generate: clean
	@printf "=== Generating client with spec: $(SPEC_FILE)\n\n"; \
	autorest client_gen_config.md --input-file=$(SPEC_FILE)

.PHONY: test-dependencies
test-dependencies: ## Install test dependencies
ifneq (, $(shell which poetry))
	poetry install
else
	@(echo "poetry is not installed. See https://python-poetry.org/docs/#installation for more info."; exit 1)
endif

.PHONY: test-mocked
ifdef TEST_PATTERN
test-mocked: PYTEST_ARG=-k ${TEST_PATTERN}
endif
test-mocked: test-dependencies
	$(PYTEST_CMD) -rA --tb=short tests/mocked/.

.PHONY: test-mocked
ifdef TEST_PATTERN
test-integration: PYTEST_ARG=-k ${TEST_PATTERN}
endif
test-integration: test-dependencies
	$(PYTEST_CMD) -rA --tb=short tests/integration/. ${PYTEST_ARG}


