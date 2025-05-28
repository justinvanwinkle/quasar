
from quasar.parser import MuleParser
from quasar.token_defs import all_ops


def test_simple_assignment():
    code = "x = 42"
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    expected = {
        'kind': 'package',
        'module_name': 'test.py',
        'body': {
            'kind': 'body',
            'forms': [{
                'kind': 'setf',
                'left': {'kind': 'symbol', 'name': 'x'},
                'right': {'kind': 'number', 'value': '42'}
            }]
        }
    }
    assert root.to_dict() == expected


def test_binary_operations():
    code = "result = a + b * c - d / e"
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    # Should parse as: result = (a + (b * c)) - (d / e)
    # Due to operator precedence: * and / before + and -
    # Left-to-right for same precedence
    assignment = root.body.forms[0]
    assert assignment.kind == 'setf'
    assert assignment.left.name == 'result'

    # Right side should be: (a + (b * c)) - (d / e)
    expr = assignment.right
    assert expr.kind == 'binary_op'
    assert expr.op == '-'


def test_function_call_with_args():
    code = "result = func(1, 2, x=3, y=4)"
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    assignment = root.body.forms[0]
    call = assignment.right

    expected_call = {
        'kind': 'call',
        'left': {'kind': 'symbol', 'name': 'func'},
        'args': [
            {'kind': 'number', 'value': '1'},
            {'kind': 'number', 'value': '2'}
        ],
        'kw_args': [
            ({'kind': 'symbol', 'name': 'x'}, {'kind': 'number', 'value': '3'}),
            ({'kind': 'symbol', 'name': 'y'}, {'kind': 'number', 'value': '4'})
        ]
    }
    assert call.to_dict() == expected_call


def test_attribute_access():
    code = "value = obj.attr.method()"
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    assignment = root.body.forms[0]
    call = assignment.right

    # Should be parsed as: ((obj.attr).method)()
    assert call.kind == 'call'
    assert call.left.kind == 'getattr'
    assert call.left.name == 'method'
    assert call.left.left.kind == 'getattr'
    assert call.left.left.name == 'attr'
    assert call.left.left.left.name == 'obj'


def test_list_indexing():
    code = "item = arr[0][key]"
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    assignment = root.body.forms[0]
    getitem = assignment.right

    # Should be parsed as: (arr[0])[key]
    assert getitem.kind == 'getitem'
    assert getitem.key.name == 'key'
    assert getitem.left.kind == 'getitem'
    assert getitem.left.key.value == '0'
    assert getitem.left.left.name == 'arr'


def test_string_literals():
    code = '''
s1 = "hello world"
s2 = 'single quotes'
s3 = """multiline
string"""
'''
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    forms = root.body.forms
    assert len(forms) == 3

    assert forms[0].right.kind == 'string'
    assert forms[0].right.value == 'hello world'

    assert forms[1].right.kind == 'string'
    assert forms[1].right.value == 'single quotes'

    assert forms[2].right.kind == 'string'
    assert forms[2].right.value == 'multiline\nstring'


def test_number_literals():
    code = '''
a = 42
b = 3.14
c = 1e5
'''
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    forms = root.body.forms
    assert len(forms) == 3

    assert forms[0].right.kind == 'number'
    assert forms[0].right.value == '42'

    assert forms[1].right.kind == 'number'
    assert forms[1].right.value == '3.14'

    assert forms[2].right.kind == 'number'
    assert forms[2].right.value == '1e5'


def test_boolean_literals():
    code = '''
a = True
b = False
c = None
'''
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    forms = root.body.forms
    assert len(forms) == 3

    # Python True/False/None should be parsed as special symbols
    assert forms[0].right.__class__.__name__ == 'PythonTrue'
    assert forms[1].right.__class__.__name__ == 'PythonFalse'
    assert forms[2].right.kind == 'nil'