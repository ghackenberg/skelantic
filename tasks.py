import os
import shutil
from invoke.tasks import task # pyright: ignore[reportUnknownVariableType]
from invoke.context import Context
from invoke.collection import Collection

@task # type: ignore
def test(c: Context) -> None:
    """Führt die Unit-Tests für den Linter Core aus."""
    c.run("python -m pytest tests/")

@task # type: ignore
def types(c: Context) -> None:
    """Führt eine strikte statische Typ-Prüfung mit pyright aus"""
    print("Checking core modules with pyright...")
    res = c.run("python -m pyright src/skelantic tasks.py", warn=True)
    if res and res.failed:
        import sys
        sys.exit(1)

@task # type: ignore
def build(c: Context) -> None:
    """Baut die Wheel- und Source-Distributionen für PyPI."""
    if os.path.exists("dist"):
        shutil.rmtree("dist")
    c.run("python -m pip install --upgrade build twine")
    c.run("python -m build")

@task(pre=[build]) # type: ignore
def publish(c: Context) -> None:
    """Lädt die gebauten Pakete auf PyPI hoch (benötigt konfigurierte PyPI Credentials)."""
    c.run("twine upload dist/*")

ns = Collection()
ns.add_task(test, name="test") # type: ignore
ns.add_task(types, name="types") # type: ignore
ns.add_task(build, name="build") # type: ignore
ns.add_task(publish, name="publish") # type: ignore
