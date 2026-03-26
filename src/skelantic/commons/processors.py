import re
import os
from typing import List, Set, cast
from pydantic import BaseModel, Field
from .decorators import processor
from .nodes import FileNode, MarkdownNode

# --- GLOBAL STATE ---

class GlobalMetadataState(BaseModel):
    """Sammelt repository-weite Metadaten für die Validierung."""
    all_markdown_files: Set[str] = Field(default_factory=set)
    referenced_markdown_files: Set[str] = Field(default_factory=set)

# --- CORE LINTER RULES ---

@processor(match="**/*.md", phase=2)
def dead_link(node: MarkdownNode) -> List[str]:
    """Checks for broken relative links in markdown files."""
    rel_path = node.rel_path.as_posix()
    if ".templates" in rel_path or "linter/templates" in rel_path:
        return []
    
    errors: List[str] = []
    links = node.document.get_links()
    
    for link in links:
        link_path = link.split('#')[0]
        if not link_path: continue
        
        target_abs_path = (node.abs_path.parent / link_path).resolve()
        
        if not target_abs_path.exists():
            errors.append(f"Dead Link: Verweist auf '{link}', aber Ziel existiert nicht!")

    return errors

@processor(match="**/*.md", phase=1)
def build_document_graph(node: MarkdownNode, state: GlobalMetadataState) -> None:
    """Phase 1: Sammelt alle Markdown-Dateien und alle Referenzen (Links) im gesamten Repo."""
    rel_path = node.rel_path.as_posix()
    if ".templates" in rel_path or "linter/templates" in rel_path:
        return

    abs_filepath = node.abs_path.as_posix()

    if rel_path != "README.md":
        state.all_markdown_files.add(abs_filepath)

    links = node.document.get_links()

    for link in links:
        link_path = link.split('#')[0]
        if not link_path: continue
        target_abs_path = (node.abs_path.parent / link_path).resolve()
        state.referenced_markdown_files.add(target_abs_path.as_posix())

@processor(match="root", phase=3)
def check_orphaned_documents(state: GlobalMetadataState) -> List[str]:
    """Phase 3: Prüft, ob es gibt Dateien gibt, die nie referenziert wurden."""
    warnings: List[str] = []

    orphans = state.all_markdown_files - state.referenced_markdown_files

    for orphan in sorted(list(orphans)):
        try:
            pretty_path = os.path.relpath(orphan, os.getcwd()).replace('\\', '/')
            warnings.append(f"Orphaned Document: Niemand verlinkt auf '{pretty_path}'. Bitte referenzieren.")
        except: pass

    return warnings

@processor(match="**/*.md", phase=2)
def backlink_enforcement(node: MarkdownNode) -> List[str]:
    """Stellt sicher, dass jede MD-Datei einen Backlink zur nächstgelegenen README am Anfang hat."""    
    rel_path = node.rel_path.as_posix()
    filename = node.name

    if rel_path == "README.md":
        return []

    if ".templates" in rel_path or "linter/templates" in rel_path:
        return []

    target_rel_path = None
    search_dir: str = os.path.dirname(rel_path)

    while True:
        potential_readme = os.path.join(search_dir, "README.md").replace('\\', '/')
        if os.path.exists(potential_readme):
            # Calculate path from current file's directory to the README
            target_rel_path = os.path.relpath(potential_readme, os.path.dirname(rel_path)).replace('\\', '/')
            break

        if not search_dir or search_dir == ".":
            break
        search_dir = os.path.dirname(search_dir)

    if not target_rel_path:
        return []

    raw = node.document.raw_content
    lines = raw.splitlines()

    is_marp = False
    search_block = ""
    if len(lines) > 0 and lines[0].strip() == "---":
        try:
            closing_idx = -1
            for i in range(1, min(20, len(lines))):
                if lines[i].strip() == "---":
                    closing_idx = i
                    break
            if closing_idx != -1:
                frontmatter = "\n".join(lines[:closing_idx+1])
                if "marp: true" in frontmatter:
                    is_marp = True
                    search_block = "\n".join(lines[closing_idx+1:closing_idx+6])
        except: pass

    if not is_marp:
        search_block = "\n".join(lines[:5])

    regex_path = target_rel_path.replace('.', r'\.')
    pattern = rf'\[.*\]\({regex_path}\)'

    if not re.search(pattern, search_block):
        loc = "nach dem Frontmatter" if is_marp else "am Dateianfang"
        return [f"Fehlender oder falscher Backlink {loc}! Erwartet: Link auf '{target_rel_path}'."]      

    return []

