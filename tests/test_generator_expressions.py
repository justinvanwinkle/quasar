"""Test generator expressions and comprehensions."""

from quasar.parser import MuleParser
from quasar.token_defs import all_ops


def test_simple_generator_expression():
    """Test parsing a simple generator expression in function call."""
    code = '''
def test():
    return ', '.join(x for x in [1, 2, 3])
'''
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    # Should parse without error
    func = root.body.forms[0]
    assert func.kind == 'defun'
    assert func.name.name == 'test'

    # Check the return statement
    return_stmt = func.body.forms[0]
    assert return_stmt.kind == 'return'

    # Check the join call
    join_call = return_stmt.return_expr
    assert join_call.kind == 'call'
    assert join_call.left.kind == 'getattr'
    assert join_call.left.name == 'join'

    # Check that the generator expression is parsed correctly
    assert len(join_call.args) == 1
    generator_expr = join_call.args[0]
    assert generator_expr.kind == 'comprehension'  # New unified comprehension node


def test_generator_with_method_call():
    """Test generator expression with method calls."""
    code = '''
def fmt_args(lst):
    return ', '.join(arg.py() for arg in lst)
'''
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    # Should parse without error
    func = root.body.forms[0]
    assert func.kind == 'defun'
    assert func.name.name == 'fmt_args'


def test_list_comprehension():
    """Test list comprehension parsing."""
    code = '''
result = [x * 2 for x in items]
'''
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    # Should parse without error
    assignment = root.body.forms[0]
    assert assignment.kind == 'setf'
    assert assignment.left.name == 'result'


def test_generator_in_function_with_condition():
    """Test generator expression with condition."""
    code = '''
def filtered_items(items):
    return [item for item in items if item > 0]
'''
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    # Should parse without error
    func = root.body.forms[0]
    assert func.kind == 'defun'


def test_nested_comprehensions():
    """Test nested comprehensions."""
    code = '''
matrix = [[x * y for x in row] for row in data]
'''
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    # Should parse without error
    assignment = root.body.forms[0]
    assert assignment.kind == 'setf'


def test_multiple_generator_args():
    """Test function call with multiple generator expression arguments."""
    code = '''
result = zip(
    (x for x in list1),
    (y for y in list2)
)
'''
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    # Should parse without error
    assignment = root.body.forms[0]
    assert assignment.kind == 'setf'

    zip_call = assignment.right
    assert zip_call.kind == 'call'
    assert len(zip_call.args) == 2  # Two generator expressions


def test_dict_comprehension():
    """Test dictionary comprehension."""
    code = '''
result = {k: v for k, v in items}
'''
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    # Should parse without error
    assignment = root.body.forms[0]
    assert assignment.kind == 'setf'


def test_set_comprehension():
    """Test set comprehension."""
    code = '''
result = {x for x in items}
'''
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    # Should parse without error
    assignment = root.body.forms[0]
    assert assignment.kind == 'setf'