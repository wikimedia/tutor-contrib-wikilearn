.DEFAULT_GOAL := help
.PHONY: docs
SRC_DIRS = ./tutorwikilearn
BLACK_OPTS = --exclude templates ${SRC_DIRS}

# === Wikilearn branch versions ===
WIKILEARN_EDX_PLATFORM_VERSION := $(shell python -c 'import tutorwikilearn.constants as c; print(c.WIKILEARN_EDX_PLATFORM_VERSION)')
WIKILEARN_MESSENGER_MFE_VERSION := $(shell python -c 'import tutorwikilearn.constants as c; print(c.WIKILEARN_MESSENGER_MFE_VERSION)')
WIKILEARN_DISCUSSIONS_MFE_VERSION := $(shell python -c 'import tutorwikilearn.constants as c; print(c.WIKILEARN_DISCUSSIONS_MFE_VERSION)')
WIKILEARN_EDX_FEATURES_VERSION := $(shell python -c 'import tutorwikilearn.constants as c; print(c.WIKILEARN_EDX_FEATURES_VERSION)')
WIKILEARN_INDIGO_BRANCH_VERSION := $(shell python -c 'import tutorwikilearn.constants as c; print(c.WIKILEARN_INDIGO_BRANCH_VERSION)')

# Warning: These checks are not necessarily run on every PR.
test: test-lint test-types test-format  # Run some static checks.

test-format: ## Run code formatting tests
	black --check --diff $(BLACK_OPTS)

test-lint: ## Run code linting tests
	pylint --errors-only --enable=unused-import,unused-argument --ignore=templates --ignore=docs/_ext ${SRC_DIRS}

test-types: ## Run type checks.
	mypy --exclude=templates --ignore-missing-imports --implicit-reexport --strict ${SRC_DIRS}

format: ## Format code automatically
	black $(BLACK_OPTS)

isort: ##  Sort imports. This target is not mandatory because the output may be incompatible with black formatting. Provided for convenience purposes.
	isort --skip=templates ${SRC_DIRS}

install: ## Install wikilearn plugin and dependencies in editable mode
	@echo "Installing tutor-contrib-wikilearn in editable mode..."
	pip install --upgrade --editable .

	@echo "Installing tutor-indigo-wikilearn from branch '${WIKILEARN_INDIGO_BRANCH_VERSION}'..."
	pip install --upgrade --editable "git+https://github.com/wikimedia/tutor-indigo-wikilearn.git@${WIKILEARN_INDIGO_BRANCH_VERSION}#egg=tutor-indigo-wikilearn"

setup:
	@echo "Enabling Tutor plugins..."
	tutor plugins enable wikilearn
	tutor plugins enable mfe indigo notes forum

clone-indigo:
	@echo "Cloning tutor-indigo-wikilearn..."
	cd .. && \
	{ \
		echo "Checking out branch: $(WIKILEARN_INDIGO_BRANCH_VERSION)"; \
		git clone -b $(WIKILEARN_INDIGO_BRANCH_VERSION) "https://github.com/wikimedia/tutor-indigo-wikilearn.git" || true; \
	}

clone-edx-platform:
	@echo "Cloning edx-platform..."
	cd .. && \
	{ \
		echo "Checking out branch: $(WIKILEARN_EDX_PLATFORM_VERSION)"; \
		git clone -b $(WIKILEARN_EDX_PLATFORM_VERSION) "https://github.com/wikimedia/edx-platform.git" || true; \
	}

clone-messenger:
	@echo "Cloning frontend-app-messenger..."
	cd .. && \
	{ \
		echo "Checking out branch: $(WIKILEARN_MESSENGER_MFE_VERSION)"; \
		git clone -b $(WIKILEARN_MESSENGER_MFE_VERSION) "https://github.com/wikimedia/frontend-app-messenger.git" || true; \
	}

clone-discussions:
	@echo "Cloning frontend-app-discussions..."
	cd .. && \
	{ \
		echo "Checking out branch: $(WIKILEARN_DISCUSSIONS_MFE_VERSION)"; \
		git clone -b $(WIKILEARN_DISCUSSIONS_MFE_VERSION) "https://github.com/edly-io/frontend-app-discussions.git" || true; \
	}

clone-features:
	@echo "Cloning openedx-wikilearn-features..."
	cd .. && \
	{ \
		echo "Checking out branch: $(WIKILEARN_EDX_FEATURES_VERSION)"; \
		git clone -b $(WIKILEARN_EDX_FEATURES_VERSION) "https://github.com/wikimedia/openedx-wikilearn-features.git" || true; \
	}

clone-all: clone-indigo clone-edx-platform clone-messenger clone-discussions clone-features

ESCAPE = 
help: ## Print this help
	@grep -E '^([a-zA-Z_-]+:.*?## .*|######* .+)$$' Makefile \
		| sed 's/######* \(.*\)/@               $(ESCAPE)[1;31m\1$(ESCAPE)[0m/g' | tr '@' '\n' \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "\033[33m%-30s\033[0m %s\n", $$1, $$2}'
