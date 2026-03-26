# Command Line Interface (CLI) Reference

The `skelantic` command-line tool is the primary way to interact with the framework. It is designed to be **AI-Native**, providing structured information for coding agents while enforcing strict repository governance.

## Configuration & Settings

Skelantic uses a settings file at `.skelantic/settings.yaml` to store default paths. If this file exists, most CLI arguments become optional.

**Default Settings:**
```yaml
types_file: "tools/skelantic/types.py"
types_module: "tools.skelantic.types"
processors_package: "tools.skelantic.processors"
```

---

## `skelantic run`

Executes the Skelantic workflow engine. It validates the repository against the configuration and executes custom Python processor functions. **It always operates on the Current Working Directory (CWD).**

The output is grouped by file and processor (`⚙️ module:method`) for maximum readability.

**Usage:**
```bash
skelantic run [options]
```

**Arguments:**
* `-v`, `--verbose`: Enables verbose matching logs.

---

## `skelantic processors`

Lists all registered processors (internal and custom) and their metadata. This is the primary way to discover which logic governs your repository.

**Usage:**
```bash
skelantic processors
```

The command displays:
* **Execution Phase**: When the processor runs.
* **Match Pattern**: Which files/directories are targeted.
* **Source File**: The physical location of the logic.
* **Docstring**: The semantic description of the rule.

---

## `skelantic generate`

Parses your templates and `config.yaml` to generate the strongly-typed `RepoGraph` and Pydantic models.

**Usage:**
```bash
skelantic generate [options]
```

**Arguments:**
* `-v`, `--verbose`: Enables verbose matching logs.

---

## `skelantic init`

Initializes a new Skelantic project. It creates the base folder structure, a default configuration, and deploys the **Gemini Skill** to `.gemini/skills/skelantic/`. It also generates the initial `.skelantic/settings.yaml`.

**Usage:**
```bash
skelantic init
```

---

## `skelantic migrate`

Updates the repository to the current Skelantic version. It refreshes the local Skill files and updates the `.skelantic/version` file.

**Usage:**
```bash
skelantic migrate
```

---

## `skelantic info`

The "Architecture Orakel". It virtually resolves a path against the schema (even if the file doesn't exist yet) and returns the required types, variables, and data schemas.

**Usage:**
```bash
skelantic info <path>
```

---

## `skelantic template`

Returns the raw Skeletal Template content for a given target path.

**Usage:**
```bash
skelantic template <path>
```

---

## 🛡️ Version Checking

Skelantic automatically checks for version mismatches.
* If your **Pip package** is older than the repository, it will prompt you to run `pip install --upgrade skelantic`.
* If your **Repository** is older than the installed package, it will prompt you to run `skelantic migrate`.
