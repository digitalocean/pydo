LOCAL_SPEC_FILE=./DigitalOcean-public.v2.yaml
MODELERFOUR_VERSION="4.23.6"
AUTOREST_PYTHON_VERSION="6.0.1"

.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'; \
	printf "\nNOTE: Run 'SPEC_FILE=path/to/local/spec make generate' to skip the download and use a local spec file.\n"

.PHONY: dev-dependencies
dev-dependencies: ## Install development tooling
	npm install --only=dev

.PHONY: clean
clean: ## Removes all generated code (except _patch.py files)
	@printf "=== Cleaning src directory\n"
	@find src/digitalocean -type f ! -name "_patch.py" -exec rm -rf {} +

.PHONY: download-spec
download-spec: ## Download Latest DO Spec
	@echo Downloading published spec; \
	touch DigitalOcean-public.v2.yaml && \
	curl https://api-engineering.nyc3.digitaloceanspaces.com/spec-ci/DigitalOcean-public.v2.yaml -o $(LOCAL_SPEC_FILE)

.PHONY: generate
ifndef SPEC_FILE
generate: SPEC_FILE = $(LOCAL_SPEC_FILE)
generate: dev-dependencies download-spec ## Generates the python client using the latest published spec first.
endif 
generate: clean dev-dependencies
	@printf "=== Generating client with spec: $(SPEC_FILE)\n\n"; \
	npm run autorest -- client_gen_config.md \
		--use:@autorest/modelerfour@$(MODELERFOUR_VERSION) \
		--use:@autorest/python@$(AUTOREST_PYTHON_VERSION) \
		--input-file=$(SPEC_FILE)

.PHONY: test-dependencies
test-dependencies: ## Install test dependencies
ifneq (, $(shell which poetry))
	poetry install --no-interaction
else
	@(echo "poetry is not installed. See https://python-poetry.org/docs/#installation for more info."; exit 1)
endif

.PHONY: lint-tests
lint-tests: test-dependencies
	poetry run black --check tests/. && \
	poetry run pylint ${PYLINT_ARGS} tests/.

.PHONY: test-mocked
ifdef TEST_PATTERN
test-mocked: PYTEST_ARG=-k ${TEST_PATTERN}
endif
test-mocked: test-dependencies
	poetry run pytest -rA --tb=short tests/mocked/.

.PHONY: test-mocked
ifdef TEST_PATTERN
test-integration: PYTEST_ARG=-k ${TEST_PATTERN}
endif
test-integration: test-dependencies
	poetry run pytest -rA --tb=short tests/integration/. ${PYTEST_ARG}
