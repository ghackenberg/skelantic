import os
import re
import yaml
from typing import Any, Callable, Dict, Pattern, List, Match, cast

class ConfigLoader:
    def __init__(self, add_results_callback: Callable[[str, str, List[str]], None]) -> None:
        self.add_results = add_results_callback

    def load_config(self, path: str) -> Dict[str, Any]:
        if not os.path.exists(path): return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                config = cast(Dict[str, Any], yaml.safe_load(f) or {})
            self._validate_config(config, path)
            return self.expand_deep_paths(config)
        except Exception as e:
            self.add_results("ERROR", path, [f"YAML Error: {e}"])
            return {}

    def _validate_config(self, config: Any, config_path: str) -> None:
        if not isinstance(config, dict):
            self.add_results("ERROR", config_path, ["Konfiguration muss ein Dictionary sein."])
            return
        
        config_dict = cast(Dict[str, Any], config)
        if "description" not in config_dict:
            self.add_results("ERROR", config_path, ["Fehlende 'description' auf Root-Ebene der Konfiguration."])
            
        allowed_root = {"description", "files", "directories", "assertions", "patterns"}
        for k, v in config_dict.items():
            if k not in allowed_root:
                self.add_results("ERROR", config_path, [f"Ungültiger Key '{k}'."])
            if k in ["files", "directories"] and isinstance(v, dict):
                for sub_k, sub_v in cast(Dict[str, Any], v).items():
                    self._validate_node_config(sub_v, config_path, sub_k)

    def _validate_node_config(self, config: Any, config_path: str, node_name: str) -> None:
        if not isinstance(config, dict): return

        config_dict = cast(Dict[str, Any], config)
        if "description" not in config_dict:
            self.add_results("ERROR", config_path, [f"Fehlende 'description' für den Knoten '{node_name}'."])

        allowed = {"description", "assertions", "template", "optional", "silent", "files", "directories", "authorize"}
        for k in config_dict.keys():
            if k not in allowed:
                self.add_results("ERROR", config_path, [f"Ungültiger Key '{k}' im Knoten '{node_name}'."])
                
        if "files" in config_dict and isinstance(config_dict["files"], dict):
            for sub_k, sub_v in cast(Dict[str, Any], config_dict["files"]).items():
                self._validate_node_config(sub_v, config_path, f"{node_name}/{sub_k}")
        if "directories" in config_dict and isinstance(config_dict["directories"], dict):
            for sub_k, sub_v in cast(Dict[str, Any], config_dict["directories"]).items():
                self._validate_node_config(sub_v, config_path, f"{node_name}/{sub_k}")

    def expand_deep_paths(self, config: Dict[str, Any]) -> Dict[str, Any]:
        for section in ["files", "directories"]:
            if section not in config: continue
            new_section: Dict[str, Any] = {}
            for pat, val in cast(Dict[str, Any], config[section]).items():
                if "/" in pat and "*" not in pat:
                    parts = pat.split("/")
                    curr = new_section
                    for part in parts[:-1]:
                        if part not in curr: curr[part] = {"directories": {}, "optional": True, "silent": True}
                        curr = cast(Dict[str, Any], curr[part]["directories"])
                    curr[parts[-1]] = val
                else: new_section[pat] = val
            config[section] = new_section
        return config

    def resolve_paths(self, config: Dict[str, Any], base_dir: str) -> Dict[str, Any]:
        new_c = config.copy()
        for k, v in new_c.items():
            if k == 'template' and isinstance(v, str) and not os.path.isabs(v):
                new_c[k] = os.path.join(base_dir, v).replace('\\', '/')
            elif isinstance(v, dict):
                new_c[k] = self.resolve_paths(cast(Dict[str, Any], v), base_dir)
        return new_c

def get_regex(pattern: str) -> Pattern[str]:
    if pattern == "*": return re.compile(r"^[^/]+$")
    if pattern == "**": return re.compile(r"^.*$")
    is_recursive_start = pattern.startswith("**/")
    if is_recursive_start: pattern = pattern[3:]
    pattern = pattern.replace("**", "__DOUBLE_STAR__").replace("*", "__SINGLE_STAR__")
    escaped = re.escape(pattern)
    def repl(match: Match[str]) -> str:
        var_name, var_type, var_args = match.groups()
        word_regex = r"[a-z][a-z0-9]*"
        if var_type == "int": type_regex = rf"\d{{{var_args}}}" if var_args else r"\d+"
        elif var_type == "words":
            min_w = int(var_args.split(',')[0]) if var_args else 1
            max_w = int(var_args.split(',')[1]) if var_args and ',' in var_args else min_w
            type_regex = rf"{word_regex}(?:-{word_regex}){{{max(0, min_w-1)},{max(0, max_w-1)}}}"
        else: type_regex = word_regex
        return f"(?P<{var_name}>{type_regex})"
    regex_string = re.sub(r'\\\{([a-zA-Z0-9_]+)(?::([a-zA-Z0-9_]+)(?:\\\(([0-9,]+)\\\))?)?\\\}', repl, escaped)
    regex_string = regex_string.replace("__DOUBLE_STAR__", ".*").replace("__SINGLE_STAR__", "[^/]*")
    return re.compile(rf"^(?:.*\/)?{regex_string}$") if is_recursive_start else re.compile(f"^{regex_string}$")
