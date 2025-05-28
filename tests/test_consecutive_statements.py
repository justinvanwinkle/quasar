"""Test cases for consecutive statement parsing issues."""

from quasar.parser import MuleParser
from quasar.token_defs import all_ops


def test_assignment_followed_by_if_statement():
    """Test that assignment followed by if statement parses correctly."""
    code = """x = y
if z:
    pass
"""
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    # Should have 2 separate forms
    assert len(root.body.forms) == 2

    # First form should be assignment
    assignment = root.body.forms[0]
    assert assignment.kind == 'setf'
    assert assignment.left.name == 'x'
    assert assignment.right.name == 'y'

    # Second form should be if statement
    if_stmt = root.body.forms[1]
    assert if_stmt.kind == 'cond'
    assert if_stmt.clauses[0].condition.name == 'z'


def test_complex_assignment_followed_by_if():
    """Test complex assignment pattern from quasar.py that was failing."""
    code = """type = token_names[tokenize_token.type]
value = tokenize_token.string
if type == 'op':
    type = value
"""
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    # Should have 3 separate forms
    assert len(root.body.forms) == 3

    # First: type = token_names[tokenize_token.type]
    assignment1 = root.body.forms[0]
    assert assignment1.kind == 'setf'
    assert assignment1.left.name == 'type'

    # Second: value = tokenize_token.string
    assignment2 = root.body.forms[1]
    assert assignment2.kind == 'setf'
    assert assignment2.left.name == 'value'

    # Third: if type == 'op':
    if_stmt = root.body.forms[2]
    assert if_stmt.kind == 'cond'
    assert if_stmt.clauses[0].condition.kind == 'equal'


def test_attribute_access_followed_by_if():
    """Test attribute access assignment followed by if statement."""
    code = """result = obj.attr
if condition:
    action()
"""
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    # Should have 2 separate forms
    assert len(root.body.forms) == 2

    # First form: assignment with attribute access
    assignment = root.body.forms[0]
    assert assignment.kind == 'setf'
    assert assignment.left.name == 'result'
    assert assignment.right.kind == 'getattr'

    # Second form: if statement
    if_stmt = root.body.forms[1]
    assert if_stmt.kind == 'cond'
    assert if_stmt.clauses[0].condition.name == 'condition'


def test_multiple_consecutive_statements():
    """Test multiple consecutive statements with various patterns."""
    code = """a = 1
b = 2
if a > 0:
    c = 3
    if b > 0:
        d = 4
e = 5
"""
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    # Should have 4 top-level forms: a=1, b=2, if statement, e=5
    assert len(root.body.forms) == 4

    # Check each form
    assert root.body.forms[0].kind == 'setf'  # a = 1
    assert root.body.forms[1].kind == 'setf'  # b = 2
    assert root.body.forms[2].kind == 'cond'  # if statement
    assert root.body.forms[3].kind == 'setf'  # e = 5

    # Check the if statement has proper nested structure
    if_stmt = root.body.forms[2]
    assert len(if_stmt.clauses) == 1
    if_body = if_stmt.clauses[0].body
    assert len(if_body.forms) == 2  # c = 3 and nested if


def test_ternary_expression_should_still_work():
    """Test that legitimate ternary expressions still work correctly."""
    code = """result = x if condition else y
print(result)
"""
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    # Should have 2 forms
    assert len(root.body.forms) == 2

    # First should be assignment with ternary expression
    assignment = root.body.forms[0]
    assert assignment.kind == 'setf'
    assert assignment.right.kind == 'conditional'

    # Second should be print call
    print_call = root.body.forms[1]
    assert print_call.kind == 'call'


def test_function_definition_followed_by_if():
    """Test function definition followed by if statement."""
    code = """def func():
    return 42
if condition:
    call_func()
"""
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    # Should have 2 forms
    assert len(root.body.forms) == 2

    # First: function definition
    func_def = root.body.forms[0]
    assert func_def.kind == 'defun'
    assert func_def.name.name == 'func'

    # Second: if statement
    if_stmt = root.body.forms[1]
    assert if_stmt.kind == 'cond'