import os
import glob
import re
import keyword
from typing import Any, Dict, List, cast
from skelantic.templates.parser import TemplateParser, TemplateNode, LineNode
from skelantic.commons.config import ConfigLoader

def to_pascal(name: str) -> str:
    """Konvertiert einen Dateinamen in einen gültigen PascalCase Klassennamen."""
    # Führende Punkte ersetzen
    if name.startswith('.'):
        name = "Dot-" + name[1:]

    # Variablen {slug:char(1,)} extrahieren
    name = re.sub(r'\{([a-zA-Z0-9_]+)[^}]*\}', lambda m: "-" + m.group(1).capitalize() + "-", name)

    # Alle illegalen Zeichen durch Bindestrich ersetzen
    name = re.sub(r'[^a-zA-Z0-9_-]', '-', name)

    # Standard PascalCase (Bindestriche/Unterstriche/Punkte entfernen)
    clean_name = "".join(x.title() for x in re.split(r'[-_.]', name) if x)
    
    if not clean_name:
        return "UnknownNode"
        
    # Zahlen am Anfang
    if clean_name[0].isdigit():
        return "Node" + clean_name
        
    return clean_name

def to_snake(name: str) -> str:
    """Konvertiert einen String (z.B. PascalCase) zu snake_case für Properties."""
    name = re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()
    # Handle reserved keywords
    if keyword.iskeyword(name) or name in ["pass", "def", "class"]:
        name += "_"
    return name

def map_type(t_str: str) -> str:
    if t_str.startswith('digit'): return 'int'
    if t_str == 'int': return 'int'
    if t_str == 'decimal': return 'float'
    if t_str == 'bool': return 'bool'
    if t_str == 'any': return 'Any'
    if t_str.startswith('enum['): return 'str'
    return 'str'

