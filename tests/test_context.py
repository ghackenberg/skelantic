from skelantic.commons.context import LinterContext
from skelantic.commons.nodes import FSNode

class DummyNode(FSNode):
    pass

def test_linter_context_get_node():
    ctx = LinterContext()
    node = DummyNode("abs", "some/path.py", ctx)
    ctx.register_node(node)
    
    # Test normal get
    assert ctx.get_node("some/path.py") is node
    
    # Test windows slashes
    assert ctx.get_node("some\\path.py") is node
    
    # Test relative starting with ./
    assert ctx.get_node("./some/path.py") is node
    
    # Test absolute starting with /
    assert ctx.get_node("/some/path.py") is node
    
    # Test missing
    assert ctx.get_node("missing") is None
