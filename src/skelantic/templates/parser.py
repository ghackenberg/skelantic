import re
from dataclasses import dataclass, field
from typing import List, Optional, Pattern

@dataclass
class Variable:
    name: str
    var_type: str

@dataclass
class TemplateNode:
    type: str  # 'line', 'block', 'repeat', 'choice', 'case'
    name: Optional[str] = None
    children: List['TemplateNode'] = field(default_factory=lambda: []) # type: ignore

@dataclass
class LineNode(TemplateNode):
    type: str = 'line'
    template_line: str = ""
    is_multiline: bool = False
    multiline_var: Optional[str] = None
    multiline_type: Optional[str] = None
    variables: List[Variable] = field(default_factory=lambda: []) # type: ignore
    regex: Optional[Pattern[str]] = None

def get_regex_for_type(type_str: str) -> str:
    if type_str == "str": return r".+?"
    elif type_str == "any": return r".*?"
    elif type_str == "slug": return r"[a-zA-Z0-9-_]+"
    elif type_str == "camelCase": return r"[a-z][a-zA-Z0-9]*"
    elif type_str == "Pascal_Snake": return r"[A-Z][a-zA-Z0-9]*(?:_[A-Z][a-zA-Z0-9]*)*"
    elif type_str == "snake_case": return r"[a-z0-9]+(?:_+[a-z0-9]+)*"
    elif type_str == "kebab-case": return r"[a-z0-9]+(?:-[a-z0-9]+)*"
    elif type_str == "UPPER_SNAKE_CASE": return r"[A-Z0-9]+(?:_[A-Z0-9]+)*"
    elif type_str == "int": return r"\d+"
    elif type_str == "decimal": return r"\d+(?:\.\d+)?"
    elif type_str == "bool": return r"true|false|True|False"
    elif type_str == "route": return r"\/?[a-zA-Z0-9\-\/\{\}_]*(?:\?[a-zA-Z0-9\-\_=&\{\},]+)?"       
    elif type_str.startswith("regex("):
        return type_str[6:-1]
    elif type_str.startswith("enum["):
        options = type_str[5:-1].split(",")
        return "|".join([re.escape(opt.strip()) for opt in options])
    return r".+?"

class TemplateParser:
    """Parst einen Skeletal-Markdown-String in einen Abstract Syntax Tree (AST)."""
    
    def __init__(self, template_str: str) -> None:
        self.lines: List[str] = [l for l in template_str.splitlines() if l.strip()]
        self.idx: int = 0

    def parse(self) -> List[TemplateNode]:
        self.idx = 0
        return self._parse_nodes(len(self.lines))

    def _parse_nodes(self, end_idx: int) -> List[TemplateNode]:
        nodes: List[TemplateNode] = []
        while self.idx < end_idx:
            line = self.lines[self.idx].strip()
            
            if line.startswith("[[block:"):
                m = re.match(r"\[\[block:([a-zA-Z0-9_]+)\]\]", line)
                if m:
                    b_name = m.group(1)
                    self.idx += 1
                    block_end = self._find_closing("block", b_name)
                    children = self._parse_nodes(block_end)
                    nodes.append(TemplateNode(type='block', name=b_name, children=children))
                    self.idx += 1
                    continue

            if line.startswith("[[repeat:"):
                m = re.match(r"\[\[repeat:([a-zA-Z0-9_]+)\]\]", line)
                if m:
                    r_name = m.group(1)
                    self.idx += 1
                    r_end = self._find_closing("repeat", r_name)
                    children = self._parse_nodes(r_end)
                    nodes.append(TemplateNode(type='repeat', name=r_name, children=children))
                    self.idx += 1
                    continue
                    
            if line.startswith("[[choice:"):
                m = re.match(r"\[\[choice:([a-zA-Z0-9_]+)\]\]", line)
                if m:
                    c_name = m.group(1)
                    self.idx += 1
                    c_end = self._find_closing("choice", c_name)
                    choice_node = TemplateNode(type='choice', name=c_name)
                    
                    while self.idx < c_end:
                        c_line = self.lines[self.idx].strip()
                        if c_line.startswith("[[case:"):
                            case_m = re.match(r"\[\[case:([a-zA-Z0-9_]+)\]\]", c_line)
                            if case_m:
                                case_val = case_m.group(1)
                                self.idx += 1
                                case_end = self._find_closing("case", case_val)
                                case_children = self._parse_nodes(case_end)
                                choice_node.children.append(TemplateNode(type='case', name=case_val, children=case_children))
                                self.idx += 1
                                continue
                        self.idx += 1
                        
                    nodes.append(choice_node)
                    self.idx = c_end + 1
                    continue
                    
            if line.startswith("[["):
                # Ignoriere schließende Tags oder ungültige
                self.idx += 1
                continue
                
            # Parse Line
            line_node = LineNode(template_line=self.lines[self.idx])
            t_line = self.lines[self.idx]
            
            # Check multiline
            text_match = re.search(r"\{\{([a-zA-Z0-9_]+):(text|json)\}\}$", t_line)
            if text_match:
                line_node.is_multiline = True
                line_node.multiline_var = text_match.group(1)
                line_node.multiline_type = text_match.group(2)
                t_line = t_line[:text_match.start()]
                
            parts = re.split(r"(\{\{[a-zA-Z0-9_]+:[^}]+\}\})", t_line)
            regex_parts: List[str] = []
            
            for part in parts:
                v_match = re.match(r"\{\{([a-zA-Z0-9_]+):([^}]+)\}\}", part)
                if v_match:
                    var_name, var_type = v_match.groups()
                    line_node.variables.append(Variable(name=var_name, var_type=var_type))
                    type_regex = get_regex_for_type(var_type)
                    regex_parts.append(f"(?P<{var_name}>{type_regex})")
                else:
                    regex_parts.append(re.escape(part))
                    
            pattern = "^" + "".join(regex_parts)
            if not line_node.is_multiline:
                pattern += "$"
                
            line_node.regex = re.compile(pattern)
                
            nodes.append(line_node)
            self.idx += 1
            
        return nodes

    def _find_closing(self, tag_type: str, name: str) -> int:
        depth = 1
        search_idx = self.idx
        while search_idx < len(self.lines):
            l = self.lines[search_idx]
            if f"[[{tag_type}:" in l: depth += 1
            if f"[[/{tag_type}]]" in l:
                depth -= 1
                if depth == 0: return search_idx
            search_idx += 1
        raise Exception(f"Missing closing tag for [[{tag_type}:{name}]]")