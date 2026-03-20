from pathlib import Path
from typing import Any, Optional
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
        # Wir müssen den absoluten Pfad in den relativen Repo-Pfad zurückübersetzen,
        # um ihn im Kontext (oder in der Registry) nachzuschlagen.
        # Da Path.resolve() auf Windows C:\... erzeugt, ist es einfacher, 
        # die sauberen relativen Pfade zu verwenden.
        
        # Normiere den Pfad relativ zum Root-Verzeichnis (das wir hier als CWD annehmen)
        try:
            rel_target = target_path.relative_to(Path.cwd()).as_posix()
        except ValueError:
            return None
            
        return self._ctx.get_node(rel_target)

class DirectoryNode(FSNode):
    """Repräsentiert einen geprüften Ordner."""
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
