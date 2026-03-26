# pyright: reportPrivateUsage=false
import yaml
import re
from unittest.mock import patch, MagicMock, mock_open
from skelantic.commons.core import LinterEngine
from skelantic.commons.config import ConfigLoader
from skelantic.commons.decorators import registry

from typing import Any, List


def test_strict_by_default(tmp_path: Any) -> None:
    linter_yaml = tmp_path / "linter.yaml"
    linter_yaml.write_text(yaml.dump({
        "description": "Test Config",
        "files": {
            "required_file.md": {"description": "Required file for testing"}
        }
    }))
    
    # We need a real engine here because _walk_and_validate is in LinterEngine
    engine = LinterEngine(registry, models_module="test_models")
    all_files: List[Any] = []
    # We use engine's config_loader to load the config from tmp_path
    config = engine.config_loader.load_config(str(linter_yaml))
    engine._walk_and_validate(str(tmp_path), config, all_files)  # pyright: ignore[reportPrivateUsage]
    
    assert engine.total_errors == 1
    assert "Fehlendes Element: 'required_file.md': Datei/Ordner existiert nicht." in engine.results_tree["root"]["_errors"]

def test_optional_flag(tmp_path: Any) -> None:
    linter_yaml = tmp_path / "linter.yaml"
    linter_yaml.write_text(yaml.dump({
        "description": "Test Config",
        "files": {
            "missing_but_optional.md": {"description": "Optional file for testing", "optional": True}
        }
    }))
    
    engine = LinterEngine(registry, models_module="test_models")
    all_files: List[Any] = []
    config = engine.config_loader.load_config(str(linter_yaml))
    engine._walk_and_validate(str(tmp_path), config, all_files)  # pyright: ignore[reportPrivateUsage]
    
    assert engine.total_errors == 0
    assert engine.total_warnings == 1
    assert "Kein Match für 'missing_but_optional.md'" in engine.results_tree["root"]["_warnings"][0]

def test_silent_flag(tmp_path: Any) -> None:
    linter_yaml = tmp_path / "linter.yaml"
    linter_yaml.write_text(yaml.dump({
        "description": "Test Config",
        "files": {
            "missing_and_silent.md": {"description": "Silent optional file for testing", "optional": True, "silent": True}
        }
    }))
    
    engine = LinterEngine(registry, models_module="test_models")
    all_files: List[Any] = []
    config = engine.config_loader.load_config(str(linter_yaml))
    engine._walk_and_validate(str(tmp_path), config, all_files)  # pyright: ignore[reportPrivateUsage]
    
    assert engine.total_errors == 0
    assert engine.total_warnings == 0

def test_recursive_glob_matching(tmp_path: Any) -> None:
    linter_yaml = tmp_path / "linter.yaml"
    linter_yaml.write_text(yaml.dump({
        "description": "Test Config",
        "files": {
            "**/*.md": {"description": "Any markdown file"}
        }
    }))

    file_md = tmp_path / "test.md"
    file_md.write_text("# Test")

    engine = LinterEngine(registry, models_module="test_models")
    all_files: List[Any] = []
    config = engine.config_loader.load_config(str(linter_yaml))
    engine._walk_and_validate(str(tmp_path), config, all_files, rel_path=".")  # pyright: ignore[reportPrivateUsage]

    test_md_entry = next((f for f in all_files if f["rel_path"].endswith("test.md")), None)
    assert test_md_entry is not None

def test_unauthorized_file_error(tmp_path: Any) -> None:
    linter_yaml = tmp_path / "linter.yaml"
    linter_yaml.write_text(yaml.dump({
        "description": "Test Config",
        "files": {"README.md": {"description": "Readme file"}}
    }))
    
    readme = tmp_path / "README.md"
    readme.write_text("# Readme")
    
    secret = tmp_path / "secret.txt"
    secret.write_text("shhh")
    
    engine = LinterEngine(registry, models_module="test_models")
    all_files: List[Any] = []
    config = engine.config_loader.load_config(str(linter_yaml))
    engine._walk_and_validate(str(tmp_path), config, all_files)  # pyright: ignore[reportPrivateUsage]
    
    print("Errors:", engine.results_tree)
    assert engine.total_errors == 1

def test_linter_engine_init_and_run(tmp_path: Any) -> None:
    engine = LinterEngine(registry, models_module="test_models")
    with patch.object(engine, '_walk_and_validate') as mock_walk, \
         patch.object(engine, '_run_templates') as mock_tmpl, \
         patch.object(engine, '_run_phase') as mock_phase, \
         patch.object(engine, '_run_global_phase') as mock_global:
        engine.run(str(tmp_path))
        mock_walk.assert_called_once()
        mock_tmpl.assert_called_once()
        assert mock_phase.call_count == 2
        mock_global.assert_called_once_with(3)

def test_linter_engine_log(capsys: Any) -> None:
    engine = LinterEngine(registry, verbose=True, models_module="test_models")
    engine._log("test message", "INFO")
    captured = capsys.readouterr()
    assert "INFO" in captured.out
    assert "test message" in captured.out

def test_get_or_create_doc(tmp_path: Any) -> None:
    engine = LinterEngine(registry, models_module="test_models")
    file_path = tmp_path / "test.md"
    file_path.write_text("# hello")
    doc = engine._get_or_create_doc(str(file_path), "test.md", is_directory=False)
    assert doc.raw_content == "# hello"
    # Should be from cache the second time
    doc2 = engine._get_or_create_doc(str(file_path), "test.md", is_directory=False)
    assert doc is doc2
    # Directory test
    dir_path = tmp_path / "testdir"
    dir_path.mkdir()
    doc_dir = engine._get_or_create_doc(str(dir_path), "testdir", is_directory=True)
    assert doc_dir.raw_content == ""

