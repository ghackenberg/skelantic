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

* `description` **(Required)**: A short description of the matched file.
* `template` (Optional): The path to a Skeletal Template file (`.md` or `.txt`) used to parse and validate the file's content.
* `optional` (Optional, `bool`): If set to `true`, the engine will only emit a **warning** (instead of an error) if the file is missing.
* `silent` (Optional, `bool`): If set to `true` (and `optional` is also `true`), the engine will emit **no warning** if the file is missing.
* `authorize` (Optional, `bool`): If `false`, allows matching against a pattern without granting implicit authorization for its existence.

## Directory Configuration

When configuring a directory within the `directories` section, the following keys are allowed:

* `description` **(Required)**: A short description of the matched directory.
* `files` (Optional): Nested dictionary of file patterns inside this directory.
* `directories` (Optional): Nested dictionary of directory patterns inside this directory.
* `optional` (Optional, `bool`): If set to `true`, the engine will only emit a **warning** (instead of an error) if the directory is missing.
* `silent` (Optional, `bool`): If set to `true` (and `optional` is also `true`), the engine will emit **no warning** if the directory is missing.
* `authorize` (Optional, `bool`): If `false`, allows matching against a pattern without granting implicit authorization for its existence.
* `model` (Optional, `str`): Overrides the auto-generated PascalCase name for this node's class in the `RepoGraph`.
* `property` (Optional, `str`): Overrides the auto-generated snake_case property name used to access this node from its parent in the `RepoGraph`.

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

## Deep Path Expansion

Skelantic supports deep paths directly in the keys of `files` and `directories`. You don't need to deeply nest your YAML if you only want to define a specific deep path.

```yaml
directories:
  "src/skelantic/commons":
    description: "The workflow engine directory"
```
Behind the scenes, Skelantic automatically expands `"src/skelantic/commons"` into the corresponding nested directory tree, making the `config.yaml` much more concise.

## Path Patterns & Variables

Skelantic features a powerful pattern matching engine for file and directory names.

### Wildcards

* `*`: Matches any sequence of characters within a single directory level (excluding `/`).
* `**`: Recursive glob. Matches any character including directory boundaries (`.*`).
* `**/`: When placed at the **start** of a pattern (e.g., `**/*.md`), it matches the subsequent pattern recursively in the current directory or any subdirectory.

### Path Variables

You can extract dynamic parts of paths into variables that are later passed into your Python processors. For more details on how to receive these variables in your code, see [Writing Processors > Injecting Path Variables](processors.md#injecting-path-variables-from-configyaml).

Path variables use the syntax `{variable_name:type(arguments)}`. 

#### 1. Default (No type)

If no type is specified, the parser assumes a single lowercase alphanumeric word (`[a-z][a-z0-9]*`).
* **Restriction:** The word must start with a letter.
* **Syntax:** `{variable_name}`

**Examples:**
* `"{slug}.md"` matches `feature.md` and extracts `slug="feature"`.
* `"{slug}.md"` matches `bug123.md` and extracts `slug="bug123"`.
* `"{slug}.md"` does **not** match `123bug.md` (does not start with a letter).
* `"{slug}.md"` does **not** match `new-feature.md` (contains a hyphen).

#### 2. Integer (`int`)

Matches a sequence of digits (`\d+`). You can enforce exact lengths or variable length ranges using arguments.
* **Syntax:** `{variable_name:int}` or `{variable_name:int(length)}` or `{variable_name:int(min,max)}`

**Examples:**
* `"{id:int}.md"` matches `42.md` and extracts `id="42"`.
* `"{id:int(4)}.md"` matches `0042.md` and extracts `id="0042"`.
* `"{id:int(4)}.md"` does **not** match `42.md` (too short).
* `"{id:int(1,4)}.md"` matches `42.md` and `0042.md`.

#### 3. Words (`words`)

Matches one or more hyphen-separated words (kebab-case). Each individual word must start with a letter.
* **Syntax:** `{variable_name:words}` or `{variable_name:words(length)}` or `{variable_name:words(min,max)}`

**Examples:**
* `"{title:words}.md"` matches `feature.md`.
* `"{title:words(3)}.md"` matches `new-feature-design.md` and extracts `title="new-feature-design"`.
* `"{title:words(1,3)}.md"` matches `design.md`, `feature-design.md`, and `new-feature-design.md`.
* `"{title:words(1,3)}.md"` does **not** match `1st-feature.md` (words must start with a letter).

#### 4. Fallback Behavior

Any unknown or misspelled type declaration falls back to the **Default** type (a single word) silently.
* **Example:** `"{slug:custom}.md"` behaves exactly like `"{slug}.md"`.
