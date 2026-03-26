---
name: skelantic
description: "Skelantic strictly governs this repository's architecture. CRITICAL RULES: 1. You MUST run `skelantic run` after modifying or creating any files. 2. NEVER create files or directories that are not explicitly allowed in a `.skelantic/config.yaml`. 3. ALWAYS run `skelantic generate` after modifying a config or template. Activate this skill for detailed instructions on how to manage the repository structure."
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
`skelantic info <intended/path>`
This will tell you if the path is allowed, which variables are required, and which template applies.

### 2. Creating a File
To understand the required content structure for a file, run:
`skelantic template <intended/path>`
This returns the raw Skeletal Template. NEVER guess the Markdown structure.

### 3. Implementing a Processor
When writing a Python processor, run:
`skelantic info <target/path>`
Copy the **Node Type** and the **Template Data** schema directly into your Python code to ensure perfect Dependency Injection and type safety.

### 4. The Validation Loop (Mandatory)
After every task, execute this sequence:
1. `skelantic generate` (Updates the types)
2. `skelantic run` (Validates the repo)
3. Fix all reported `❌ Unerlaubte Datei` or `❌ Syntax-Fehler`.

## 📚 Detailed Documentation
For deep dives into syntax, read these local files using your `read_file` tool:
- [Configuration Guide](docs/config.md)
- [Skeletal Templates Guide](docs/templates.md)
- [Processors & Context Guide](docs/processors.md)
- [Migration Guide](docs/migrations/001_v0.1.0_to_v0.2.0.md)
