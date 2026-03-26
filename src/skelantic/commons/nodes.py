from pathlib import Path
from typing import Any, Optional, cast
from .documents import Document, MarkdownDocument
from .context import LinterContext

class FSNode:
    """Basisklasse für alle geprüften Elemente im Dateisystem."""
    def __init__(self, abs_path: str, rel_path: str, ctx: LinterContext):
        self.abs_path = Path(abs_path)
        self.rel_path = Path(rel_path)
        self._ctx = ctx
        self.data: Any = None # Wird zur Laufzeit mit dem validierten Pydantic-Modell befüllt

    @property
    def name(self) -> str:
        return self.rel_path.name
        
    @property
    def parent_dir(self) -> Path:
        return self.rel_path.parent

    def resolve(self, path_str: str) -> Optional['FSNode']:
        """
        Navigiert relativ zum aktuellen Knoten im Dateisystem-Graphen.
        Gibt den referenzierten Knoten zurück, falls er existiert.
        """
        target_path = (self.parent_dir / path_str).resolve()
        
        try:
            rel_target = target_path.relative_to(Path.cwd()).as_posix()
        except ValueError:
            return None
            
        return self._ctx.get_node(rel_target)
        
    @property
    def parent_node(self) -> Optional['DirectoryNode']:
        """Sucht den Knoten des übergeordneten Ordners im Graphen."""
        parent_path = self.parent_dir.as_posix()
        if parent_path == '.' and self.rel_path.as_posix() == '.':
            return None
        node = self._ctx.get_node(parent_path)
        if isinstance(node, DirectoryNode):
            return node
        return None

    @property
    def root_node(self) -> 'DirectoryNode':
        """Gibt den Wurzelknoten des Repositories zurück."""
        node = self._ctx.get_node(".")
        return cast(DirectoryNode, node)

class DirectoryNode(FSNode):
    """Repräsentiert einen geprüften Ordner."""
    
    def get_child_file(self, filename: str) -> Optional['FileNode']:
        """Holt eine spezifische Datei aus diesem Ordner."""
        node = self._ctx.get_node((self.rel_path / filename).as_posix())
        if isinstance(node, FileNode):
            return node
        return None

    def get_child_dir(self, dirname: str) -> Optional['DirectoryNode']:
        """Holt einen spezifischen Unterordner aus diesem Ordner."""
        node = self._ctx.get_node((self.rel_path / dirname).as_posix())
        if isinstance(node, DirectoryNode):
            return node
        return None

    def get_child_files_by_pattern(self, pattern: str) -> list['FileNode']:
        """Findet alle Dateien in diesem Ordner, die einem Config-Pattern entsprechen."""
        from .config import get_regex
        regex = get_regex(pattern)
        results: list['FileNode'] = []
        for _, node in self._ctx.nodes_registry.items():
            if isinstance(node, FileNode) and node.parent_dir == self.rel_path:
                if regex.match(node.name):
                    results.append(node)
        return results

    def get_child_dirs_by_pattern(self, pattern: str) -> list['DirectoryNode']:
        """Findet alle Unterordner in diesem Ordner, die einem Config-Pattern entsprechen."""
        from .config import get_regex
        regex = get_regex(pattern)
        results: list['DirectoryNode'] = []
        for _, node in self._ctx.nodes_registry.items():
            if isinstance(node, DirectoryNode) and node.parent_dir == self.rel_path:
                if regex.match(node.name):
                    results.append(node)
        return results

class RootNode(DirectoryNode):
    """Repräsentiert den Wurzelknoten des Repositories."""
    pass

class FileNode(FSNode):
    """Repräsentiert eine geprüfte Datei und hält deren geparsten Inhalt."""
    def __init__(self, abs_path: str, rel_path: str, ctx: LinterContext):
        super().__init__(abs_path, rel_path, ctx)
        self.document: Document
        
        if self.rel_path.suffix == '.md':
            self.document = MarkdownDocument(abs_path)
        else:
            self.document = Document(abs_path)

    @property
    def raw_content(self) -> str:
        """Gibt den rohen Textinhalt der Datei zurück (Proxy für node.document.raw_content)."""
        return self.document.raw_content

class MarkdownNode(FileNode):
    """Repräsentiert eine geprüfte Markdown-Datei."""
    def __init__(self, abs_path: str, rel_path: str, ctx: LinterContext):
        super().__init__(abs_path, rel_path, ctx)
        self.document: MarkdownDocument # type: ignore[reportIncompatibleVariableOverride]

