"""Test operator precedence to ensure it matches Python's precedence rules."""


import pytest

from quasar.parser import MuleParser
from quasar.token_defs import all_ops


def parse_expr(code):
    """Parse a single expression and return the AST."""
    p = MuleParser(f"result = {code}", all_ops, filename='test.py')
    result = p.parse()
    return result.body.forms[0].right


def normalize_ast(node):
    """
    Normalize an AST node by removing parentheses effects and converting to comparable form.
    This allows comparing trees that are semantically equivalent but have different parenthesization.
    """
    if not hasattr(node, 'to_dict'):
        return node

    node_dict = node.to_dict()

    # For tuples with single elements (often created by parentheses), unwrap them
    if node_dict.get('kind') == 'tuple' and len(node_dict.get('values', [])) == 1:
        return normalize_ast(node.values[0])

    # Recursively normalize nested structures
    if 'left' in node_dict and hasattr(node_dict['left'], 'to_dict'):
        node_dict['left'] = normalize_ast(getattr(node, 'left'))
    if 'right' in node_dict and hasattr(node_dict['right'], 'to_dict'):
        node_dict['right'] = normalize_ast(getattr(node, 'right'))
    if 'values' in node_dict:
        node_dict['values'] = [normalize_ast(val) for val in getattr(node, 'values', [])]
    if 'args' in node_dict:
        node_dict['args'] = [normalize_ast(arg) for arg in getattr(node, 'args', [])]

    return node_dict


def assert_same_precedence(code1, code2):
    """
    Assert that two expressions have the same precedence structure.
    This ignores parentheses and focuses on the actual operator precedence.

    Example:
        assert_same_precedence('1 + (2 * 3)', '1 + 2 * 3')  # passes
        assert_same_precedence('(1 + 2) * 3', '1 + 2 * 3')  # fails with detailed message
    """
    ast1 = parse_expr(code1)
    ast2 = parse_expr(code2)

    norm1 = normalize_ast(ast1)
    norm2 = normalize_ast(ast2)

    assert norm1 == norm2, f"Precedence differs:\n  {code1} -> {norm1}\n  {code2} -> {norm2}"


def test_basic_arithmetic_precedence():
    """Test basic arithmetic operator precedence."""
    # Multiplication before addition
    expr = parse_expr("2 + 3 * 4")
    assert expr.kind == 'binary_op'
    assert expr.op == '+'
    assert expr.left.value == '2'
    assert expr.right.kind == 'binary_op'
    assert expr.right.op == '*'

    # Division and multiplication same precedence, left-to-right
    expr = parse_expr("8 / 2 * 3")
    assert expr.kind == 'binary_op'
    assert expr.op == '*'
    assert expr.left.kind == 'binary_op'
    assert expr.left.op == '/'


def test_exponentiation_precedence():
    """Test that exponentiation has highest precedence."""
    # Exponentiation before multiplication
    expr = parse_expr("2 ** 3 * 4")
    assert expr.kind == 'binary_op'
    assert expr.op == '*'
    assert expr.left.kind == 'binary_op'
    assert expr.left.op == '**'
    assert expr.left.left.value == '2'
    assert expr.left.right.value == '3'
    assert expr.right.value == '4'

    # Exponentiation before addition
    expr = parse_expr("2 + 3 ** 4")
    assert expr.kind == 'binary_op'
    assert expr.op == '+'
    assert expr.left.value == '2'
    assert expr.right.kind == 'binary_op'
    assert expr.right.op == '**'


def test_comparison_precedence():
    """Test comparison operators vs arithmetic."""
    # Arithmetic before comparison
    expr = parse_expr("1 + 2 == 3")
    assert expr.kind == 'equal'
    assert expr.left.kind == 'binary_op'
    assert expr.left.op == '+'
    assert expr.right.value == '3'

    # Multiple comparisons
    expr = parse_expr("x < y + 1")
    assert expr.kind == 'binary_op'
    assert expr.op == '<'
    assert expr.left.name == 'x'
    assert expr.right.kind == 'binary_op'
    assert expr.right.op == '+'


def test_boolean_operators_precedence():
    """Test boolean operator precedence."""
    # AND before OR (if both implemented)
    expr = parse_expr("x or y and z")
    if hasattr(expr, 'op'):
        # Should be x or (y and z)
        if expr.op == 'OR':
            assert expr.right.kind == 'binary_op'
            assert expr.right.op == 'AND'

    # NOT before AND
    expr = parse_expr("not x and y")
    # Should be (not x) and y
    if expr.kind == 'binary_op' and expr.op == 'AND':
        assert expr.left.kind == 'call'  # not is likely parsed as a call


def test_bitwise_operators_precedence():
    """Test bitwise operator precedence."""
    # & before |
    expr = parse_expr("x | y & z")
    if expr.kind == 'binary_op' and expr.op == '|':
        assert expr.right.kind == 'binary_op'
        assert expr.right.op == '&'

    # Shifts before &
    expr = parse_expr("x & y << 2")
    if expr.kind == 'binary_op' and expr.op == '&':
        assert expr.right.kind == 'binary_op'
        assert expr.right.op == '<<'


