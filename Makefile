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

.PHONY: download-spec generate
ifndef SPEC_FILE
generate: SPEC_FILE = $(LOCAL_SPEC_FILE)
generate: download-spec ## Generates the python client using the latest published spec first.
endif
generate: clean dev-dependencies
	@printf "=== Generating client with spec: $(SPEC_FILE)\n\n"; \
	npm run autorest -- client_gen_config.md \
		--use:@autorest/modelerfour@$(MODELERFOUR_VERSION) \
		--use:@autorest/python@$(AUTOREST_PYTHON_VERSION) \
		--input-file=$(SPEC_FILE)