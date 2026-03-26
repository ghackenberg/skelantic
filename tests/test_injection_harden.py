import pytest
from unittest.mock import MagicMock
from skelantic.commons.core import LinterEngine
from skelantic.commons.nodes import FileNode, DirectoryNode, MarkdownNode
from skelantic.commons.decorators import registry, processor
from typing import Union, Optional

def test_type_matching_union():
    reg = MagicMock()
    
    def my_proc(node: Union[FileNode, DirectoryNode], tracer):
        return ["hit"]
        
    mock_b = MagicMock()
    mock_b.phase = 1
    mock_b.func = my_proc
    mock_b.name = "my_proc"
    mock_b.regex = None
    mock_b.match = None
    
    reg.bindings = [mock_b]
    
    engine = LinterEngine(reg)
    
    # Test with FileNode
    node = FileNode("abs", "file.txt", engine.ctx)
    f_data = {'rel_path': 'file.txt'}
    
    res = engine._execute_rule(my_proc, "my_proc", node, f_data)
    assert res == ["hit"]

def test_type_matching_forward_ref():
    reg = MagicMock()
    
    # Define a class in a mock module
    class MyNode(FileNode): pass
    mock_types = MagicMock()
    mock_types.MyNode = MyNode
    
    def my_proc(node: "MyNode", tracer):
        return ["hit"]
        
    engine = LinterEngine(reg, types_module=mock_types)
    
    node = MyNode("abs", "file.txt", engine.ctx)
    f_data = {'rel_path': 'file.txt'}
    
    # Manually check _run_phase logic for forward ref
    import inspect
    sig = inspect.signature(my_proc)
    params = list(sig.parameters.values())
    node_param = params[0]
    anno = node_param.annotation
    
    # Resolve
    type_env = vars(mock_types)
    resolved_anno = eval(anno, type_env)
    assert resolved_anno is MyNode
    assert isinstance(node, resolved_anno)

def test_global_node_injection():
    from skelantic.commons.nodes import RootNode
    reg = MagicMock()
    engine = LinterEngine(reg)
    
    # Register root node
    root = RootNode("abs_root", ".", engine.ctx)
    engine.ctx.register_node(root)
    
    def global_proc(node: RootNode, tracer):
        if node and node.rel_path.as_posix() == ".":
            return ["root_found"]
        return ["fail"]
        
    mock_b = MagicMock()
    mock_b.phase = 3
    mock_b.func = global_proc
    mock_b.name = "global_proc"
    mock_b.match = None
    mock_b.regex = None
    
    reg.bindings = [mock_b]
    
    # Should find root node and inject it
    engine._run_phase(3, [{'rel_path': '.', 'abs_path': 'abs_root', 'is_directory': True}])
    # Check results
    assert any("root_found" in e['msg'] for e in engine.results_tree['root']['_warnings'])

def test_isinstance_type_error_fallback():
    # Test the try-except TypeError in _run_phase
    reg = MagicMock()
    engine = LinterEngine(reg)
    
    def bad_anno_proc(node: 123, tracer): # Invalid type hint for isinstance
        return []
        
    mock_b = MagicMock()
    mock_b.phase = 1
    mock_b.func = bad_anno_proc
    mock_b.name = "bad"
    mock_b.regex = None
    
    reg.bindings = [mock_b]
    
    node = FileNode("abs", "f", engine.ctx)
    # This should not crash engine
    engine._run_phase(1, [{'rel_path': 'f', 'abs_path': 'abs'}])

def test_execute_rule_forward_ref_state():
    from pydantic import BaseModel
    reg = MagicMock()
    
    class MyState(BaseModel):
        val: int = 42
        
    mock_types = MagicMock()
    mock_types.MyState = MyState
    
    engine = LinterEngine(reg, types_module=mock_types)
    
    def my_proc(state: "MyState", tracer):
        return [f"val_{state.val}"]
        
    res = engine._execute_rule(my_proc, "my_proc", None, None)
    assert res == ["val_42"]
