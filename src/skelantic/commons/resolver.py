import pathlib
import os
from typing import Any, Dict, List, Optional, cast
from pydantic import BaseModel

class ResolvedNode(BaseModel):
    path: str
    is_directory: bool
    allowed_child_files: List[str] = []
    allowed_child_dirs: List[str] = []
    match_path: Optional[str] = None
    node_type: Optional[str] = None
    path_variables: Dict[str, str] = {}
    template_vars: Dict[str, str] = {}
    # Extra fields for CLI display
    exists: bool = False
    parent_folder: str = "."
    config: Dict[str, Any] = {}
    template_path: Optional[str] = None
    parent_type: Optional[str] = None

class PathResolver:
    def __init__(self, node_map: Dict[str, Any]) -> None:
        self.node_map = node_map
        from .config import ConfigLoader
        self.config_loader = ConfigLoader(lambda _s, _p, _r: None)

    def resolve(self, target_path: str, base_dir: str = ".") -> Optional[ResolvedNode]:
        """Resolves a path segment by segment against the schema."""
        from .config import get_regex
        target_path = target_path.replace('\\', '/').strip('/')
        if target_path == "" or target_path == ".":
            target_path = "."

        current_abs = pathlib.Path(base_dir).resolve()
        current_rel = "."
        
        # Load root config
        root_cfg_path = current_abs / ".skelantic" / "config.yaml"
        if not root_cfg_path.exists():
            return None
            
        current_config: Dict[str, Any] = self.config_loader.load_config(str(root_cfg_path))
        
        res = ResolvedNode(path=target_path, is_directory=True)
        res.exists = os.path.exists(os.path.join(base_dir, target_path)) if target_path != "." else True
        res.config = current_config
        
        if target_path == ".":
            res.node_type = self.node_map.get(".", object).__name__ if "." in self.node_map else "RepoGraph"
            for pat in cast(Dict[str, Any], current_config.get('files', {})).keys():
                res.allowed_child_files.append(str(pat))
            for pat in cast(Dict[str, Any], current_config.get('directories', {})).keys():
                res.allowed_child_dirs.append(str(pat))
            return res

        segments = target_path.split('/')
        for i, segment in enumerate(segments):
            is_last = (i == len(segments) - 1)
            found = False
            
            # Check directories
            for pattern, cfg_val in cast(Dict[str, Any], current_config.get('directories', {})).items():
                regex = get_regex(str(pattern))
                match = regex.match(segment)
                if match:
                    res.path_variables.update({str(k): str(v) for k, v in match.groupdict().items()})
                    res.parent_folder = current_rel
                    current_rel = f"{current_rel}/{segment}".strip('/')
                    current_abs = current_abs / segment
                    
                    # Merge local config if exists
                    local_cfg = current_abs / ".skelantic" / "config.yaml"
                    if local_cfg.exists():
                        new_cfg: Dict[str, Any] = self.config_loader.load_config(str(local_cfg))
                        current_config = {
                            'description': str(new_cfg.get('description', current_config.get('description', ''))),
                            'files': {**cast(Dict[str, Any], current_config.get('files', {})), **cast(Dict[str, Any], new_cfg.get('files', {}))},
                            'directories': {**cast(Dict[str, Any], current_config.get('directories', {})), **cast(Dict[str, Any], new_cfg.get('directories', {}))}
                        }
                    else:
                        current_config = cast(Dict[str, Any], cfg_val)
                    
                    if is_last:
                        res.is_directory = True
                        res.match_path = str(pattern)
                        res.config = current_config
                        res.node_type = self.node_map.get(current_rel, object).__name__ if current_rel in self.node_map else "DirectoryNode"
                    found = True
                    break
            
            if found: continue
            
            # Check files (only at the last segment)
            if is_last:
                for pattern, cfg_val in cast(Dict[str, Any], current_config.get('files', {})).items():
                    regex = get_regex(str(pattern))
                    match = regex.match(segment)
                    if match:
                        res.path_variables.update({str(k): str(v) for k, v in match.groupdict().items()})
                        res.is_directory = False
                        res.match_path = str(pattern)
                        res.config = cast(Dict[str, Any], cfg_val)
                        res.parent_folder = current_rel
                        current_rel = f"{current_rel}/{segment}".strip('/')
                        res.node_type = self.node_map.get(current_rel, object).__name__ if current_rel in self.node_map else "FileNode"
                        
                        # Extract template vars if possible
                        template_p = res.config.get('template')
                        if template_p:
                            from .core import SkeletalMatcher
                            # Resolve template path relative to current config or root
                            t_path = pathlib.Path(base_dir) / str(template_p)
                            res.template_path = str(t_path)
                            if t_path.exists():
                                matcher = SkeletalMatcher(t_path.read_text(encoding="utf-8"))
                                for node_item in matcher.nodes:
                                    name_val: Optional[Any] = getattr(node_item, "name", None)
                                    type_val: Optional[Any] = getattr(node_item, "type_str", None)
                                    if name_val is not None and type_val is not None:
                                        res.template_vars[str(name_val)] = str(type_val)
                        
                        found = True
                        break
            
            if not found:
                return None # Path cannot be resolved

        # Finalize allowed children if it's a directory
        if res.is_directory:
            for pat in cast(Dict[str, Any], current_config.get('files', {})).keys():
                res.allowed_child_files.append(str(pat))
            for pat in cast(Dict[str, Any], current_config.get('directories', {})).keys():
                res.allowed_child_dirs.append(str(pat))
                
        return res
