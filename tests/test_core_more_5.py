from skelantic.commons.core import LinterEngine
from skelantic.commons.decorators import registry
from unittest.mock import MagicMock, patch

def test_core_run_phase_pydantic_instantiation():
    class DummyTypeModule:
        pass
        
    class DummyPydanticModel:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            
    setattr(DummyTypeModule, 'DummyModel', DummyPydanticModel)
    
    class MockNodeWithAnnotations:
        __annotations__ = {'data': 'DummyModel'}
        def __init__(self, abs_path, rp, ctx):
            from pathlib import Path
            self.rel_path = Path(rp)
            self.data = None            
    engine = LinterEngine(registry, types_module=DummyTypeModule)
    engine.node_map = {"test.md": MockNodeWithAnnotations}
    
    # We need to simulate extracted data being a dict
    engine.ctx.extracted_data['test.md'] = {"field": "value"}
    
    engine._run_phase(1, [{'abs_path': 'abs', 'rel_path': 'test.md', 'kwargs': {}}])
    
    # Assert that the node was instantiated and its data is the DummyPydanticModel
    node = engine.ctx.nodes_registry.get('test.md')
    assert node is not None
    assert isinstance(node.data, DummyPydanticModel)
    assert node.data.kwargs['field'] == "value"
    assert node.data.kwargs['rel_path'] == "test.md"

def test_core_run_phase_pydantic_exception():
    class DummyTypeModule:
        pass
        
    class DummyPydanticModel:
        def __init__(self, **kwargs):
            raise Exception("Validation Error")
            
    setattr(DummyTypeModule, 'DummyModel', DummyPydanticModel)
    
    class MockNodeWithAnnotations:
        __annotations__ = {'data': 'DummyModel'}
        def __init__(self, abs_path, rp, ctx):
            from pathlib import Path
            self.rel_path = Path(rp)
            self.data = None
            
    engine = LinterEngine(registry, types_module=DummyTypeModule)
    engine.node_map = {"test.md": MockNodeWithAnnotations}
    engine.ctx.extracted_data['test.md'] = {"field": "value"}
    
    with patch.object(engine, '_log') as mock_log:
        engine._run_phase(1, [{'abs_path': 'abs', 'rel_path': 'test.md', 'kwargs': {}}])
        
    node = engine.ctx.nodes_registry.get('test.md')
    assert node is not None
    assert isinstance(node.data, dict)
    assert node.data['field'] == "value"

def test_core_global_phase_crash():
    engine = LinterEngine(registry)
    
    def bad_global_rule(node, tracer):
        raise ValueError("global boom")
        
    class MockBinding:
        phase = 3
        match = "root"
        func = bad_global_rule
        name = "bad_global_rule"
        regex = None
        
    engine.registry.bindings = [MockBinding]
    engine._run_phase(3, [{'rel_path': '.', 'abs_path': 'root', 'is_directory': True}])
    assert engine.total_errors == 1
    assert "Global Crash 'bad_global_rule': global boom" in engine.results_tree['root']['_errors'][0]['msg']

def test_core_walk_and_validate_directories(tmp_path):
    engine = LinterEngine(registry)
    
    # Create a dummy structure
    d = tmp_path / "mydir"
    d.mkdir()
    f = d / "file.txt"
    f.write_text("hello")
    
    config = {
        "directories": {
            "mydir": {
                "authorize": True,
                "files": {
                    "file.txt": {"authorize": True}
                }
            }
        }
    }
    
    all_files = []
    engine._walk_and_validate(str(tmp_path), config, all_files, rel_path=".")
    
    # Check if directory was added to all_files
    assert any(f['filename'] == 'mydir' and f['is_directory'] for f in all_files)
    assert any(f['filename'] == 'file.txt' and not f['is_directory'] for f in all_files)
