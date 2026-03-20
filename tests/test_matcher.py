from skelantic.templates.matcher import SkeletalMatcher

def test_basic_variable_extraction() -> None:
    template = "# {{title:str}}\n\n{{description:text}}"
    doc = "# Welcome\n\nThis is a multiline\ndescription."
    
    matcher = SkeletalMatcher(template)
    success, _, data = matcher.match(doc)
    
    assert success is True
    assert data["title"] == "Welcome"
    assert data["description"] == "This is a multiline\ndescription."

def test_block_matching() -> None:
    template = """
# Page
[[block:meta]]
## Metadata
Date: {{date:str}}
[[/block]]
"""
    doc = "# Page\n## Metadata\nDate: 2026-03-06"
    
    matcher = SkeletalMatcher(template)
    success, _, data = matcher.match(doc)
    
    assert success is True
    assert data["meta"]["date"] == "2026-03-06"

def test_repeat_matching() -> None:
    template = """
# List
[[repeat:items]]
* {{name:str}}: {{value:int}}
[[/repeat]]
"""
    doc = "# List\n* Apple: 10\n* Banana: 5\n* Cherry: 15"
    
    matcher = SkeletalMatcher(template)
    success, _, data = matcher.match(doc)
    
    assert success is True
    assert len(data["items"]) == 3
    assert data["items"][0] == {"name": "Apple", "value": "10"}
    assert data["items"][1] == {"name": "Banana", "value": "5"}
    assert data["items"][2] == {"name": "Cherry", "value": "15"}

def test_choice_matching() -> None:
    template = """
# Component
[[choice:type]]
[[case:TABLE]]
Type: Table
Columns: {{cols:str}}
[[/case]]
[[case:TEXT]]
Type: Text
Content: {{content:str}}
[[/case]]
[[/choice]]
"""
    doc_table = "# Component\nType: Table\nColumns: ID, Name"
    doc_text = "# Component\nType: Text\nContent: Hello World"
    
    # Test Case Table
    matcher = SkeletalMatcher(template)
    success, _, data = matcher.match(doc_table)
    assert success is True
    assert data["type_type"] == "TABLE"
    assert data["cols"] == "ID, Name"
    
    # Test Case Text
    matcher = SkeletalMatcher(template)
    success, _, data = matcher.match(doc_text)
    assert success is True
    assert data["type_type"] == "TEXT"
    assert data["content"] == "Hello World"

def test_nested_complex_structures() -> None:
    template = """
# Main
[[repeat:sections]]
## {{title:str}}
[[block:details]]
Info: {{info:str}}
[[repeat:tags]]
- {{tag:slug}}
[[/repeat]]
[[/block]]
[[/repeat]]
"""
    doc = """
# Main
## Section 1
Info: First
- tag-one
- tag-two
## Section 2
Info: Second
- tag-three
"""
    matcher = SkeletalMatcher(template)
    success, _, data = matcher.match(doc)
    
    assert success is True
    assert len(data["sections"]) == 2
    assert data["sections"][0]["title"] == "Section 1"
    assert data["sections"][0]["details"]["info"] == "First"
    assert len(data["sections"][0]["details"]["tags"]) == 2
    assert data["sections"][1]["details"]["info"] == "Second"

def test_mismatch_error_reporting() -> None:
    template = "# {{title:str}}\nRequired line"
    doc = "# Title\nWrong line"
    
    matcher = SkeletalMatcher(template)
    success, errors, _ = matcher.match(doc)
    
    assert success is False
    assert any("passt nicht zum Template" in e for e in errors)
    assert any("Erwartet: 'Required line'" in e for e in errors)
