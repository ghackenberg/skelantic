from skelantic.commons.core import LinterEngine
from skelantic.commons.decorators import registry
from unittest.mock import patch, MagicMock

def test_execute_rule_with_traces(tmp_path):
    engine = LinterEngine(registry)
    node = MagicMock()
    
    def rule_with_trace(tracer):
        tracer("Trace step A")
        return ["error X"]
        
    f_data = {"rel_path": "path/to/test.md"}
    
    engine._execute_rule(rule_with_trace, "my_rule", node, f_data)
    
    assert engine.total_errors == 2
    # Check if trace log was written
    trace_dir = tmp_path / ".skelantic" / "traces"
    # Wait, the engine writes to os.getcwd(), so we should mock os.getcwd
    
@patch('os.getcwd')
def test_execute_rule_tracing(mock_getcwd, tmp_path):
    mock_getcwd.return_value = str(tmp_path)
    engine = LinterEngine(registry)
    node = MagicMock()
    
    def rule_with_trace(tracer):
        tracer("Trace step A")
        return ["error X"]
        
    f_data = {"rel_path": "path/to/test.md"}
    engine._execute_rule(rule_with_trace, "my_rule", node, f_data)
    
    trace_file = tmp_path / ".skelantic" / "traces" / "my_rule_path_to_test.md.log"
    assert trace_file.exists()
    assert trace_file.read_text() == "Trace step A"

def test_execute_rule_unsupported_arg():
    engine = LinterEngine(registry, verbose=True)
    node = MagicMock()
    
    def rule_with_unsupported(unsupported_arg):
        return []
        
    f_data = {"rel_path": "path/to/test.md"}
    with patch.object(engine, '_log') as mock_log:
        engine._execute_rule(rule_with_unsupported, "my_rule", node, f_data)
        mock_log.assert_called_with("Warning: Argument 'unsupported_arg' requested by processor 'my_rule' cannot be injected. Only 'node', 'tracer', and Pydantic state models are supported.", level="WARNING")

