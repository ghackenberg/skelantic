# Configuration Guide (`config.yaml`)

Skelantic operates on a **"Strict-by-Default" (Default-Deny)** philosophy. Every file and directory in your project must be explicitly permitted by a configuration file, usually named `config.yaml` or `.skelantic/config.yaml`. Anything not explicitly permitted is flagged as an error by the validation engine.

This document describes the schema of `config.yaml` and the various options available.

## Global Structure

The root of a `config.yaml` file defines the baseline configuration for a directory level. 

```yaml
description: "Brief description of this directory's purpose."
files:
  # ... file patterns and their configurations
directories:
  # ... directory patterns and their configurations
```

### Root Keys

* `description` **(Required)**: A human-readable explanation of what this directory or configuration scope represents.
* `files` (Optional): A dictionary of file matching patterns and their specific configurations.
* `directories` (Optional): A dictionary of directory matching patterns and their specific configurations.

## Node Configuration (Files & Directories)

Inside the `files` and `directories` dictionaries, the keys are path patterns (see "Path Patterns & Variables" below) and the values are the **Node Configurations**.

**CRITICAL RULE:** Deep paths (e.g., `src/commons`) and Glob wildcards (`*`, `**`) are **strictly forbidden** in node keys to guarantee type safety. You must nest your YAML or use Cascading Configs to represent deep structures.

```yaml
directories:
  "docs":
    description: "Main documentation folder"
    directories:
      "issues":
        description: "Task tracking"
        files:
          "{slug:words}.md":
            description: "An individual issue file"
            template: ".skelantic/templates/issue.md"
            optional: true
```

## File Configuration

When configuring a file within the `files` section, the following keys are allowed:

* `description` **(Required unless ignored)**: A short description of the matched file.
* `template` (Optional): The path to a Skeletal Template file (`.md` or `.txt`) used to parse and validate the file's content.
* `optional` (Optional, `bool`): If set to `true`, the engine will only emit a **warning** (instead of an error) if the file is missing.
* `silent` (Optional, `bool`): If set to `true` (and `optional` is also `true`), the engine will emit **no warning** if the file is missing.
* `ignore` (Optional, `bool`): If set to `true`, the file is completely ignored by the engine (useful for noise like `.pdf` or `~temp` files). If this is true, no other keys are allowed!

## Directory Configuration

When configuring a directory within the `directories` section, the following keys are allowed:

* `description` **(Required unless ignored)**: A short description of the matched directory.
* `files` (Optional): Nested dictionary of file patterns inside this directory.
* `directories` (Optional): Nested dictionary of directory patterns inside this directory.
* `optional` (Optional, `bool`): If set to `true`, the engine will only emit a **warning** (instead of an error) if the directory is missing.
* `silent` (Optional, `bool`): If set to `true` (and `optional` is also `true`), the engine will emit **no warning** if the directory is missing.
* `ignore` (Optional, `bool`): If set to `true`, the directory is completely ignored by the engine (useful for `node_modules` or `__pycache__`). If this is true, no other keys are allowed!
* `model` (Optional, `str`): Overrides the auto-generated PascalCase name for this node's class in the `RepoGraph`.
* `property` (Optional, `str`): Overrides the auto-generated snake_case property name used to access this node from its parent in the `RepoGraph`.

## Ignoring Files & Directories (The Noise Plane)

Skelantic is a "Strict-by-Default" system. If your repository contains cache files, build folders, or other "noise", you must tell Skelantic to ignore them, otherwise they will be flagged as an error (`Unerlaubte Datei`).

To ignore items, you define them just like regular files or directories, but set `ignore: true`.

**Example:**
```yaml
directories:
  "node_modules":
    ignore: true
files:
  "{any_name}.pdf":
    ignore: true
  "{temp_file}.tmp":
    ignore: true
```
*Note: Because wildcards are banned, you must use standard variables like `{any_name}` to catch files you want to ignore.*

## Cascading Configurations (Sub-Directory Configs)

For large repositories or monorepos, keeping everything in a single root `config.yaml` can become overwhelming. Skelantic supports **cascading configurations**. 

You can place a `.skelantic/config.yaml` inside any subdirectory of your repository. 

When the Skelantic engine (or the `generate` command) encounters a local config file during traversal, it **deep-merges** the local rules into the global configuration tree. 

**Example:**
If you have a root config:
```yaml
directories:
  "docs":
    description: "Documentation"
```
And a local config in `docs/.skelantic/config.yaml`:
```yaml
files:
  "README.md":
    description: "Docs Readme"
```
Skelantic will treat this exactly as if the root config contained:
```yaml
directories:
  "docs":
    description: "Documentation"
    files:
      "README.md":
        description: "Docs Readme"
```

This allows individual teams or modules in a monorepo to manage their own local Linter rules and Skelantic configurations autonomously!

## Path Patterns & Variables

Skelantic features a powerful pattern matching engine for file and directory names. **Glob wildcards (`*`, `**`) are not allowed.**

### Path Variables

You can extract dynamic parts of paths into variables that are later passed into your Python processors. For more details on how to receive these variables in your code, see [Writing Processors > Injecting Path Variables](processors.md#injecting-path-variables-from-configyaml).

Path variables use the syntax `{variable_name:type(arguments)}`. 

#### 1. Digit (`digit`)

Matches a sequence of digits (`\d`). You can enforce exact lengths or variable length ranges using arguments. If no argument is provided, exactly ONE digit is matched.
* **Syntax:** `{variable_name:digit}` or `{variable_name:digit(length)}` or `{variable_name:digit(min,max)}`

**Examples:**
* `"{id:digit(1,)}"` matches `42.md` and extracts `id="42"`.
* `"{id:digit(4)}"` matches `0042.md` and extracts `id="0042"`.
* `"{id:digit(4)}"` does **not** match `42.md` (too short).
* `"{id:digit}"` matches `4.md` but does **not** match `42.md` (too long).

#### 2. Char (`char`)

Matches alphanumeric characters (`[a-zA-Z0-9]`). You can enforce exact lengths or variable length ranges using arguments. If no argument is provided, exactly ONE character is matched.
* **Syntax:** `{variable_name:char}` or `{variable_name:char(length)}` or `{variable_name:char(min,max)}`

**Examples:**
* `"{title:char(1,)}.md"` matches `feature.md`.
* `"{initial:char}.md"` matches `f.md` but does **not** match `feature.md`.
* `"{title:char(3)}.md"` matches `new.md` and extracts `title="new"`.
