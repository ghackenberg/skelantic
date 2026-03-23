import os
import inspect
from collections import defaultdict
from typing import Any, Dict, List, Optional, TypedDict, Pattern, cast
from .documents import MarkdownDocument, Document
from .context import LinterContext
from skelantic.templates.matcher import SkeletalMatcher
from .config import ConfigLoader, get_regex
from .decorators import Registry

class MatcherDict(TypedDict):
    regex: Pattern[str]
    pattern: str
    config: Dict[str, Any]
    matched: bool

def tree() -> defaultdict[Any, Any]:
    return defaultdict(tree)

class LinterEngine:
    def __init__(self, registry: Registry, verbose: bool = False, types_module: Any = None, models_module: str = "") -> None:
        self.registry: Registry = registry
        self.verbose: bool = verbose
        self.models_module: str = models_module
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

        
        # We remove hardcoded import of tools.skelantic.processors here to make skelantic independent.
        # It's up to the user of LinterEngine to import their processors so they register themselves via @processor.
        
        new_config_path = os.path.join(".", ".skelantic", "config.yaml")
        if os.path.exists(new_config_path):
            self.config = self.config_loader.load_config(new_config_path)
            self._log(f"Loaded ROOT config from {new_config_path}")
        else:
            self.config = {}
        self.compiled_patterns: List[Any] = []

    def _log(self, msg: str, level: str = "DEBUG") -> None:
        if self.verbose: print(f"{'🔍 DEBUG: ' if level == 'DEBUG' else '💡 INFO:  '}{msg}")

    def run(self, base_dir: str = ".") -> None:
        all_files: List[Dict[str, Any]] = []
        self._walk_and_validate(base_dir, self.config, all_files, rel_path=".", active_patterns=self.compiled_patterns)
        self._run_templates(all_files); self._run_phase(1, all_files); self._run_phase(2, all_files); self._run_global_phase(3)

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
                        errs.append(f"💡 Trace-Details gespeichert in: {os.path.relpath(trace_file, os.getcwd())}")
                        self._add_results("ERROR", f_data['rel_path'], errs)
                    else:
                        self.ctx.extracted_data[f_data['rel_path']] = data
                except Exception as e: self._add_results("ERROR", f_data['rel_path'], [f"Template Error: {e}"])

    def _get_or_create_doc(self, abs_filepath: str, rel_path: str, is_directory: bool = False) -> Document:
        if abs_filepath in self.document_cache: return self.document_cache[abs_filepath]
        doc = Document(abs_filepath) if is_directory else (MarkdownDocument(abs_filepath) if rel_path.endswith('.md') else Document(abs_filepath))
        self.document_cache[abs_filepath] = doc
        return doc

    def _run_phase(self, phase: int, files_data: List[Dict[str, Any]]) -> None:
        from .nodes import FSNode, FileNode, DirectoryNode
        for f_data in files_data:
            rp = f_data['rel_path']
            # Find matching class in node_map
            NodeClass = None
            if rp in self.node_map:
                NodeClass = self.node_map[rp]
            else:
                for pat, cls in self.node_map.items():
                    if get_regex(pat).match(rp):
                        NodeClass = cls
                        break
            
            if NodeClass is None:
                NodeClass = DirectoryNode if f_data.get('is_directory', False) else FileNode

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

            node.data = self.ctx.extracted_data.get(rp)
            self.ctx.register_node(node)
            
            # Execute rules
            for binding in self.registry.bindings:
                if binding.phase != phase:
                    continue

                is_match = False
                
                # Check regex match
                if binding.regex:
                    match = binding.regex.match(rp)
                    if match:
                        is_match = True
                        
                # Check type hint match
                sig = inspect.signature(binding.func)
                params = list(sig.parameters.values())
                if params and issubclass(type(node), FSNode):
                    first_param = params[0]
                    if first_param.annotation != inspect.Parameter.empty and isinstance(node, first_param.annotation):
                        is_match = True
                        
                if is_match:
                    self._execute_rule(binding.func, binding.name, node, f_data)

    def _execute_rule(self, func: Any, rule_name: str, node: Any, f_data: Dict[str, Any]) -> None:
        from pydantic import BaseModel
        sig = inspect.signature(func)
        kwargs: Dict[str, Any] = {}

        current_traces: List[str] = []
        def tracer(msg: str) -> None:
            current_traces.append(msg)

        for param_name, param in sig.parameters.items():
            if hasattr(param.annotation, '__mro__') and issubclass(param.annotation, BaseModel):
                state_cls = param.annotation
                if state_cls not in self._state_singletons:
                    self._state_singletons[state_cls] = state_cls()
                kwargs[param_name] = self._state_singletons[state_cls]
            elif param_name == 'node': kwargs['node'] = node
            elif param_name == 'tracer': kwargs['tracer'] = tracer
            else:
                self._log(f"Warning: Argument '{param_name}' requested by processor '{rule_name}' cannot be injected. Only 'node', 'tracer', and Pydantic state models are supported.", level="WARNING")
                
        try:
            res = func(**kwargs)
            if res:
                if current_traces:
                    safe_path = f_data['rel_path'].replace('/', '_').replace('\\', '_')
                    trace_dir = os.path.join(os.getcwd(), ".skelantic", "traces")
                    os.makedirs(trace_dir, exist_ok=True)
                    trace_file = os.path.join(trace_dir, f"{rule_name}_{safe_path}.log")
                    with open(trace_file, "w", encoding="utf-8") as f:
                        f.write("\n".join(current_traces))
                    res.append(f"💡 Trace-Details gespeichert in: {os.path.relpath(trace_file, os.getcwd())}")
                self._add_results("ERROR", f_data['rel_path'], res)
        except Exception as e: self._add_results("ERROR", f_data['rel_path'], [f"Crash '{rule_name}': {e}"])

    def _run_global_phase(self, phase: int) -> None:
        for binding in self.registry.bindings:
            if binding.phase != phase:
                continue
            if binding.match != "root" and binding.match is not None:
                continue
                
            sig = inspect.signature(binding.func)
            kwargs: Dict[str, Any] = {}
            if 'ctx' in sig.parameters: kwargs['ctx'] = self.ctx
            try:
                res = binding.func(**kwargs)
                if res: self._add_results("WARNING", "root", res)
            except Exception as e: self._add_results("ERROR", "root", [f"Global Crash '{binding.name}': {e}"])

    def _add_results(self, severity: str, full_rel_path: str, results: List[str]) -> None:
        if not results: return
        parts = full_rel_path.split('/') if full_rel_path not in ['.', ''] else ['root']
        current_node = self.results_tree
        for part in parts: current_node = current_node[part]
        if '_errors' not in current_node: current_node['_errors'], current_node['_warnings'] = [], []
        for msg in results:
            if severity == "ERROR":
                if msg not in current_node['_errors']: current_node['_errors'].append(msg); self.total_errors += 1
            else:
                if msg not in current_node['_warnings']: current_node['_warnings'].append(msg); self.total_warnings += 1

    def _print_node(self, name: str, node: Any, indent: int = 0) -> None:
        prefix = "   " * indent
        if name and name not in ["_errors", "_warnings"]:
            print(f"{prefix}{'📄' if '.' in name else '📁'} {name}{'/' if '.' not in name else ''}")
            indent += 1
            prefix = "   " * indent
        for w in node.get('_warnings', []): print(f"{prefix}⚠️ {w}")
        for e in node.get('_errors', []): print(f"{prefix}❌ {e}")
        for child_name, child_node in sorted(node.items()):
            if child_name not in ['_errors', '_warnings']: self._print_node(child_name, child_node, indent)

    def print_report(self) -> bool:
        print("\n" + "="*70 + "\n🛡️  AEDICORE ARCHITECT 🛡️\n" + "="*70 + "\n")
        if not self.results_tree: print("✨ PERFECT REPOSITORY: 0 Errors, 0 Warnings."); return False
        for top_level, node in sorted(self.results_tree.items()): self._print_node(top_level, node)
        print("\n" + "="*70)
        if self.total_errors > 0: print(f"🛑 FAILED: {self.total_errors} Errors, {self.total_warnings} Warnings."); return True
        print(f"✅ PASSED: 0 Errors, {self.total_warnings} Warnings." if self.total_warnings else "✨ PERFECT REPOSITORY!"); return False

    def _walk_and_validate(self, current_dir: str, current_config: Dict[str, Any], all_files_out: List[Dict[str, Any]], rel_path: str = ".", active_patterns: Optional[List[Any]] = None, inherited_kwargs: Optional[Dict[str, Any]] = None) -> None:
        inherited_kwargs = inherited_kwargs or {}
        active_patterns = list(active_patterns) if active_patterns else []
        try: entries = os.listdir(current_dir)
        except PermissionError: return
        ignore = {".git", "node_modules", "venv", "__pycache__", ".skelantic", ".pytest_cache", ".mypy_cache", "linter.yaml", ".coverage"}
        config_dir = rel_path
        entries = [e for e in entries if e not in ignore and not e.endswith('.pyc')]
        
        # New Config Loading
        lcp_new = os.path.join(current_dir, ".skelantic", "config.yaml")
        
        if os.path.exists(lcp_new):
            local_c = self.config_loader.load_config(lcp_new)
            local_c = self.config_loader.resolve_paths(local_c, current_dir)
            if rel_path != ".":
                current_config = current_config.copy()
                current_config['files'] = {**current_config.get('files', {}), **(local_c.get('files') or {})}
                current_config['directories'] = {**current_config.get('directories', {}), **(local_c.get('directories') or {})}
            for pat, data in local_c.get('files', {}).items():
                if "**" in pat: active_patterns.append((get_regex(pat), data, config_dir))
            
        d_m: List[MatcherDict] = [{'regex': get_regex(p), 'pattern': p, 'config': cast(Dict[str, Any], v) or {}, 'matched': False} for p, v in current_config.get('directories', {}).items()]
        f_m: List[MatcherDict] = [{'regex': get_regex(p), 'pattern': p, 'config': cast(Dict[str, Any], v) or {}, 'matched': False} for p, v in current_config.get('files', {}).items()]
        
        for entry in sorted(entries):
            full_p, entry_rp = os.path.join(current_dir, entry), (entry if rel_path == "." else f"{rel_path}/{entry}")
            is_d = os.path.isdir(full_p)
            matched_n: Optional[Dict[str, Any]] = None
            extracted_k: Dict[str, str] = {}
            m_list = d_m if is_d else f_m
            is_auth = False
            
            for m in m_list:
                match = m['regex'].match(entry)
                if match:
                    matched_n, extracted_k, m['matched'] = m['config'], match.groupdict(), True
                    if matched_n.get('authorize', True): is_auth = True
                    break
            if not is_auth:
                for regex, data, _ in active_patterns:
                    if regex.match(entry_rp):
                        if not matched_n: matched_n = data or {}
                        if data.get('authorize', True): is_auth = True; break
            if matched_n is None:
                self._add_results("ERROR", entry_rp, [f"Unerlaubte(r) {'Ordner' if is_d else 'Datei'}!"])
                continue
            if not is_auth:
                self._add_results("ERROR", entry_rp, [f"Unerlaubte(r) {'Ordner' if is_d else 'Datei'}!"])
            curr_k = {**inherited_kwargs, **extracted_k}
            if is_d: self._walk_and_validate(full_p, matched_n, all_files_out, entry_rp, active_patterns, curr_k)
            else:
                all_files_out.append({'abs_path': full_p, 'rel_path': entry_rp, 'filename': entry, 'is_directory': False, 'kwargs': curr_k, 'template': matched_n.get('template'), 'base_dir': config_dir})
                
        for m in d_m + f_m:
            if not m['matched'] and "**" not in m['pattern']:
                is_opt = m['config'].get('optional', False)
                if not is_opt: self._add_results("ERROR", rel_path, [f"Fehlendes Element: '{m['pattern']}'"])
                elif not m['config'].get('silent', False): self._add_results("WARNING", rel_path, [f"Kein Match für '{m['pattern']}'"])
