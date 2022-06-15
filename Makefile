BUNDLE_PATH ?= tests/openapi-bundled.yaml
SPEC_FILE ?= tests/DigitalOcean-public.v2.yaml

.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: dev-dependencies
dev-dependencies: ## Install development tooling using npm
	npm install --only=dev

.PHONY: download-spec
download-spec: dev-dependencies ## Download Latest DO Spec
	touch tests/DigitalOcean-public.v2.yaml
	curl https://api-engineering.nyc3.digitaloceanspaces.com/spec-ci/DigitalOcean-public.v2.yaml -o ${SPEC_FILE}

# .PHONY: bundle
# bundle: dev-dependencies download-spec ## Use openapi-cli to bundle the spec
# 	npm run bundle -- ${SPEC_FILE} -o ${BUNDLE_PATH}

.PHONY: autorest-python
autorest-python: dev-dependencies 
	cp -r do-client-python/digitalocean tests/
	find tests/digitalocean -type f ! -name "_patch.py" -exec rm -rf {} \;
	autorest client_gen_config.md --input-file=${SPEC_FILE} --output-folder=tests/ 