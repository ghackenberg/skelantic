import pytest
import yaml
from skelantic.commons.config import ConfigLoader, get_regex

def test_config_path_variables_validation(tmp_path):
    errors = []
    def cb(sev, p, res):
        errors.extend(res)
    loader = ConfigLoader(cb)
    
    bad_vars = tmp_path / "bad_vars.yaml"
    bad_vars.write_text(yaml.dump({
        "description": "test",
        "files": {
            "{my_var}.md": {"description": "no type"},
            "{my_var:unknown}.md": {"description": "unknown type"}
        }
    }))
    
    loader.load_config(str(bad_vars))
    assert any("hat keinen expliziten Datentyp" in e for e in errors)
    assert any("Unbekannter Datentyp 'unknown'" in e for e in errors)

def test_get_regex_lengths():
    # Test strict char and digit length parsing
    regex = get_regex("{id:digit}.md")
    assert regex.match("5.md")
    assert regex.match("55.md") is None
    
    regex2 = get_regex("{id:digit(2)}.md")
    assert regex2.match("42.md")
    assert regex2.match("4.md") is None
    
    regex3 = get_regex("{name:char(1,3)}.md")
    assert regex3.match("a.md")
    assert regex3.match("abc.md")
    assert regex3.match("abcd.md") is None

    regex4 = get_regex("{name:char(2,)}.md")
    assert regex4.match("ab.md")
    assert regex4.match("abc.md")
    assert regex4.match("a.md") is None
