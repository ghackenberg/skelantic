# Command Line Interface (CLI) Reference

The `skelantic` command-line tool is the primary way to interact with the framework. It provides commands to generate models, run the validation engine, and access documentation.

## `skelantic run`

Executes the Skelantic workflow engine against your repository. It parses configuration files, matches files against templates, and executes your custom Python processor functions.

**Usage:**
```bash
skelantic run -p <processors_package> -t <types_module> [options]
```

**Arguments:**
* `-t`, `--types` **(Required)**: The Python module path where your generated `skelantic_types.py` is located (e.g., `tools.skelantic_types`).
* `-p`, `--processors` (Optional): The Python package path containing your `@processor` functions (e.g., `tools.processors`). If provided, Skelantic will dynamically import all modules within this package to register the processors.
* `-d`, `--dir` (Optional): The base directory to lint. Defaults to the current working directory (`.`).
* `-v`, `--verbose` (Optional): Enables verbose output, which is helpful for debugging why a specific file was or was not matched.

---

## `skelantic generate`

Parses your `.skelantic/templates/*.md` files and your `.skelantic/config.yaml` to automatically generate a single, strongly-typed "File System ORM" (`RepoGraph`). You should run this command whenever you change the structure of a Skeletal Template or your `config.yaml`.

**Usage:**
```bash
skelantic generate -o <output_file>
```

**Arguments:**
* `-o`, `--output` **(Required)**: The file path where the generated Python code should be saved (e.g., `tools/skelantic_types.py`). This file will contain the `RepoGraph` and all Pydantic models.

---

## `skelantic migrate`

Outputs strictly formatted XML prompts designed to guide AI coding agents through upgrading a target repository to a newer version of Skelantic. The command determines the repository's current version (from `.skelantic/version`) and reads the required migration steps bundled within the `skelantic` package.

**Usage:**
```bash
skelantic migrate [--from <version>]
```

**Arguments:**
* `--from` (Optional): Manually specify the version to migrate from (e.g., `0.1.0`). If omitted, the command automatically reads the `.skelantic/version` file in the current directory.

---

## `skelantic docs`

A specialized command that prints the Skelantic framework documentation directly to your terminal. 

This command is particularly powerful for **AI Coding Agents** (like Gemini, Claude, or Cursor). Because it reads the documentation directly from the installed Python package, it guarantees that the documentation perfectly matches the installed version of the framework.

**Usage for Humans:**
```bash
skelantic docs             # Lists all available documentation topics
skelantic docs templates   # Prints the Skeletal Templates syntax guide
skelantic docs config      # Prints the config.yaml guide
```

**Usage for AI Agents:**
```bash
skelantic docs --all
```
*The `--all` flag dumps the entire framework documentation (README, CLI, Config, Templates, Processors, Nodes) formatted with XML tags (`<document path="...">`). This is the recommended way to inject Skelantic's context into an LLM prompt.*
