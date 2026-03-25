from skelantic.commons.core import LinterEngine
from skelantic.commons.decorators import registry

def test_core_walk_and_validate_directories(tmp_path):
    engine = LinterEngine(registry)
    
    # Create a dummy structure
    d = tmp_path / "mydir"
    d.mkdir()
    f = d / "file.txt"
    f.write_text("hello")
    
    config = {
        "directories": {
            "mydir": {
                "authorize": True,
                "files": {
                    "file.txt": {"authorize": True}
                }
            }
        }
    }
    
    all_files = []
    engine._walk_and_validate(str(tmp_path), config, all_files, rel_path=".")
    
    # Check if directory was added to all_files
    assert any(f['filename'] == 'mydir' and f['is_directory'] for f in all_files)
    assert any(f['filename'] == 'file.txt' and not f['is_directory'] for f in all_files)

def test_core_walk_and_validate_ignore_patterns(tmp_path):
    engine = LinterEngine(registry)
    
    d = tmp_path / "mydir"
    d.mkdir()
    f = d / "test.md"
    f.write_text("hello")
    i = tmp_path / "ignored.tmp"
    i.write_text("ignore me")
    
    config = {
        "directories": {
            "mydir": {}
        },
        "files": {
            "test.md": {},
            "*.tmp": {"ignore": True}
        }
    }
    
    engine.config = config
    all_files = []
    engine.run(str(tmp_path))
    
    assert "ignored.tmp" not in engine.results_tree["root"]
