import sys
import pytest
from unittest.mock import patch
from io import StringIO
from skelantic.cli import main

def test_cli_docs_help():
    with patch.object(sys, 'argv', ['skelantic', 'docs']):
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            try:
                main()
            except SystemExit:
                pass
            
            output = mock_stdout.getvalue()
            assert "Skelantic Documentation" in output
            assert "Available topics:" in output

def test_cli_docs_topic():
    with patch.object(sys, 'argv', ['skelantic', 'docs', 'templates']):
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            try:
                main()
            except SystemExit:
                pass
            output = mock_stdout.getvalue()
            assert "Skeletal Templates" in output
            
def test_cli_docs_invalid_topic():
    with patch.object(sys, 'argv', ['skelantic', 'docs', 'invalid_topic']):
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            with pytest.raises(SystemExit) as excinfo:
                main()
            assert excinfo.value.code == 1
            output = mock_stdout.getvalue()
            assert "Error: Topic 'invalid_topic' not found" in output

def test_cli_docs_all():
    with patch.object(sys, 'argv', ['skelantic', 'docs', '--all']):
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            try:
                main()
            except SystemExit:
                pass
            output = mock_stdout.getvalue()
            assert "<skelantic_documentation>" in output
            assert "<document path=" in output
