from typing import Any
from unittest.mock import Mock, patch
from pathlib import Path

from skelantic.commons.processors import dead_link, build_document_graph, check_orphaned_documents, backlink_enforcement
from skelantic.commons.documents import MarkdownDocument
from skelantic.commons.context import LinterContext

def test_dead_link(tmp_path: Any) -> None:
    doc_path = tmp_path / "test.md"
    doc_path.write_text("[Dead Link](non-existent.md)")
    
    mock_node = Mock()
    mock_node.rel_path = Path("test.md")
    mock_node.parent_dir = tmp_path
    mock_node.document = MarkdownDocument(str(doc_path))
    
    res = dead_link(mock_node)
    
    assert any("Dead Link" in e for e in res)

    # Test templates ignored
    mock_node.rel_path = Path(".templates/test.md")
    assert dead_link(mock_node) == []

    # Test missing document
    del mock_node.document
    mock_node.rel_path = Path("test.md")
    assert dead_link(mock_node) == []

def test_build_document_graph(tmp_path: Path) -> None:
    ctx = LinterContext()
    doc_path = tmp_path / "test.md"
    doc_path.write_text("[Link](other.md)")

    mock_node = Mock()
    mock_node.rel_path = Path("test.md")
    mock_node.abs_path = doc_path
    mock_node.parent_dir = tmp_path
    mock_node.document = MarkdownDocument(str(doc_path))

    build_document_graph(mock_node, ctx)
    assert "all_markdown_files" in ctx.store
    assert str(doc_path.as_posix()) in ctx.store["all_markdown_files"]
    assert "referenced_markdown_files" in ctx.store
    assert str((tmp_path / "other.md").resolve().as_posix()) in ctx.store["referenced_markdown_files"]

    # Test templates ignored
    mock_node.rel_path = Path(".templates/test.md")
    build_document_graph(mock_node, ctx)
    
    # Test missing document
    del mock_node.document
    mock_node.rel_path = Path("test2.md")
    mock_node.abs_path = tmp_path / "test2.md"
    build_document_graph(mock_node, ctx)

def test_check_orphaned_documents(tmp_path: Path) -> None:
    ctx = LinterContext()
    ctx.store["all_markdown_files"] = {"orphan.md", "linked.md"}
    ctx.store["referenced_markdown_files"] = {"linked.md"}
    
    res = check_orphaned_documents(ctx)
    assert len(res) == 1
    assert "orphan.md" in res[0]

def test_backlink_enforcement(tmp_path: Path) -> None:
    def mock_exists_fn(path_str: Any) -> bool:
        return str(path_str).endswith("README.md")

    # Test README.md ignored
    mock_node = Mock()
    mock_node.rel_path = Path("README.md")
    mock_node.name = "README.md"
    assert backlink_enforcement(mock_node) == []

    # Test templates ignored
    mock_node.rel_path = Path(".templates/test.md")
    mock_node.name = "test.md"
    assert backlink_enforcement(mock_node) == []

    # Test missing document
    mock_node.rel_path = Path("dir/test.md")
    mock_node.name = "test.md"
    mock_node.document = None
    del mock_node.document
    # Mocking that a README exists
    readme_path = tmp_path / "README.md"
    readme_path.write_text("Mock README")

    with patch("os.path.exists") as mock_exists:
        mock_exists.side_effect = mock_exists_fn
        assert backlink_enforcement(mock_node) == []

    # Test missing backlink
    doc_path = tmp_path / "test.md"
    doc_path.write_text("No backlink here")
    mock_node.document = MarkdownDocument(str(doc_path))

    with patch("os.path.exists") as mock_exists:
        mock_exists.side_effect = mock_exists_fn
        res = backlink_enforcement(mock_node)
        assert len(res) == 1
        assert "Fehlender oder falscher Backlink" in res[0]

    # Test valid backlink
    doc_path.write_text("[Zurück](README.md)")
    mock_node.document = MarkdownDocument(str(doc_path))

    with patch("os.path.exists") as mock_exists:
        mock_exists.side_effect = mock_exists_fn
        res = backlink_enforcement(mock_node)
        assert res == []

    # Test frontmatter
    doc_path.write_text("---\nmarp: true\n---\n[Zurück](README.md)")
    mock_node.document = MarkdownDocument(str(doc_path))

    with patch("os.path.exists") as mock_exists:
        mock_exists.side_effect = mock_exists_fn
        res = backlink_enforcement(mock_node)
        assert res == []

