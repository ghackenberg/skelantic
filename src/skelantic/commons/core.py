import os
import inspect
from collections import defaultdict
from typing import Any, Dict, List, Optional, TypedDict, Pattern, cast
from .documents import MarkdownDocument, Document
from .context import LinterContext
from skelantic.templates.matcher import SkeletalMatcher
from .config import ConfigLoader, get_regex, RESERVED_NAMES
from .decorators import Registry

class MatcherDict(TypedDict):
    regex: Pattern[str]
    pattern: str
    config: Dict[str, Any]
    matched: bool

def tree() -> defaultdict[Any, Any]:
    return defaultdict(tree)

def get_specificity_score(pattern: str) -> int:
    score = len(pattern)
    if '**' in pattern:
        score -= 1000
    elif '*' in pattern:
        score -= 100
    if '{' in pattern and '}' in pattern:
        score -= 50
    return score

class LinterEngine:
    def __init__(self, registry: Registry, verbose: bool = False, types_module: Any = None, models_module: str = "") -> None:
        self.registry: Registry = registry
        self.verbose: bool = verbose
        self.models_module: str = models_module
        self.types_module: Any = types_module
        self.ctx: LinterContext = LinterContext()
        self.results_tree: defaultdict[Any, Any] = tree()
        self.total_errors: int = 0
        self.total_warnings: int = 0
        self.document_cache: Dict[str, Document] = {}
        self.config_loader: ConfigLoader = ConfigLoader(self._add_results)
        self._state_singletons: Dict[type, Any] = {}
        
        self.node_map: Dict[str, Any] = {}
        if types_module and hasattr(types_module, "__SKELANTIC_NODE_MAP__"):
            self.node_map = getattr(types_module, "__SKELANTIC_NODE_MAP__")
        
        new_config_path = os.path.join(".", ".skelantic", "config.yaml")
        if os.path.exists(new_config_path):
            self.config = self.config_loader.load_config(new_config_path)
            self._log(f"Loaded ROOT config from {new_config_path}")
        else:
            self.config = {}

    def _log(self, msg: str, level: str = "DEBUG") -> None:
        if self.verbose: print(f"{'🔍 DEBUG: ' if level == 'DEBUG' else '💡 INFO:  '}{msg}")

    def run(self, base_dir: str = ".") -> None:
        all_files: List[Dict[str, Any]] = []
        self._walk_and_validate(base_dir, self.config, all_files, rel_path=".")
        self._run_templates(all_files)
        
        # Bestimme alle registrierten Phasen dynamisch
        all_phases = sorted(list(set(b.phase for b in self.registry.bindings if b.phase is not None)))
        
        for phase in all_phases:
            self._run_phase(phase, all_files)

    def _run_templates(self, files_data: List[Dict[str, Any]]) -> None:
        for f_data in files_data:
            t_p = f_data.get('template')
            if t_p and os.path.exists(t_p):
                try:
                    with open(t_p, "r", encoding="utf-8") as f: t_s = f.read()
                    doc = self._get_or_create_doc(f_data['abs_path'], f_data['rel_path'])
                    matcher = SkeletalMatcher(t_s)
                    succ, errs, data = matcher.match(doc.raw_content)
                    if not succ:
                        safe_path = f_data['rel_path'].replace('/', '_').replace('\\', '_')
                        trace_dir = os.path.join(os.getcwd(), ".skelantic", "traces")
                        os.makedirs(trace_dir, exist_ok=True)
                        trace_file = os.path.join(trace_dir, f"template_{safe_path}.log")
                        with open(trace_file, "w", encoding="utf-8") as f:
                            f.write("\n".join(matcher.trace_log))
                        
                        rel_trace_p = os.path.relpath(trace_file, os.getcwd())
                        self._add_results("ERROR", f_data['rel_path'], [f"Struktur-Fehler: Die Datei entspricht nicht dem Skeletal Template."])
                        self._add_results("ERROR", f_data['rel_path'], errs)
                        self._add_results("INFO", f_data['rel_path'], [f"💡 Analyse-Hilfe: Öffne die Log-Datei '{rel_trace_p}', um genau zu sehen, in welcher Zeile der Matcher gescheitert ist und was er stattdessen erwartet hat."])
                    else:
                        self.ctx.extracted_data[f_data['rel_path']] = data
                except Exception as e: self._add_results("ERROR", f_data['rel_path'], [f"Template Error: {e}"])

    def _get_or_create_doc(self, abs_filepath: str, rel_path: str, is_directory: bool = False) -> Document:
        if abs_filepath in self.document_cache: return self.document_cache[abs_filepath]
        doc = Document(abs_filepath) if is_directory else (MarkdownDocument(abs_filepath) if rel_path.endswith('.md') else Document(abs_filepath))
        self.document_cache[abs_filepath] = doc
        return doc

    def _run_phase(self, phase: int, files_data: List[Dict[str, Any]]) -> None:
        from .nodes import FileNode, DirectoryNode, MarkdownNode, RootNode
        for f_data in files_data:
            rp = f_data['rel_path']
            # Find matching class in node_map
            NodeClass = None
            if rp in self.node_map:
                NodeClass = self.node_map[rp]
            else:
                best_score = -9999
                for pat, cls in self.node_map.items():
                    if get_regex(pat).match(rp):
                        score = get_specificity_score(pat)
                        if score > best_score:
                            best_score = score
                            NodeClass = cls
            
            if NodeClass is None:
                if f_data.get('is_directory', False):
                    NodeClass = RootNode if rp == "." else DirectoryNode
                else:
                    NodeClass = MarkdownNode if rp.endswith('.md') else FileNode

            node = NodeClass(f_data['abs_path'], rp, self.ctx)
            if not f_data.get('is_directory', False):
                if not hasattr(node, 'document'):
                    setattr(node, 'document', self._get_or_create_doc(f_data['abs_path'], rp)) # type: ignore[reportAttributeAccessIssue]
                    
            # Inject path params if class expects it
            if hasattr(NodeClass, 'PathParams') and hasattr(NodeClass, '__annotations__') and 'path_params' in NodeClass.__annotations__:
                try:
                    ParamsClass = getattr(NodeClass, 'PathParams') # type: ignore[reportAttributeAccessIssue]
                    setattr(node, 'path_params', ParamsClass(**f_data.get('kwargs', {}))) # type: ignore[reportAttributeAccessIssue]
                except Exception as e:
                    self._log(f"Failed to instantiate PathParams for {rp}: {e}")

            raw_data = self.ctx.extracted_data.get(rp)
            if raw_data is not None and hasattr(NodeClass, '__annotations__') and 'data' in NodeClass.__annotations__:
                model_cls_name = NodeClass.__annotations__['data']
                if model_cls_name != 'Any' and isinstance(raw_data, dict):
                    try:
                        if isinstance(model_cls_name, str) and self.types_module:
                            model_cls = eval(model_cls_name, dict(cast(Dict[str, Any], vars(self.types_module))))
                        else:
                            model_cls = model_cls_name
                            
                        raw_data['rel_path'] = rp
                        model_constructor = cast(Any, model_cls)
                        node.data = model_constructor(**raw_data)
                    except Exception as e:
                        self._log(f"Failed to instantiate Pydantic model for {rp}: {e}", level="WARNING")
                        node.data = raw_data
                else:
                    node.data = raw_data
            else:
                node.data = raw_data
            self.ctx.register_node(node)
            
            # Execute rules
            for binding in self.registry.bindings:
                if binding.phase != phase:
                    continue
                
                # Check if it matches this node
                is_match = False
                if binding.match == "root":
                    if rp == ".": is_match = True
                elif binding.regex:
                    if binding.regex.match(rp): is_match = True
                else:
                    # No explicit match -> fallback to type-based only
                    is_match = True

                if not is_match:
                    continue

                # Type Hint Match
                sig = inspect.signature(binding.func)
                params = list(sig.parameters.values())
                node_param = next((p for p in params if p.name == 'node'), None)
                
                if node_param and node_param.annotation != inspect.Parameter.empty:
                    anno = node_param.annotation
                    # Handle forward references
                    if isinstance(anno, str) and self.types_module:
                        try:
                            type_env = cast(Dict[str, Any], vars(self.types_module))
                            anno = eval(anno, type_env)
                        except Exception: pass
                    
                    try:
                        if not isinstance(anno, str):
                            # Skip check if annotation is Any
                            if anno is not Any:
                                if not isinstance(node, anno):
                                    continue
                        else:
                            # If eval failed and it's still a string, we can't reliably match
                            continue
                    except TypeError:
                        continue
                        
                self._execute_rule(binding.func, binding.name, node, f_data)

    def _execute_rule(self, func: Any, rule_name: str, node: Optional[Any], f_data: Optional[Dict[str, Any]]) -> List[str]:
        from pydantic import BaseModel
        sig = inspect.signature(func)
        kwargs: Dict[str, Any] = {}

        current_traces: List[str] = []
        def tracer(msg: str) -> None:
            current_traces.append(msg)

        for param_name, param in sig.parameters.items():
            anno = param.annotation
            # Handle forward references
            if isinstance(anno, str) and self.types_module:
                try: 
                    type_env = cast(Dict[str, Any], vars(self.types_module))
                    anno = eval(anno, type_env)
                except Exception: pass

            if not isinstance(anno, str) and hasattr(anno, '__mro__') and issubclass(anno, BaseModel):
                state_cls = anno
                if state_cls not in self._state_singletons:
                    self._state_singletons[state_cls] = state_cls()
                kwargs[param_name] = self._state_singletons[state_cls]
            elif param_name == 'node': 
                kwargs['node'] = node
            elif param_name == 'tracer': kwargs['tracer'] = tracer
            else:
                self._log(f"Warning: Argument '{param_name}' requested by processor '{rule_name}' cannot be injected. Only 'node', 'tracer', and Pydantic state models are supported.", level="WARNING")
        
        origin = None
        try:
            origin = {
                'method': func.__name__,
                'module': func.__module__,
                'file': os.path.relpath(inspect.getfile(func), os.getcwd()).replace('\\', '/'),
                'doc': (getattr(func, "__doc__", "") or "").strip().split('\n')[0]
            }
        except Exception: pass

        findings: List[str] = []
        crashed = False
        try:
            res_val = func(**kwargs)
            findings = list(res_val) if res_val is not None else []
        except Exception as e:
            # Determine if it's a global check for prefix
            is_global = (f_data.get('rel_path') == "." if f_data else False)
            prefix = "Global " if is_global else ""
            findings = [f"{prefix}Crash '{rule_name}': {e}"]
            crashed = True
        finally:
            target_path = f_data.get('rel_path', 'root') if f_data else "root"
            
            # 1. ALWAYS write trace logs if they exist
            if current_traces:
                import re as regex_mod
                safe_path = regex_mod.sub(r'[^a-zA-Z0-9_-]', '_', target_path)
                trace_dir = os.path.join(os.getcwd(), ".skelantic", "traces")
                os.makedirs(trace_dir, exist_ok=True)
                trace_file = os.path.join(trace_dir, f"{rule_name}_{safe_path}.log")
                with open(trace_file, "w", encoding="utf-8") as f:
                    f.write("\n".join(current_traces))
                
                rel_trace_p = os.path.relpath(trace_file, os.getcwd())
                hint = f"💡 Analyse-Hilfe: Öffne die Log-Datei '{rel_trace_p}', um den detaillierten Ausführungsplan dieses Prozessors zu sehen."
                
                # Show hint as INFO (doesn't affect success status)
                # We show it if errors occurred OR if we are in verbose mode
                if findings or self.verbose or crashed:
                    self._add_results("INFO", target_path, [hint], origin=origin)

            # 2. Add real findings (errors/warnings)
            if findings:
                is_global_warning = (not crashed and target_path == ".")
                severity = "WARNING" if is_global_warning else "ERROR"
                self._add_results(severity, target_path, findings, origin=origin)
                
        return findings

    def _add_results(self, severity: str, full_rel_path: str, results: List[str], origin: Optional[Dict[str, Any]] = None) -> None:
        if not results: return
        parts = full_rel_path.split('/') if full_rel_path not in ['.', ''] else ['root']
        current_node = self.results_tree
        for part in parts: current_node = current_node[part]
        if '_errors' not in current_node: 
            current_node['_errors'] = []
            current_node['_warnings'] = []
            current_node['_infos'] = []
            
        for msg in results:
            entry = {'msg': msg, 'origin': origin}
            if severity == "ERROR":
                if entry not in current_node['_errors']: current_node['_errors'].append(entry); self.total_errors += 1
            elif severity == "WARNING":
                if entry not in current_node['_warnings']: current_node['_warnings'].append(entry); self.total_warnings += 1
            else: # INFO
                if entry not in current_node['_infos']: current_node['_infos'].append(entry)

    def _print_node(self, name: str, node: Any, indent: int = 0) -> None:
        prefix = "   " * indent
        if name and name not in ["_errors", "_warnings", "_infos"]:
            print(f"{prefix}{'📄' if '.' in name else '📁'} {name}{'/' if '.' not in name else ''}")
            indent += 1
            prefix = "   " * indent
        
        # Processor-spezifische Meldungen sammeln
        processor_groups: Dict[str, Dict[str, List[str]]] = defaultdict(lambda: {'errors': [], 'warnings': [], 'infos': []})
        
        for e in cast(List[Dict[str, Any]], node.get('_errors', [])):
            origin = cast(Optional[Dict[str, Any]], e.get('origin'))
            okey = f"{origin['module']}:{origin['method']}" if origin else "system"
            processor_groups[okey]['errors'].append(e['msg'])
            
        for w in cast(List[Dict[str, Any]], node.get('_warnings', [])):
            origin = cast(Optional[Dict[str, Any]], w.get('origin'))
            okey = f"{origin['module']}:{origin['method']}" if origin else "system"
            processor_groups[okey]['warnings'].append(w['msg'])
            
        for i in cast(List[Dict[str, Any]], node.get('_infos', [])):
            origin = cast(Optional[Dict[str, Any]], i.get('origin'))
            okey = f"{origin['module']}:{origin['method']}" if origin else "system"
            processor_groups[okey]['infos'].append(i['msg'])
            
        for okey, group in sorted(processor_groups.items()):
            if okey != "system":
                print(f"{prefix}⚙️ {okey}")
                p_indent = prefix + "   "
                for msg in group['errors']: print(f"{p_indent}❌ {msg}")
                for msg in group['warnings']: print(f"{p_indent}⚠️ {msg}")
                for msg in group['infos']: print(f"{p_indent}{msg}")
            else:
                for msg in group['errors']: print(f"{prefix}❌ {msg}")
                for msg in group['warnings']: print(f"{prefix}⚠️ {msg}")
                for msg in group['infos']: print(f"{prefix}{msg}")

        for child_name, child_node in sorted(node.items()):
            if child_name not in ['_errors', '_warnings', '_infos']: self._print_node(child_name, child_node, indent)

    def print_report(self) -> bool:
        print("\n" + "="*70 + "\n🛡️  SKELANTIC ARCHITECT 🛡️\n" + "="*70 + "\n")
        if not self.results_tree: print("✨ PERFECT REPOSITORY: 0 Errors, 0 Warnings."); return False
        for top_level, node in sorted(self.results_tree.items()): self._print_node(top_level, node)
        print("\n" + "="*70)
        if self.total_errors > 0: print(f"🛑 FAILED: {self.total_errors} Errors, {self.total_warnings} Warnings."); return True
        print(f"✅ PASSED: 0 Errors, {self.total_warnings} Warnings." if self.total_warnings else "✨ PERFECT REPOSITORY!"); return False

    def _walk_and_validate(self, current_dir: str, current_config: Dict[str, Any], all_files_out: List[Dict[str, Any]], rel_path: str = ".", ignore_patterns: Optional[List[Pattern[str]]] = None, inherited_kwargs: Optional[Dict[str, Any]] = None) -> None:
        inherited_kwargs = inherited_kwargs or {}
        ignore_patterns = list(ignore_patterns) if ignore_patterns else []
        
        if rel_path == ".":
            # Add root directory node explicitly
            all_files_out.append({
                'abs_path': os.path.abspath(current_dir),
                'rel_path': ".",
                'filename': os.path.basename(os.path.abspath(current_dir)),
                'is_directory': True,
                'kwargs': {},
                'template': None,
                'base_dir': "."
            })

        try: entries = os.listdir(current_dir)
        except PermissionError: return
        config_dir = rel_path
        
        # New Config Loading
        lcp_new = os.path.join(current_dir, ".skelantic", "config.yaml")
        
        if os.path.exists(lcp_new):
            local_c = self.config_loader.load_config(lcp_new)
            local_c = self.config_loader.resolve_paths(local_c, current_dir)
            if rel_path != ".":
                current_config = current_config.copy()
                current_config['files'] = {**current_config.get('files', {}), **(local_c.get('files') or {})}
                current_config['directories'] = {**current_config.get('directories', {}), **(local_c.get('directories') or {})}
            
            for ig_pat in local_c.get('ignore', []):
                ignore_patterns.append(get_regex(ig_pat))

        filtered_entries: List[str] = []
        for e in entries:
            if e in RESERVED_NAMES or e.endswith('.pyc'):
                continue
            e_rp = e if rel_path == "." else f"{rel_path}/{e}"
            if any(p.match(e_rp) or p.match(e) for p in ignore_patterns):
                continue
            filtered_entries.append(e)
            
        d_m: List[MatcherDict] = [{'regex': get_regex(p), 'pattern': p, 'config': cast(Dict[str, Any], v) or {}, 'matched': False} for p, v in current_config.get('directories', {}).items()]
        f_m: List[MatcherDict] = [{'regex': get_regex(p), 'pattern': p, 'config': cast(Dict[str, Any], v) or {}, 'matched': False} for p, v in current_config.get('files', {}).items()]
        
        for entry in sorted(filtered_entries):
            full_p, entry_rp = os.path.join(current_dir, entry), (entry if rel_path == "." else f"{rel_path}/{entry}")
            is_d = os.path.isdir(full_p)
            matched_n: Optional[Dict[str, Any]] = None
            extracted_k: Dict[str, str] = {}
            m_list = d_m if is_d else f_m
            best_score = -9999
            
            for m in m_list:
                match = m['regex'].match(entry)
                if match:
                    m['matched'] = True
                    score = get_specificity_score(m['pattern'])
                    if score > best_score:
                        best_score = score
                        matched_n = m['config']
                        extracted_k = match.groupdict()
                        
            if matched_n is None:
                self._add_results("ERROR", entry_rp, [f"Unerlaubte(r) {'Ordner' if is_d else 'Datei'}: Dieses Element ist nicht in der Konfiguration (config.yaml) erlaubt. Bitte definiere es in der Konfiguration oder lösche das Element."])
                continue
                
            if matched_n.get('ignore'):
                continue
                
            curr_k = {**inherited_kwargs, **extracted_k}
            if is_d:
                all_files_out.append({'abs_path': full_p, 'rel_path': entry_rp, 'filename': entry, 'is_directory': True, 'kwargs': curr_k, 'template': matched_n.get('template'), 'base_dir': config_dir})
                self._walk_and_validate(full_p, matched_n, all_files_out, entry_rp, ignore_patterns, curr_k)
            else:
                all_files_out.append({'abs_path': full_p, 'rel_path': entry_rp, 'filename': entry, 'is_directory': False, 'kwargs': curr_k, 'template': matched_n.get('template'), 'base_dir': config_dir})
                
        for m in d_m + f_m:
            if not m['matched']:
                is_opt = m['config'].get('optional', False)
                if not is_opt: self._add_results("ERROR", rel_path, [f"Fehlendes Element: Das erwartete Element '{m['pattern']}' wurde nicht gefunden. Bitte erstelle die Datei/den Ordner oder markiere das Element in der Konfiguration als 'optional: true'."])
                elif not m['config'].get('silent', False): self._add_results("WARNING", rel_path, [f"Kein Match für '{m['pattern']}': Dieses optionale Element fehlt im Dateisystem."])
