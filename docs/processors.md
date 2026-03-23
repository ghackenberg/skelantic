# The Skelantic Workflow & Processors

Skelantic operates in four distinct passes (phases). Understanding these phases, how the `RepoGraph` translates into strongly-typed nodes, and how Dependency Injection works is key to writing powerful, repository-wide validations.

## 1. The 4 Processing Phases

When the engine runs (`skelantic run`), it executes the following sequence:

| Phase | Name | Description |
| :--- | :--- | :--- |
| **Pass 0** | **Template Matching & Graph Generation** | Verifies documents against [Skeletal Templates](templates.md). The engine automatically generates your `RepoGraph`, instantiates the correct specific node classes, and validates the extracted text against generated Pydantic models. |
| **Pass 1** | **Indexing** | Executes Python processors (`phase=1`) designed to collect data for later global checks (e.g., collecting all Markdown file paths into a global state). |
| **Pass 2** | **Validation** | Executes domain-specific Python processors (`phase=2`) on a per-file or per-directory basis to check constraints. This is where most of your business logic lives. |
| **Pass 3** | **Global Pass** | Executes system-wide checks (`phase=3`) (e.g., finding orphaned documents that were never linked to). |

## 2. Type-Based Matching

The core of Skelantic's processor system is **Type-Based Matching**. When you define your repository structure in `config.yaml`, Skelantic generates a strongly-typed `RepoGraph` class.

Instead of writing complex regex strings to target files, you simply **type-hint** your processor function with the specific class from your `RepoGraph`. The engine automatically knows *exactly* which files to pass to this processor.

```python
from typing import List
from skelantic.commons.decorators import processor

# Import the generated RepoGraph
from tools.skelantic_types import RepoGraph

# The engine executes this processor ONLY for files matching this specific class!
# The `match=` parameter is completely optional.
@processor(phase=2)
def validate_issue_status(node: RepoGraph.Docs.Issues.SlugMd) -> List[str]:
    # node.data is strongly-typed to the exact Pydantic model for this template!
    model = node.data
    
    if model and model.status == "DONE" and not model.description:
        return ["DONE issues must have a description."]
        
    return []
```

## 3. Dependency Injection (The Magic)

The Skelantic `@processor` decorator uses Python's `inspect` module to dynamically inject exactly what your function needs based on its signature.

You can request any combination of the following parameters:
* `node: <Your RepoGraph Class>`: The file or directory currently being inspected. Gives you typsafe access to `node.rel_path`, `node.parent_node`, `node.path_params`, and `node.data`.
* `tracer: Callable[[str], None]`: A function you can call to write debug logs. If your processor returns an error, these traces will be saved to `.skelantic/traces/` to help the user debug.

### Injecting Global State

If you need to share data between processors (e.g., aggregating data in Phase 1 to validate it in Phase 3), you can define a custom Pydantic `BaseModel` for your state.

Simply add your state class to the processor's signature. **Skelantic will automatically instantiate it as a Singleton and inject it!**

```python
from typing import Set, List
from pydantic import BaseModel, Field
from skelantic.commons.decorators import processor
from skelantic.commons.nodes import MarkdownNode
from tools.skelantic_types import RepoGraph

# 1. Define your custom State
class DocumentState(BaseModel):
    all_markdown_files: Set[str] = Field(default_factory=set)
    referenced_files: Set[str] = Field(default_factory=set)

# 2. Inject it into Phase 1 to collect data
#    (Using the base class MarkdownNode to target ALL markdown files)
@processor(phase=1)
def collect_links(node: MarkdownNode, state: DocumentState):
    state.all_markdown_files.add(node.rel_path.as_posix())
    for link in node.document.get_links():
        state.referenced_files.add(link)

# 3. Inject it into Phase 3 to validate global constraints
@processor(match="root", phase=3)
def check_orphans(state: DocumentState) -> List[str]:
    orphans = state.all_markdown_files - state.referenced_files
    if orphans:
        return [f"Found orphaned documents: {orphans}"]
    return []
```

### Path Variables (`path_params`)

If your `.skelantic/config.yaml` defines a path with variables (e.g., `{team_id:int}-{slug:words}.md`), the Skelantic engine automatically extracts these values and makes them available on the node in a strictly typed manner!

```python
@processor(phase=2)
def validate_team_file(node: RepoGraph.Docs.Teams.TeamFile):
    # Typsafe access to variables extracted from the path!
    team_id: int = node.path_params.team_id
    domain: str = node.path_params.slug
    
    if team_id < 100:
        return ["Team IDs must be >= 100."]
```
