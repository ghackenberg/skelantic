import os
import pathlib
from typing import Any, Dict, List, Optional, cast
from dataclasses import dataclass, field
from .config import ConfigLoader, get_regex

@dataclass
class ResolvedNode:
    path: str
    is_directory: bool
    exists: bool
    match_path: str
    parent_folder: str
    config: Dict[str, Any]
    path_params: Dict[str, str] = field(default_factory=lambda: cast(Dict[str, str], {}))
    node_type: str = ""
    parent_type: str = ""
    template_path: Optional[str] = None
    allowed_child_files: List[str] = field(default_factory=lambda: cast(List[str], []))
    allowed_child_dirs: List[str] = field(default_factory=lambda: cast(List[str], []))

class PathResolver:
    def __init__(self, node_map: Dict[str, Any]) -> None:
        self.config_loader = ConfigLoader(lambda s, p, r: None)
        self.node_map = node_map

    def resolve(self, target_path: str, base_dir: str = ".") -> Optional[ResolvedNode]:
        target_path_obj = pathlib.Path(target_path)
        segments = target_path_obj.parts
        
        current_abs_path = pathlib.Path(base_dir).resolve()
        
        # Start with root config
        root_config_path = current_abs_path / ".skelantic" / "config.yaml"
        current_config = self.config_loader.load_config(str(root_config_path)) or {}
        current_config = self.config_loader.resolve_paths(current_config, str(current_abs_path))
        
        path_params: Dict[str, str] = {}
        current_match_parts: List[str] = []
        is_dir = True # Root is a directory
        
        # Traverse segments
        for segment in segments:
            matched_n: Optional[Dict[str, Any]] = None
            matched_pattern: Optional[str] = None
            seg_is_dir = False
            
            # Try directories first
            for pat, conf in current_config.get('directories', {}).items():
                regex = get_regex(pat)
                m = regex.match(segment)
                if m:
                    matched_n = cast(Dict[str, Any], conf)
                    matched_pattern = pat
                    path_params.update(m.groupdict())
                    seg_is_dir = True
                    break
            
            # Try files
            if not matched_n:
                for pat, conf in current_config.get('files', {}).items():
                    regex = get_regex(pat)
                    m = regex.match(segment)
                    if m:
                        matched_n = cast(Dict[str, Any], conf)
                        matched_pattern = pat
                        path_params.update(m.groupdict())
                        seg_is_dir = False
                        break
            
            if not matched_n:
                return None
            
            current_match_parts.append(matched_pattern) # type: ignore
            current_config = matched_n
            current_abs_path = current_abs_path / segment
            
            # Load cascading config if we entered a directory
            if seg_is_dir:
                local_config_path = current_abs_path / ".skelantic" / "config.yaml"
                if local_config_path.exists():
                    local_c = self.config_loader.load_config(str(local_config_path))
                    local_c = self.config_loader.resolve_paths(local_c, str(current_abs_path))
                    if 'files' not in current_config: current_config['files'] = {}
                    if 'directories' not in current_config: current_config['directories'] = {}
                    current_config['files'].update(local_c.get('files') or {})
                    current_config['directories'].update(local_c.get('directories') or {})
            
            is_dir = seg_is_dir

        full_path = current_abs_path
        res_exists = full_path.exists()
        res_is_dir = full_path.is_dir() if res_exists else (not segments or is_dir)

        # Final resolved state
        if res_is_dir:
            local_config_path = current_abs_path / ".skelantic" / "config.yaml"
            if local_config_path.exists():
                local_c = self.config_loader.load_config(str(local_config_path))
                local_c = self.config_loader.resolve_paths(local_c, str(current_abs_path))
                if 'files' not in current_config: current_config['files'] = {}
                if 'directories' not in current_config: current_config['directories'] = {}
                current_config['files'].update(local_c.get('files') or {})
                current_config['directories'].update(local_c.get('directories') or {})

        full_match_path = "/".join(current_match_parts)
        parent_folder = str(pathlib.Path(target_path).parent).replace('\\', '/')
        
        res = ResolvedNode(
            path=target_path.replace('\\', '/'),
            is_directory=res_is_dir,
            exists=res_exists,
            match_path=full_match_path,
            parent_folder=parent_folder if parent_folder != "." else ".",
            config=current_config,
            path_params=path_params,
            template_path=current_config.get('template')
        )
        
        # Determine types from node_map
        if full_match_path in self.node_map:
            cls = self.node_map[full_match_path]
            res.node_type = f"RepoGraph.{cls.__qualname__}" if hasattr(cls, "__qualname__") else str(cls)
            # Parent type
            if "." in res.node_type:
                res.parent_type = ".".join(res.node_type.split(".")[:-1])

        # If directory, list allowed children
        if res.is_directory:
            for pat in current_config.get('files', {}).keys():
                res.allowed_child_files.append(pat)
            for pat in current_config.get('directories', {}).keys():
                res.allowed_child_dirs.append(pat)
                
        return res
