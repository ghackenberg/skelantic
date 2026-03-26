import pytest
import os
import sys
import pathlib
import shutil
import yaml
import importlib.metadata
import inspect
from unittest.mock import patch, MagicMock
from skelantic.cli import main

def test_cli_init(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, 'argv', ['skelantic', 'init'])

    with patch('importlib.metadata.version', return_value='0.2.0'):
        with patch('skelantic.cli._get_pkg_data_path', return_value=pathlib.Path(os.getcwd())):
            pathlib.Path("SKILL.md").write_text("test skill")
            os.makedirs("docs")
            pathlib.Path("docs/info.md").write_text("info")
            main()

    assert (tmp_path / ".skelantic/version").read_text() == "0.2.0"
    assert (tmp_path / ".skelantic/settings.yaml").exists()
    assert (tmp_path / "tools/__init__.py").exists()
    assert (tmp_path / "tools/skelantic/__init__.py").exists()
    assert (tmp_path / "tools/skelantic/processors/__init__.py").exists()
    assert (tmp_path / "tools/skelantic/tests/__init__.py").exists()
    assert (tmp_path / ".gemini/skills/skelantic/SKILL.md").exists()

    # Verify pyproject.toml
    pyproj = (tmp_path / "pyproject.toml").read_text()
    assert f'name = "{tmp_path.name}"' in pyproj
    assert 'dependencies = ["skelantic>=0.2.0"]' in pyproj

    # Verify NO top-level src/tests
    assert not (tmp_path / "src").exists()
    # Note: the test environment has a 'tests' folder for our own tests, 
    # but we are in tmp_path which should be empty.
