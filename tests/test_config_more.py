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
    assert res["files"]["test.md"]["template"].replace('\\', '/').startswith("/base")

    # Test validation
    bad_conf = tmp_path / "invalid.yaml"
    bad_conf.write_text(yaml.dump({
        "files": {
            "test.md": {"unknown_key": "val"}
        }
    }))
    loader.load_config(str(bad_conf))

def test_config_ignore_validation(tmp_path):
    # Test our new ignore restrictions
    errors = []
    def cb(sev, p, res):
        errors.extend(res)
    loader = ConfigLoader(cb)
    
    bad_ignore = tmp_path / "bad_ignore.yaml"
    bad_ignore.write_text(yaml.dump({
        "description": "test",
        "directories": {
            "my_dir": {
                "ignore": True,
                "optional": True, # Should error because we can't have both
                "files": {
                    "test.md": {}
                }
            }
        },
        "files": {
            "my_file.md": {
                "ignore": True,
                "template": "x.md" # Should error
            }
        }
    }))
    
    loader.load_config(str(bad_ignore))
    assert any("ist der Key 'optional' nicht erlaubt" in e for e in errors)
    assert any("ist der Key 'files' nicht erlaubt" in e for e in errors)
    assert any("ist der Key 'template' nicht erlaubt" in e for e in errors)