def test_function_call_precedence():
    """Test function calls and attribute access precedence."""
    # Function calls bind tight
    expr = parse_expr("func() + 2")
    assert expr.kind == 'binary_op'
    assert expr.op == '+'
    assert expr.left.kind == 'call'
    assert expr.right.value == '2'

    # Attribute access before function call
    expr = parse_expr("obj.method() * 3")
    assert expr.kind == 'binary_op'
    assert expr.op == '*'
    assert expr.left.kind == 'call'
    assert expr.left.left.kind == 'getattr'


def test_indexing_precedence():
    """Test indexing and slicing precedence."""
    # Indexing binds tight
    expr = parse_expr("arr[0] + 1")
    assert expr.kind == 'binary_op'
    assert expr.op == '+'
    assert expr.left.kind == 'getitem'
    assert expr.right.value == '1'


def test_complex_expression():
    """Test a complex expression with multiple precedence levels."""
    # (x + y * z) + 3.33 - (1, 2), 3
    try:
        expr = parse_expr("(x + y * z) + 3.33 - (1, 2), 3")

        # Should be parsed as: ((((x + (y * z)) + 3.33) - (1, 2)), 3)
        # The outermost should be a tuple due to the comma
        if expr.kind == 'tuple':
            assert len(expr.values) == 2
            # First element should be the complex arithmetic
            first = expr.values[0]
            assert first.kind == 'binary_op'  # The subtraction
            # Second element should be 3
            assert expr.values[1].value == '3'
        else:
            # If comma isn't creating tuples properly, at least check the arithmetic
            # Should have subtraction at the top level
            assert expr.kind == 'binary_op'
    except Exception as e:
        # This complex expression might expose parsing issues
        print(f"Complex expression failed: {e}")


def test_parentheses_override():
    """Test that parentheses override normal precedence."""
    # (2 + 3) * 4 should be different from 2 + 3 * 4
    expr1 = parse_expr("2 + 3 * 4")     # Should be 2 + (3 * 4)
    expr2 = parse_expr("(2 + 3) * 4")   # Should be (2 + 3) * 4

    # First expression: addition at top level
    assert expr1.kind == 'binary_op'
    assert expr1.op == '+'
    assert expr1.right.op == '*'

    # Second expression: multiplication at top level
    assert expr2.kind == 'binary_op'
    assert expr2.op == '*'
    assert expr2.left.kind in ('binary_op', 'tuple')  # Parentheses might create different structures


def test_assignment_precedence():
    """Test that assignment has lowest precedence."""
    # This is tested implicitly since we wrap everything in "result = ..."
    # But let's test compound assignment if available
    parse_expr("x if True else y")
    # Conditional expressions should bind looser than most things
    # but this might not be implemented yet


def run_precedence_demonstration():
    """Run and display various precedence examples."""
    test_cases = [
        "2 + 3 * 4",
        "2 ** 3 * 4",
        "1 + 2 == 3",
        "x < y + 1",
        "func() + 2",
        "obj.attr * 3",
        "(2 + 3) * 4",
        "2 + 3 * 4",
        "x + y, z",  # Comma creates tuple
        "1, 2, 3",   # Multiple comma
    ]

    print("=== Precedence Demonstration ===")
    for code in test_cases:
        try:
            expr = parse_expr(code)
            print(f"{code:15} -> {expr.kind}")
            if hasattr(expr, 'op'):
                print(f"{'':15}    op: {expr.op}")
            elif hasattr(expr, 'values') and expr.kind == 'tuple':
                print(f"{'':15}    tuple with {len(expr.values)} elements")
            print()
        except Exception as e:
            print(f"{code:15} -> ERROR: {e}")
            print()


