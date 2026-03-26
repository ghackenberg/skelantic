---
name: skelantic
description: "Skelantic strictly governs this repository's architecture. CRITICAL RULES: 1. You MUST run `skelantic verify` after every modification to ensure architectural, type, and logic integrity. 2. NEVER create files or directories that are not explicitly allowed in a `.skelantic/config.yaml`. 3. If any step in verify fails, run the specific command with `-v` (e.g., `skelantic run -v`) for detailed traces. Activate this skill for detailed instructions."
---

# 🛡️ Skelantic Agent Skill

You are an expert at managing repositories governed by the Skelantic framework. Your primary goal is to ensure that the file tree remains 100% consistent with the declared architecture.

## ⚠️ Hard Constraints (Gotchas)

1. **Explicit Typing Only:** You MUST use strictly typed path variables in `config.yaml` (e.g., `{name:char(1,)}` or `{id:digit(4)}`). The old `{slug}` fallback is removed.
2. **No Wildcards:** Do NOT use `*` or `**` in `files` or `directories` keys in `config.yaml`. Use typed variables instead.
3. **No Deep Paths:** Keys in `config.yaml` cannot contain slashes (`/`). Use nested YAML structures or cascading configs.
4. **Pure Processors:** Python `@processor` functions must never perform I/O operations (like `os.path` or `open`). Rely entirely on the injected `node` and its `document` or `data` properties.

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
- Run the specific command with `-v` (e.g., `skelantic run -v`) to see detailed traces.
- Fix all reported errors before considering the task complete.
- NEVER ignore Pyright errors or low test coverage.

## 📚 Detailed Documentation
For deep dives into syntax, read these local files using your `read_file` tool:
- [Configuration Guide](docs/config.md)
- [Skeletal Templates Guide](docs/templates.md)
- [Processors & Context Guide](docs/processors.md)
- [Migration Guide](docs/migrations/001_v0.1.0_to_v0.2.0.md)
