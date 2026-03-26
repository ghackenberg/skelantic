from typing import Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .nodes import FSNode

class LinterContext:
    """Der globale Speicher (Shared Context) für den Linter-Lauf."""
    
    def __init__(self) -> None:
        # Offener Speicher für domänen-/projektspezifische Daten
        from collections import defaultdict
        self.store: defaultdict[str, Any] = defaultdict(dict)
        
        # Registry aller instanziierten Knoten im Dateisystem-Graphen
        # Key: relativer Pfad (as_posix() String), Value: FSNode
        self.nodes_registry: Dict[str, 'FSNode'] = {}
        
        # Speichert die durch Templates extrahierten Daten. 
        # Wird noch von vielen Alt-Prozessoren verwendet (Legacy Support)
        self.extracted_data: Dict[str, Any] = {}
        
    def register_node(self, node: 'FSNode') -> None:
        """Registriert einen Knoten in der globalen Registry."""
        self.nodes_registry[node.rel_path.as_posix()] = node
        
    def get_node(self, rel_path: str) -> Optional['FSNode']:
        """Holt einen Knoten anhand seines relativen Pfades."""
        # Sicherstellen, dass der Pfad saubere Slashes verwendet
        clean_path = rel_path.replace('\\', '/')
        
        # Falls der Pfad mit ./ anfängt, bereinigen
        if clean_path.startswith('./'):
            clean_path = clean_path[2:]
            
        # Absolute Pfade am Anfang bereinigen
        if clean_path.startswith('/'):
            clean_path = clean_path[1:]
            
        # Leere Pfade oder . auf . normalisieren
        if clean_path in ["", "."]:
            clean_path = "."
            
        return self.nodes_registry.get(clean_path)
