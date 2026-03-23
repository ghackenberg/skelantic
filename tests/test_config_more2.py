from skelantic.commons.config import ConfigLoader
from collections import defaultdict
import yaml

def test_config_loader_invalid_node(tmp_path):
    loader = ConfigLoader(lambda sev, p, res: None)
    
    # Missing description
    bad_conf = tmp_path / "bad.yaml"
    bad_conf.write_text(yaml.dump({
        "files": {
            "test.md": {}
        }
    }))
    loader.load_config(str(bad_conf))

    # Unknown key
    bad_conf2 = tmp_path / "bad2.yaml"
    bad_conf2.write_text(yaml.dump({
        "files": {
            "test.md": {"description": "desc", "unknown": "value"}
        }
    }))
    loader.load_config(str(bad_conf2))

    # Not a dict
    bad_conf3 = tmp_path / "bad3.yaml"
    bad_conf3.write_text(yaml.dump({
        "files": "not_a_dict"
    }))
    loader.load_config(str(bad_conf3))

    # Directories not a dict
    bad_conf4 = tmp_path / "bad4.yaml"
    bad_conf4.write_text(yaml.dump({
        "directories": "not_a_dict"
    }))
    loader.load_config(str(bad_conf4))
