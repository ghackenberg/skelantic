import argparse
import os
import sys
import importlib
import importlib.metadata
import pkgutil
import pathlib
import shutil
import yaml
import inspect
from typing import Dict, List, cast
from skelantic.commons.core import LinterEngine
from skelantic.commons.decorators import registry, ProcessorBinding
from skelantic.commons.resolver import PathResolver

def _get_versions() -> tuple[str, str]:
    try:
        installed = importlib.metadata.version('skelantic')
    except importlib.metadata.PackageNotFoundError:
        installed = "0.0.0-dev"
        
    repo_version = "unknown"
    v_file = pathlib.Path(".skelantic/version")
    if v_file.exists():
        repo_version = v_file.read_text(encoding="utf-8").strip()
        
    return installed, repo_version

def _load_settings() -> Dict[str, str]:
    settings = {
        "types_file": "tools/skelantic/types.py",
        "types_module": "tools.skelantic.types",
        "processors_package": "tools.skelantic.processors",
        "processors_dir": "tools/skelantic/processors"
    }
    s_file = pathlib.Path(".skelantic/settings.yaml")
    if s_file.exists():
        try:
            with open(s_file, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f)
                if isinstance(loaded, dict):
                    settings.update(cast(Dict[str, str], loaded))
        except Exception: pass
    return settings

def _save_settings(settings: Dict[str, str]) -> None:
    pathlib.Path(".skelantic").mkdir(parents=True, exist_ok=True)
    with open(".skelantic/settings.yaml", "w", encoding="utf-8") as f:
        yaml.dump(settings, f, default_flow_style=False)

def _check_version(command: str) -> None:
    if command in ["init", "migrate"]:
        return # Skip check for life-cycle commands
        
    installed, repo = _get_versions()
    if repo == "unknown":
        print(f"❌ ERROR: Repository is not initialized with Skelantic.")
        print(f"👉 For new projects, run: 'skelantic init'")
        print(f"👉 For existing projects, run: 'skelantic migrate'")
        sys.exit(1)
        
    if installed != repo:
        if installed < repo:
            print(f"❌ ERROR: Your installed Skelantic version ({installed}) is older than the repository version ({repo}).")
            print(f"👉 Please run: pip install --upgrade skelantic")
            sys.exit(1)
        else:
            print(f"❌ ERROR: The repository is using an older version of Skelantic ({repo}). Installed is {installed}.")
            print(f"👉 You MUST run 'skelantic migrate' to update the skill files and acknowledgment the upgrade.")
            sys.exit(1)

def _get_pkg_data_path() -> pathlib.Path:
    cli_path = pathlib.Path(__file__).resolve()
    pkg_root = cli_path.parent
    
    # 1. Try package data first (production/pip install)
    data_root = pkg_root / "_docs"
    if (data_root / "SKILL.md").exists():
        return data_root
        
    # 2. Fallback to repository root (local development)
    repo_root = cli_path.parent.parent.parent
    if (repo_root / "SKILL.md").exists():
        return repo_root
        
    raise Exception("Could not locate Skelantic data files (SKILL.md, docs/).")

