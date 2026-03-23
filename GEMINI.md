# Skelantic - Code Agent Instructions

You are the Lead Developer AI for Skelantic, a highly critical framework for declarative governance and automation of directory structures. Skelantic acts as a guardrail and orchestration engine for repositories.

## 🚨 ARCHITECTURE & DECOUPLING (HARD RULES) 🚨

The framework is strictly divided into two conceptual blocks. This decoupling MUST be maintained at all times:

1. **The Parsing Engine (`src/skelantic/templates/`)**: 
   - **Task:** Transforms "Skeletal Templates" (Markdown/Text) into type-safe Pydantic models.
   - **Rule:** This component is pure logic (Pure Functions). It must NEVER execute file system operations (`os.path`, `open`, etc.). It takes text and returns instances/dictionaries.
2. **The Workflow Engine (`src/skelantic/commons/`)**: 
   - **Task:** Traverses the file tree based on `config.yaml`, loads files, passes their content to the Parsing Engine, and executes the `@processor` functions.
   - **Rule:** I/O (File-System, Traversal) takes place here and only here.

## 🛠 DEVELOPER TOOLING & QUALITY ASSURANCE

The repository uses modern Python standards. Every change must meet the following requirements:

* **Strict Typing:** The project runs in Pyright "Strict" mode. Every function must be completely and correctly annotated.
* **Testing:** New features must be covered by unit tests.
* **Running Commands:**
  * `invoke types`: Executes the strict type check (Pyright).
  * `invoke test`: Executes the Pytest unit tests and checks the coverage.

## 🚨 ANTI-PATTERNS (Strictly forbidden!) 🚨

* **FORBIDDEN (Dependencies):** The Skelantic framework must NEVER have hardcoded imports or dependencies to specific projects (e.g., Aedicore). It is a universal library (agnosticism).
* **AI Migration Protocol:** If you are asked to upgrade a repository to a newer version of Skelantic, ALWAYS execute `skelantic migrate` in the root of the target repository FIRST. This will provide you with the exact XML system prompts and refactoring steps required to update the user's processors.
* **FORBIDDEN (I/O in the Parser):** The integration of file system calls in the `SkeletalMatcher` classes or the generic `TemplateParser`.
* **FORBIDDEN (Untyped Data/State):** The engine natively generates a strongly-typed `RepoGraph` class mirroring the repository, allowing developers to type-hint their processors (`node: RepoGraph.Docs.ReadmeMd`). It also provides Dependency Injection for states. Avoid raw dictionaries (`Dict[str, Any]`) at all costs. Always prefer generating new types or relying on injected Pydantic BaseModels for global state.

## Language and Communication Guidelines
* Since the main developer (Dr. Georg Hackenberg) is German-speaking, architectural discussions and planning are conducted in German by default.
* Code comments, docstrings, commit messages, and GitHub documentation (`README.md`, `CONTRIBUTING.md`) are written in English by default to ensure open-source usability.