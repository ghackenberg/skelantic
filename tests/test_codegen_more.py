from skelantic.commons.codegen import CodeGenerator, run_codegen
from unittest.mock import patch, mock_open

def test_generate_path_params():
    cg = CodeGenerator(".")
    out = cg._generate_path_params("{slug:words}", "    ")
    assert "slug: str" in out
    
    out = cg._generate_path_params("{year:int}-{month:int}", "    ")
    assert "year: int" in out
    assert "month: int" in out
    assert "path_params: PathParams" in out
    
    out = cg._generate_path_params("no_params_here", "    ")
    assert out == ""

def test_parse_template_nodes_complex():
    from skelantic.templates.parser import TemplateNode, LineNode, Variable
    
    # Mock choice node
    var_a = Variable("propA", "str")
    line_a = LineNode(variables=[var_a])
    case_a = TemplateNode("case", "A", [line_a])
    choice_node = TemplateNode("choice", "MyChoice", [case_a])
    
    # Mock repeat node
    var_b = Variable("propB", "int")
    line_b = LineNode(variables=[var_b])
    repeat_node = TemplateNode("repeat", "MyRepeat", [line_b])
    
    cg = CodeGenerator(".")
    classes_out = {}
    cg._parse_template_nodes([choice_node, repeat_node], "TestClass", classes_out)
    
    # Check choice
    assert "TestClass" in classes_out
    assert classes_out["TestClass"]["MyChoice_type"] == "str"
    assert classes_out["TestClass"]["propA"] == "str"
    
    # Check repeat
    assert classes_out["TestClass"]["MyRepeat"] == "List['TestClassMyrepeatItem']"
    assert "TestClassMyrepeatItem" in classes_out
    assert classes_out["TestClassMyrepeatItem"]["propB"] == "int"

def test_codegen_render_tree_aliases():
    cg = CodeGenerator(".")
    tree = {
        "TestTemplate": {
            "class": "str",
            "def": "int",
            "normal": "bool"
        }
    }
    
    # We must access render_tree inside generate_templates_graph...
    # Actually just call _parse_template_nodes with a variable named 'class'
    from skelantic.templates.parser import LineNode, Variable
    v1 = Variable("class", "str")
    v2 = Variable("def", "int")
    line = LineNode(variables=[v1, v2])
    
    classes_out = {}
    cg._parse_template_nodes([line], "MyClass", classes_out)
    assert classes_out["MyClass"]["class"] == "str"
    assert classes_out["MyClass"]["def"] == "int"

@patch('skelantic.commons.codegen.CodeGenerator.generate')
@patch('os.makedirs')
@patch('builtins.open', new_callable=mock_open)
def test_run_codegen(mock_file, mock_makedirs, mock_generate):
    mock_generate.return_value = "fake_code"
    
    run_codegen("dummy_config.yaml", "dummy_output.py")
    
    mock_generate.assert_called_once_with("dummy_config.yaml", verbose=False)
    mock_makedirs.assert_called_once()
    mock_file.assert_called_once()
    mock_file().write.assert_called_once_with("fake_code")

def test_codegen_generate_cascading_configs():
    cg = CodeGenerator(".")
    
    with patch('skelantic.commons.config.ConfigLoader.load_config') as mock_load:
        with patch('glob.glob') as mock_glob:
            def glob_side_effect(pattern, recursive):
                if "config.yaml" in pattern:
                    return [".skelantic/config.yaml", "docs/sales/.skelantic/config.yaml"]
                return []
            mock_glob.side_effect = glob_side_effect
            
            def side_effect(path):
                if "docs/sales" in path:
                    return {"files": {"local.md": {}}, "directories": {"sub": {}}}
                return {"directories": {"docs": {}}}
                
            mock_load.side_effect = side_effect
            
            # Use generate to merge configs
            code = cg.generate(".skelantic/config.yaml")
            
            assert "class Docs(DirectoryNode):" in code
            assert "class Sales(DirectoryNode):" in code
            assert "class LocalMd(MarkdownNode):" in code
            assert "class Sub(DirectoryNode):" in code
