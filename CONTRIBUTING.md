# Contributing to Skelantic

Thank you for your interest in contributing to the Skelantic engine! This document outlines the architecture of the project and how to set up your local development environment.

## 🧠 Architecture & Design Principles

Skelantic is a framework for file-tree processing and repository governance. It consists of two main conceptual blocks:

1. **The Parsing Engine (`skelantic.templates`)**: Responsible for reading "Skeletal Templates", compiling them into a matching AST, and extracting raw text into structured dictionaries (and eventually Pydantic models).
2. **The Workflow Engine (`skelantic.commons`)**: Responsible for crawling the file system based on `config.yaml` files, executing the matching process, and running the decorated `@processor` functions in sequence.

### Dynamic Processing Phases

When the engine runs (`engine.run()`), it discovers all registered phase numbers from the `@processor` decorators and executes them in ascending order. Each phase consists of two steps:

1. **Local Pass**: Executes all processors matched to specific files or directories (including type-based matches).
2. **Global Pass**: Executes all processors matched to `"root"`.

Commonly used phases are:

| Phase | Recommended Use |
| :--- | :--- |
| **Pass 0** | **Implicit: Template Matching** (Always runs first, extracting data into `node.data`). |
| **Pass 1** | **Indexing**: Collect data into global Pydantic state models. |
| **Pass 2** | **Validation**: Perform per-node constraints and checks. |
| **Pass 3** | **Global Checks**: Perform repository-wide validations (e.g., finding orphaned files). |

*Note: You can define any integer as a phase (e.g., `phase=10`) to insert logic between or after these standard steps.*

## 🛠️ Local Development Setup

We use `invoke` for task running and `pyright` for strict static type checking.

### 1. Clone & Install
```bash
git clone https://github.com/ghackenberg/skelantic.git
cd skelantic

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate

# Install the package in editable mode with development dependencies
pip install -e .[dev]

# Install the task runner
pip install invoke
```

### 2. Available Commands

We have configured `tasks.py` to make development easy.

* **Run Type Checking (Pyright):**
  ```bash
  invoke types
  ```
  Skelantic is built with `typeCheckingMode = "strict"`. All new code must be fully type-hinted and pass Pyright without errors.

* **Run Unit Tests (Pytest):**
  ```bash
  invoke test
  ```
  This runs the test suite located in the `tests/` directory and calculates test coverage. We aim to keep coverage above 90%.

## 🏗️ Adding Features

Skelantic enforces a strict **GitHub Flow** with branch protection:
1. You cannot push directly to `main`. Create a feature branch (e.g., `feat/my-new-feature`).
2. Write unit tests for your changes in the `tests/` folder.
3. Ensure that the **I/O logic** remains strictly in the Workflow Engine (`commons/core.py`), and the Parsing Engine (`templates/`) remains pure logic.
4. Run `invoke types` and `invoke test` (Coverage must be >= 90%).
5. Submit a Pull Request.

**Important:** We enforce **Conventional Commits** via `pre-commit` and GitHub Actions. Your Pull Request title (which becomes the squash commit) must start with a valid type (e.g., `feat:`, `fix:`, `docs:`, `chore:`).

## 📦 Release Workflow (Automated)

Skelantic uses **Google Release Please** for fully automated release management. You **do not** need to manually update version numbers, write changelogs, or push Git tags.

To release a new version:

1. **Merge your Feature PRs:** As you merge PRs into `main` using "Squash and Merge", ensure the PR title is a Conventional Commit. If your PR introduces a breaking change, use `feat!:` or add a `BREAKING CHANGE:` footer.
2. **The Release PR:** A GitHub Action (Release Please) will automatically open or update a "Release Pull Request". This PR contains the auto-generated `CHANGELOG.md` and the calculated next version number.
3. **Approve the Release:** When you are ready to publish the package to PyPI, simply **merge the Release PR**.
4. **Automated Deployment:** Merging the Release PR automatically creates a Git tag (e.g., `v0.2.0`). This triggers our `ci.yml` pipeline to build the package (using `hatch-vcs` for dynamic versioning) and publish it to PyPI securely via OIDC.

### Writing AI Migration Prompts
If your PR introduces a breaking change to the processor API (e.g., changing how `node.data` is accessed), you MUST include a migration prompt for AI agents.
Create a Markdown file in `docs/migrations/` (e.g., `002_v0.2.0_to_v0.3.0.md`) detailing the required refactoring steps. This file will be bundled into the CLI so agents can use `skelantic migrate`.

Welcome aboard!
