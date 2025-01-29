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
PRECOMMIT_FILE_PATHS=./podflix/__init__.py
PROFILE_FILE_PATH=./podflix/__init__.py
DOCKER_IMAGE=podflix
DOCKER_TARGET=development


.PHONY: help install test doc pre-commit format lint profile
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
	$(MAKE) install-precommit

install-no-cache: ## Installs the development version of the package without cache
	$(MAKE) install-uv
	$(MAKE) update-uv
	uv sync --frozen --no-cache
	$(MAKE) install-precommit

install-test: ## Install only test version of the package
	uv sync --frozen --only-group test

install-precommit: ## Install pre-commit hooks
	uv run pre-commit install

install-lint:
	uv pip install ruff==0.8.0

install-doc: ## Install mkdocs, mkdocs-material and mkdocstrings
	uv pip install mkdocs mkdocs-material mkdocstrings[python]

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

doc-github: ## Build documentation with mkdocs and deploy to github pages
	uv run mkdocs gh-deploy --force

doc-dev: ## Show documentation preview with mkdocs
	uv run mkdocs serve -w ${PACKAGE}

pre-commit-one: ## Run pre-commit with specific files
	uv lock --locked
	uv run pre-commit run --files ${PRECOMMIT_FILE_PATHS}

pre-commit: ## Run pre-commit for all package files
	uv lock --locked
	uv run pre-commit run --all-files

pre-commit-clean: ## Clean pre-commit cache
	uv run pre-commit clean

lint: ## Lint code with ruff
	uv lock --locked
	uv run --module ruff format ${PACKAGE} --check --diff
	uv run --module ruff check ${PACKAGE}

lint-report: ## Lint report for gitlab
	uv lock --locked
	uv run --module ruff format ${PACKAGE} --check --diff
	uv run --module ruff check ${PACKAGE} --format gitlab > gl-code-quality-report.json

format: ## Run ruff for all package files. CHANGES CODE
	uv lock --locked
	uv run --module ruff format ${PACKAGE}
	uv run --module ruff check ${PACKAGE} --fix --show-fixes

format-unsafe: ## Run ruff for all package files. with unsafe mode. CHANGES CODE
	uv lock --locked
	uv run --module ruff format ${PACKAGE}
	uv run --module ruff check ${PACKAGE} --fix --unsafe-fixes --show-fixes

update-submodules: ## Update submodules to their latest versions and commit changes
	git submodule update --remote chainlit-datalayer
	git add chainlit-datalayer
	git commit -m "chore: update chainlit-datalayer submodule" || echo "No changes to commit"

typecheck:  ## Checks code with mypy
	uv lock --locked
	uv run --module mypy --package ${PACKAGE}
	# MYPYPATH=src uv run --module mypy --package ${PACKAGE}

typecheck-no-cache:  ## Checks code with mypy no cache
	uv lock --locked
	uv run --module mypy --package ${PACKAGE} --no-incremental

typecheck-report: ## Checks code with mypy and generates html report
	uv lock --locked
	uv run --module mypy --package ${PACKAGE} --html-report mypy_report

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