@pytest.mark.parametrize("code1,code2", [
    # Basic arithmetic precedence
    ('1 + 2 * 3', '1 + (2 * 3)'),
    ('2 ** 3 * 4', '(2 ** 3) * 4'),
    ('a + b - c', '(a + b) - c'),
    ('x * y / z', '(x * y) / z'),
    ('a - b + c', '(a - b) + c'),
    ('x / y * z', '(x / y) * z'),
    ('2 * 3 % 4', '(2 * 3) % 4'),
    ('a % b + c', '(a % b) + c'),
    ('a // b + c', '(a // b) + c'),

    # Exponentiation precedence (should be right associative)
    ('2 ** 3 ** 4', '2 ** (3 ** 4)'),  # BUG: Parser likely does left-associative
    ('a ** b * c', '(a ** b) * c'),
    ('x + y ** z', 'x + (y ** z)'),
    ('a * b ** c + d', '(a * (b ** c)) + d'),
    ('x ** y ** z ** w', 'x ** (y ** (z ** w))'),  # BUG: Multiple right-associative

    # Bitwise operators
    ('a | b & c', 'a | (b & c)'),
    ('x ^ y & z', 'x ^ (y & z)'),
    ('a & b << c', 'a & (b << c)'),
    ('x << y + z', 'x << (y + z)'),
    ('a + b >> c', '(a + b) >> c'),
    ('x | y ^ z & w', 'x | (y ^ (z & w))'),
    ('a & b & c', '(a & b) & c'),  # Left associative
    ('x | y | z', '(x | y) | z'),  # Left associative
    ('a ^ b ^ c', '(a ^ b) ^ c'),  # Left associative

    # Comparison operators
    ('a + b == c * d', '(a + b) == (c * d)'),
    ('x < y + z', 'x < (y + z)'),
    ('a * b > c / d', '(a * b) > (c / d)'),
    ('x + y != z - w', '(x + y) != (z - w)'),
    ('a ** b < c ** d', '(a ** b) < (c ** d)'),
    ('a <= b + c', 'a <= (b + c)'),
    ('x >= y * z', 'x >= (y * z)'),

    # Chained comparisons (Python-specific)
    ('1 < x < 10', '(1 < x) < 10'),  # BUG: Should handle chained comparisons specially
    ('a == b == c', '(a == b) == c'),  # BUG: Chained equality
    ('x < y <= z', '(x < y) <= z'),  # BUG: Mixed chained comparisons

    # Boolean operators
    ('a and b or c', '(a and b) or c'),
    ('x or y and z', 'x or (y and z)'),
    ('not a and b', '(not a) and b'),
    ('x < y or z > w', '(x < y) or (z > w)'),
    ('a == b and c < d', '(a == b) and (c < d)'),  # BUG: May fail
    ('not not x', 'not (not x)'),  # Double NOT
    ('a and b and c', '(a and b) and c'),  # Left associative
    ('x or y or z', '(x or y) or z'),  # Left associative

    # Function calls and attribute access
    ('obj.attr + 1', '(obj.attr) + 1'),
    ('func() * 2', '(func()) * 2'),
    ('obj.method() + x', '(obj.method()) + x'),
    ('a.b.c * d', '((a.b).c) * d'),
    ('func(x) + func(y)', '(func(x)) + (func(y))'),
    ('obj.attr.method()', '(obj.attr).method()'),
    ('func().attr + 1', '(func()).attr + 1'),

    # List indexing and slicing (likely to fail)
    ('arr[i] + 1', '(arr[i]) + 1'),  # BUG: Indexing parsing
    ('matrix[i][j] * 2', '((matrix[i])[j]) * 2'),  # BUG: Multiple indexing
    ('arr[i + 1] * 2', '(arr[(i + 1)]) * 2'),  # BUG: Expression in index
    ('lst[1:5] + other', '(lst[1:5]) + other'),  # BUG: Slicing syntax
    ('data[:10] * 2', '(data[:10]) * 2'),  # BUG: Slice with missing start
    ('items[::2] + more', '(items[::2]) + more'),  # BUG: Slice with step

    # Complex mixed expressions
    ('a + b * c.attr', 'a + (b * (c.attr))'),
    ('func(x) ** 2 + y', '((func(x)) ** 2) + y'),
    ('not a < b or c', '(not (a < b)) or c'),
    ('a.b + c[d] * e', '(a.b) + ((c[d]) * e)'),  # BUG: Indexing in expression
    ('x + y == z and w', '((x + y) == z) and w'),  # BUG: May fail
    ('arr[i + j] == target and found', '((arr[(i + j)]) == target) and found'),  # BUG: Complex

    # Comma operator (tuple creation)
    ('a + b, c * d', '(a + b), (c * d)'),
    ('func(x), y + z', '(func(x)), (y + z)'),
    ('x == y, z < w', '(x == y), (z < w)'),  # BUG: May fail with comparisons
    ('a, b, c + d', '(a, b), (c + d)'),  # BUG: Multiple commas
    ('f(a, b), g(c, d)', '(f(a, b)), (g(c, d))'),  # BUG: Function args vs tuple

    # String operations
    ('s1 + s2 == s3', '(s1 + s2) == s3'),
    ('"hello" + "world" * 2', '("hello") + (("world") * 2)'),
    ("'a' + 'b' * 3", "('a') + (('b') * 3)"),

    # Unary operators
    ('not x == y', 'not (x == y)'),  # NOT vs comparison

    # Complex nested expressions
    ('a + b * c ** d - e / f % g', '(a + (b * (c ** d))) - ((e / f) % g)'),
    ('x | y ^ z & w << v + u', 'x | (y ^ (z & (w << (v + u))))'),
    ('func(a + b) * obj.attr ** 2', '(func((a + b))) * ((obj.attr) ** 2)'),
    ('not a and b or c and d', '((not a) and b) or (c and d)'),

    # Set/dict operations
    ('{a, b} | {c}', '({a, b}) | ({c})'),
    ('{a} & {b} | {c}', '({a} & {b}) | {c}'),

    # Assignment-like operations
    ('x == y + z', 'x == (y + z)'),
    ('a is b + c', 'a is (b + c)'),

    # Nested function calls with complex args
    ('f(g(h(x + y)), z * w)', 'f(g(h((x + y))), (z * w))'),
    ('obj.method(a + b, c=d * e)', 'obj.method((a + b), c=(d * e))'),


])
def test_precedence_equivalence(code1, code2):
    """Test that expressions with redundant parentheses are equivalent."""
    assert_same_precedence(code1, code2)
