from skelantic.commons.core import LinterEngine
from skelantic.commons.decorators import registry
from unittest.mock import MagicMock, patch

def test_core_run_global_phase_success():
    engine = LinterEngine(registry)
    
    def good_global_rule(ctx):
        return ["global warning"]
        
    class MockBinding:
        phase = 3
        match = "root"
        func = good_global_rule
        name = "good_global_rule"
        regex = None
        
    engine.registry.bindings = [MockBinding]
    engine._run_global_phase(3)
    assert engine.total_warnings == 1
    assert "global warning" in engine.results_tree['root']['_warnings'][0]

def test_core_global_phase_crash():
    engine = LinterEngine(registry)
    
    def bad_global_rule():
        raise ValueError("global boom")
        
    class MockBinding:
        phase = 3
        match = "root"
        func = bad_global_rule
        name = "bad_global_rule"
        regex = None
        
    engine.registry.bindings = [MockBinding]
    engine._run_global_phase(3)
    assert engine.total_errors == 1
    assert "Global Crash 'bad_global_rule': global boom" in engine.results_tree['root']['_errors'][0]
