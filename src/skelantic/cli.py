import argparse
import os
import sys
import importlib
import pkgutil
from skelantic.commons.core import LinterEngine
from skelantic.commons.decorators import registry
from skelantic.templates.generator import generate_models

def main() -> None:
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Skelantic - Declarative file-tree governance and automation.")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    run_parser = subparsers.add_parser("run", help="Run the Skelantic linter/engine against a directory.")
    run_parser.add_argument("-d", "--dir", default=".", help="The base directory to lint.")
    run_parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output.")
    run_parser.add_argument("-p", "--processors", default=None, help="The Python package containing the @processor functions (e.g. 'tools.skelantic.processors').")
    run_parser.add_argument("-m", "--models", required=True, help="The Python package where Pydantic models are located.")

    gen_parser = subparsers.add_parser("generate", help="Generate Pydantic models from Skeletal Templates.")
    gen_parser.add_argument("-o", "--output", required=True, help="Output directory for generated models.")

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

        engine = LinterEngine(registry, verbose=args.verbose, models_module=args.models)
        engine.run(args.dir)
        failed = engine.print_report()
        if failed:
            sys.exit(1)

    elif args.command == "generate":
        generate_models(output_dir=args.output)

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