def main() -> None:
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8') # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue]
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Skelantic - AI-Native Repository Governance.")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # RUN
    run_parser = subparsers.add_parser("run", help="Run the linter against the repository.")
    run_parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output.")

    # GENERATE
    gen_parser = subparsers.add_parser("generate", help="Generate RepoGraph types.")
    gen_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output.")

    # INIT
    subparsers.add_parser("init", help="Initialize a new Skelantic project.")

    # MIGRATE
    subparsers.add_parser("migrate", help="Update repository to match installed Skelantic version.")

    # PROCESSORS
    subparsers.add_parser("processors", help="List all registered processors and their details.")

    # INFO
    info_parser = subparsers.add_parser("info", help="Inspect a path against the schema.")
    info_parser.add_argument("path", help="The path to inspect.")

    # TEMPLATE
    tmpl_parser = subparsers.add_parser("template", help="Get the raw template for a path.")
    tmpl_parser.add_argument("path", help="The path to resolve.")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    _check_version(args.command)
    settings = _load_settings()

    if args.command == "run":
        sys.path.insert(0, os.getcwd())
        processors_pkg = settings.get("processors_package")
        types_mod_name = settings.get("types_module")
        
        if not types_mod_name:
            print("❌ ERROR: 'types_module' is not defined in .skelantic/settings.yaml")
            sys.exit(1)

        # Import internal core processors
        import skelantic.commons.processors as _

        if processors_pkg:
            try:
                proc_module = importlib.import_module(processors_pkg)
                if hasattr(proc_module, '__path__'):
                    for _, module_name, _ in pkgutil.walk_packages(proc_module.__path__, f"{processors_pkg}."):
                        importlib.import_module(module_name)
            except ImportError as e:
                print(f"Error importing processors: {e}"); sys.exit(1)

        types_module = None
        try:
            types_module = importlib.import_module(types_mod_name)
        except ImportError as e:
            print(f"Error importing types: {e}"); sys.exit(1)

        engine = LinterEngine(registry, verbose=args.verbose, types_module=types_module)
        engine.run(".")
        if engine.print_report(): sys.exit(1)

    elif args.command == "generate":
        from skelantic.commons.codegen import run_codegen
        output_path = settings.get("types_file")
        if not output_path:
            print("❌ ERROR: 'types_file' is not defined in .skelantic/settings.yaml")
            sys.exit(1)
            
        config_path = os.path.join(".", ".skelantic", "config.yaml")
        run_codegen(config_path=config_path, output_path=output_path, verbose=args.verbose)

    elif args.command == "init":
        # 1. Structure
        for d in ["src", "tests", ".skelantic/templates", "tools/skelantic/processors"]:
            pathlib.Path(d).mkdir(parents=True, exist_ok=True)
        
        # 2. Configs
        c_file = pathlib.Path(".skelantic/config.yaml")
        if not c_file.exists():
            c_file.write_text("description: 'Repository Root'\nfiles: {}\ndirectories: {}\n", encoding="utf-8")
            
        pyproj = pathlib.Path("pyproject.toml")
        if not pyproj.exists():
            pyproj.write_text("[tool.pyright]\ntypeCheckingMode = 'strict'\n\n[tool.pytest.ini_options]\naddopts = '--cov=src --cov-report=term-missing --cov-fail-under=90'\n", encoding="utf-8")
            
        # 3. Settings & Version
        installed, _ = _get_versions()
        pathlib.Path(".skelantic/version").write_text(installed, encoding="utf-8")
        _save_settings(settings)
        
        # 4. Skill
        _deploy_skill()
        print(f"✅ Project initialized with Skelantic {installed}.")
        print(f"🚀 Skill deployed to .gemini/skills/skelantic/")
        print(f"⚙️ Settings saved to .skelantic/settings.yaml")

    elif args.command == "migrate":
        installed, _ = _get_versions()
        pathlib.Path(".skelantic").mkdir(parents=True, exist_ok=True)
        pathlib.Path(".skelantic/version").write_text(installed, encoding="utf-8")
        if not pathlib.Path(".skelantic/settings.yaml").exists():
            _save_settings(settings)
        _deploy_skill()
        print(f"✅ Repository migrated to Skelantic {installed}.")
        print(f"📜 Please read the migration docs in .gemini/skills/skelantic/docs/migrations/ for refactoring steps.")

    elif args.command == "processors":
        sys.path.insert(0, os.getcwd())
        processors_pkg = settings.get("processors_package")
        
        # Import internal core processors
        import skelantic.commons.processors as _

        # Import custom processors recursively
        if processors_pkg:
            try:
                proc_module = importlib.import_module(processors_pkg)
                if hasattr(proc_module, '__path__'):
                    for _, module_name, _ in pkgutil.walk_packages(proc_module.__path__, f"{processors_pkg}."):
                        importlib.import_module(module_name)
            except ImportError as e:
                print(f"Error importing processors: {e}"); sys.exit(1)

        print("\nRegistered Skelantic Processors:")
        print("-" * 50)
        
        # Group by phase for better overview
        by_phase: Dict[int, List[ProcessorBinding]] = {1: [], 2: [], 3: []}
        for b in registry.bindings:
            phase = b.phase if b.phase is not None else 2
            if phase not in by_phase:
                by_phase[phase] = []
            by_phase[phase].append(b)
            
        all_phases = sorted(by_phase.keys())
        for phase in all_phases:
            if not by_phase[phase]: continue
            print(f"\n[PHASE {phase}]")
            for b in sorted(by_phase[phase], key=lambda x: f"{x.func.__module__}.{x.func.__name__}"):
                func_name = b.func.__name__
                func_module = b.func.__module__
                try:
                    f_file = inspect.getfile(b.func)
                    f_file = os.path.relpath(f_file, os.getcwd()).replace('\\', '/')
                except Exception:
                    f_file = "Unknown"
                
                doc = (getattr(b.func, "__doc__", "") or "No docstring.").strip().split('\n')[0]
                print(f"⚙️ {func_module}:{func_name}")
                print(f"   Match: {b.match or 'Type-based only'}")
                print(f"   File:  {f_file}")
                print(f"   Doc:   \"{doc}\"")
        print("-" * 50)

    elif args.command == "info" or args.command == "template":
        sys.path.insert(0, os.getcwd())
        types_mod_name = settings.get("types_module")
        processors_pkg = settings.get("processors_package")
        
        if not types_mod_name:
            print("❌ ERROR: 'types_module' is not defined in .skelantic/settings.yaml")
            sys.exit(1)
            
        # Import internal core processors
        import skelantic.commons.processors as _

        # Import processors recursively so they register themselves in the registry
        if processors_pkg:
            try:
                proc_module = importlib.import_module(processors_pkg)
                if hasattr(proc_module, '__path__'):
                    # RECURSIVE WALK
                    for _, module_name, _ in pkgutil.walk_packages(proc_module.__path__, f"{processors_pkg}."):
                        importlib.import_module(module_name)
            except ImportError: pass # Silence if package doesn't exist
            
        try:
            types_module = importlib.import_module(types_mod_name)
            node_map = getattr(types_module, "__SKELANTIC_NODE_MAP__", {})
        except Exception as e:
            print(f"Error loading types: {e}"); sys.exit(1)
            
        resolver = PathResolver(node_map)
        res = resolver.resolve(args.path)
        
        if not res:
            print(f"❌ Path '{args.path}' does not match any pattern in the configuration.")
            sys.exit(1)
            
        if args.command == "info":
            match_path: str = res.match_path or "N/A"
            parent_folder: str = res.parent_folder or "N/A"
            print(f"Path:   {args.path.replace('\\', '/')}")
            print(f"Status: {'✅ MATCHED' if res.exists else '👻 SCHEMA MATCH (File does not exist yet)'}")
            print("-" * 50)
            print("--- Configuration State ---")
            print(f"Full Match Path:    {match_path.replace('\\', '/')}")
            print(f"Parent Folder Path: {parent_folder.replace('\\', '/')}")
            print(f"Description:        {res.config.get('description', 'N/A')}")
            print(f"Ignore:             {res.config.get('ignore', False)}")
            print(f"Optional:           {res.config.get('optional', False)}")
            print(f"Silent:             {res.config.get('silent', False)}")
            
            t_file_rel: str = "None"
            if res.template_path:
                try: t_file_rel = os.path.relpath(res.template_path, os.getcwd()).replace('\\', '/')
                except Exception: t_file_rel = res.template_path.replace('\\', '/')
            print(f"Template File:      {t_file_rel}")
            
            print("\n--- Python Injection Interface ---")
            print(f"Node Type:   {res.node_type or 'N/A'}")
            print(f"Parent Type: {res.parent_type or 'N/A'}")
            print("\nPath Variables (node.path_params):")
            for k, v in res.path_variables.items():
                print(f"  {k}: {v}")
            
            # Extract template fields if exists
            if res.template_path and os.path.exists(res.template_path):
                from skelantic.templates.matcher import SkeletalMatcher
                from skelantic.templates.parser import LineNode
                try:
                    with open(res.template_path, 'r', encoding='utf-8') as tf:
                        m = SkeletalMatcher(tf.read())
                        # Flatten data structure
                        print("\nTemplate Data (node.data):")
                        # This is a bit complex without instantiating the Pydantic model, 
                        # but we can try to list variables from the parser.
                        for n in m.parser.parse():
                            if isinstance(n, LineNode):
                                for var_item in n.variables:
                                    print(f"  {var_item.name}: {var_item.var_type}")
                except: pass
            
            # --- Active Processors ---
            print("\n--- Active Processors for this Path ---")
            found_procs = False
            for binding in registry.bindings:
                # Check if it matches this path
                is_match = False
                if binding.match == "root" and args.path == ".": is_match = True
                elif binding.regex and binding.regex.match(args.path): is_match = True
                
                # Check if type matches
                if not is_match:
                    sig = inspect.signature(binding.func)
                    params = list(sig.parameters.values())
                    if params:
                        first_param = params[0]
                        if first_param.annotation != inspect.Parameter.empty:
                            # Resolve actual node class
                            node_cls = None
                            if res.match_path in node_map: node_cls = node_map[res.match_path]
                            elif args.path == "." and "root" in node_map: node_cls = node_map["root"]
                            
                            if node_cls:
                                target_anno = first_param.annotation
                                # Handle forward references if necessary
                                if isinstance(target_anno, str):
                                    try: target_anno = eval(target_anno, vars(types_module))
                                    except: pass
                                
                                try:
                                    if isinstance(target_anno, type) and issubclass(node_cls, target_anno):
                                        is_match = True
                                except: pass
                
                if is_match:
                    found_procs = True
                    try:
                        f_file = inspect.getfile(binding.func)
                        f_file = os.path.relpath(f_file, os.getcwd()).replace('\\', '/')
                    except: f_file = "Unknown"
                    
                    doc = (binding.func.__doc__ or "No docstring.").strip().split('\n')[0]
                    print(f"- Function: {binding.func.__name__} (Phase {binding.phase})")
                    print(f"  File:     {f_file}")
                    print(f"  Doc:      \"{doc}\"")
            
            if not found_procs:
                print("None.")
                
            if res.is_directory:
                print("\n--- Allowed Children (Navigation) ---")
                print("📁 Folders:")
                for d in sorted(res.allowed_child_dirs): print(f"  - {d.replace('\\', '/')}")
                print("📄 Files:")
                for f in sorted(res.allowed_child_files): print(f"  - {f.replace('\\', '/')}")
        else:
            # template command
            if not res.template_path:
                print(f"❌ No template defined for path '{args.path}'.")
                sys.exit(1)
            
            t_file_rel = res.template_path
            try: t_file_rel = os.path.relpath(res.template_path, os.getcwd()).replace('\\', '/')
            except: t_file_rel = t_file_rel.replace('\\', '/')
            print(f"Template File: {t_file_rel}")
            print("-" * 50)
            try:
                with open(res.template_path, 'r', encoding='utf-8') as f:
                    print(f.read())
            except Exception as e:
                print(f"Error reading template: {e}"); sys.exit(1)

def _deploy_skill() -> None:
    try:
        data_path = _get_pkg_data_path()
        dest = pathlib.Path(".gemini/skills/skelantic")
        if dest.exists():
            shutil.rmtree(dest)
        dest.mkdir(parents=True, exist_ok=True)
        
        # Copy SKILL.md
        shutil.copy(data_path / "SKILL.md", dest / "SKILL.md")
        
        # Copy docs/
        docs_src = data_path / "docs"
        if docs_src.exists():
            shutil.copytree(docs_src, dest / "docs")
    except Exception as e:
        print(f"Warning: Could not deploy skill files: {e}")

if __name__ == "__main__":
    main()
