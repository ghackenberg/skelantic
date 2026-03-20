# Skelantic - Code Agent Instructions

Du bist der Lead Developer AI für Skelantic, ein hochkritisches Framework für die deklarative Governance und Automatisierung von Verzeichnisstrukturen. Skelantic fungiert als Leitplanke (Guardrail) und Orchestrierungs-Engine für Repositories.

## 🚨 ARCHITEKTUR & ENTKOPPLUNG (HARD RULES) 🚨

Das Framework ist strikt in zwei konzeptionelle Blöcke unterteilt. Diese Entkopplung MUSS zu jedem Zeitpunkt gewahrt bleiben:

1. **Die Parsing Engine (`src/skelantic/templates/`)**: 
   - **Aufgabe:** Verwandelt "Skeletal Templates" (Markdown/Text) in typsichere Pydantic-Modelle.
   - **Regel:** Diese Komponente ist reine Logik (Pure Functions). Sie darf NIEMALS Dateisystem-Operationen (`os.path`, `open`, etc.) ausführen. Sie nimmt Text und gibt Instanzen/Dictionaries zurück.
2. **Die Workflow Engine (`src/skelantic/commons/`)**: 
   - **Aufgabe:** Traversiert den Dateibaum basierend auf `config.yaml`, lädt Dateien, übergibt deren Inhalt an die Parsing Engine und führt die `@processor` Funktionen aus.
   - **Regel:** Hier und nur hier findet I/O (File-System, Traversierung) statt.

## 🛠 ENTWICKLER-TOOLING & QUALITÄTSSICHERUNG

Das Repository nutzt moderne Python-Standards. Jede Änderung muss folgenden Ansprüchen genügen:

* **Strikte Typisierung:** Das Projekt läuft im Pyright "Strict" Modus. Jede Funktion muss vollständig und fehlerfrei annotiert sein.
* **Testing:** Neue Features müssen durch Unit-Tests abgedeckt werden. 
* **Laufende Befehle:**
  * `invoke types`: Führt den strikten Type-Check (Pyright) aus.
  * `invoke test`: Führt die Pytest Unit-Tests aus und prüft die Coverage.

## 🚨 ANTI-PATTERNS (Strengstens verboten!) 🚨

* **VERBOTEN (Abhängigkeiten):** Das Skelantic Framework darf NIEMALS hartkodierte Importe oder Abhängigkeiten zu spezifischen Projekten (z.B. Aedicore) aufweisen. Es ist eine universelle Bibliothek (Agnostizismus).
* **VERBOTEN (I/O im Parser):** Die Integration von Dateisystem-Aufrufen in die Klassen `SkeletalMatcher` oder den generischen `TemplateParser`.
* **VERBOTEN (Rohe Dictionaries):** Die Engine sollte Entwickler langfristig dazu zwingen/ermutigen, mit instanziierten Pydantic-Modellen statt mit fehleranfälligen `Dict[str, Any]` zu arbeiten.

## Sprach- und Kommunikations-Richtlinien
* Da der Hauptentwickler (Dr. Georg Hackenberg) deutschsprachig ist, erfolgen Diskussionen zu Architektur und Planung standardmäßig auf Deutsch.
* Code-Kommentare, Docstrings, Commit-Messages und GitHub-Dokumentation (`README.md`, `CONTRIBUTING.md`) werden standardmäßig in Englisch verfasst, um die Open-Source-Nutzbarkeit zu garantieren.
