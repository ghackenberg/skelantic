# The Skelantic Workflow & Processors

Skelantic operates in four distinct passes (phases). Understanding these phases, how the `RepoGraph` translates into strongly-typed nodes, and how Dependency Injection works is key to writing powerful, repository-wide validations.

## 1. Dynamic Processing Phases

When the engine runs (`skelantic run`), it discovers all registered phase numbers from the `@processor` decorators and executes them in ascending order. Each phase consists of a **Local Pass** (per node) and a **Global Pass** (root only).

Common phases used in the architecture:

| Phase | Recommendation |
| :--- | :--- |
| **Pass 0** | **Implicit: Template Matching** (Always runs first). |
| **Phase 1** | **Indexing**: Collect data into global Singleton state models. |
| **Phase 2** | **Validation**: Domain-specific logic on a per-node basis. |
| **Phase 3** | **Global Pass**: Repository-wide integrity checks. |

*You can use any integer for a phase to define your own execution order.*

To see exactly when each processor runs, use:
`skelantic processors`

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

**Mandatory Docstrings:** Every processor function MUST have a Python docstring. This is used by `skelantic info` to describe the validation logic to agents and humans.

You can request any combination of the following parameters:
* `node: <Your RepoGraph Class>`: The file or directory currently being inspected. Gives you typsafe access to `node.rel_path`, `node.parent_node`, `node.root_node`, `node.path_params`, and `node.data`.
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

If your `.skelantic/config.yaml` defines a path with variables (e.g., `{team_id:digit}-{slug:char(1,)}.md`), the Skelantic engine automatically extracts these values and makes them available on the node in a strictly typed manner!

```python
@processor(phase=2)
def validate_team_file(node: RepoGraph.Docs.Teams.TeamFile):
    # Typsafe access to variables extracted from the path!
    team_id: str = node.path_params.team_id
    domain: str = node.path_params.slug
    
    if int(team_id) < 100:
        return ["Team IDs must be >= 100."]
```
