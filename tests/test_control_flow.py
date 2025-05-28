
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


def test_simple_if_statement():
    """Test basic if statement without else."""
    code = "if x:\n    y = 1"
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    cond = root.body.forms[0]
    assert cond.kind == 'cond'
    assert len(cond.clauses) == 1
    assert cond.clauses[0].condition.name == 'x'


def test_if_else_statement():
    """Test if-else statement."""
    code = """if x > 0:
    result = "positive"
else:
    result = "not positive"
"""
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    cond = root.body.forms[0]
    assert cond.kind == 'cond'
    assert len(cond.clauses) == 2

    # if clause
    if_clause = cond.clauses[0]
    assert if_clause.condition.kind == 'binary_op'
    assert if_clause.condition.op == '>'

    # else clause
    else_clause = cond.clauses[1]
    assert else_clause.condition.kind == 'cl_literal'
    assert else_clause.condition.literal == 't'


def test_if_elif_statement():
    """Test if-elif without final else."""
    code = """if x > 0:
    result = "positive"
elif x < 0:
    result = "negative"
"""
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    cond = root.body.forms[0]
    assert cond.kind == 'cond'
    assert len(cond.clauses) == 2

    # First clause: if x > 0
    assert cond.clauses[0].condition.op == '>'

    # Second clause: elif x < 0
    assert cond.clauses[1].condition.op == '<'


def test_multiple_elif_statements():
    """Test multiple elif clauses."""
    code = """if x == 1:
    result = "one"
elif x == 2:
    result = "two"
elif x == 3:
    result = "three"
else:
    result = "other"
"""
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    cond = root.body.forms[0]
    assert cond.kind == 'cond'
    assert len(cond.clauses) == 4

    # Check each clause condition
    assert cond.clauses[0].condition.kind == 'equal'  # x == 1
    assert cond.clauses[1].condition.kind == 'equal'  # x == 2
    assert cond.clauses[2].condition.kind == 'equal'  # x == 3
    assert cond.clauses[3].condition.kind == 'cl_literal'  # else


def test_if_with_complex_condition():
    """Test if statement with complex boolean condition."""
    code = """if x > 0 and y < 10:
    result = True
"""
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    cond = root.body.forms[0]
    assert cond.kind == 'cond'
    condition = cond.clauses[0].condition
    assert condition.kind == 'binary_op'
    assert condition.op == 'AND'


def test_if_with_comparison_chain():
    """Test if statement with comparison chain."""
    code = """if 0 < x < 10:
    result = True
"""
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    cond = root.body.forms[0]
    assert cond.kind == 'cond'
    # The exact structure depends on how chained comparisons are parsed


def test_if_with_function_call():
    """Test if statement with function call in condition."""
    code = """if is_valid(x):
    process(x)
"""
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    cond = root.body.forms[0]
    assert cond.kind == 'cond'
    condition = cond.clauses[0].condition
    assert condition.kind == 'call'
    assert condition.left.name == 'is_valid'


def test_ternary_if_expression():
    """Test ternary if expression (value if condition else other)."""
    code = """result = positive_value if x > 0 else negative_value"""

    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    assignment = root.body.forms[0]
    assert assignment.kind == 'setf'

    # The right side should be a conditional expression
    ternary = assignment.right
    assert ternary.kind == 'conditional'
    assert ternary.true_expr.name == 'positive_value'
    assert ternary.condition.kind == 'binary_op'
    assert ternary.false_expr.name == 'negative_value'


def test_nested_ternary_expressions():
    """Test nested ternary expressions."""
    code = """result = a if x > 0 else b if y > 0 else c"""

    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    assignment = root.body.forms[0]
    ternary = assignment.right
    assert ternary.kind == 'conditional'

    # The false_expr should be another conditional
    assert ternary.false_expr.kind == 'conditional'


def test_if_statement_vs_ternary_expression():
    """Test that if statements and ternary expressions are parsed differently."""

    # Regular if statement
    stmt_code = """if condition:
    x = value
"""
    p1 = MuleParser(stmt_code, all_ops, filename='test.py')
    stmt_root = p1.parse()
    stmt_form = stmt_root.body.forms[0]
    assert stmt_form.kind == 'cond'

    # Ternary expression
    expr_code = """x = value if condition else other"""
    p2 = MuleParser(expr_code, all_ops, filename='test.py')
    expr_root = p2.parse()
    expr_form = expr_root.body.forms[0]
    assert expr_form.kind == 'setf'
    assert expr_form.right.kind == 'conditional'


def test_if_with_multiline_body():
    """Test if statement with multiple statements in body."""
    code = """if x > 0:
    y = x * 2
    z = y + 1
    print(z)
"""
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    cond = root.body.forms[0]
    body = cond.clauses[0].body
    assert body.kind == 'body'
    assert len(body.forms) == 3  # Three statements in the body


def test_if_with_empty_body():
    """Test if statement with pass (empty body)."""
    code = """if condition:
    pass
else:
    action()
"""
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    cond = root.body.forms[0]
    assert len(cond.clauses) == 2

    # First clause should have pass (nil)
    pass_stmt = cond.clauses[0].body.forms[0]
    assert pass_stmt.kind == 'nil'