def test_cli_run_and_generate(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    os.makedirs(".skelantic")
    (tmp_path / ".skelantic/version").write_text("0.2.0")
    # Settings
    settings = {
        "types_file": "types.py",
        "types_module": "types",
        "processors_package": "tools.procs"
    }
    with open(tmp_path / ".skelantic/settings.yaml", "w") as f:
        yaml.dump(settings, f)
        
    (tmp_path / ".skelantic/config.yaml").write_text("description: 'r'\nfiles: {'types.py': {description: 'd'}}", encoding="utf-8")
    
    with patch('importlib.metadata.version', return_value='0.2.0'):
        # Test Generate
        monkeypatch.setattr(sys, 'argv', ['skelantic', 'generate'])
        main()
        assert (tmp_path / "types.py").exists()
        
        # Test Run
        pathlib.Path("tools").mkdir()
        pathlib.Path("tools/__init__.py").touch()
        pathlib.Path("tools/procs.py").write_text("from skelantic.commons.decorators import processor\n@processor(phase=1)\ndef p(node, tracer):\n    \"\"\"My Doc\"\"\"\n    return []")
        
        mock_types = MagicMock()
        with patch('importlib.import_module', return_value=mock_types):
            monkeypatch.setattr(sys, 'argv', ['skelantic', 'run'])
            try:
                main()
            except SystemExit:
                pass
            assert "🛡️" in capsys.readouterr().out

def test_cli_info_with_processors(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    pathlib.Path(".skelantic").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".skelantic/version").write_text("0.2.0")
    (tmp_path / ".skelantic/config.yaml").write_text("description: 'root'\nfiles: {'test.md': {description: 'd', template: 't.md'}}", encoding="utf-8")
    pathlib.Path("t.md").write_text("{{var:str}}")
    with open(tmp_path / ".skelantic/settings.yaml", "w") as f:
        yaml.dump({"types_module": "types"}, f)

    # Mock types
    mock_types = MagicMock()
    mock_types.__SKELANTIC_NODE_MAP__ = {"test.md": MagicMock(__qualname__="TestMd")}
    
    from skelantic.commons.decorators import registry, ProcessorBinding
    import re
    # Clear registry for clean test
    registry.bindings = []
    
    def my_test_proc(node, tracer):
        """Validates the test file."""
        return []
    
    with patch('importlib.metadata.version', return_value='0.2.0'):
        with patch('importlib.import_module', return_value=mock_types):
            binding = ProcessorBinding(name="test_proc", func=my_test_proc, match="test.md", phase=2, regex=re.compile("^test.md$"))
            registry.bindings.append(binding)
            
            monkeypatch.setattr(sys, 'argv', ['skelantic', 'info', 'test.md'])
            main()
            out = capsys.readouterr().out
            assert "Active Processors" in out
            assert "my_test_proc" in out
            assert "Template Data" in out

def test_cli_template(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    os.makedirs(".skelantic")
    (tmp_path / ".skelantic/version").write_text("0.2.0")
    (tmp_path / ".skelantic/config.yaml").write_text("files: {'test.md': {template: 't.md'}}", encoding="utf-8")
    (tmp_path / "t.md").write_text("CONTENT")
    with open(tmp_path / ".skelantic/settings.yaml", "w") as f:
        yaml.dump({"types_module": "types"}, f)
        
    with patch('importlib.metadata.version', return_value='0.2.0'):
        monkeypatch.setattr(sys, 'argv', ['skelantic', 'template', 'test.md'])
        with patch('importlib.import_module'):
            main()
            assert "CONTENT" in capsys.readouterr().out

def test_cli_errors_missing_settings(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    os.makedirs(".skelantic")
    (tmp_path / ".skelantic/version").write_text("0.2.0")
    
    # Mock empty settings
    with patch('skelantic.cli._load_settings', return_value={}):
        with patch('importlib.metadata.version', return_value='0.2.0'):
            monkeypatch.setattr(sys, 'argv', ['skelantic', 'generate'])
            with pytest.raises(SystemExit): main()
            assert "ERROR: 'types_file' is not defined" in capsys.readouterr().out
            
            monkeypatch.setattr(sys, 'argv', ['skelantic', 'run'])
            with pytest.raises(SystemExit): main()
            assert "ERROR: 'types_module' is not defined" in capsys.readouterr().out
            
            monkeypatch.setattr(sys, 'argv', ['skelantic', 'info', 'path'])
            with pytest.raises(SystemExit): main()
            assert "ERROR: 'types_module' is not defined" in capsys.readouterr().out

def test_processor_node_enforcement():
    from skelantic.commons.decorators import processor
    def p_no_node(tracer): return []
    with pytest.raises(ValueError) as exc:
        processor()(p_no_node)
    assert "must accept a 'node' parameter" in str(exc.value)

def test_processor_tracer_enforcement():
    from skelantic.commons.decorators import processor
    def p_no_tracer(node): return []
    with pytest.raises(ValueError) as exc:
        processor()(p_no_tracer)
    assert "must accept a 'tracer' parameter" in str(exc.value)

def test_processor_docstring_enforcement():
    from skelantic.commons.decorators import processor
    def p_no_doc(node, tracer): return []
    with pytest.raises(ValueError) as exc:
        processor()(p_no_doc)
    assert "must have a docstring" in str(exc.value)
    assert "test_cli_ai.py" in str(exc.value) # Check for file info

def test_processor_docstring_enforcement_inspect_fail():
    from skelantic.commons.decorators import processor
    def p_no_doc(node, tracer): return []
    with patch('inspect.getfile', side_effect=Exception("fail")):
        with pytest.raises(ValueError) as exc:
            processor()(p_no_doc)
        assert "must have a docstring" in str(exc.value)
        assert " in '" not in str(exc.value) # No location info

def test_cli_version_check_missing_file(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, 'argv', ['skelantic', 'run'])
    with patch('importlib.metadata.version', return_value='0.2.0'):
        with pytest.raises(SystemExit):
            main()
        out = capsys.readouterr().out
        assert "Repository is not initialized" in out
        assert "skelantic init" in out

def test_cli_migrate_success(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, 'argv', ['skelantic', 'migrate'])
    with patch('importlib.metadata.version', return_value='0.2.0'):
        with patch('skelantic.cli._get_pkg_data_path', return_value=pathlib.Path(os.getcwd())):
            pathlib.Path("SKILL.md").write_text("skill")
            main()
    assert (tmp_path / ".skelantic/version").read_text() == "0.2.0"

def test_cli_resolver_base(tmp_path):
    from skelantic.commons.resolver import PathResolver
    pathlib.Path(tmp_path / ".skelantic").mkdir()
    (tmp_path / ".skelantic/config.yaml").write_text("description: 'root'\nfiles: {test.md: {description: 'd'}}")
    
    resolver = PathResolver({})
    res = resolver.resolve("test.md", base_dir=str(tmp_path))
    assert res is not None
    assert res.match_path == "test.md"
    assert res.is_directory == False

def test_cli_info_processor_import_error(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    os.makedirs(".skelantic")
    (tmp_path / ".skelantic/version").write_text("0.2.0")
    (tmp_path / ".skelantic/config.yaml").write_text("description: 'r'\nfiles: {test.md: {}}")
    with open(tmp_path / ".skelantic/settings.yaml", "w") as f:
        yaml.dump({"types_module": "types", "processors_package": "non_existent_pkg"}, f)
        
    with patch('importlib.metadata.version', return_value='0.2.0'):
        monkeypatch.setattr(sys, 'argv', ['skelantic', 'info', 'test.md'])
        with patch('importlib.import_module', side_effect=[ImportError("fail"), ImportError("fail")]):
            with pytest.raises(SystemExit): main()
            assert "Error loading types" in capsys.readouterr().out

def test_cli_info_with_string_annotation(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    os.makedirs(".skelantic")
    (tmp_path / ".skelantic/version").write_text("0.2.0")
    
    config = {
        "description": "root",
        "files": {
            "test.md": {"description": "d"}
        }
    }
    with open(tmp_path / ".skelantic/config.yaml", "w") as f:
        yaml.dump(config, f)
        
    with open(tmp_path / ".skelantic/settings.yaml", "w") as f:
        yaml.dump({"types_module": "types"}, f)

    class TestMd: pass
    mock_types = MagicMock()
    mock_types.TestMd = TestMd
    mock_types.__SKELANTIC_NODE_MAP__ = {"test.md": TestMd}
    
    from skelantic.commons.decorators import registry, ProcessorBinding
    import re
    # Clear registry for clean test
    registry.bindings = []
    
    # Use string annotation "TestMd"
    def my_string_proc(node: "TestMd", tracer):
        """Doc string for eval test."""
        return []
    
    with patch('importlib.metadata.version', return_value='0.2.0'):
        with patch('importlib.import_module', return_value=mock_types):
            with patch('skelantic.cli.eval', return_value=TestMd):
                binding = ProcessorBinding(name="test", func=my_string_proc, match=None, phase=2)
                registry.bindings.append(binding)
                
                monkeypatch.setattr(sys, 'argv', ['skelantic', 'info', 'test.md'])
                main()
                out = capsys.readouterr().out
                assert "my_string_proc" in out

def test_cli_run_import_processors_error(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    os.makedirs(".skelantic")
    (tmp_path / ".skelantic/version").write_text("0.2.0")
    with open(tmp_path / ".skelantic/settings.yaml", "w") as f:
        yaml.dump({"types_module": "types", "processors_package": "fail_pkg"}, f)
        
    with patch('importlib.metadata.version', return_value='0.2.0'):
        monkeypatch.setattr(sys, 'argv', ['skelantic', 'run'])
        # 1st call: importlib.import_module('fail_pkg') -> raises ImportError
        with patch('importlib.import_module', side_effect=ImportError("fail")):
            with pytest.raises(SystemExit): main()
            assert "Error importing processors" in capsys.readouterr().out

def test_cli_misc(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['skelantic'])
    main()
    assert "Skelantic" in capsys.readouterr().out
    
    # Test version fallback
    from skelantic.cli import _get_versions
    monkeypatch.chdir(tmp_path)
    with patch('importlib.metadata.version') as mock_v:
        mock_v.side_effect = importlib.metadata.PackageNotFoundError()
        assert _get_versions() == ("0.0.0-dev", "unknown")
    
    with patch('skelantic.cli._get_pkg_data_path') as mock_pkg:
        mock_pkg.side_effect = Exception("err")
        from skelantic.cli import _deploy_skill
        _deploy_skill()
        assert "Warning: Could not deploy" in capsys.readouterr().out

def test_cli_info_allowed_children(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    os.makedirs(".skelantic")
    (tmp_path / ".skelantic/version").write_text("0.2.0")
    (tmp_path / ".skelantic/config.yaml").write_text("description: 'r'\ndirectories: {subdir: {files: {item.md: {}}}}", encoding="utf-8")
    with open(tmp_path / ".skelantic/settings.yaml", "w") as f:
        yaml.dump({"types_module": "types"}, f)
        
    with patch('importlib.metadata.version', return_value='0.2.0'):
        monkeypatch.setattr(sys, 'argv', ['skelantic', 'info', 'subdir'])
        with patch('importlib.import_module'):
            main()
            out = capsys.readouterr().out
            assert "📁 Folders:" in out
            assert "📄 Files:" in out
            assert "item.md" in out

def test_cli_right_command(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    os.makedirs(".skelantic")
    (tmp_path / ".skelantic/version").write_text("0.2.0")
    
    with patch('importlib.metadata.version', return_value='0.2.0'), \
         patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        monkeypatch.setattr(sys, 'argv', ['skelantic', 'right'])
        main()
        mock_run.assert_called_once_with([sys.executable, "-m", "pyright", "."], capture_output=False)
        assert "Next recommended step: 'skelantic test'" in capsys.readouterr().out

def test_cli_test_command(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    os.makedirs(".skelantic")
    (tmp_path / ".skelantic/version").write_text("0.2.0")
    
    with patch('importlib.metadata.version', return_value='0.2.0'), \
         patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        monkeypatch.setattr(sys, 'argv', ['skelantic', 'test'])
        main()
        # Should call pytest with default dirs
        args, _ = mock_run.call_args
        cmd = args[0]
        assert sys.executable in cmd
        assert "-m" in cmd
        assert "pytest" in cmd
        assert "tools/skelantic/tests" in cmd
        assert "--cov=tools/skelantic/processors" in cmd
        assert "Next recommended step: 'skelantic run'" in capsys.readouterr().out

def test_cli_verify_command(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    os.makedirs(".skelantic")
    (tmp_path / ".skelantic/version").write_text("0.2.0")
    
    with patch('importlib.metadata.version', return_value='0.2.0'), \
         patch('subprocess.run') as mock_run:
        monkeypatch.setattr(sys, 'argv', ['skelantic', 'verify'])
        main()
        # Should call all 4 steps
        assert mock_run.call_count == 4
        calls = [c.args[0][3] for c in mock_run.call_args_list]
        assert calls == ["generate", "right", "test", "run"]
