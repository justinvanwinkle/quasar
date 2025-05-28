from quasar.parser import MuleParser
from quasar.token_defs import all_ops

simple_function_def = """\
def hello():
    return 'world'
"""


def test_simple_function_def():
    p = MuleParser(simple_function_def, all_ops, filename='test.py')
    root = p.parse()

    defun = root.body.forms[0]
    assert defun.kind == 'defun'
    assert defun.name.name == 'hello'
    assert len(defun.arg_names) == 0
    assert len(defun.kw_args) == 0
    assert defun.body.kind == 'body'


def test_function_with_args():
    code = """def greet(name, age):
    return f'Hello {name}, you are {age}'"""
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    defun = root.body.forms[0]
    assert defun.kind == 'defun'
    assert defun.name.name == 'greet'
    assert len(defun.arg_names) == 2
    assert defun.arg_names[0].name == 'name'
    assert defun.arg_names[1].name == 'age'
    assert len(defun.kw_args) == 0


def test_function_with_default_args():
    code = """def greet(name, age=25):
    return f'Hello {name}'"""
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    defun = root.body.forms[0]
    assert defun.kind == 'defun'
    assert defun.name.name == 'greet'
    assert len(defun.arg_names) == 1
    assert defun.arg_names[0].name == 'name'
    assert len(defun.kw_args) == 1
    assert defun.kw_args[0][0].name == 'age'
    assert defun.kw_args[0][1].value == '25'


def test_function_with_mixed_args():
    code = """def complex_func(a, b, c=10, d='default'):
    return a + b + c"""
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    defun = root.body.forms[0]
    assert defun.kind == 'defun'
    assert defun.name.name == 'complex_func'
    assert len(defun.arg_names) == 2
    assert defun.arg_names[0].name == 'a'
    assert defun.arg_names[1].name == 'b'
    assert len(defun.kw_args) == 2
    assert defun.kw_args[0][0].name == 'c'
    assert defun.kw_args[0][1].value == '10'
    assert defun.kw_args[1][0].name == 'd'
    assert defun.kw_args[1][1].value == 'default'


def test_function_with_multiline_body():
    code = """def calculate(x, y):
    result = x * y
    return result + 1"""
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    defun = root.body.forms[0]
    assert defun.kind == 'defun'
    assert defun.name.name == 'calculate'
    assert len(defun.arg_names) == 2
    assert defun.body.kind == 'body'
    assert len(defun.body.forms) == 2


def test_function_with_return_none():
    code = """def no_return():
    x = 5"""
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    defun = root.body.forms[0]
    assert defun.kind == 'defun'
    assert defun.name.name == 'no_return'
    assert defun.body.kind == 'body'


def test_function_with_explicit_return_none():
    code = """def explicit_none():
    return None"""
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    defun = root.body.forms[0]
    assert defun.kind == 'defun'
    assert defun.name.name == 'explicit_none'
    return_stmt = defun.body.forms[0]
    assert return_stmt.kind == 'return'
    assert return_stmt.return_expr.kind == 'nil'


def test_function_with_early_return():
    code = """def early_return(x):
    if x > 0:
        return x
    return 0"""
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    defun = root.body.forms[0]
    assert defun.kind == 'defun'
    assert defun.name.name == 'early_return'
    assert len(defun.body.forms) == 2


def test_nested_function():
    code = """def outer(x):
    def inner(y):
        return y * 2
    return inner(x)"""
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    outer_defun = root.body.forms[0]
    assert outer_defun.kind == 'defun'
    assert outer_defun.name.name == 'outer'

    # The inner function should be in the body
    inner_defun = outer_defun.body.forms[0]
    assert inner_defun.kind == 'defun'
    assert inner_defun.name.name == 'inner'


def test_function_with_pass():
    code = """def empty_func():
    pass"""
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    defun = root.body.forms[0]
    assert defun.kind == 'defun'
    assert defun.name.name == 'empty_func'
    pass_stmt = defun.body.forms[0]
    assert pass_stmt.kind == 'nil'


def test_function_with_docstring():
    code = '''def documented():
    """This is a docstring"""
    return True'''
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    defun = root.body.forms[0]
    assert defun.kind == 'defun'
    assert defun.name.name == 'documented'
    assert len(defun.body.forms) == 2
    docstring = defun.body.forms[0]
    assert docstring.kind == 'string'
    assert docstring.value == 'This is a docstring'


def test_function_args_with_newlines():
    code = """def func_with_newlines(
    a,
    b,
    c=10
):
    return a + b + c"""
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    defun = root.body.forms[0]
    assert defun.kind == 'defun'
    assert defun.name.name == 'func_with_newlines'
    assert len(defun.arg_names) == 2
    assert defun.arg_names[0].name == 'a'
    assert defun.arg_names[1].name == 'b'
    assert len(defun.kw_args) == 1
    assert defun.kw_args[0][0].name == 'c'
