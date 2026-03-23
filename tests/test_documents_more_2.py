from skelantic.commons.documents import Document, MarkdownDocument
from unittest.mock import patch, mock_open
import pytest

def test_document_fallback_encoding(tmp_path):
    # Create a file with non-utf8 encoding
    f = tmp_path / "latin1.txt"
    f.write_bytes(b'Test \xe4') # latin-1 for 'ä'
    
    doc = Document(str(f))
    assert doc.raw_content == "Test ä"
    assert doc.parse_error is None

def test_document_read_error(tmp_path):
    f = tmp_path / "protected.txt"
    f.write_text("secret")
    
    with patch('builtins.open', side_effect=Exception("Access Denied")):
        doc = Document(str(f))
        assert doc.parse_error is not None
        assert "Access Denied" in doc.parse_error

def test_markdown_parser_error(tmp_path):
    f = tmp_path / "bad.md"
    f.write_text("# Hello")
    
    with patch('markdown_it.MarkdownIt.parse', side_effect=Exception("Markdown Error")):
        doc = MarkdownDocument(str(f))
        assert doc.parse_error is not None
        assert "Markdown Syntax Error" in doc.parse_error
