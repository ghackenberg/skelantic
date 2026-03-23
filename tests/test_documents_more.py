from skelantic.commons.documents import Document, MarkdownDocument
from unittest.mock import mock_open, patch

def test_document_errors():
    doc = Document("non_existent_file.txt")
    assert doc.raw_content == ""
    assert doc.parse_error is not None

@patch('builtins.open', new_callable=mock_open, read_data="line1\nline2")
def test_document_success(mock_file):
    doc = Document("fake_file.txt")
    assert doc.raw_content == "line1\nline2"

@patch('builtins.open', new_callable=mock_open, read_data="---\ntitle: test\n---\n# H1\n[link](/test/url)")
def test_markdown_document(mock_file):
    doc = MarkdownDocument("fake.md")
    assert doc.ast_node is not None
    assert doc.has_text("title: test")
    
    links = doc.get_links()
    assert "/test/url" in links

@patch('builtins.open', new_callable=mock_open, read_data="---\n|table|a|\n|---|---|\n")
def test_markdown_document_tables(mock_file):
    doc = MarkdownDocument("fake.md")
    tables = doc.get_tables()
    assert len(tables) > 0
