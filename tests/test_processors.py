from typing import Any
from unittest.mock import Mock, patch
from pathlib import Path

from skelantic.commons.processors import dead_link, build_document_graph, check_orphaned_documents, backlink_enforcement, GlobalMetadataState
from skelantic.commons.nodes import MarkdownNode, FileNode

def test_dead_link(tmp_path):
    """Prüft, ob tote Links erkannt werden."""
    doc_path = tmp_path / "README.md"
    doc_path.write_text("[Toter Link](non_existent.md)")
    
    mock_node = Mock(spec=MarkdownNode)
    mock_node.abs_path = doc_path
    mock_node.rel_path = Path("README.md")
    
    from skelantic.commons.documents import MarkdownDocument
    mock_node.document = MarkdownDocument(str(doc_path))
    
    res = dead_link(mock_node, lambda x: None)
    assert len(res) == 1
    assert "Toter Link" in res[0]

def test_build_document_graph(tmp_path):
    """Prüft, ob das Indexing von Markdown-Dateien funktioniert."""
    doc_path = tmp_path / "test.md"
    doc_path.write_text("[Link](target.md)")
    
    mock_node = Mock(spec=MarkdownNode)
    mock_node.abs_path = doc_path
    mock_node.rel_path = Path("test.md")
    
    from skelantic.commons.documents import MarkdownDocument
    mock_node.document = MarkdownDocument(str(doc_path))
    
    state = GlobalMetadataState()
    build_document_graph(mock_node, state, lambda x: None)
    
    assert str(doc_path.as_posix()) in state.all_markdown_files
    
    # Test README is NOT added to orphans
    readme_node = Mock(spec=MarkdownNode)
    readme_node.rel_path = Path("README.md")
    readme_node.abs_path = tmp_path / "README.md"
    mock_doc = Mock()
    mock_doc.get_links.return_value = []
    readme_node.document = mock_doc
    build_document_graph(readme_node, state, lambda x: None)
    assert str((tmp_path / "README.md").as_posix()) not in state.all_markdown_files
    # Link-Extraktion
    target_abs = (tmp_path / "target.md").resolve().as_posix()
    assert target_abs in state.referenced_markdown_files

def test_check_orphaned_documents():
    """Prüft, ob verwaiste Dokumente erkannt werden."""
    state = GlobalMetadataState()
    state.all_markdown_files = {"/a.md", "/b.md"}
    state.referenced_markdown_files = {"/a.md"}
    
    res = check_orphaned_documents(state, lambda x: None)
    assert len(res) == 1
    assert "b.md" in res[0]

def test_backlink_enforcement(tmp_path):
    """Prüft, ob Backlinks erzwungen werden."""
    # Setup: Subdir mit README.md und Datei ohne Backlink
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    readme = subdir / "README.md"
    readme.write_text("# Sub Readme")
    
    doc = subdir / "file.md"
    doc.write_text("# No Backlink here")
    
    mock_node = Mock(spec=MarkdownNode)
    mock_node.abs_path = doc
    mock_node.rel_path = Path("subdir/file.md")
    mock_node.name = "file.md"
    
    from skelantic.commons.documents import MarkdownDocument
    mock_node.document = MarkdownDocument(str(doc))
    
    # Sollte Fehler melden
    res = backlink_enforcement(mock_node, lambda x: None)
    assert len(res) == 2
    assert "Strukturfehler" in res[0]
    assert "Handlungsempfehlung" in res[1]
    
    # Mit korrektem Backlink
    doc.write_text("[Back](../README.md)\n# File")
    mock_node.document = MarkdownDocument(str(doc))
    res = backlink_enforcement(mock_node, lambda x: None)
    assert res == []

def test_backlink_enforcement_marp(tmp_path):
    """Prüft Backlinks in Marp-Präsentationen."""
    doc = tmp_path / "pres.md"
    doc.write_text("---\nmarp: true\n---\n\n[Home](README.md)\n# Pres")
    readme = tmp_path / "README.md"
    readme.write_text("# Readme")
    
    mock_node = Mock(spec=MarkdownNode)
    mock_node.abs_path = doc
    mock_node.rel_path = Path("pres.md")
    mock_node.name = "pres.md"
    from skelantic.commons.documents import MarkdownDocument
    mock_node.document = MarkdownDocument(str(doc))
    
    res = backlink_enforcement(mock_node, lambda x: None)
    assert res == []

def test_backlink_enforcement_multi_level(tmp_path):
    """Prüft, ob Backlinks über mehrere Ebenen gefunden werden."""
    # Root README
    (tmp_path / "README.md").write_text("# Root")
    # Sub / SubSub / file.md
    sub = tmp_path / "a" / "b"
    sub.mkdir(parents=True)
    doc = sub / "file.md"
    doc.write_text("[Back](../../README.md)")
    
    mock_node = Mock(spec=MarkdownNode)
    mock_node.abs_path = doc
    mock_node.rel_path = Path("a/b/file.md")
    mock_node.name = "file.md"
    from skelantic.commons.documents import MarkdownDocument
    mock_node.document = MarkdownDocument(str(doc))
    
    # Sollte Root README finden
    with patch("os.path.exists", side_effect=lambda x: str(tmp_path / "README.md") in x.replace('\\', '/')):
        res = backlink_enforcement(mock_node, lambda x: None)
        assert res == []

def test_check_orphaned_documents_error():
    """Prüft Fehlerbehandlung bei verwaisten Dokumenten."""
    state = GlobalMetadataState()
    state.all_markdown_files = {"/invalid/path.md"}
    # os.path.relpath will fail if path is invalid or on different drive
    with patch("os.path.relpath", side_effect=ValueError):
        res = check_orphaned_documents(state, lambda x: None)
        assert res == []

def test_check_orphaned_documents_success():
    """Prüft erfolgreiche Pfad-Umwandlung bei verwaisten Dokumenten."""
    state = GlobalMetadataState()
    state.all_markdown_files = {"/a/b/test.md"}
    with patch("os.path.relpath", return_value="a/b/test.md"):
        res = check_orphaned_documents(state, lambda x: None)
        assert len(res) == 1
        assert "a/b/test.md" in res[0]

def test_dead_link_ignore_templates(tmp_path):
    """Prüft, ob Templates ignoriert werden."""
    mock_node = Mock(spec=MarkdownNode)
    mock_node.rel_path = Path(".templates/test.md")
    assert dead_link(mock_node, lambda x: None) == []

def test_dead_link_empty_path(tmp_path):
    """Prüft leere Link-Pfade."""
    doc_path = tmp_path / "test.md"
    doc_path.write_text("[Anchor](#anchor) [Empty]()")
    mock_node = Mock(spec=MarkdownNode)
    mock_node.rel_path = Path("test.md")
    from skelantic.commons.documents import MarkdownDocument
    mock_node.document = MarkdownDocument(str(doc_path))
    assert dead_link(mock_node, lambda x: None) == []
