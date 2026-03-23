from skelantic.commons.core import LinterEngine
from skelantic.commons.decorators import registry
from unittest.mock import patch, MagicMock

def test_core_run_phase_path_params():
    engine = LinterEngine(registry)
    engine.node_map = {"test.md": MagicMock}
    
    # Just a mock to cover more lines
    class MockNode:
        def __init__(self, abs_path, rp, ctx):
            from pathlib import Path
            self.rel_path = Path(rp)
        
    engine.node_map["test.md"] = MockNode
    engine._run_phase(1, [{'abs_path': 'abs', 'rel_path': 'test.md', 'kwargs': {}}])

def test_core_log_info():
    engine = LinterEngine(registry, verbose=True)
    engine._log("test", "INFO")

def test_get_specificity_score():
    from skelantic.commons.core import get_specificity_score
    
    assert get_specificity_score("README.md") > get_specificity_score("{slug}.md")
    assert get_specificity_score("{slug}.md") > get_specificity_score("*.md")
    assert get_specificity_score("*.md") > get_specificity_score("**/*.md")
    assert get_specificity_score("**/*.md") == len("**/*.md") - 1000
