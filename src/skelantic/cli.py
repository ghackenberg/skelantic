import argparse
import os
import sys
import importlib
import importlib.metadata
import pkgutil
from skelantic.commons.core import LinterEngine
from skelantic.commons.decorators import registry

def main() -> None:
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8') # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue]
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Skelantic - Declarative file-tree governance and automation.")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    run_parser = subparsers.add_parser("run", help="Run the Skelantic linter/engine against a directory.")
    run_parser.add_argument("-d", "--dir", default=".", help="The base directory to lint.")
    run_parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output.")
    run_parser.add_argument("-p", "--processors", default=None, help="The Python package containing the @processor functions (e.g. 'tools.skelantic.processors').")
    run_parser.add_argument("-t", "--types", required=True, help="The Python module containing the generated types (e.g. 'tools.skelantic.types').")

    gen_parser = subparsers.add_parser("generate", help="Generate Pydantic models from Skeletal Templates.")
    gen_parser.add_argument("-o", "--output", required=True, help="Output file path for generated types (e.g. 'tools/skelantic/types.py').")
    gen_parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output during generation.")

    migrate_parser = subparsers.add_parser("migrate", help="Output AI-ready migration prompts for upgrading Skelantic.")
    migrate_parser.add_argument("--from", dest="from_version", default=None, help="The version to migrate from (e.g., '0.1.0'). If omitted, reads from .skelantic/version.")

    docs_parser = subparsers.add_parser("docs", help="Print Skelantic documentation (useful for AI Agents).")
    docs_parser.add_argument("topic", nargs="?", default=None, help="The documentation topic to print (e.g. 'templates'). If omitted, prints a summary.")
    docs_parser.add_argument("--all", action="store_true", help="Print all documentation in an XML-tagged format for AI agents.")

    args = parser.parse_args()

    if args.command == "run":
        sys.path.insert(0, os.getcwd()) # Ensure local packages can be imported
        if args.processors:
            try:
                proc_module = importlib.import_module(args.processors)
                if hasattr(proc_module, '__path__'):
                    for _, module_name, _ in pkgutil.iter_modules(proc_module.__path__):
                        importlib.import_module(f"{args.processors}.{module_name}")
                else:
                    print(f"Warning: The processors module '{args.processors}' does not seem to be a package. Imports might not be complete.")
            except ImportError as e:
                print(f"Error importing processors module '{args.processors}': {e}")
                sys.exit(1)

        types_module = None
        if args.types:
            try:
                types_module = importlib.import_module(args.types)
            except ImportError as e:
                print(f"Error importing types module '{args.types}': {e}")
                sys.exit(1)

        engine = LinterEngine(registry, verbose=args.verbose, types_module=types_module)
        engine.run(args.dir)
        failed = engine.print_report()
        if failed:
            sys.exit(1)

    elif args.command == "generate":
        from skelantic.commons.codegen import run_codegen
        config_path = os.path.join(".", ".skelantic", "config.yaml")
        run_codegen(config_path=config_path, output_path=args.output, verbose=args.verbose)

    elif args.command == "migrate":
        import importlib.metadata
        import pathlib
        
        try:
            current_version = importlib.metadata.version('skelantic')
        except importlib.metadata.PackageNotFoundError:
            current_version = "unknown"
            
        from_version = args.from_version
        
        if not from_version:
            version_file = pathlib.Path(".skelantic/version")
            if version_file.exists():
                from_version = version_file.read_text(encoding="utf-8").strip()
            else:
                from_version = "0.1.x"
                print(f"Warning: Could not find .skelantic/version file. Assuming starting version is {from_version}.\n")
                
        cli_path = pathlib.Path(__file__).resolve()
        pkg_root = cli_path.parent
        migrations_dir = pkg_root / "migrations"
        
        if not migrations_dir.exists() or not migrations_dir.is_dir():
            migrations_dir = cli_path.parent.parent.parent / "src" / "skelantic" / "migrations"
            
        if not migrations_dir.exists():
            print("No migrations found in the Skelantic installation.")
            sys.exit(0)
            
        migration_files = sorted(migrations_dir.glob("*.md"))
        
        print("<system_instruction>")
        print(f"You are upgrading a Skelantic repository from v{from_version} to v{current_version}.")
        print("Apply the following refactoring steps sequentially:")
        print("</system_instruction>\n")
        
        for m_file in migration_files:
            print(f'<migration file="{m_file.name}">')
            print(m_file.read_text(encoding="utf-8"))
            print("</migration>\n")
            
        print("<system_instruction>")
        print("Once the refactoring is complete, run your skelantic generate command to update the types and the .skelantic/version file.")
        print("</system_instruction>")

    elif args.command == "docs":
        import pathlib
        
        def get_docs_base_path() -> pathlib.Path | None:
            cli_path = pathlib.Path(__file__).resolve()
            pkg_root = cli_path.parent
            
            # 1. Try package data first (production/pip install)
            docs_root = pkg_root / "_docs"
            if (docs_root / "README.md").exists() and (docs_root / "docs").is_dir():
                return docs_root
                
            # 2. Fallback to repository root (local development)
            repo_root = cli_path.parent.parent.parent
            if (repo_root / "README.md").exists() and (repo_root / "docs").is_dir():
                return repo_root
                
            return None
            
        base_path = get_docs_base_path()
        if not base_path:
            print("Error: Could not locate Skelantic documentation files.")
            sys.exit(1)
            
        doc_files: list[tuple[str, str, str]] = [
            ("readme", "README.md", "High-Level Overview, Quickstart and Philosophy"),
            ("cli", "docs/cli.md", "Command Line Interface (CLI) Reference"),
            ("config", "docs/config.md", "Configuration Guide (config.yaml)"),
            ("templates", "docs/templates.md", "Skeletal Templates Syntax Guide"),
            ("processors", "docs/processors.md", "Writing Processors & Understanding Context"),
            ("nodes", "docs/nodes.md", "File System Nodes API"),
        ]
        
        if args.all:
            print("<skelantic_documentation>\n")
            for _, rel_path, desc in doc_files:
                p = base_path / rel_path
                if p.exists():
                    print(f'<document path="{rel_path}" description="{desc}">')
                    print(p.read_text(encoding="utf-8"))
                    print("</document>\n")
                else:
                    print(f'<!-- Warning: Document {rel_path} not found -->\n')
            print("</skelantic_documentation>")
            
        elif args.topic:
            topic = args.topic.lower()
            found = False
            for t, rel_path, desc in doc_files:
                if t == topic or (topic.endswith(".md") and rel_path.endswith(topic)):
                    p = base_path / rel_path
                    if p.exists():
                        print(p.read_text(encoding="utf-8"))
                    else:
                        print(f"Error: Documentation file {rel_path} not found.")
                    found = True
                    break
            if not found:
                print(f"Error: Topic '{topic}' not found. Available topics: {', '.join(t[0] for t in doc_files)}")
                sys.exit(1)
                
        else:
            print("Skelantic Documentation")
            print("-----------------------")
            print("Available topics:")
            for topic, rel_path, desc in doc_files:
                print(f"  {topic:<15} - {desc}")
            print("\nUsage:")
            print("  skelantic docs <topic>   # Read specific topic")
            print("  skelantic docs --all     # Dump all docs for AI Agents")

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
