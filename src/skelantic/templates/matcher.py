import re
import json
from typing import List, Dict, Tuple, Any, Optional, Pattern
from skelantic.templates.parser import TemplateParser, TemplateNode, LineNode

class SkeletalMatcher:
    def __init__(self, template_str: str) -> None:
        self.parser = TemplateParser(template_str)
        self.nodes = self.parser.parse()
        self.errors: List[str] = []
        self.extracted_data: Dict[str, Any] = {}
        self.debug_depth: int = 0
        self._last_logged_line: Optional[int] = None
        self._max_line_digits: int = 2
        self.doc_line_map: Dict[int, int] = {}
        self.trace_log: List[str] = []

    def _log(self, d_idx: Optional[int], msg: str, color: Optional[str] = None) -> None:
        indent = "│  " * self.debug_depth
        padding = " " * (self._max_line_digits + 4)
        if isinstance(d_idx, int):
            if d_idx != self._last_logged_line:
                line_prefix = f"[L{d_idx+1:0{self._max_line_digits}d}] "
                self._last_logged_line = d_idx
            else:
                line_prefix = padding
        else:
            line_prefix = padding
            
        msg_lines = msg.split('\n')
        self.trace_log.append(f"{line_prefix}{indent}{msg_lines[0]}")
        for extra_line in msg_lines[1:]:
             self.trace_log.append(f"{padding}{indent}{extra_line}")

    def _get_lookaheads(self, nodes: List[TemplateNode]) -> List[Pattern[str]]:
        if not nodes:
            return []
        first = nodes[0]
        if isinstance(first, LineNode) and first.regex:
            return [first.regex]
        elif first.type == 'block':
            return self._get_lookaheads(first.children)
        elif first.type == 'repeat':
            l = self._get_lookaheads(first.children)
            l.extend(self._get_lookaheads(nodes[1:]))
            return l
        elif first.type == 'choice':
            l: List[Pattern[str]] = []
            for case in first.children:
                l.extend(self._get_lookaheads(case.children))
            l.extend(self._get_lookaheads(nodes[1:]))
            return l
        elif first.type == 'case':
            return self._get_lookaheads(first.children)
        return []

    def match(self, doc_str: str) -> Tuple[bool, List[str], Dict[str, Any]]:
        raw_lines = doc_str.splitlines()
        doc_lines: List[str] = []
        self.doc_line_map = {}
        for i, l in enumerate(raw_lines):
            if l.strip():
                self.doc_line_map[len(doc_lines)] = i
                doc_lines.append(l)

        self.errors = []
        self.extracted_data = {}
        self.debug_depth = 0
        self._last_logged_line = None
        self._max_line_digits = len(str(len(raw_lines)))
        
        self._log(None, f"🏁 Starting match. Nodes: {len(self.nodes)}, Document lines: {len(doc_lines)}", color="CYAN")
        
        try:
            doc_idx, data = self._match_nodes(self.nodes, doc_lines, 0, [])
            self.extracted_data = data
            
            if doc_idx < len(doc_lines):
                raw_idx = self.doc_line_map.get(doc_idx, doc_idx)
                clean_err = f"Überzählige Zeilen am Ende des Dokuments ab Zeile {raw_idx+1}."
                self._log(raw_idx, f"├─ ❌ {clean_err}", color="RED")
                self.errors.append(clean_err)
            
            if not self.errors:
                self._log(None, "└─ ✅ Match finished. Success: True", color="GREEN")
            else:
                self._log(None, "└─ ❌ Match finished. Success: False", color="RED")
        except Exception as e:
            self._log(None, f"└─ ❌ Match failed with Exception: {str(e)}", color="RED")
            self.errors.append(f"Struktur-Fehler: {str(e)}")
            
        return not self.errors, self.errors, self.extracted_data

    def _match_nodes(self, nodes: List[TemplateNode], d_lines: List[str], d_idx: int, parent_lookaheads: List[Pattern[str]]) -> Tuple[int, Dict[str, Any]]:
        data: Dict[str, Any] = {}
        
        for n_idx, node in enumerate(nodes):
            raw_d_idx = self.doc_line_map.get(d_idx, d_idx)
            current_lookaheads = self._get_lookaheads(nodes[n_idx + 1:]) + parent_lookaheads

            if node.type == 'block':
                block_name = node.name or 'unknown'
                self._log(raw_d_idx, f"├─ 📦 [BLOCK] '{block_name}'", color="BLUE")
                self.debug_depth += 1
                
                new_d_idx, block_data = self._match_nodes(node.children, d_lines, d_idx, current_lookaheads)
                data[block_name] = block_data
                d_idx = new_d_idx
                
                self._log(self.doc_line_map.get(d_idx, d_idx), f"└─ 🏁 [END BLOCK] '{block_name}'", color="BLUE")
                self.debug_depth -= 1
                continue

            if node.type == 'choice':
                choice_name = node.name or 'unknown'
                self._log(raw_d_idx, f"├─ 🔀 [CHOICE] '{choice_name}'", color="MAGENTA")
                self.debug_depth += 1
                
                case_matched = False
                case_errors: List[str] = []
                
                for case_node in node.children:
                    case_val = case_node.name or 'unknown'
                    self._log(raw_d_idx, f"├─ 🔍 Trying [CASE] '{case_val}'", color="CYAN")
                    self.debug_depth += 1
                    try:
                        new_d_idx, case_data = self._match_nodes(case_node.children, d_lines, d_idx, current_lookaheads)
                        self._log(self.doc_line_map.get(new_d_idx, new_d_idx), f"└─ ✅ [CASE MATCHED] '{case_val}'", color="GREEN")
                        data[f"{choice_name}_type"] = case_val
                        data.update(case_data)
                        d_idx = new_d_idx
                        case_matched = True
                        self.debug_depth -= 1
                        break
                    except Exception as e:
                        self._log(raw_d_idx, f"└─ ❌ [CASE FAILED] '{case_val}': {str(e)}", color="YELLOW")
                        case_errors.append(f"Case {case_val} fehlgeschlagen: {str(e)}")
                        self.debug_depth -= 1
                
                if not case_matched:
                    err = f"Zeile {self.doc_line_map.get(d_idx, d_idx)+1}: Kein Choice-Case hat gepasst. Fehler:\n" + "\n".join(case_errors)
                    raise Exception(err)

                self._log(self.doc_line_map.get(d_idx, d_idx), f"└─ 🏁 [END CHOICE] '{choice_name}'", color="MAGENTA")
                self.debug_depth -= 1
                continue

            if node.type == 'repeat':
                repeat_name = node.name or 'unknown'
                self._log(raw_d_idx, f"├─ 🔄 [REPEAT] '{repeat_name}'", color="MAGENTA")
                self.debug_depth += 1
                
                repeat_items: List[Dict[str, Any]] = []
                while d_idx < len(d_lines):
                    should_exit = False
                    for la_regex in current_lookaheads:
                        if la_regex.match(d_lines[d_idx]):
                            self._log(self.doc_line_map.get(d_idx, d_idx), f"├─ 🛑 [EXIT] Lookahead matched: '{d_lines[d_idx]}'", color="CYAN")
                            should_exit = True
                            break
                    if should_exit:
                        break
                        
                    try:
                        self._log(self.doc_line_map.get(d_idx, d_idx), f"├─ ➡️ [ITEM {len(repeat_items) + 1}]", color="CYAN")
                        self.debug_depth += 1
                        # Lookaheads for an item in a repeat block includes the repeat block's own start (for the next item)
                        # plus the lookaheads for after the repeat block. But wait, if an item matches the next item's start, it shouldn't exit the item?
                        # Actually, we just pass the current_lookaheads! 
                        # Wait! A repeat block item might need to look ahead for the next ITEM of the same repeat block!
                        # The start of the repeat block's item IS the lookahead for the item itself!
                        # self._get_lookaheads(node.children) gives the start of the item.
                        item_lookaheads = self._get_lookaheads(node.children) + current_lookaheads
                        new_d_idx, item_data = self._match_nodes(node.children, d_lines, d_idx, item_lookaheads)
                        if new_d_idx == d_idx: 
                            self.debug_depth -= 1
                            break
                        repeat_items.append(item_data)
                        d_idx = new_d_idx
                        self._log(self.doc_line_map.get(d_idx, d_idx), f"└─ 🏁 [END ITEM]", color="CYAN")
                        self.debug_depth -= 1
                    except Exception as e:
                        self._log(self.doc_line_map.get(d_idx, d_idx), f"└─ ⚠️ [BREAK] End of items: {e}", color="YELLOW")
                        self.debug_depth -= 1
                        break
                
                data[repeat_name] = repeat_items
                self._log(self.doc_line_map.get(d_idx, d_idx), f"└─ 🏁 [END REPEAT] '{repeat_name}' (Items: {len(repeat_items)})", color="MAGENTA")
                self.debug_depth -= 1
                continue

            if isinstance(node, LineNode):
                if d_idx >= len(d_lines):
                    err = f"├─ ❌ Erwartete Template-Zeile '{node.template_line}', aber Dokument ist zu Ende."
                    self._log(raw_d_idx, err, color="RED")
                    raise Exception(err)
                
                if not node.regex:
                    raise Exception("LineNode has no compiled regex.")
                    
                match = node.regex.match(d_lines[d_idx])
                
                if not match:
                    colored_t_line = re.sub(r"(\{\{[^}]+\}\})", r"\033[93m\1\033[91m", node.template_line)
                    found_text = d_lines[d_idx]
                    found_display = f"'{found_text}'"

                    err_lines: List[str] = [
                        f"├─ ❌ Mismatch:",
                        f"│  ├─ 🎯 Expected: '{colored_t_line}'",
                        f"│  ├─ 🔍 Regex:    {node.regex.pattern}",
                        f"│  ├─ 📝 Found:    {found_display}"
                    ]
                    
                    context_lines: List[str] = []
                    if d_idx > 0:
                        prev_line = d_lines[d_idx - 1]
                        context_lines.append(f"[L{self.doc_line_map.get(d_idx-1, d_idx-1)+1:0{self._max_line_digits}d}] {prev_line}")
                    
                    context_lines.append(f"[L{raw_d_idx+1:0{self._max_line_digits}d}] {found_text} <--- ERROR")
                    
                    if d_idx + 1 < len(d_lines):
                        next_line = d_lines[d_idx + 1]
                        context_lines.append(f"[L{self.doc_line_map.get(d_idx+1, d_idx+1)+1:0{self._max_line_digits}d}] {next_line}")
                    
                    if context_lines:
                         err_lines.append("│  └─ 📖 Context:")
                         for cl in context_lines:
                             err_lines.append(f"│        {cl}")

                    err_str = "\n".join(err_lines)
                    clean_err = f"Zeile {raw_d_idx+1} passt nicht zum Template. Erwartet: '{node.template_line}', Gefunden: '{d_lines[d_idx]}' (Regex-Pattern: {node.regex.pattern})"
                    self._log(raw_d_idx, err_str, color="RED")
                    raise Exception(clean_err)
                
                self._log(raw_d_idx, f"├─ ✅ Match: '{node.template_line}'", color="GREEN")
                data.update(match.groupdict())
                
                if node.is_multiline:
                    consumed_lines: List[str] = []

                    remainder = d_lines[d_idx][match.end():]
                    if remainder or node.regex.pattern == "^":
                        consumed_lines.append(remainder if node.regex.pattern != "^" else d_lines[d_idx])
                    
                    self._log(raw_d_idx, f"│  ├─ 🔍 Checking lookaheads for multiline '{node.multiline_var}': {[r.pattern for r in current_lookaheads]}", color="CYAN")
                    
                    d_idx += 1
                    while d_idx < len(d_lines):
                        should_break = False
                        for la_regex in current_lookaheads:
                            if la_regex.match(d_lines[d_idx]):
                                self._log(self.doc_line_map.get(d_idx, d_idx), f"│  ├─ 🛑 [EXIT MULTILINE] Lookahead matched: '{d_lines[d_idx]}'", color="CYAN")
                                should_break = True
                                break
                        if should_break:
                            break
                        consumed_lines.append(d_lines[d_idx])
                        d_idx += 1
                    
                    captured_text = "\n".join(consumed_lines)
                    
                    if node.multiline_type == "json":
                        try:
                            json.loads(captured_text)
                            self._log(self.doc_line_map.get(d_idx-1, d_idx-1), f"│  └─ 📄 [JSON] Validated {len(consumed_lines)} lines into '{node.multiline_var}'", color="MAGENTA")
                        except json.JSONDecodeError as e:
                            err_str = f"Zeile {self.doc_line_map.get(d_idx-1, d_idx-1)+1}: Ungültiges JSON im Block '{node.multiline_var}': {str(e)}"
                            self._log(self.doc_line_map.get(d_idx-1, d_idx-1), f"├─ ❌ {err_str}", color="RED")
                            raise Exception(err_str)
                    else:
                        self._log(self.doc_line_map.get(d_idx-1, d_idx-1), f"│  └─ 📄 [MULTILINE] Captured {len(consumed_lines)} lines into '{node.multiline_var}'", color="MAGENTA")
                    
                    if node.multiline_var:
                        data[node.multiline_var] = captured_text
                    continue
                else:
                    d_idx += 1
            
        return d_idx, data
