import os
import sys
from unittest.mock import patch, MagicMock

def test_main_generate(monkeypatch):
    monkeypatch.setattr('sys.argv', ['skelantic', 'generate', '-o', 'types.py'])
    with patch('skelantic.commons.codegen.run_codegen') as mock_run_codegen:
        from skelantic.cli import main
        main()
        mock_run_codegen.assert_called_once_with(config_path=os.path.join('.', '.skelantic', 'config.yaml'), output_path='types.py', verbose=False)

def test_main_run_with_args(monkeypatch):
    monkeypatch.setattr('sys.argv', ['skelantic', 'run', '-t', 'dummy_types', '-p', 'dummy_processors'])
    with patch('skelantic.cli.LinterEngine') as mock_linter_engine:
        with patch('importlib.import_module') as mock_import:
            from skelantic.cli import main
            mock_engine_instance = MagicMock()
            mock_engine_instance.print_report.return_value = False
            mock_linter_engine.return_value = mock_engine_instance
            
            main()
            
            assert mock_import.call_count >= 2
            mock_linter_engine.assert_called_once()
            mock_engine_instance.run.assert_called_once_with('.')

def test_main_docs(monkeypatch, capsys):
    monkeypatch.setattr('sys.argv', ['skelantic', 'docs', 'nodes'])
    from skelantic.cli import main
    try:
        main()
    except SystemExit:
        pass
    captured = capsys.readouterr()
    assert "Error: Could not locate" in captured.out or "Skelantic File System Nodes" in captured.out
