from markdown_it import MarkdownIt
from markdown_it.tree import SyntaxTreeNode
from markdown_it.token import Token
from mdit_py_plugins.front_matter import front_matter_plugin
from typing import List, Dict, Optional

class ParseError(Exception):
    pass

class Document:
    """Basisklasse für alle Dokumente. Implementiert Fault-Tolerance."""
    def __init__(self, filepath: str) -> None:
        self.filepath: str = filepath
        self.parse_error: Optional[str] = None
        self.raw_content: str = ""
        try:
            # Versuche als UTF-8, Fallback auf latin-1/windows-1252 bei Fehlern
            with open(filepath, 'r', encoding='utf-8') as f:
                self.raw_content = f.read()
        except UnicodeDecodeError:
            try:
                with open(filepath, 'r', encoding='latin-1') as f:
                    self.raw_content = f.read()
            except Exception as e:
                self.parse_error = f"Konnte Datei nicht lesen (Encoding/IO): {e}"
        except Exception as e:
            self.parse_error = f"Konnte Datei nicht lesen: {e}"

class MarkdownDocument(Document):
    """Wrapper um den markdown-it-py AST."""
    
    def __init__(self, filepath: str) -> None:
        super().__init__(filepath)
        self.ast_node: Optional[SyntaxTreeNode] = None
        self._tokens: Optional[List[Token]] = None
        
        if not self.parse_error:
            self._parse_markdown()

    def _parse_markdown(self) -> None:
        try:
            md = MarkdownIt("commonmark").use(front_matter_plugin)
            self._tokens = md.parse(self.raw_content)
            self.ast_node = SyntaxTreeNode(self._tokens)
        except Exception as e:
            self.parse_error = f"Markdown Syntax Error: {e}"

    def has_text(self, text: str) -> bool:
        return text in self.raw_content

    def get_tables(self) -> List[Dict[str, str]]:
        tables: List[Dict[str, str]] = []
        if '|' in self.raw_content and '---' in self.raw_content:
            tables.append({'raw': 'found'})
        return tables
        
    def get_inline_code_blocks(self) -> List[str]:
        import re
        return re.findall(r'`([^`]+)`', self.raw_content)

    def get_links(self) -> List[str]:
        import re
        return re.findall(r'\[.*?\]\((?!http|mailto|#)(.*?)\)', self.raw_content)
