# Oneshell means one can run multiple lines in a recipe in the same shell, so one doesn't have to
# chain commands together with semicolon
.ONESHELL:
SHELL=/bin/bash
ROOT_DIR=podflix
PACKAGE=src/podflix
DOC_DIR=./docs
TEST_DIR=./tests
TEST_MARKER=placeholder
TEST_OUTPUT_DIR=tests_outputs
PREK_FILE_PATHS=./src/podflix/__init__.py
PROFILE_FILE_PATH=./podflix/__init__.py
DOCKER_IMAGE=podflix
DOCKER_TARGET=development


.PHONY: help install test doc prek format profile
.DEFAULT_GOAL=help

help:
	@grep -E '^[0-9a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) |\
		 awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m\
		 %s\n", $$1, $$2}'

# If .env file exists, include it and export its variables
ifeq ($(shell test -f .env && echo 1),1)
    include .env
    export
endif

install-uv: ## Install uv
	! command -v uv &> /dev/null && curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR="~/.local/bin" sh

update-uv: ## Update uv to the latest version
	uv self update

install-base: ## Installs only package dependencies
	uv sync --frozen --no-dev --no-install-project

install: ## Installs the development version of the package
	$(MAKE) install-uv
	$(MAKE) update-uv
	uv sync --frozen
	$(MAKE) install-prek

install-no-cache: ## Installs the development version of the package without cache
	$(MAKE) install-uv
	$(MAKE) update-uv
	uv sync --frozen --no-cache
	$(MAKE) install-prek

install-prek: ## Install prek and git hooks
	uv tool install --upgrade prek
	prek install

update-dependencies: ## Updates the lockfiles and installs dependencies. Dependencies are updated if necessary
	uv sync

upgrade-dependencies: ## Updates the lockfiles and installs the latest version of the dependencies
	uv sync -U

test-one: ## Run specific tests with TEST_MARKER=<test_name>, default marker is `placeholder`
	uv lock --locked
	uv run --module pytest -m ${TEST_MARKER}

test-one-parallel: ## Run specific tests with TEST_MARKER=<test_name> in parallel, default marker is `placeholder`
	uv lock --locked
	uv run --module pytest -n auto -m ${TEST_MARKER}

test-all: ## Run all tests
	uv lock --locked
	uv run --module pytest

test-all-parallel: ## Run all tests with parallelization
	uv lock --locked
	uv run --module pytest -n auto

test-coverage: ## Run all tests with coverage
	uv lock --locked
	uv run --module pytest --cov=${PACKAGE} --cov-report=html:coverage

test-coverage-parallel:
	uv lock --locked
	uv run --module pytest -n auto --cov=${PACKAGE} --cov-report=html:coverage

test-docs: ## Test documentation examples with doctest
	uv lock --locked
	uv run --module pytest --doctest-modules ${PACKAGE}

test: clean-test test-all ## Cleans and runs all tests
test-parallel: clean-test test-all-parallel ## Cleans and runs all tests with parallelization

clean-test: ## Clean test related files left after test
	# rm -rf ./htmlcov
	# rm -rf ./coverage.xml
	find . -type f -regex '\.\/\.*coverage[^rc].*' -delete
	rm -rf ${TEST_OUTPUT_DIR}
	find ${TEST_DIR} -type f -regex '\.\/\.*coverage[^rc].*' -delete
	find ${TEST_DIR} -type d -name 'htmlcov' -exec rm -r {} +
	find . -type d -name '.pytest_cache' -prune -exec rm -rf {} \;

doc: ## Build documentation with mkdocs
	uv run mkdocs build

doc-dev: ## Show documentation preview with mkdocs
	uv run mkdocs serve -w ${PACKAGE}

prek-one: ## Run prek with specific files
	uv lock --locked
	prek run --files ${PREK_FILE_PATHS}

prek: ## Run prek for all package files
	uv lock --locked
	prek run --all-files

prek-clean: ## Clean prek cache
	prek cache clean

format: ## Format checks via prek hooks
	uv lock --locked
	prek run ruff-format --all-files

typecheck:  ## Checks code with Astral ty
	uv lock --locked
	uvx ty check ${PACKAGE}

typecheck-no-cache:  ## Checks code with Astral ty no cache
	uv lock --locked
	uvx ty check ${PACKAGE}

typecheck-report: ## Checks code with Astral ty and generates JUnit report
	uv lock --locked
	uvx ty check ${PACKAGE} --output-format junit > ty_report.xml

# profile: ## Profile the file with scalene and shows the report in the terminal
# 	uv lock --locked
# 	uv run --module scalene --cli --reduced-profile ${PROFILE_FILE_PATH}

# profile-gui: ## Profile the file with scalene and shows the report in the browser
# 	uv lock --locked
# 	uv run --module scalene ${PROFILE_FILE_PATH}

profile-builtin: ## Profile the file with cProfile and shows the report in the terminal
	uv lock --locked
	uv run --module cProfile -s tottime ${PROFILE_FILE_PATH}

docker-build: ## Build docker image
	docker build --tag ${DOCKER_IMAGE} --file docker/Dockerfile --target ${DOCKER_TARGET} .

reset-postgres-db: ## Reset the postgres database using prisma
	cd chainlit-datalayer
	uv run prisma migrate reset --force

reset-sqlite-db: ## Reset the sqlite database
	rm -f ./db.sqlite
	uv run src/podflix/db/init_db.py

create-ssl-cert: ## Create a self-signed SSL certificate for localhost development
	bash scripts/create_ssl_cert.sh

download-hf-model: ## Download the huggingface model
	uv run src/podflix/utils/hf_related.py

run-mock-graph:
	uv run chainlit run src/podflix/gui/mock.py --host 0.0.0.0 --port 5000 --headless

run-audio-graph:
	uv run chainlit run src/podflix/gui/audio.py --host 0.0.0.0 --port 5000 --headless

run-chat-graph:
	uv run chainlit run src/podflix/gui/base_chat.py --host 0.0.0.0 --port 5000 --headless

run-fasthtml:
	uv run uvicorn podflix.gui.fasthtml_ui.home:app --host 0.0.0.0 --port 5002
	# uv run uvicorn podflix.gui.fasthtml_ui.copilot:app --host 0.0.0.0 --port 5002

run-backend:
	uv run uvicorn podflix.gui.backend:app --host 0.0.0.0 --port 5000
	# uv run uvicorn podflix.gui.backend:app --host 0.0.0.0 --port 5000 --root-path=/chat
