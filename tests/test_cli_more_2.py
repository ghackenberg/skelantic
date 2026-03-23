from unittest.mock import patch, MagicMock
import pytest
import sys

def test_main_stdout_reconfigure(monkeypatch):
    monkeypatch.setattr('sys.argv', ['skelantic', '--help'])
    # Mock sys.stdout to have reconfigure
    mock_stdout = MagicMock()
    monkeypatch.setattr('sys.stdout', mock_stdout)
    from skelantic.cli import main
    try:
        main()
    except SystemExit:
        pass
    mock_stdout.reconfigure.assert_called_once_with(encoding='utf-8')

def test_main_stdout_reconfigure_exception(monkeypatch):
    monkeypatch.setattr('sys.argv', ['skelantic', '--help'])
    mock_stdout = MagicMock()
    mock_stdout.reconfigure.side_effect = Exception("test")
    monkeypatch.setattr('sys.stdout', mock_stdout)
    from skelantic.cli import main
    try:
        main()
    except SystemExit:
        pass

def test_main_run_processor_import_error(monkeypatch):
    monkeypatch.setattr('sys.argv', ['skelantic', 'run', '-t', 'dummy', '-p', 'non_existent'])
    from skelantic.cli import main
    with pytest.raises(SystemExit) as e:
        main()
    assert e.value.code == 1

def test_main_run_types_import_error(monkeypatch):
    monkeypatch.setattr('sys.argv', ['skelantic', 'run', '-t', 'non_existent'])
    from skelantic.cli import main
    with pytest.raises(SystemExit) as e:
        main()
    assert e.value.code == 1

def test_main_docs_error(monkeypatch, capsys):
    monkeypatch.setattr('sys.argv', ['skelantic', 'docs', 'unknown'])
    from skelantic.cli import main
    with patch('skelantic.cli.get_docs_base_path', return_value=None, create=True):
        # We don't really need to patch get_docs_base_path if we just pass a bad topic
        pass
    try:
        main()
    except SystemExit:
        pass
    captured = capsys.readouterr()
    assert "Error:" in captured.out

def test_main_run_failed(monkeypatch):
    monkeypatch.setattr('sys.argv', ['skelantic', 'run', '-t', 'os']) # Use an existing module for types
    with patch('skelantic.cli.LinterEngine') as mock_engine:
        mock_instance = MagicMock()
        mock_instance.print_report.return_value = True # failed
        mock_engine.return_value = mock_instance
        from skelantic.cli import main
        with pytest.raises(SystemExit) as e:
            main()
        assert e.value.code == 1
