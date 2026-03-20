from pathlib import Path
from unittest.mock import patch
from skelantic.commons.nodes import FSNode, FileNode
from skelantic.commons.context import LinterContext
from typing import Any

def test_fsnode_properties() -> None:
    ctx = LinterContext()
    node = FSNode("C:/abs/path/file.txt", "path/file.txt", ctx)
    
    assert node.name == "file.txt"
    assert node.parent_dir == Path("path")

def test_fsnode_resolve() -> None:
    ctx = LinterContext()
    target_node = FSNode("C:/abs/path/other.txt", "path/other.txt", ctx)
    ctx.register_node(target_node)
    
    node = FSNode("C:/abs/path/file.txt", "path/file.txt", ctx)
    
    # Test valid resolve
    with patch("pathlib.Path.cwd", return_value=Path("C:/abs")):
        # We need to explicitly mock resolve() on the path object since the actual test filesystem path 'C:/abs/path' might not exist on Windows and cause resolve() to behave weirdly, or just patch Path.resolve to return the mocked path.
        with patch.object(Path, "resolve", return_value=Path("C:/abs/path/other.txt")):
            resolved = node.resolve("other.txt")
            assert resolved is target_node
            
        # Test invalid path string that cannot be resolved relative to cwd
        with patch("pathlib.Path.relative_to", side_effect=ValueError):
            assert node.resolve("impossible") is None

def test_filenode_document(tmp_path: Any) -> None:
    ctx = LinterContext()
    
    md_path = tmp_path / "test.md"
    md_path.write_text("# Test")
    
    md_node = FileNode(str(md_path), "test.md", ctx)
    assert md_node.document.__class__.__name__ == "MarkdownDocument"
    
    txt_path = tmp_path / "test.txt"
    txt_path.write_text("Test")
    
    txt_node = FileNode(str(txt_path), "test.txt", ctx)
    assert txt_node.document.__class__.__name__ == "Document"
