# The Skelantic Workflow & Context

Skelantic operates in four distinct passes (phases). Understanding these phases and how the `LinterContext` works is key to writing powerful, repository-wide validations.

## 1. The 4 Processing Phases

When the engine runs (`skelantic run`), it executes the following sequence:

| Phase | Name | Description |
| :--- | :--- | :--- |
| **Pass 0** | **Template Matching** | Verifies documents against [Skeletal Templates](templates.md) using the custom AST parser (`SkeletalMatcher`) and extracts raw data into dictionaries. It then automatically validates this data against generated Pydantic models. All data is saved into `ctx.extracted_data`. |
| **Pass 1** | **Indexing** | Executes Python processors (`phase=1`) designed to collect data for later global checks (e.g., collecting all Markdown file paths). |
| **Pass 2** | **Validation** | Executes domain-specific Python processors (`phase=2`) on a per-file or per-directory basis to check constraints. This is where most of your business logic lives. |
| **Pass 3** | **Global Pass** | Executes system-wide checks (`phase=3`) (e.g., finding orphaned documents that were never linked to). |

## 2. The `LinterContext` (Shared Memory)

The `LinterContext` is a shared state object injected into your processors. It holds the parsed data for every file in the repository, allowing you to perform relational checks (e.g. checking if an ID referenced in file A actually exists in file B).

It has two main attributes:
* `ctx.extracted_data`: A dictionary where the key is the relative path of the file (e.g. `docs/issues/001.md`), and the value is the parsed data (a dictionary).
* `ctx.store`: A generic dictionary where you can store custom indexing data during Phase 1 to use later in Phase 2 or Phase 3.

## 3. Real-World Processor Example

Here is a real-world example of how to write a processor that checks if a milestone ID referenced in an issue file actually exists as a file in the milestone folder.

```python
from typing import List, Callable, Set, cast
from skelantic.commons.decorators import processor
from skelantic.commons.context import LinterContext
from skelantic.commons.nodes import FileNode

# Import your generated models
from my_project.models.issue import IssueTemplate
from my_project.models.milestone import MilestoneTemplate

@processor(match="docs/issues/*.md", phase=2)
def issue_milestone_valid(node: FileNode, ctx: LinterContext) -> List[str]:
    # 1. Fetch the data for the CURRENT file being linted
    full_path = node.rel_path.as_posix()
    data = ctx.extracted_data.get(full_path, {})
    if not data: return []
    
    # 2. Cast the raw dictionary into your typsafe model
    model = IssueTemplate.model_validate(data)
    
    # 3. Check if the issue defines a milestone
    milestone_id = model.milestone
    if not milestone_id:
        return []
        
    # 4. Use the LinterContext to iterate over the entire repository
    #    and find all existing milestones.
    valid_milestones: Set[str] = set()
    for path, ex_data in ctx.extracted_data.items():
        if "docs/milestones/" in path and path.endswith('.md'):
            # Cast the remote file's data into its respective model
            m_model = MilestoneTemplate.model_validate(ex_data)
            if m_model.id:
                valid_milestones.add(m_model.id)
                
    # 5. Assert referential integrity
    if milestone_id not in valid_milestones:
        return [f"Issue Milestone Invalid: Milestone '{milestone_id}' does not exist in the milestones/ folder."]
        
    return []
```

## 4. Understanding the Injection Magic

The Skelantic `@processor` decorator uses Python's `inspect` module to dynamically inject exactly what your function needs based on its signature.

You can request any combination of the following parameters:
* `node: FileNode` (or `DirectoryNode`): The file currently being inspected. Gives you access to `node.rel_path`, `node.parent_dir`, and `node.document.raw_content`. For details, see the [File System Nodes API](nodes.md).
* `ctx: LinterContext`: The global shared memory.
* `tracer: Callable[[str], None]`: A function you can call to write debug logs. If your processor returns an error, these traces will be saved to `.skelantic/traces/` to help the user debug.

### Injecting Path Variables from `config.yaml`

One of the most powerful features of Skelantic is its ability to inject **Path Variables** directly into your processor functions. 

If your `.skelantic/config.yaml` defines a path with variables (e.g., `{id:int}-{slug:words}.md`), the Skelantic engine automatically extracts these values during the directory traversal. For a full list of available variable types, see the [Configuration Guide > Path Variables](config.md#path-variables).

To use them in your processor, simply add arguments to your function signature with the **exact same names** as the variables in your `config.yaml` (or the variables in your `@processor(match="...")` regex).

**Example `config.yaml`:**
```yaml
directories:
  "docs":
    directories:
      "teams":
        files:
          "{team_id:int}-{domain_name:words}.md":
            description: "A team definition file"
```

**Example Processor:**
```python
from typing import List
from skelantic.commons.decorators import processor
from skelantic.commons.nodes import FileNode

# The match parameter binds the processor, but the variables 
# are actually extracted by the engine using the config.yaml definition!
@processor(match="docs/teams/*.md", phase=2)
def validate_team_domain(node: FileNode, team_id: str, domain_name: str) -> List[str]:
    # team_id and domain_name are automatically injected!
    # E.g., for "docs/teams/004-auth-services.md":
    # team_id == "004"
    # domain_name == "auth-services"
    
    if not domain_name.islower():
        return [f"Domain name '{domain_name}' must be completely lowercase."]
        
    return []
```

**Note on Types:** Even if you defined `{team_id:int}` in your config, all path variables are currently injected as **strings** (`str`) into your Python functions. You must cast them to integers (`int(team_id)`) if you need to perform mathematical operations.