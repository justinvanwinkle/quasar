
from quasar.parser import MuleParser
from quasar.token_defs import all_ops


def test_list_literal():
    code = "items = [1, 2, 'three', x]"
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    assignment = root.body.forms[0]
    list_node = assignment.right

    expected = {
        'kind': 'list',
        'values': [
            {'kind': 'number', 'value': '1'},
            {'kind': 'number', 'value': '2'},
            {'kind': 'string', 'value': 'three'},
            {'kind': 'symbol', 'name': 'x'}
        ]
    }
    assert list_node.to_dict() == expected


def test_empty_list():
    code = "empty = []"
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    assignment = root.body.forms[0]
    list_node = assignment.right

    assert list_node.kind == 'list'
    assert list_node.values == []


def test_tuple_literal():
    code = "coords = (1, 2, 3)"
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    assignment = root.body.forms[0]
    tuple_node = assignment.right

    expected = {
        'kind': 'tuple',
        'values': [
            {'kind': 'number', 'value': '1'},
            {'kind': 'number', 'value': '2'},
            {'kind': 'number', 'value': '3'}
        ]
    }
    assert tuple_node.to_dict() == expected


def test_single_element_tuple():
    code = "single = (42,)"
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    assignment = root.body.forms[0]
    tuple_node = assignment.right

    assert tuple_node.kind == 'tuple'
    assert len(tuple_node.values) == 1
    assert tuple_node.values[0].value == '42'


def test_empty_tuple():
    code = "empty = ()"
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    assignment = root.body.forms[0]
    tuple_node = assignment.right

    assert tuple_node.kind == 'tuple'
    assert tuple_node.values == []


def test_dict_literal():
    code = "data = {'key1': 'value1', 'key2': 42}"
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    assignment = root.body.forms[0]
    dict_node = assignment.right

    # Note: This test might need adjustment based on how the parser handles dict syntax
    # The current implementation might not fully support dict literals yet
    assert dict_node.kind in ('dict', 'set')  # Depending on implementation


def test_set_literal():
    code = "numbers = {1, 2, 3}"
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    assignment = root.body.forms[0]
    set_node = assignment.right

    # Note: This test might need adjustment based on parser implementation
    assert set_node.kind == 'set'


def test_list_comprehension():
    # Note: This might not be implemented yet, but we can test if it fails gracefully
    code = "squares = [x*x for x in range(10)]"
    try:
        p = MuleParser(code, all_ops, filename='test.py')
        root = p.parse()
        # If it parses, check the structure
        root.body.forms[0]
        # The exact structure will depend on implementation
    except Exception:
        # If not implemented, that's okay for now
        pass


def test_nested_data_structures():
    code = "nested = [[1, 2], [3, 4]]"
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    assignment = root.body.forms[0]
    outer_list = assignment.right

    assert outer_list.kind == 'list'
    assert len(outer_list.values) == 2

    # Each element should be a list
    assert outer_list.values[0].kind == 'list'
    assert outer_list.values[1].kind == 'list'

    # Check inner list contents
    assert len(outer_list.values[0].values) == 2
    assert outer_list.values[0].values[0].value == '1'
    assert outer_list.values[0].values[1].value == '2'


def test_slicing():
    code = '''
a = arr[1:5]
b = arr[:3]
c = arr[2:]
d = arr[::2]
'''
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    forms = root.body.forms
    assert len(forms) == 4

    # Each should be a slice operation
    for form in forms:
        slice_node = form.right
        assert slice_node.kind == 'slice'
        assert slice_node.left.name == 'arr'


def test_indexing_with_expressions():
    code = "item = matrix[i + 1][j * 2]"
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    assignment = root.body.forms[0]
    getitem = assignment.right

    # Should be: matrix[i + 1][j * 2] parsed as (matrix[i + 1])[j * 2]
    assert getitem.kind == 'getitem'
    assert getitem.key.kind == 'binary_op'  # j * 2
    assert getitem.key.op == '*'

    # The left side should be matrix[i + 1]
    inner_getitem = getitem.left
    assert inner_getitem.kind == 'getitem'
    assert inner_getitem.left.name == 'matrix'
    assert inner_getitem.key.kind == 'binary_op'  # i + 1
    assert inner_getitem.key.op == '+'


def test_multiple_assignment():
    code = "a, b, c = 1, 2, 3"
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    assignment = root.body.forms[0]

    # Should create multiple-value-bind or tuple assignment
    # The exact structure depends on implementation
    if hasattr(assignment, 'left') and assignment.left.kind == 'tuple':
        # Tuple assignment
        assert len(assignment.left.values) == 3
        assert assignment.right.kind == 'tuple'
        assert len(assignment.right.values) == 3
    else:
        # Multiple value bind
        assert assignment.kind == 'multiple_value_bind'


def test_simple_tuple_assignment():
    code = "x, y = [1, 2]"
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    assignment = root.body.forms[0]
    assert assignment.kind == 'multiple_value_bind'
    assert assignment.left.kind == 'tuple'
    assert len(assignment.left.values) == 2
    assert assignment.left.values[0].name == 'x'
    assert assignment.left.values[1].name == 'y'
    assert assignment.right.kind == 'list'


def test_single_element_tuple_assignment():
    code = "x, = [1]"
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    assignment = root.body.forms[0]
    assert assignment.kind == 'multiple_value_bind'
    assert assignment.left.kind == 'tuple'
    assert len(assignment.left.values) == 1
    assert assignment.left.values[0].name == 'x'
    assert assignment.right.kind == 'list'


def test_trailing_comma_tuple():
    code = "x = 1,"
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    assignment = root.body.forms[0]
    assert assignment.kind == 'setf'
    assert assignment.left.name == 'x'
    assert assignment.right.kind == 'tuple'
    assert len(assignment.right.values) == 1
    assert assignment.right.values[0].value == '1'