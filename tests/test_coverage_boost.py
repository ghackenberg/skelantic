import os
import sys
import yaml
import pathlib
import pytest
import importlib
from unittest.mock import patch, MagicMock, mock_open
from skelantic.cli import main, _load_settings, _check_version, _get_versions
from skelantic.commons.core import LinterEngine
from skelantic.commons.decorators import registry, processor

def test_cli_processors_command(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    os.makedirs(".skelantic")
    (tmp_path / ".skelantic/version").write_text("0.2.0")
    with open(tmp_path / ".skelantic/settings.yaml", "w") as f:
        yaml.dump({"types_module": "types", "processors_package": "procs"}, f)
    
    # Mock a processor module
    mock_proc = MagicMock()
    mock_proc.__path__ = []
    
    with patch('importlib.metadata.version', return_value='0.2.0'), \
         patch('importlib.import_module', return_value=mock_proc), \
         patch('pkgutil.walk_packages', return_value=[]):
        
        monkeypatch.setattr(sys, 'argv', ['skelantic', 'processors'])
        main()
        out = capsys.readouterr().out
        assert "Registered Skelantic Processors" in out

def test_engine_dynamic_phases():
    reg = MagicMock()
    
    mock_b1 = MagicMock()
    mock_b1.phase = 5
    mock_b1.match = "file.md"
    
    mock_b2 = MagicMock()
    mock_b2.phase = 10
    mock_b2.match = "root"
    
    reg.bindings = [mock_b1, mock_b2]
    
    engine = LinterEngine(reg)
    
    with patch.object(engine, '_walk_and_validate'), \
         patch.object(engine, '_run_templates'), \
         patch.object(engine, '_run_phase') as mock_lp, \
         patch.object(engine, '_run_global_phase') as mock_gp:
        
        engine.run(".")
        
        # Phases 5 and 10 should be executed
        assert mock_lp.call_count == 2
        assert mock_gp.call_count == 2
        
        # Check order
        calls_lp = [c.args[0] for c in mock_lp.call_args_list]
        assert calls_lp == [5, 10]

def test_cli_info_with_template_vars(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "t.md").write_text("Hello {{ name:char }}")
    (tmp_path / "test.md").write_text("# Test")
    
    os.makedirs(".skelantic")
    (tmp_path / ".skelantic/version").write_text("0.2.0")
    (tmp_path / ".skelantic/config.yaml").write_text("description: 'Root'\nfiles: {test.md: {description: 'd', template: 't.md'}}", encoding="utf-8")
    
    with open(tmp_path / ".skelantic/settings.yaml", "w") as f:
        yaml.dump({"types_module": "types"}, f)
        
    mock_types = MagicMock()
    mock_types.__SKELANTIC_NODE_MAP__ = {}
    
    with patch('importlib.metadata.version', return_value='0.2.0'), \
         patch('importlib.import_module', return_value=mock_types):
        monkeypatch.setattr(sys, 'argv', ['skelantic', 'info', 'test.md'])
        main()
        out = capsys.readouterr().out
        assert "MATCHED" in out
        assert "t.md" in out

def test_cli_migrate_existing_settings(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    os.makedirs(".skelantic")
    (tmp_path / ".skelantic/settings.yaml").write_text("custom: setting")
    
    with patch('importlib.metadata.version', return_value='0.2.0'), \
         patch('skelantic.cli._deploy_skill'):
        monkeypatch.setattr(sys, 'argv', ['skelantic', 'migrate'])
        main()
        assert "Repository migrated" in capsys.readouterr().out
        assert "custom: setting" in (tmp_path / ".skelantic/settings.yaml").read_text()

def test_cli_check_version_older_installed(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    os.makedirs(".skelantic")
    (tmp_path / ".skelantic/version").write_text("0.3.0")
    
    with patch('importlib.metadata.version', return_value='0.2.0'):
        with pytest.raises(SystemExit):
            _check_version("run")
        assert "installed Skelantic version (0.2.0) is older" in capsys.readouterr().out

def test_cli_check_version_newer_installed(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    os.makedirs(".skelantic")
    (tmp_path / ".skelantic/version").write_text("0.1.0")
    
    with patch('importlib.metadata.version', return_value='0.2.0'):
        with pytest.raises(SystemExit):
            _check_version("run")
        assert "using an older version of Skelantic (0.1.0)" in capsys.readouterr().out

def test_cli_processors_with_registry(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    os.makedirs(".skelantic")
    (tmp_path / ".skelantic/version").write_text("0.2.0")
    with open(tmp_path / ".skelantic/settings.yaml", "w") as f:
        yaml.dump({"types_module": "types"}, f)
        
    def my_test_proc(node):
        """Test Docstring"""
        return []
    
    # Manually register for the test
    mock_binding = MagicMock()
    mock_binding.phase = 2
    mock_binding.func = my_test_proc
    mock_binding.name = "my_test_proc"
    mock_binding.match = "test.md"
    
    with patch.object(registry, 'bindings', [mock_binding]):
        with patch('importlib.metadata.version', return_value='0.2.0'), \
             patch('importlib.import_module'):
            monkeypatch.setattr(sys, 'argv', ['skelantic', 'processors'])
            main()
            out = capsys.readouterr().out
            assert "[PHASE 2]" in out
            assert "my_test_proc" in out
            assert "Test Docstring" in out

def test_load_settings_corrupt(tmp_path):
    s_file = tmp_path / ".skelantic/settings.yaml"
    os.makedirs(tmp_path / ".skelantic")
    s_file.write_text("!!corrupt")
    # Should fallback to defaults
    with patch('pathlib.Path.exists', return_value=True), \
         patch('builtins.open', mock_open(read_data="!!binary | ...")):
         settings = _load_settings()
         assert settings["types_file"] == "tools/skelantic/types.py"
