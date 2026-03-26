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
            return config
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

        allowed_root = {"description", "files", "directories"}
        for k, v in config_dict.items():
            if k not in allowed_root:
                self.add_results("ERROR", config_path, [f"Ungültiger Key '{k}'."])
            if k == "files" and isinstance(v, dict):
                for sub_k, sub_v in cast(Dict[str, Any], v).items():
                    self._validate_node_config(sub_v, config_path, sub_k, is_directory=False)
            if k == "directories" and isinstance(v, dict):
                for sub_k, sub_v in cast(Dict[str, Any], v).items():
                    self._validate_node_config(sub_v, config_path, sub_k, is_directory=True)

    def _validate_node_config(self, config: Any, config_path: str, node_name: str, is_directory: bool = False) -> None:
        if '*' in node_name:
            self.add_results("ERROR", config_path, [f"Wildcards ('*') sind in Dateinamen nicht mehr erlaubt: '{node_name}'. Nutze stattdessen Variablen wie '{{name:char}}.md'."])
        if '/' in node_name:
            self.add_results("ERROR", config_path, [f"Deep-Paths ('/') sind in Keys nicht erlaubt: '{node_name}'. Nutze verschachtelte YAML-Directories oder Cascading Configs."])

        # Überprüfe, ob Pfad-Variablen streng typisiert sind
        for match in re.finditer(r'\{([a-zA-Z0-9_]+)(?::([a-zA-Z0-9_]+)(?:\([0-9,]+\))?)?\}', node_name):
            var_name = match.group(1)
            var_type = match.group(2)
            if not var_type:
                self.add_results("ERROR", config_path, [f"Pfad-Variable '{{{var_name}}}' in '{node_name}' hat keinen expliziten Datentyp. Verwende z.B. '{{{var_name}:char}}'."])
            elif var_type not in ["digit", "char"]:
                self.add_results("ERROR", config_path, [f"Unbekannter Datentyp '{var_type}' in Pfad-Variable '{{{var_name}}}'."])

        if not isinstance(config, dict): return

        config_dict = cast(Dict[str, Any], config)
        if "description" not in config_dict and not config_dict.get("ignore"):
            self.add_results("ERROR", config_path, [f"Fehlende 'description' für den Knoten '{node_name}'."])

        if config_dict.get("ignore"):
            allowed_ignored = {"ignore", "description"}
            for k in config_dict.keys():
                if k not in allowed_ignored:
                    self.add_results("ERROR", config_path, [f"Knoten '{node_name}' wird ignoriert ('ignore: true'). Daher ist der Key '{k}' nicht erlaubt."])
        else:
            allowed_common = {"description", "optional", "silent", "ignore", "model", "property"}
            allowed_dir = allowed_common | {"files", "directories"}
            allowed_file = allowed_common | {"template"}
            allowed = allowed_dir if is_directory else allowed_file

            for k in config_dict.keys():
                if k not in allowed:
                    self.add_results("ERROR", config_path, [f"Ungültiger Key '{k}' im Knoten '{node_name}'."])
                
        if is_directory and not config_dict.get("ignore"):
            if "files" in config_dict and isinstance(config_dict["files"], dict):
                for sub_k, sub_v in cast(Dict[str, Any], config_dict["files"]).items():
                    self._validate_node_config(sub_v, config_path, sub_k, is_directory=False)
            if "directories" in config_dict and isinstance(config_dict["directories"], dict):
                for sub_k, sub_v in cast(Dict[str, Any], config_dict["directories"]).items():
                    self._validate_node_config(sub_v, config_path, sub_k, is_directory=True)

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
        char_regex = r"[a-zA-Z0-9_-]"
        
        # Default lengths
        min_len, max_len = "1", "1"
        
        if var_args:
            if ',' in var_args:
                parts = var_args.split(',')
                min_len = parts[0].strip() or "0"
                max_len = parts[1].strip() or ""
            else:
                min_len = var_args.strip()
                max_len = var_args.strip()
                
        quantifier = f"{{{min_len},{max_len}}}" if max_len else f"{{{min_len},}}"
        
        if var_type == "digit":
            type_regex = rf"\d{quantifier}"
        elif var_type == "char":
            type_regex = rf"{char_regex}{quantifier}"
        else:
            type_regex = rf"{char_regex}{quantifier}"
            
        return f"(?P<{var_name}>{type_regex})"
    regex_string = re.sub(r'\\\{([a-zA-Z0-9_]+)(?::([a-zA-Z0-9_]+)(?:\\\(([0-9,]+)\\\))?)?\\\}', repl, escaped)
    regex_string = regex_string.replace("__DOUBLE_STAR__", ".*").replace("__SINGLE_STAR__", "[^/]*")
    return re.compile(rf"^(?:.*\/)?{regex_string}$") if is_recursive_start else re.compile(f"^{regex_string}$")
