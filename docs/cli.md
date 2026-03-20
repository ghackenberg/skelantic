# Command Line Interface (CLI) Reference

The `skelantic` command-line tool is the primary way to interact with the framework. It provides commands to generate models, run the validation engine, and access documentation.

## `skelantic run`

Executes the Skelantic workflow engine against your repository. It parses configuration files, matches files against templates, and executes your custom Python processor functions.

**Usage:**
```bash
skelantic run -p <processors_package> -m <models_package> [options]
```

**Arguments:**
* `-m`, `--models` **(Required)**: The Python package path where your generated Pydantic models are located (e.g., `my_project.models`).
* `-p`, `--processors` (Optional): The Python package path containing your `@processor` functions (e.g., `my_project.processors`). If provided, Skelantic will dynamically import all modules within this package to register the processors.
* `-d`, `--dir` (Optional): The base directory to lint. Defaults to the current working directory (`.`).
* `-v`, `--verbose` (Optional): Enables verbose output, which is helpful for debugging why a specific file was or was not matched.

---

## `skelantic generate`

Parses your `.skelantic/templates/*.md` files and automatically generates strongly-typed Pydantic models into the specified output directory. You should run this command whenever you change the structure of a Skeletal Template.

**Usage:**
```bash
skelantic generate -o <output_directory>
```

**Arguments:**
* `-o`, `--output` **(Required)**: The directory where the generated `.py` files should be saved. This directory must exist or will be created.

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
