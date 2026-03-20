import os
import glob
import re
from collections import defaultdict
from typing import Dict, List, Tuple, Optional
from skelantic.templates.parser import TemplateParser, TemplateNode, LineNode

def to_pascal(name: str) -> str:
    return "".join(x.title() for x in re.split(r'[-_]', name) if x)

def map_type(t_str: str) -> str:
    if t_str == 'int': return 'int'
    if t_str == 'decimal': return 'float'
    if t_str == 'bool': return 'bool'
    if t_str == 'any': return 'Any'
    if t_str.startswith('enum['): return 'str'
    return 'str'

def parse_nodes(nodes: List[TemplateNode], class_name: str, classes_out: Dict[str, Dict[str, str]]) -> Dict[str, str]:
    fields: Dict[str, str] = {}
    
    for node in nodes:
        if isinstance(node, LineNode):
            if node.multiline_var:
                fields[node.multiline_var] = 'str'
            for var in node.variables:
                fields[var.name] = map_type(var.var_type)
                
        elif node.type == 'block' and node.name:
            b_class = f"{class_name}{to_pascal(node.name)}Block"
            fields[node.name] = f"'{b_class}'"
            parse_nodes(node.children, b_class, classes_out)
            
        elif node.type == 'repeat' and node.name:
            r_class = f"{class_name}{to_pascal(node.name)}Item"
            fields[node.name] = f"List['{r_class}']"
            parse_nodes(node.children, r_class, classes_out)
            
        elif node.type == 'choice' and node.name:
            fields[f"{node.name}_type"] = 'str'
            for case_node in node.children:
                if case_node.type == 'case':
                    # Choice cases flatten into the parent class
                    c_fields = parse_nodes(case_node.children, class_name, classes_out)
                    fields.update(c_fields)
                    
    if class_name not in classes_out:
        classes_out[class_name] = fields
    else:
        classes_out[class_name].update(fields)
        
    return fields

def get_module_info(template_path: str) -> Tuple[Optional[str], Optional[str]]:
    parts = template_path.replace('\\', '/').split('/')
    idx = -1
    for marker in ['.templates', 'templates']:
        if marker in parts:
            idx = parts.index(marker)
            if marker == 'templates' and idx > 0 and parts[idx-1] == '.skelantic':
                idx = idx - 1
            break
            
    if idx == -1:
        return None, None
        
    domain_parts = parts[:idx]
    clean_parts: List[str] = []
    for part in domain_parts:
        clean = re.sub(r'^[\d\-]+', '', part)
        clean = clean.replace('-', '_')
        if not clean:
            clean = part.replace('-', '_')
        clean_parts.append(clean)
        
    module_dir = "/".join(clean_parts)
    filename = parts[-1].replace('.md', '')
    return module_dir, filename

def generate_models(output_dir: str) -> None:
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    search_pattern_1 = os.path.join(base_dir, '**', '.templates', '*.md')
    search_pattern_2 = os.path.join(base_dir, '**', '.skelantic', 'templates', '*.md')
    templates = sorted(glob.glob(search_pattern_1, recursive=True) + glob.glob(search_pattern_2, recursive=True))
    
    modules: Dict[str, Dict[str, Dict[str, Dict[str, str]]]] = defaultdict(dict)
    
    for t_path in templates:
        rel_path = os.path.relpath(t_path, base_dir)
        mod_dir, t_name = get_module_info(rel_path)
        if not mod_dir or not t_name: continue
        
        with open(t_path, 'r', encoding='utf-8') as f:
            template_str = f.read()
            
        parser = TemplateParser(template_str)
        nodes = parser.parse()
        
        class_name = to_pascal(t_name) + "Template"
        classes: Dict[str, Dict[str, str]] = {}
        parse_nodes(nodes, class_name, classes)
        
        # Add rel_path explicitly
        classes[class_name]['rel_path'] = 'str'
        
        modules[mod_dir][class_name] = classes

    models_out_dir = os.path.abspath(output_dir)
    
    for mod_dir in sorted(modules.keys()):
        t_classes = modules[mod_dir]
        out_file = os.path.join(models_out_dir, mod_dir + '.py')
        os.makedirs(os.path.dirname(out_file), exist_ok=True)
        
        # Create init files
        parts = mod_dir.split('/')
        for i in range(len(parts) - 1):
            dir_path = os.path.join(models_out_dir, *parts[:i+1])
            os.makedirs(dir_path, exist_ok=True)
            init_path = os.path.join(dir_path, '__init__.py')
            if not os.path.exists(init_path):
                open(init_path, 'w').close()
                
        with open(out_file, 'w', encoding='utf-8') as f:
            f.write("from pydantic import BaseModel, Field  # pyright: ignore[reportUnusedImport]\n")
            f.write("from typing import List, Any, Optional\n\n")
            
            for root_class in sorted(t_classes.keys()):
                sub_classes = t_classes[root_class]
                for cls_name in sorted(sub_classes.keys()):
                    fields = sub_classes[cls_name]
                    f.write(f"class {cls_name}(BaseModel):\n")
                    if not fields:
                        f.write("    pass\n")
                    for k in sorted(fields.keys()):
                        v = fields[k]
                        if k in ['pass', 'def', 'class', 'import', 'from', 'return', 'if', 'else', 'elif', 'try', 'except', 'in', 'is']:
                            alias = k
                            k = f"{k}_"
                            f.write(f"    {k}: Optional[{v}] = Field(default=None, alias='{alias}')\n")
                        else:
                            f.write(f"    {k}: Optional[{v}] = None\n")
                    f.write("\n")
                    
    print(f"✅ Generated {len(templates)} models in {output_dir}/")