def test_run_templates_match_success(tmp_path: Any) -> None:
    engine = LinterEngine(registry, models_module="test_models")
    template_path = tmp_path / "template.md"
    template_path.write_text("# Template\n{{ data }}")
    
    file_path = tmp_path / "file.md"
    file_path.write_text("# Template\nContent")
    
    files_data = [{
        'abs_path': str(file_path),
        'rel_path': 'file.md',
        'template': str(template_path)
    }]
    
    with patch('skelantic.commons.core.SkeletalMatcher') as MockMatcher:
        instance = MockMatcher.return_value
        instance.match.return_value = (True, [], {'data': 'Content'})
        engine._run_templates(files_data)
        assert engine.ctx.extracted_data['file.md'] == {'data': 'Content'}

def test_run_templates_match_failure(tmp_path: Any) -> None:
    engine = LinterEngine(registry, models_module="test_models")
    template_path = tmp_path / "template.md"
    template_path.write_text("# Template")
    
    file_path = tmp_path / "file.md"
    file_path.write_text("# Wrong")
    
    files_data = [{
        'abs_path': str(file_path),
        'rel_path': 'file.md',
        'template': str(template_path)
    }]
    
    with patch('skelantic.commons.core.SkeletalMatcher') as MockMatcher:
        instance = MockMatcher.return_value
        instance.match.return_value = (False, ["error1"], {})
        instance.trace_log = ["trace1"]
        engine._run_templates(files_data)
        assert engine.total_errors == 2
        assert "error1" in engine.results_tree["file.md"]["_errors"]

def test_run_phase(tmp_path: Any) -> None:
    engine = LinterEngine(registry, models_module="test_models")
    file_path = tmp_path / "test.md"
    file_path.write_text("content")
    
    files_data = [{
        'abs_path': str(file_path),
        'rel_path': 'test.md',
        'is_directory': False,
        'kwargs': {'arg1': 'val1'}
    }]
    
    mock_binding = MagicMock()
    mock_binding.phase = 1
    mock_binding.regex = re.compile(r'test\.md')
    mock_binding.name = 'test_rule'
    mock_binding.func = MagicMock()
    
    engine.registry.bindings = [mock_binding]
    with patch.object(engine, '_execute_rule') as mock_exec:
        engine._run_phase(1, files_data)
        mock_exec.assert_called_once()

def test_execute_rule_success_and_crash() -> None:
    engine = LinterEngine(registry, models_module="test_models")
    node = MagicMock()
    node.document = MagicMock()

    def dummy_rule(node: Any, tracer: Any) -> List[str]: 
        tracer("tracing step 1")
        return ["warning 1"]

    f_data = {'rel_path': 'path/to/file.md', 'filename': 'file.md'}

    # Test success returning a result (warning/error list)
    with patch('os.makedirs'):
        with patch('builtins.open', mock_open()):
            engine._execute_rule(dummy_rule, "dummy_rule", node, f_data)
    assert engine.total_errors == 2  # the results are added as errors by default in execute_rule if returned
    
    # Test crash
    def crash_rule() -> None:
        raise ValueError("boom")
        
    engine._execute_rule(crash_rule, "crash_rule", node, f_data)
    assert engine.total_errors == 3

def test_run_global_phase() -> None:
    engine = LinterEngine(registry, models_module="test_models")
    mock_binding = MagicMock()
    mock_binding.phase = 3
    mock_binding.match = "root"
    mock_binding.func = MagicMock(return_value=["global warn"])
    mock_binding.name = "global_rule"
    
    engine.registry.bindings = [mock_binding]
    engine._run_global_phase(3)
    assert engine.total_warnings == 1
    
    # Test crash
    mock_binding.func.side_effect = ValueError("boom")
    engine._run_global_phase(3)
    assert engine.total_errors == 1

def test_print_report(capsys: Any) -> None:
    engine = LinterEngine(registry, models_module="test_models")
    # 0 errors 0 warnings
    has_errors = engine.print_report()
    assert not has_errors
    captured = capsys.readouterr()
    assert "PERFECT REPOSITORY" in captured.out
    
    # with errors
    engine._add_results("ERROR", "file1.md", ["error 1"])
    engine._add_results("WARNING", "dir1/file2.md", ["warn 1"])
    has_errors = engine.print_report()
    assert has_errors
    captured = capsys.readouterr()
    assert "FAILED" in captured.out
    assert "file1.md" in captured.out
    assert "dir1/" in captured.out
    assert "error 1" in captured.out
    assert "warn 1" in captured.out

def test_walk_and_validate_permission_error(tmp_path: Any) -> None:
    engine = LinterEngine(registry, models_module="test_models")
    with patch('os.listdir', side_effect=PermissionError):
        all_files: List[Any] = []
        engine._walk_and_validate(str(tmp_path), {}, all_files)
        # Root node is now added before listdir
        assert len(all_files) == 1

def test_walk_and_validate_local_config(tmp_path: Any) -> None:
    linter_dir = tmp_path / ".skelantic"
    linter_dir.mkdir()
    local_cfg = linter_dir / "config.yaml"
    local_cfg.write_text(yaml.dump({
        "files": {"local.md": {"description": "local file"}}
    }))
    
    local_md = tmp_path / "local.md"
    local_md.write_text("local")
    
    engine = LinterEngine(registry, models_module="test_models")
    all_files: List[Any] = []
    
    # First dir doesn't pick up local config as child config if rel_path=="." but will load it as lcp_new
    engine._walk_and_validate(str(tmp_path), {}, all_files, rel_path="subdir")
    assert any(f['filename'] == 'local.md' for f in all_files)
