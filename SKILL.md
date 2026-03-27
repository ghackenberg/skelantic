---
name: skelantic
description: "Skelantic strictly governs this repository's architecture. CRITICAL RULES: 1. You MUST run `skelantic verify` after every modification. 2. NEVER create files or directories not allowed in `config.yaml`. 3. DO NOT define configuration for reserved/ignored names like `.skelantic` or `__pycache__`. 4. If any step in verify fails, follow the 'Recommended action'. Activate this skill for detailed instructions."
---

# 🛡️ Skelantic Agent Skill

You are an expert at managing repositories governed by the Skelantic framework. Your primary goal is to ensure that the file tree remains 100% consistent with the declared architecture.

## ⚠️ Hard Constraints (Gotchas)

1. **Explicit Typing Only:** You MUST use strictly typed path variables in `config.yaml` (e.g., `{name:char(1,)}` or `{id:digit(4)}`). The old `{slug}` fallback is removed.
2. **No Wildcards:** Do NOT use `*` or `**` in `files` or `directories` keys in `config.yaml`. Use typed variables instead.
3. **No Deep Paths:** Keys in `config.yaml` cannot contain slashes (`/`). Use nested YAML structures or cascading configs.
4. **Pure Processors:** Python `@processor` functions must never perform I/O operations (like `os.path` or `open`). Rely entirely on the injected `node` and its `document` or `data` properties.
5. **Reserved Names:** NEVER define rules for `.git`, `node_modules`, `venv`, `__pycache__`, `.skelantic`, `.pytest_cache`, `.mypy_cache`, `linter.yaml`, or `.coverage` in your `config.yaml`. These are automatically ignored by Skelantic and will cause validation errors if used in configuration.

## 🔄 Core Workflows

### 1. Planning a Change
Before creating a new file or directory, ALWAYS run:
* `skelantic info <intended/path>`: Tells you if the path is allowed and which types apply.
* `skelantic processors`: Gives you a global overview of all active validation rules and their documentation.

### 2. Creating a File
To understand the required content structure for a file, run:
`skelantic template <intended/path>`
This returns the raw Skeletal Template. NEVER guess the Markdown structure.

### 3. Implementing or Fixing a Processor
When a validation fails or you need to write a new one:
1. Run `skelantic processors` to find the physical file and function responsible for the rule.
2. Run `skelantic info <target/path>` to get the exact **Node Type** for type-hinting.

### 4. The Validation Loop (Mandatory)
After every task (modifying configs, templates, or processors), execute the full verification pipeline:
`skelantic verify`

This command performs four critical steps:
1. **Generate**: Updates the `RepoGraph` types.
2. **Right**: Runs strict `pyright` checks on your code.
3. **Test**: Runs `pytest` to ensure your processor logic is correct and has >= 90% coverage.
4. **Run**: Validates the actual repository structure.

**If any step fails:**
- Read the error message carefully. `skelantic verify` will suggest a **recommended action** (e.g., running a sub-command with `-v` for more details).
- Follow the recommended action to diagnose and fix all reported errors.
- NEVER ignore Pyright errors or low test coverage.

## 📚 Detailed Documentation
For deep dives into syntax, read these local files using your `read_file` tool:
- [Configuration Guide](docs/config.md)
- [Skeletal Templates Guide](docs/templates.md)
- [Processors & Context Guide](docs/processors.md)
- [Migration Guide](docs/migrations/001_v0.1.0_to_v0.2.0.md)
