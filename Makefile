##@ General

all:	help

# NOTE: Help stolen from operator-sdk auto-generated makefile!
.PHONY: help
help: ## Display this help.
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-\\.]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

.PHONY: test
test: ## Run the unit tests
	PARALLEL=1 ./scripts/run_tests.sh

.PHONY: fmt
fmt: ## Run code formatting
	./scripts/fmt.sh

##@ Develop

.PHONY: venv
venv: ## Create a local development venv with uv
	uv venv --python 3.12
	uv pip install -e .[test]

##@ Build

.PHONY: build
build: ## Build sdist and wheel artifacts (uses hatchling via uv)
	uv build --sdist --wheel

# Alias
.PHONY: wheel
wheel: build