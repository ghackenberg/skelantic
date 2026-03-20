# Skeletal Templates

Skeletal Templates are the heart of Skelantic's parsing engine. They define the expected structure of your text files (usually Markdown) and allow Skelantic to automatically extract structured data and generate Pydantic models.

The parser reads your document line by line and matches it against your template.

## 1. Variables & Types
You extract values using the `{{name:type}}` syntax.

| Type | Regex Behavior | Description |
| :--- | :--- | :--- |
| **`str`** | `.+?` | A single line of text (at least one character). |
| **`any`** | `.*?` | Any text (can be empty). |
| **`int`** | `\d+` | An integer number. |
| **`decimal`** | `\d+(\.\d+)?` | A decimal number (optional dot). |
| **`bool`** | `true\|false\|True\|False` | A boolean value (case-insensitive). |
| **`slug`** | `[a-zA-Z0-9-_]+` | Alphanumeric with dashes/underscores. |
| **`snake_case`** | `[a-z0-9]+(_[a-z0-9]+)*` | Lowercase words separated by underscores. |
| **`kebab-case`** | `[a-z0-9]+(-[a-z0-9]+)*` | Lowercase words separated by dashes. |
| **`camelCase`** | `[a-z][a-zA-Z0-9]*` | First word lowercase, following words capitalized. |
| **`enum[A,B]`** | `A\|B` | Exact match against predefined literals. |
| **`text`** | (Multiline) | Captures all following lines until the next template instruction matches. |
| **`json`** | (Multiline) | Like `text`, but explicitly validates the captured block as valid JSON. |

*Example:*
```markdown
# Server Config: {{server_name:slug}}
Port: {{port:int}}
Active: {{is_active:bool}}
```

## 2. Block Structures & Control Flow

Skelantic supports advanced structural directives to map complex documents into nested dictionaries (and nested Pydantic models).

### 📦 Blocks: `[[block:name]]`
Groups a section of the document into a nested dictionary/model.

```markdown
[[block:metadata]]
Author: {{author:str}}
Date: {{date:str}}
[[/block]]
```
*(Generates a nested Pydantic model `MetadataBlock`)*

### 🔄 Repeats: `[[repeat:name]]`
Allows a section of the template to be matched 0 to N times. Extracts a list of dictionaries/models.

```markdown
## Server Nodes
[[repeat:nodes]]
* Node: {{node_name:slug}} (IP: {{ip:str}})
[[/repeat]]
```
*(Generates a `List[NodesItem]` in Pydantic)*

### 🔀 Choices: `[[choice:name]]`
Allows conditional structures (decision trees) based on the document's content.

```markdown
## Payload
[[choice:payload]]
[[case:JSON]]
Type: Application/JSON
Body:
{{body:json}}
[[/case]]
[[case:TEXT]]
Type: Text/Plain
Content: {{content:text}}
[[/case]]
[[/choice]]
```
*(Skelantic will try to match `JSON`. If it fails, it tries `TEXT`. It automatically extracts the winning case into the `payload_type` variable).*

## 3. Multiline Extractions (`text` & `json`)
The types `text` and `json` are special: they consume multiple lines of the document. Skelantic uses **Lookahead matching** to figure out when to stop consuming lines. 

It stops capturing when it sees a line in the document that perfectly matches the *next* instruction in your template (or the start of the next `[[block]]` / `[[repeat]]` item).

```markdown
## Description
{{description:text}}

## Next Section
```
*In this example, `{{description:text}}` consumes all lines until it encounters a line starting with exactly `## Next Section`.*