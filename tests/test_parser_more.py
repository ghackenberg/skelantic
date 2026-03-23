from skelantic.templates.parser import TemplateParser
import pytest

def test_parser_unclosed_choice():
    with pytest.raises(Exception) as exc:
        parser = TemplateParser("[[choice:MyChoice]]\n[[case:A]]\nA\n")
        parser.parse()
    assert "Missing closing tag" in str(exc.value)

def test_parser_unclosed_block():
    with pytest.raises(Exception) as exc:
        parser = TemplateParser("[[block:MyBlock]]\nA\n")
        parser.parse()
    assert "Missing closing tag" in str(exc.value)
