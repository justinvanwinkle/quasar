from pprint import pprint

from quasar.parser import MuleParser
from quasar.token_defs import all_ops


def test_if_statement():
    code = '''
if x > 0:
    print("positive")
'''
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    cond = root.body.forms[0]
    assert cond.kind == 'cond'
    assert len(cond.clauses) == 1

    clause = cond.clauses[0]
    assert clause.kind == 'condclause'
    assert clause.condition.kind == 'binary_op'
    assert clause.condition.op == '>'
    assert clause.body.kind == 'body'


def test_if_elif_else():
    code = '''
if x > 0:
    print("positive")
elif x < 0:
    print("negative")
else:
    print("zero")
'''
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    cond = root.body.forms[0]
    assert cond.kind == 'cond'
    assert len(cond.clauses) == 3

    # First clause: if x > 0
    assert cond.clauses[0].condition.op == '>'

    # Second clause: elif x < 0
    assert cond.clauses[1].condition.op == '<'

    # Third clause: else (should have literal 't' as condition)
    assert cond.clauses[2].condition.kind == 'cl_literal'


def test_while_loop():
    code = '''
while i < 10:
    i = i + 1
    print(i)
'''
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    while_loop = root.body.forms[0]
    assert while_loop.kind == 'while'
    assert while_loop.test.kind == 'binary_op'
    assert while_loop.test.op == '<'
    assert while_loop.body.kind == 'body'
    assert len(while_loop.body.forms) == 2


def test_for_loop():
    code = '''
for item in items:
    print(item)
'''
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    for_loop = root.body.forms[0]
    assert for_loop.kind == 'for'
    assert for_loop.in_node.kind == 'in'
    assert for_loop.in_node.thing.name == 'item'
    assert for_loop.in_node.collection.name == 'items'
    assert for_loop.body.kind == 'body'


def test_try_except():
    code = '''
try:
    risky_operation()
except ValueError as e:
    print("ValueError occurred")
except:
    print("Other error")
'''
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    try_block = root.body.forms[0]
    assert try_block.kind == 'try'
    assert try_block.try_body.kind == 'body'
    assert len(try_block.excepts) == 2

    # First except: ValueError as e
    except1 = try_block.excepts[0]
    assert except1.exception_class.name == 'ValueError'
    assert except1.exception_name.name == 'e'

    # Second except: bare except
    except2 = try_block.excepts[1]
    assert except2.exception_class is None
    assert except2.exception_name is None


def test_try_finally():
    code = '''
try:
    operation()
finally:
    cleanup()
'''
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    unwind_protect = root.body.forms[0]
    assert unwind_protect.__class__.__name__ == 'UnwindProtect'


def test_function_with_return():
    code = '''
def calculate(x):
    if x > 0:
        return x * 2
    return 0
'''
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    func = root.body.forms[0]
    assert func.kind == 'defun'
    assert func.name.name == 'calculate'

    # Body should contain if statement and return
    body_forms = func.body.forms
    assert len(body_forms) == 2
    assert body_forms[0].kind == 'cond'  # if statement
    assert body_forms[1].kind == 'return'  # return 0


def test_nested_control_flow():
    code = '''
for i in range(10):
    if i % 2 == 0:
        continue
    else:
        while i > 0:
            i = i - 1
'''
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    for_loop = root.body.forms[0]
    assert for_loop.kind == 'for'

    # Inside for loop should be an if statement
    if_stmt = for_loop.body.forms[0]
    assert if_stmt.kind == 'cond'
    assert len(if_stmt.clauses) == 2  # if and else

    # The else clause should contain a while loop
    else_clause = if_stmt.clauses[1]
    while_loop = else_clause.body.forms[0]
    assert while_loop.kind == 'while'


def test_pass_statement():
    code = '''
if True:
    pass
'''
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    cond = root.body.forms[0]
    pass_stmt = cond.clauses[0].body.forms[0]
    assert pass_stmt.kind == 'nil'