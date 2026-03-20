from typing import Callable, Any, List, Optional, Pattern
import inspect
import re
from dataclasses import dataclass

@dataclass
class ProcessorBinding:
    name: str
    func: Callable[..., Any]
    match: Optional[str] = None
    phase: Optional[int] = None
    regex: Optional[Pattern[str]] = None

class Registry:
    def __init__(self) -> None:
        # Neue strukturierte Ablage für Glob-basierte Prozessoren
        self.bindings: List[ProcessorBinding] = []

registry = Registry()

def processor(match: str, phase: int) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Dekorator für Linter-Prozessoren.
    :param match: Pfad-Muster (z.B. "docs/03-architecture/**/*.md" oder "root")
    :param phase: Ausführungs-Pass (1, 2, 3)
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        # Dynamisch erzeugter Name für Logging und Tracing
        name = f"{func.__module__}.{func.__name__}"

        # Baue Regex aus dem Match-String auf
        # Erlaube benannte Parameter wie {action}
        pattern = str(match)
        # Finde alle erwarteten Parameter im Match-String
        expected_params = re.findall(r'\{([a-zA-Z0-9_]+)\}', pattern)
        
        # Wandle {param} in (?P<param>[^/]+) um, für die Regex-Engine
        regex_str = re.sub(r'\{([a-zA-Z0-9_]+)\}', r'(?P<\1>[^/]+)', pattern)
        
        # Behandle **, * und . sicher
        regex_str = regex_str.replace('.', r'\.')
        regex_str = regex_str.replace('**', r'.*')
        # Hier ein Hack für einfaches *: wir ersetzen es nur, wenn es kein .* ist
        # Besser: erst **, dann *, dann zurück
        regex_str = regex_str.replace(r'.*', '___STARSTAR___')
        regex_str = regex_str.replace('*', r'[^/]*')
        regex_str = regex_str.replace('___STARSTAR___', r'.*')
        
        # Vollständiger Match
        compiled_regex = re.compile(f"^{regex_str}$")
        
        # Fail-Early Validation der Funktions-Signatur
        sig = inspect.signature(func)
        for param_name, param in sig.parameters.items():
            if param_name not in ["node", "ctx", "doc", "rel_path", "filename", "tracer"]:
                # Wenn der Parameter keinen Default-Wert hat und auch nicht im Match-String extrahiert wird
                if param.default == inspect.Parameter.empty and param_name not in expected_params:
                    raise TypeError(
                        f"Fail-Early Validator: Prozessor '{func.__name__}' verlangt den Parameter '{param_name}', "
                        f"aber das match-Pattern '{match}' extrahiert diesen nicht."
                    )
        
        binding = ProcessorBinding(
            name=name, 
            func=func, 
            match=match, 
            phase=phase,
            regex=compiled_regex
        )
        registry.bindings.append(binding)
            
        return func
    return decorator
