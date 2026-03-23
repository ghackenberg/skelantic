from skelantic.commons.core import tree
def test_tree_defaultdict():
    t = tree()
    t["a"]["b"] = "c"
    assert t["a"]["b"] == "c"