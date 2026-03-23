# Skelantic File System Nodes (FSNode)

When Skelantic traverses your repository, it wraps every file and directory into an object-oriented API before passing it to your `@processor` functions. This abstraction allows you to easily navigate the file tree and access file contents.

## The Node Class Hierarchy

Skelantic provides three main node types:

1. **`FSNode`** (Base Class)
2. **`DirectoryNode`** (Inherits from FSNode)
3. **`FileNode`** (Inherits from FSNode)

## Injecting Nodes into Processors

To use a node in your processor, simply add it to your function signature. The Skelantic engine will automatically inject the correct instance.

```python
from skelantic.commons.decorators import processor
from skelantic.commons.nodes import FileNode

@processor(match="docs/**/*.md", phase=2)
def check_markdown_files(node: FileNode) -> list[str]:
    # Work with the node here...
    return []
```

---

## The `FSNode` Base API

Every node (whether file or directory) exposes the following properties and methods:

### `node.name` (str)
The name of the file or directory.
*Example:* `"issue-001.md"`

### `node.abs_path` (pathlib.Path)
The absolute, fully resolved file system path to the item.
*Example:* `Path("C:/projects/my_project/docs/issues/issue-001.md")`

### `node.rel_path` (pathlib.Path)
The relative path of the item from the root of the repository (the folder where `skelantic run` was executed). This is usually the path you want to use for logging and indexing.
*Example:* `Path("docs/issues/issue-001.md")`

### `node.parent_node` (Optional[DirectoryNode])
Returns the strongly typed `DirectoryNode` (or its specific generated subclass) that contains this node. Useful for navigating "up" the repository tree.
*Example:* `parent = node.parent_node`

### `node.path_params` (BaseModel)
If the configuration for this node included variables in the path (e.g., `{slug}.md`), this property holds a strictly typed Pydantic model containing those extracted variables. If no variables were defined, this property may not exist.
*Example:* `slug = node.path_params.slug`

### `node.data` (Any)
If this node is a file that matched a Skeletal Template, this property holds the fully validated Pydantic model for this file (accessible via `node.data`). If it didn't match a template, this is the raw dictionary or `None`.

### `node.resolve(path_str: str) -> Optional[FSNode]`
A powerful helper method to resolve relative paths starting from the current node and fetch their corresponding `FSNode` from the engine's memory.
*Example:* 
```python
# If node is 'docs/issues/001.md'
target_node = node.resolve("../milestones/m1.md")
if target_node:
    print(f"Found milestone: {target_node.name}")
```

---

## The `FileNode` API

In addition to the `FSNode` base methods, a `FileNode` provides access to the physical contents of the file.

### `node.document` (Document / MarkdownDocument)
A wrapper around the file's content that provides fault-tolerant reading and specific helpers.

#### Reading Raw Content
You can access the raw string content of any file:
```python
content = node.document.raw_content
if "TODO" in content:
    return ["File contains unresolved TODOs."]
```

#### Markdown Helpers
If the file ends with `.md`, `node.document` is automatically instantiated as a `MarkdownDocument`. This provides additional helper methods:

* **`node.document.get_links() -> list[str]`**
  Extracts all markdown links (e.g., `[label](url)`) and returns a list of the target URLs/paths. It automatically ignores `http://`, `https://`, `mailto:`, and anchor links (`#`).
  *Example:* `["../milestones/m1.md", "other-issue.md"]`

* **`node.document.get_tables() -> list[dict]`**
  A simple heuristic that returns a non-empty list if the markdown file contains a markdown table structure (`| ... |`).