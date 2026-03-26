from typing import Callable, Any, List, Optional, Pattern
import re
import inspect
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

def processor(match: Optional[str] = None, phase: int = 2) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Dekorator für Linter-Prozessoren.
    :param match: Pfad-Muster (z.B. "docs/03-architecture/**/*.md" oder "root")
    :param phase: Ausführungs-Pass (1, 2, 3)
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if not func.__doc__ or not func.__doc__.strip():
            try:
                f_path = inspect.getfile(func)
                _, line = inspect.getsourcelines(func)
                loc = f" in '{f_path}:{line}'"
            except Exception:
                loc = ""
            raise ValueError(f"Processor function '{func.__name__}'{loc} must have a docstring.")

        # Dynamisch erzeugter Name für Logging und Tracing
        name = f"{func.__module__}.{func.__name__}"

        compiled_regex = None
        if match is not None:
            # Baue Regex aus dem Match-String auf
            # Erlaube benannte Parameter wie {action}
            pattern = str(match)
            
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
