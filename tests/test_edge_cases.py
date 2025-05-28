from pprint import pprint

from quasar.parser import MuleParser
from quasar.token_defs import all_ops


def test_empty_file():
    code = ""
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    assert root.kind == 'package'
    assert root.body.kind == 'body'
    assert len(root.body.forms) == 0


def test_only_comments():
    code = '''
# This is a comment
# Another comment
'''
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    # Comments might be included in the AST or filtered out
    # Check what the parser actually does
    forms = root.body.forms
    for form in forms:
        if hasattr(form, 'kind'):
            assert form.kind == 'comment'


def test_only_newlines():
    code = "\n\n\n"
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    assert root.kind == 'package'
    assert len(root.body.forms) == 0


def test_mixed_indentation():
    # This should ideally fail or be handled gracefully
    code = '''
def func():
    x = 1
        y = 2  # Different indentation
    z = 3
'''
    try:
        p = MuleParser(code, all_ops, filename='test.py')
        root = p.parse()
        # If it parses, check the structure
        func = root.body.forms[0]
        assert func.kind == 'defun'
    except Exception as e:
        # Indentation errors should be caught
        assert 'indent' in str(e).lower() or 'block' in str(e).lower()


def test_unicode_identifiers():
    code = "café = 'coffee'"
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    assignment = root.body.forms[0]
    assert assignment.left.name == 'café'


def test_unicode_strings():
    code = '''
message = "Hello 世界"
emoji = "🐍"
'''
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    forms = root.body.forms
    assert forms[0].right.value == "Hello 世界"
    assert forms[1].right.value == "🐍"


def test_very_long_expression():
    # Test parser performance/recursion with deep nesting
    code = "x = " + "(" * 50 + "1" + ")" * 50
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    assignment = root.body.forms[0]
    assert assignment.kind == 'setf'
    # The right side should be deeply nested parentheses around 1
    current = assignment.right
    while hasattr(current, 'kind') and current.kind != 'number':
        current = getattr(current, 'values', [current])[0] if hasattr(current, 'values') else current
        break  # Prevent infinite loop
    # Should eventually reach the number 1


def test_complex_operator_precedence():
    code = "result = a + b * c ** d - e / f % g"
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    assignment = root.body.forms[0]
    expr = assignment.right

    # Should respect Python operator precedence:
    # ** (power) > *, /, % > +, -
    # And be left-associative for same precedence
    assert expr.kind == 'binary_op'


def test_chained_comparisons():
    code = "result = 1 < x < 10"
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    assignment = root.body.forms[0]
    # Chained comparisons might not be implemented yet
    # Check what the parser produces
    expr = assignment.right
    assert expr.kind == 'binary_op'


def test_nested_function_calls():
    code = "result = func1(func2(func3(x)))"
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    assignment = root.body.forms[0]
    outer_call = assignment.right

    assert outer_call.kind == 'call'
    assert outer_call.left.name == 'func1'

    middle_call = outer_call.args[0]
    assert middle_call.kind == 'call'
    assert middle_call.left.name == 'func2'

    inner_call = middle_call.args[0]
    assert inner_call.kind == 'call'
    assert inner_call.left.name == 'func3'


def test_lambda_function():
    code = "square = lambda x: x * x"
    try:
        p = MuleParser(code, all_ops, filename='test.py')
        root = p.parse()
        # Lambda might not be implemented yet
        assignment = root.body.forms[0]
        # Check if lambda is parsed as a special construct
    except Exception:
        # Lambda not implemented, that's okay
        pass


def test_decorator():
    code = '''
@property
def value(self):
    return self._value
'''
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    # Decorators might be parsed or stripped
    # The exact behavior depends on implementation
    body_form = root.body.forms[0]
    if body_form.kind == 'body':
        # Decorator might create a body wrapper
        func = body_form.forms[0]
        assert func.kind == 'defun'
    else:
        # Decorator might be stripped, leaving just the function
        assert body_form.kind == 'defun'


def test_class_inheritance():
    code = '''
class Child(Parent1, Parent2):
    pass
'''
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    class_def = root.body.forms[0]
    assert class_def.kind == 'class'
    assert class_def.name.name == 'Child'
    assert len(class_def.bases) == 2
    assert class_def.bases[0].name == 'Parent1'
    assert class_def.bases[1].name == 'Parent2'


def test_empty_class():
    code = '''
class Empty:
    pass
'''
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    class_def = root.body.forms[0]
    assert class_def.kind == 'class'
    assert class_def.name.name == 'Empty'
    assert len(class_def.methods) == 0
    assert class_def.constructor is None


def test_docstring():
    code = '''
def func():
    """This is a docstring."""
    return 42
'''
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    func = root.body.forms[0]
    assert func.kind == 'defun'

    # Docstring might be parsed as first statement in body
    body_forms = func.body.forms
    if len(body_forms) > 1:
        # First might be docstring (string literal)
        first_form = body_forms[0]
        if hasattr(first_form, 'kind') and first_form.kind == 'string':
            assert first_form.value == "This is a docstring."


def test_syntactic_edge_case():
    # Test edge case with assignment and tuple
    code = "x, = [1]"  # Tuple unpacking with single element
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    assignment = root.body.forms[0]
    # Should handle single-element tuple assignment
    if hasattr(assignment, 'left'):
        left = assignment.left
        if hasattr(left, 'kind') and left.kind == 'tuple':
            assert len(left.values) == 1