LOCAL_SPEC_FILE=./DigitalOcean-public.v2.yaml
MODELERFOUR_VERSION="4.23.6"
AUTOREST_PYTHON_VERSION="6.0.1"
PACKAGE_VERSION?="dev"

ifeq (, $(findstring -m,$(PYTEST_ARGS)))
	PYTEST_EXCLUDE_MARKS=-m "not real_billing"
endif

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
	@find src/digitalocean -type f ! -name "_patch.py" ! -name "custom_*.py" ! -name "exceptions.py" -exec rm -rf {} +

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
		--package-version=$(PACKAGE_VERSION) \
		--input-file=$(SPEC_FILE)

.PHONY: install
install: ## Install test dependencies
ifneq (, $(shell which poetry))
	poetry install --no-interaction -E aio
else
	@(echo "poetry is not installed. See https://python-poetry.org/docs/#installation for more info."; exit 1)
endif

.PHONY: lint-tests
lint-tests: install
	poetry run black --check --diff tests/. && \
	poetry run pylint $(PYLINT_ARGS) tests/.

.PHONY: test-mocked
test-mocked: install
	poetry run pytest -rA --tb=short tests/mocked/. $(PYTEST_ARGS)

.PHONY: test-mocked
test-integration: install
	poetry run pytest -rA --tb=short tests/integration/. $(PYTEST_EXCLUDE_MARKS) $(PYTEST_ARGS)

# This command runs a single integration test
# > make test-integration-single test=test_actions
.PHONY: test-mocked
test-integration-single: install
	poetry run pytest -rA --tb=short tests/integration/. -k $(test)

.PHONY: docker-build
docker-build:
	docker build -t digitalocean-client-python:dev .

.PHONY: docker-python
docker-python: docker-build  ## Runs a python shel within a docker container
	docker run -it --rm --name pydo digitalocean-client-python:dev python
