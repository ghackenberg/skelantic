import pytest
from skelantic.commons.config import ConfigLoader, get_regex
import yaml

def test_config_loader_errors(tmp_path):
    def cb(sev, p, res): pass
    loader = ConfigLoader(cb)

    # Test load_config non-existent file
    assert loader.load_config("does_not_exist.yaml") == {}

    # Test YAML syntax error
    f = tmp_path / "bad.yaml"
    f.write_text(":")
    assert loader.load_config(str(f)) == {}

    # Test resolve_paths
    conf = {"files": {"test.md": {"template": "tmp.md"}}}
    res = loader.resolve_paths(conf, "/base")
    assert res["files"]["test.md"]["template"].startswith("/base")

    # Test validation
    bad_conf = tmp_path / "invalid.yaml"
    bad_conf.write_text(yaml.dump({
        "files": {
            "test.md": {"unknown_key": "val"}
        }
    }))
    loader.load_config(str(bad_conf))

def test_expand_deep_paths():
    def cb(sev, p, res): pass
    loader = ConfigLoader(cb)
    
    # Test expanding deep path in directories
    config = {
        "directories": {
            "a/b": {
                "description": "deep path"
            }
        }
    }
    expanded = loader.expand_deep_paths(config)
    assert "a" in expanded["directories"]
    assert "b" in expanded["directories"]["a"]["directories"]
    assert expanded["directories"]["a"]["directories"]["b"]["description"] == "deep path"
    
    config2 = {
        "files": {
            "a/b/c.md": {
                "description": "deep file"
            }
        }
    }
    expanded2 = loader.expand_deep_paths(config2)
    assert "a" in expanded2["files"]
    assert "b" in expanded2["files"]["a"]["directories"]
    assert "c.md" in expanded2["files"]["a"]["directories"]["b"]["directories"]
