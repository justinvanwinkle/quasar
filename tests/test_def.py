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


function_with_args = """\
def greet(name, age):
    return f'Hello {name}, you are {age}'
"""


def test_function_with_args():
    p = MuleParser(function_with_args, all_ops, filename='test.py')
    root = p.parse()

    defun = root.body.forms[0]
    assert defun.kind == 'defun'
    assert defun.name.name == 'greet'
    assert len(defun.arg_names) == 2
    assert defun.arg_names[0].name == 'name'
    assert defun.arg_names[1].name == 'age'
    assert len(defun.kw_args) == 0


function_with_default_args = """\
def greet(name, age=25):
    return f'Hello {name}'
"""


def test_function_with_default_args():
    p = MuleParser(function_with_default_args, all_ops, filename='test.py')
    root = p.parse()

    defun = root.body.forms[0]
    assert defun.kind == 'defun'
    assert defun.name.name == 'greet'
    assert len(defun.arg_names) == 1
    assert defun.arg_names[0].name == 'name'
    assert len(defun.kw_args) == 1
    assert defun.kw_args[0][0].name == 'age'
    assert defun.kw_args[0][1].value == '25'


function_with_mixed_args = """\
def complex_func(a, b, c=10, d='default'):
    return a + b + c
"""


def test_function_with_mixed_args():
    p = MuleParser(function_with_mixed_args, all_ops, filename='test.py')
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


function_with_multiline_body = """\
def calculate(x, y):
    result = x * y
    return result + 1
"""


def test_function_with_multiline_body():
    p = MuleParser(function_with_multiline_body, all_ops, filename='test.py')
    root = p.parse()

    defun = root.body.forms[0]
    assert defun.kind == 'defun'
    assert defun.name.name == 'calculate'
    assert len(defun.arg_names) == 2
    assert defun.body.kind == 'body'
    assert len(defun.body.forms) == 2


function_with_return_none = """\
def no_return():
    x = 5
"""


def test_function_with_return_none():
    p = MuleParser(function_with_return_none, all_ops, filename='test.py')
    root = p.parse()

    defun = root.body.forms[0]
    assert defun.kind == 'defun'
    assert defun.name.name == 'no_return'
    assert defun.body.kind == 'body'


function_with_explicit_return_none = """\
def explicit_none():
    return None
"""


def test_function_with_explicit_return_none():
    p = MuleParser(function_with_explicit_return_none, all_ops, filename='test.py')
    root = p.parse()

    defun = root.body.forms[0]
    assert defun.kind == 'defun'
    assert defun.name.name == 'explicit_none'
    return_stmt = defun.body.forms[0]
    assert return_stmt.kind == 'return'
    assert return_stmt.return_expr.kind == 'nil'


function_with_early_return = """\
def early_return(x):
    if x > 0:
        return x
    return 0
"""


def test_function_with_early_return():
    p = MuleParser(function_with_early_return, all_ops, filename='test.py')
    root = p.parse()

    defun = root.body.forms[0]
    assert defun.kind == 'defun'
    assert defun.name.name == 'early_return'
    assert len(defun.body.forms) == 2


nested_function = """\
def outer(x):
    def inner(y):
        return y * 2
    return inner(x)
"""


def test_nested_function():
    p = MuleParser(nested_function, all_ops, filename='test.py')
    root = p.parse()

    outer_defun = root.body.forms[0]
    assert outer_defun.kind == 'defun'
    assert outer_defun.name.name == 'outer'

    # The inner function should be in the body
    inner_defun = outer_defun.body.forms[0]
    assert inner_defun.kind == 'defun'
    assert inner_defun.name.name == 'inner'


function_with_pass = """\
def empty_func():
    pass
"""


def test_function_with_pass():
    p = MuleParser(function_with_pass, all_ops, filename='test.py')
    root = p.parse()

    defun = root.body.forms[0]
    assert defun.kind == 'defun'
    assert defun.name.name == 'empty_func'
    pass_stmt = defun.body.forms[0]
    assert pass_stmt.kind == 'nil'


function_with_docstring = """\
def documented():
    '''This is a docstring'''
    return True
"""


def test_function_with_docstring():
    p = MuleParser(function_with_docstring, all_ops, filename='test.py')
    root = p.parse()

    defun = root.body.forms[0]
    assert defun.kind == 'defun'
    assert defun.name.name == 'documented'
    assert len(defun.body.forms) == 2
    docstring = defun.body.forms[0]
    assert docstring.kind == 'string'
    assert docstring.value == 'This is a docstring'


function_args_with_newlines = """\
def func_with_newlines(a, b, c=10):
    return a + b + c
"""


def test_function_args_with_newlines():
    p = MuleParser(function_args_with_newlines, all_ops, filename='test.py')
    root = p.parse()

    defun = root.body.forms[0]
    assert defun.kind == 'defun'
    assert defun.name.name == 'func_with_newlines'
    assert len(defun.arg_names) == 2
    assert defun.arg_names[0].name == 'a'
    assert defun.arg_names[1].name == 'b'
    assert len(defun.kw_args) == 1
    assert defun.kw_args[0][0].name == 'c'