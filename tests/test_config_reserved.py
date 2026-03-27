import pytest
import os
from skelantic.commons.config import ConfigLoader

def test_config_reserved_names(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # We need a real callback to capture results
    results = []
    def callback(level, path, messages):
        results.append((level, path, messages))
    
    loader = ConfigLoader(callback)
    
    config_path = tmp_path / "config.yaml"
    config_content = """
description: "Root"
directories:
  .skelantic:
    description: "Invalid"
"""
    config_path.write_text(config_content, encoding="utf-8")
    
    loader.load_config(str(config_path))
    
    assert any("Der Name '.skelantic' wird von Skelantic standardmäßig ignoriert" in msg 
              for level, path, messages in results for msg in messages)

def test_config_reserved_names_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    results = []
    def callback(level, path, messages):
        results.append((level, path, messages))
    
    loader = ConfigLoader(callback)
    
    config_path = tmp_path / "config.yaml"
    config_content = """
description: "Root"
files:
  __pycache__:
    description: "Invalid"
"""
    config_path.write_text(config_content, encoding="utf-8")
    
    loader.load_config(str(config_path))
    
    assert any("Der Name '__pycache__' wird von Skelantic standardmäßig ignoriert" in msg 
              for level, path, messages in results for msg in messages)
