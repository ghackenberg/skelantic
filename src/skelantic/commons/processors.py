import re
import os
from typing import List, Set, Callable
from pydantic import BaseModel, Field
from .decorators import processor
from .nodes import MarkdownNode

# --- GLOBAL STATE ---

class GlobalMetadataState(BaseModel):
    """Sammelt repository-weite Metadaten für die Validierung."""
    all_markdown_files: Set[str] = Field(default_factory=set)
    referenced_markdown_files: Set[str] = Field(default_factory=set)

# --- CORE LINTER RULES ---

@processor(match="**/*.md", phase=2)
def dead_link(node: MarkdownNode, tracer: Callable[[str], None]) -> List[str]:
    """Prüft auf tote relative Links in Markdown-Dateien."""
    tracer(f"Prüfe Links in {node.rel_path}")
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
            tracer(f"Toter Link gefunden: {link}")
            errors.append(f"Toter Link: Der Verweis auf '{link}' kann nicht aufgelöst werden, da das Ziel nicht existiert. Bitte korrigiere den Pfad oder erstelle die fehlende Datei.")

    return errors

@processor(match="**/*.md", phase=1)
def build_document_graph(node: MarkdownNode, state: GlobalMetadataState, tracer: Callable[[str], None]) -> None:
    """Indexiert alle Markdown-Dateien und deren Verknüpfungen für die globale Konsistenzprüfung."""
    tracer(f"Indexiere {node.rel_path}")
    rel_path = node.rel_path.as_posix()
    if ".templates" in rel_path or "linter/templates" in rel_path:
        return

    # Nutze voll aufgelöste Pfade für Konsistenz
    abs_filepath = node.abs_path.resolve().as_posix()

    if rel_path != "README.md":
        state.all_markdown_files.add(abs_filepath)

    links = node.document.get_links()

    for link in links:
        link_path = link.split('#')[0]
        if not link_path: continue
        target_abs_path = (node.abs_path.parent / link_path).resolve().as_posix()
        state.referenced_markdown_files.add(target_abs_path)

@processor(match="root", phase=3)
def check_orphaned_documents(state: GlobalMetadataState, tracer: Callable[[str], None]) -> List[str]:
    """Identifiziert Dateien, die im Repository existieren, aber von keiner anderen Datei verlinkt werden."""
    tracer("Suche nach verwaisten Dokumenten")
    warnings: List[str] = []

    orphans = state.all_markdown_files - state.referenced_markdown_files

    for orphan in sorted(list(orphans)):
        try:
            pretty_path = os.path.relpath(orphan, os.getcwd()).replace('\\', '/')
            tracer(f"Verwaiste Datei gefunden: {pretty_path}")
            warnings.append(f"Verwaistes Dokument: Die Datei '{pretty_path}' wird nirgendwo im Repository referenziert. Bitte füge einen Link zu dieser Datei hinzu (z.B. in der README.md des Ordners) oder lösche sie, falls sie obsolet ist.")
        except Exception: pass

    return warnings

@processor(match="**/*.md", phase=2)
def backlink_enforcement(node: MarkdownNode, tracer: Callable[[str], None]) -> List[str]:
    """Erzwingt eine saubere Navigationsstruktur durch verpflichtende Backlinks zur nächsten README.md."""    
    tracer(f"Prüfe Backlink-Erzwingung für {node.rel_path}")
    rel_path = node.rel_path.as_posix()
    filename = node.name

    if rel_path == "README.md":
        return []

    if ".templates" in rel_path or "linter/templates" in rel_path:
        return []

    # Bestimme das Startverzeichnis für die Suche nach einer README.md
    search_dir: str = "."
    if filename == "README.md":
        # Wenn wir selbst eine README sind, suchen wir im ELTERN-Ordner
        search_dir = os.path.dirname(os.path.dirname(rel_path)) or "."
    else:
        # Wenn wir eine normale Datei sind, suchen wir im EIGENEN Ordner oder höher
        search_dir = os.path.dirname(rel_path) or "."

    target_rel_path = None
    target_repo_path = None

    while True:
        potential_readme = os.path.join(search_dir, "README.md").replace('\\', '/')
        if os.path.exists(potential_readme):
            # Berechne den Pfad von der aktuellen Datei zur gefundenen README
            target_rel_path = os.path.relpath(potential_readme, os.path.dirname(rel_path)).replace('\\', '/')
            target_repo_path = potential_readme
            break

        if not search_dir or search_dir == ".":
            break
        search_dir = os.path.dirname(search_dir)

    if not target_rel_path:
        tracer("Keine übergeordnete README.md gefunden, überspringe Prüfung.")
        return []

    tracer(f"Erwarte Backlink auf {target_repo_path}")
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
        tracer("Backlink nicht am Dateianfang gefunden.")
        loc = "direkt nach dem Frontmatter" if is_marp else "am Dateianfang (in den ersten 5 Zeilen)"
        return [
            f"Strukturfehler: Diese Datei muss einen Backlink zur übergeordneten Dokumentation '{target_repo_path}' enthalten.",
            f"Handlungsempfehlung: Bitte füge {loc} folgenden Markdown-Link ein: [Zurück]({target_rel_path})"
        ]

    return []