class CodeGenerator:
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.config_loader = ConfigLoader(lambda level, path, msgs: None)
        self.template_models: Dict[str, str] = {} # template_path -> generated_class_name
        self.node_map: Dict[str, str] = {} # config_path -> generated_class_path
        
    def _parse_template_nodes(self, nodes: List[TemplateNode], class_name: str, classes_out: Dict[str, Dict[str, str]], namespace_prefix: str = "") -> Dict[str, str]:
        fields: Dict[str, str] = {}
        for node in nodes:
            if isinstance(node, LineNode):
                if node.multiline_var:
                    fields[node.multiline_var] = 'str'
                for var in node.variables:
                    fields[var.name] = map_type(var.var_type)
            elif node.type == 'block' and node.name:
                b_class = f"{class_name}{to_pascal(node.name)}Block"
                full_type = f"{namespace_prefix}{b_class}" if namespace_prefix else b_class
                fields[node.name] = f"'{full_type}'"
                self._parse_template_nodes(node.children, b_class, classes_out, namespace_prefix)
            elif node.type == 'repeat' and node.name:
                r_class = f"{class_name}{to_pascal(node.name)}Item"
                full_type = f"{namespace_prefix}{r_class}" if namespace_prefix else r_class
                fields[node.name] = f"List['{full_type}']"
                self._parse_template_nodes(node.children, r_class, classes_out, namespace_prefix)
            elif node.type == 'choice' and node.name:
                fields[f"{node.name}_type"] = 'str'
                for case_node in node.children:
                    if case_node.type == 'case':
                        c_fields = self._parse_template_nodes(case_node.children, class_name, classes_out, namespace_prefix)
                        fields.update(c_fields)
                        
        if class_name not in classes_out:
            classes_out[class_name] = fields
        else:
            classes_out[class_name].update(fields)
        return fields

    def generate_templates_graph(self) -> str:
        search_pattern_1 = os.path.join(self.base_dir, '**', '.templates', '*.md')
        search_pattern_2 = os.path.join(self.base_dir, '**', '.skelantic', 'templates', '*.md')
        templates = sorted(glob.glob(search_pattern_1, recursive=True) + glob.glob(search_pattern_2, recursive=True))
        
        # Build a tree structure from the template paths
        tree: Dict[str, Any] = {}
        
        for t_path in templates:
            rel_path = os.path.relpath(t_path, self.base_dir).replace('\\', '/')
            parts = rel_path.split('/')
            
            curr = tree
            for part in parts[:-1]:
                safe_part = to_pascal(part)
                if safe_part not in curr:
                    curr[safe_part] = {}
                curr = curr[safe_part]
                
            filename = parts[-1]
            safe_filename = to_pascal(filename.replace('.md', ''))
            
            namespace_parts = [to_pascal(p) for p in parts[:-1]]
            namespace_prefix = "Templates." + ".".join(namespace_parts) + "." if namespace_parts else "Templates."
            
            with open(t_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            parser = TemplateParser(content)
            nodes = parser.parse()
            
            classes: Dict[str, Dict[str, str]] = {}
            self._parse_template_nodes(nodes, safe_filename, classes, namespace_prefix)
            classes[safe_filename]['rel_path'] = 'str'
            
            curr[safe_filename] = classes
            
            # Store the mapping from path to the full class path in the Templates namespace
            full_class_path = namespace_prefix + safe_filename
            self.template_models[rel_path] = full_class_path

        def render_tree(node: Dict[str, Any], indent_level: int = 1) -> str:
            indent = "    " * indent_level
            out = ""
            for key, val in sorted(node.items()):
                if isinstance(val, dict) and not any(isinstance(v, dict) and 'rel_path' in v for v in cast(Dict[str, Any], val).values()):
                    # It's a directory namespace
                    out += f"{indent}class {key}:\n"
                    if not val:
                        out += f"{indent}    pass\n"
                    else:
                        out += render_tree(cast(Dict[str, Any], val), indent_level + 1)
                else:
                    # It's the classes dict for a template
                    for cls_name, fields in sorted(cast(Dict[str, Dict[str, str]], val).items()):
                        out += f"{indent}class {cls_name}(BaseModel):\n"
                        if not fields:
                            out += f"{indent}    pass\n"
                        for k, v in sorted(fields.items()):
                            if k in ['pass', 'def', 'class', 'import', 'from', 'return', 'if', 'else', 'elif', 'try', 'except', 'in', 'is']:
                                alias = k
                                k = f"{k}_"
                                out += f"{indent}    {k}: Optional[{v}] = Field(default=None, alias='{alias}')\n"
                            else:
                                out += f"{indent}    {k}: Optional[{v}] = None\n"
                        out += "\n"
            return out

        if not tree:
            return "class Templates:\n    pass\n"
            
        res = "class Templates:\n"
        res += render_tree(tree, 1)
        return res

    def _generate_path_params(self, pattern: str, indent: str) -> str:
        matches = re.finditer(r'\{([a-zA-Z0-9_]+)(?::([a-zA-Z0-9_]+)[^}]*)?\}', pattern)
        params: Dict[str, str] = {}
        for match in matches:
            var_name = match.group(1)
            var_type = match.group(2)
            if var_type == 'int':
                params[var_name] = 'int'
            else:
                params[var_name] = 'str'
                
        if not params:
            return ""
            
        out = f"{indent}class PathParams(BaseModel):\n"
        for k, v in params.items():
            out += f"{indent}    {k}: {v}\n"
        out += f"{indent}path_params: PathParams\n\n"
        return out

    def generate_repo_graph(self, config: Dict[str, Any]) -> str:
        self.node_map["root"] = "RepoGraph"
        
        def render_node(node_config: Dict[str, Any], path_parts: List[str], class_name: str, parent_class_path: str, is_dir: bool, indent_level: int) -> str:
            indent = "    " * indent_level
            
            # Determine base class
            if not is_dir:
                original_name = path_parts[-1] if path_parts else ""
                if original_name.endswith('.md'):
                    base_class = "MarkdownNode"
                else:
                    base_class = "FileNode"
            else:
                base_class = "DirectoryNode"
                
            out = f"{indent}class {class_name}({base_class}):\n"
            inner_indent = indent + "    "
            
            current_full_class_path = f"{parent_class_path}.{class_name}" if parent_class_path else class_name
            current_config_path = "/".join(path_parts) if path_parts else "root"
            self.node_map[current_config_path] = current_full_class_path
            
            has_content = False
            
            # 1. Parent Node Navigation
            if parent_class_path:
                out += f"{inner_indent}@property\n"
                out += f"{inner_indent}def parent_node(self) -> {parent_class_path}:\n"
                out += f"{inner_indent}    return cast({parent_class_path}, super().parent_node)\n\n"
                has_content = True

            # Root Node Navigation
            out += f"{inner_indent}@property\n"
            out += f"{inner_indent}def root_node(self) -> RepoGraph:\n"
            if class_name == "RepoGraph":
                out += f"{inner_indent}    return self\n\n"
            else:
                out += f"{inner_indent}    return cast(RepoGraph, super().root_node)\n\n"
            has_content = True

            # 2. Path Params
            last_part = path_parts[-1] if path_parts else ""
            if last_part:
                params_code = self._generate_path_params(last_part, inner_indent)
                if params_code:
                    out += params_code
                    has_content = True
                    
            # 3. Data Model (Template)
            template_path = node_config.get('template')
            if template_path:
                template_path = template_path.replace('\\', '/')
                if template_path in self.template_models:
                    model_type = self.template_models[template_path]
                    out += f"{inner_indent}data: {model_type}\n\n"
                    has_content = True
                else:
                    # Fallback if template not found during scanning
                    out += f"{inner_indent}data: Any # Warning: Template {template_path} not found\n\n"
                    has_content = True

            # 4. Children (Files & Directories)
            if is_dir:
                children: Dict[str, Dict[str, Any]] = {}
                for f_name, f_conf in node_config.get('files', {}).items():
                    if not f_conf.get('ignore'):
                        children[f_name] = {'config': f_conf, 'is_dir': False}
                for d_name, d_conf in node_config.get('directories', {}).items():
                    if not d_conf.get('ignore'):
                        children[d_name] = {'config': d_conf, 'is_dir': True}
                    
                # Generate child properties first
                for child_name, child_data in children.items():
                    c_conf = child_data['config']
                    c_is_dir = child_data['is_dir']
                    
                    c_class_name = c_conf.get('model', to_pascal(child_name))
                         
                    is_plural = '*' in child_name or '{' in child_name
                    
                    c_prop_name = c_conf.get('property')
                    if not c_prop_name:
                        c_prop_name = to_snake(c_class_name)
                        if is_plural and not c_prop_name.endswith('_list'):
                            c_prop_name += "_list"
                            
                    full_child_type = f"{current_full_class_path}.{c_class_name}"
                    
                    out += f"{inner_indent}@property\n"
                    out += f"{inner_indent}def {c_prop_name}(self) -> "
                    
                    if is_plural:
                        out += f"List[{full_child_type}]:\n"
                        method = "get_child_dirs_by_pattern" if c_is_dir else "get_child_files_by_pattern"
                        out += f"{inner_indent}    return cast(List[{full_child_type}], self.{method}('{child_name}'))\n\n"
                    else:
                        out += f"Optional[{full_child_type}]:\n"
                        method = "get_child_dir" if c_is_dir else "get_child_file"
                        out += f"{inner_indent}    return cast(Optional[{full_child_type}], self.{method}('{child_name}'))\n\n"
                        
                    has_content = True
                    
                # Generate child classes
                for child_name, child_data in children.items():
                    c_conf = child_data['config']
                    c_is_dir = child_data['is_dir']
                    c_class_name = c_conf.get('model', to_pascal(child_name))
                         
                    new_path = path_parts + [child_name]
                    out += render_node(c_conf, new_path, c_class_name, current_full_class_path, c_is_dir, indent_level + 1)
                    has_content = True

            if not has_content:
                out += f"{inner_indent}pass\n\n"
                
            return out

        # Merge files and directories at root level
        root_children: Dict[str, Dict[str, Any]] = {}
        for f_name, f_conf in config.get('files', {}).items():
            root_children[f_name] = {'config': f_conf, 'is_dir': False}
        for d_name, d_conf in config.get('directories', {}).items():
            root_children[d_name] = {'config': d_conf, 'is_dir': True}
            
        root_config = {'directories': config.get('directories', {}), 'files': config.get('files', {})}
        return render_node(root_config, [], "RepoGraph", "", True, 0)

    def generate(self, config_path: str, verbose: bool = False) -> str:
        config = self.config_loader.load_config(config_path)
        if verbose:
            print(f"🔍 DEBUG: Loaded root config from {config_path}")
        
        # Merge cascading config.yaml files from subdirectories
        search_pattern = os.path.join(self.base_dir, '**', '.skelantic', 'config.yaml')
        for local_config_path in glob.glob(search_pattern, recursive=True):
            rel_path = os.path.relpath(local_config_path, self.base_dir).replace('\\', '/')
            if rel_path == '.skelantic/config.yaml':
                continue # Already loaded as base config
                
            if verbose:
                print(f"🔍 DEBUG: Found cascading config: {rel_path}")
                
            local_c = self.config_loader.load_config(local_config_path)
            dir_parts = rel_path.split('/')[:-2] # Remove .skelantic/config.yaml
            local_base_dir = "/".join(dir_parts)
            local_c = self.config_loader.resolve_paths(local_c, local_base_dir)
            
            curr = config
            for part in dir_parts:
                if 'directories' not in curr:
                    curr['directories'] = {}
                if part not in curr['directories']:
                    curr['directories'][part] = {}
                curr = curr['directories'][part]
                
            if 'files' in local_c:
                if 'files' not in curr: curr['files'] = {}
                curr['files'].update(local_c['files'])
            if 'directories' in local_c:
                if 'directories' not in curr: curr['directories'] = {}
                curr['directories'].update(local_c['directories'])
                
            if verbose:
                print(f"   💡 INFO: Merged into node path: {'/'.join(dir_parts)}")

        out = "# THIS FILE IS AUTO-GENERATED BY SKELANTIC\n"
        out += "from __future__ import annotations\n"
        out += "from pydantic import BaseModel, Field # pyright: ignore[reportUnusedImport]\n"
        out += "from typing import Optional, List, Any, cast\n"
        out += "from skelantic.commons.nodes import FileNode, DirectoryNode, MarkdownNode\n\n"
        
        out += "# ==========================================\n"
        out += "# 1. TEMPLATE GRAPH\n"
        out += "# ==========================================\n"
        out += self.generate_templates_graph()
        out += "\n"
        
        out += "# ==========================================\n"
        out += "# 2. REPOSITORY GRAPH\n"
        out += "# ==========================================\n"
        out += self.generate_repo_graph(config)
        out += "\n"
        
        out += "# ==========================================\n"
        out += "# 3. RUNTIME MAPPING\n"
        out += "# ==========================================\n"
        out += "__SKELANTIC_NODE_MAP__ = {\n"
        for k, v in self.node_map.items():
            out += f"    '{k}': {v},\n"
        out += "}\n"
        
        return out

def run_codegen(config_path: str, output_path: str, verbose: bool = False) -> None:
    # config_path is usually .skelantic/config.yaml. We want the parent of the folder containing it.
    config_dir = os.path.dirname(os.path.abspath(config_path))
    base_dir = os.path.dirname(config_dir) if os.path.basename(config_dir) == '.skelantic' else config_dir
    generator = CodeGenerator(base_dir)
    code = generator.generate(config_path, verbose=verbose)
    
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(code)
    print(f"✅ Generated Skelantic Types in {output_path}")
    
    try:
        import importlib.metadata
        version = importlib.metadata.version('skelantic')
        version_file = os.path.join(config_dir, "version")
        with open(version_file, "w", encoding="utf-8") as vf:
            vf.write(version)
    except Exception as e:
        if verbose:
            print(f"💡 INFO: Could not write Skelantic version: {e}")
