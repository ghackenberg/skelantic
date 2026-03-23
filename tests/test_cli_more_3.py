import os
import sys
import pytest
from unittest.mock import patch, MagicMock

def test_main_migrate_no_version_file(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr('sys.argv', ['skelantic', 'migrate'])
    monkeypatch.chdir(tmp_path)
    
    with patch('importlib.metadata.version', return_value='0.2.0'):
        from skelantic.cli import main
        try:
            main()
        except SystemExit:
            pass
            
    captured = capsys.readouterr()
    assert "Warning: Could not find .skelantic/version file" in captured.out
    assert "<system_instruction>" in captured.out
def test_main_migrate_with_version_file(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr('sys.argv', ['skelantic', 'migrate'])
    monkeypatch.chdir(tmp_path)
    
    os.makedirs(".skelantic", exist_ok=True)
    with open(".skelantic/version", "w", encoding="utf-8") as f:
        f.write("0.1.5")
        
    with patch('importlib.metadata.version', return_value='0.2.0'):
        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.is_dir', return_value=True):
                with patch('pathlib.Path.glob') as mock_glob:
                    mock_file = MagicMock()
                    mock_file.name = "001_test.md"
                    mock_file.read_text.return_value = "migration content"
                    mock_glob.return_value = [mock_file]
                    from skelantic.cli import main
                    try:
                        main()
                    except SystemExit:
                        pass
                        
    captured = capsys.readouterr()
    assert "from v0.1.5 to v0.2.0" in captured.out
    assert "migration content" in captured.out
