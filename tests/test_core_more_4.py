from skelantic.commons.core import LinterEngine
from skelantic.commons.decorators import registry
from unittest.mock import patch, mock_open

def test_core_run_templates_exceptions():
    engine = LinterEngine(registry)
    
    files_data = [{'abs_path': 'test.md', 'rel_path': 'test.md', 'template': 'dummy.md'}]
    
    with patch('os.path.exists', return_value=True):
        with patch('builtins.open', mock_open(read_data="content")):
            with patch('skelantic.commons.core.SkeletalMatcher.match', side_effect=Exception("parse error")):
                engine._run_templates(files_data)
                
    assert engine.total_errors == 1
    assert "Template Error: parse error" in engine.results_tree['test.md']['_errors'][0]
