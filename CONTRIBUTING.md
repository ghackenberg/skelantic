# Contributing to Skelantic

Thank you for your interest in contributing to the Skelantic engine! This document outlines the architecture of the project and how to set up your local development environment.

## 🧠 Architecture & Design Principles

Skelantic is a framework for file-tree processing and repository governance. It consists of two main conceptual blocks:

1. **The Parsing Engine (`skelantic.templates`)**: Responsible for reading "Skeletal Templates", compiling them into a matching AST, and extracting raw text into structured dictionaries (and eventually Pydantic models).
2. **The Workflow Engine (`skelantic.commons`)**: Responsible for crawling the file system based on `config.yaml` files, executing the matching process, and running the decorated `@processor` functions in sequence.

### The 4 Processing Phases (Passes)

When the engine runs (`engine.run()`), it executes the following sequence:

| Phase | Name | Description |
| :--- | :--- | :--- |
| **Pass 0** | **Template Matching** | Verifies documents against Skeletal Templates using the custom AST parser (`SkeletalMatcher`) and extracts raw data into dictionaries. It then automatically validates this data against generated Pydantic models. |
| **Pass 1** | **Indexing** | Executes Python processors (`phase=1`) designed to collect data for later global checks (e.g., collecting all Markdown file paths). |
| **Pass 2** | **Validation** | Executes domain-specific Python processors (`phase=2`) on a per-file or per-directory basis to check constraints. |
| **Pass 3** | **Global Pass** | Executes system-wide checks (`phase=3`) (e.g., finding orphaned documents that were never linked to). |

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

If you are adding a new core feature:
1. Please ensure that the **I/O logic** (file reading/writing) remains strictly in the Workflow Engine (`commons/core.py`), and the Parsing Engine (`templates/`) remains pure logic.
2. Write unit tests for your changes in the `tests/` folder.
3. Run `invoke types` and `invoke test` before submitting a Pull Request.

## 📦 Release Workflow

Skelantic uses GitHub Actions to automate the release process to PyPI via Trusted Publishing. The project uses `hatch-vcs` for dynamic versioning, so you **do not** need to manually update a version number in a file. The Git tag is the single source of truth for the version.

To release a new version:

1. **Create and push a Git tag:** The CI/CD pipeline triggers the deployment exclusively on tags that start with `v`.
   ```bash
   git tag vX.Y.Z
   git push origin vX.Y.Z
   ```
2. **Automated Deployment:** Once the tag is pushed, GitHub Actions will:
   - Run the full test suite and type checker.
   - Build the source distribution and wheel, dynamically injecting the version from the Git tag.
   - Publish the artifacts to PyPI securely using OpenID Connect (OIDC).

Welcome aboard!
