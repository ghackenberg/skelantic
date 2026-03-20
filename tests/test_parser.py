from skelantic.templates.parser import TemplateParser, LineNode

def test_parse_simple_line() -> None:
    template = "# {{title:str}} - {{id:int}}"
    parser = TemplateParser(template)
    nodes = parser.parse()
    
    assert len(nodes) == 1
    assert isinstance(nodes[0], LineNode)
    assert nodes[0].template_line == template
    assert len(nodes[0].variables) == 2
    assert nodes[0].variables[0].name == "title"
    assert nodes[0].variables[0].var_type == "str"
    assert nodes[0].variables[1].name == "id"
    assert nodes[0].variables[1].var_type == "int"

def test_parse_multiline() -> None:
    template = "Description:\n{{desc:text}}"
    parser = TemplateParser(template)
    nodes = parser.parse()
    
    assert len(nodes) == 2
    assert isinstance(nodes[1], LineNode)
    assert nodes[1].is_multiline is True
    assert nodes[1].multiline_var == "desc"
    assert nodes[1].multiline_type == "text"

def test_parse_block() -> None:
    template = "[[block:meta]]\nTitle: {{t:str}}\n[[/block]]"
    parser = TemplateParser(template)
    nodes = parser.parse()
    
    assert len(nodes) == 1
    assert nodes[0].type == "block"
    assert nodes[0].name == "meta"
    assert len(nodes[0].children) == 1
    assert isinstance(nodes[0].children[0], LineNode)
    assert nodes[0].children[0].variables[0].name == "t"

def test_parse_choice() -> None:
    template = "[[choice:action]]\n[[case:ADD]]\n+ {{val:int}}\n[[/case]]\n[[case:SUB]]\n- {{val:int}}\n[[/case]]\n[[/choice]]"
    parser = TemplateParser(template)
    nodes = parser.parse()
    
    assert len(nodes) == 1
    assert nodes[0].type == "choice"
    assert nodes[0].name == "action"
    assert len(nodes[0].children) == 2
    assert nodes[0].children[0].type == "case"
    assert nodes[0].children[0].name == "ADD"
    assert nodes[0].children[1].name == "SUB"
    
    add_case = nodes[0].children[0]
    assert len(add_case.children) == 1
    assert isinstance(add_case.children[0], LineNode)
    assert add_case.children[0].variables[0].name == "val"