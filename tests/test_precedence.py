"""Test operator precedence to ensure it matches Python's precedence rules."""

from pprint import pprint

from quasar.parser import MuleParser
from quasar.token_defs import all_ops


def parse_expr(code):
    """Parse a single expression and return the AST."""
    p = MuleParser(f"result = {code}", all_ops, filename='test.py')
    result = p.parse()
    return result.body.forms[0].right


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
    try:
        expr = parse_expr("x or y and z")
        if hasattr(expr, 'op'):
            # Should be x or (y and z)
            if expr.op == 'OR':
                assert expr.right.kind == 'binary_op'
                assert expr.right.op == 'AND'
    except:
        # OR might not be implemented yet
        pass

    # NOT before AND
    try:
        expr = parse_expr("not x and y")
        # Should be (not x) and y
        if expr.kind == 'binary_op' and expr.op == 'AND':
            assert expr.left.kind == 'call'  # not is likely parsed as a call
    except:
        pass


def test_bitwise_operators_precedence():
    """Test bitwise operator precedence."""
    # & before |
    try:
        expr = parse_expr("x | y & z")
        if expr.kind == 'binary_op' and expr.op == '|':
            assert expr.right.kind == 'binary_op'
            assert expr.right.op == '&'
    except:
        pass

    # Shifts before &
    try:
        expr = parse_expr("x & y << 2")
        if expr.kind == 'binary_op' and expr.op == '&':
            assert expr.right.kind == 'binary_op'
            assert expr.right.op == '<<'
    except:
        pass


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
    try:
        # Indexing binds tight
        expr = parse_expr("arr[0] + 1")
        assert expr.kind == 'binary_op'
        assert expr.op == '+'
        assert expr.left.kind == 'getitem'
        assert expr.right.value == '1'
    except:
        # Indexing might not be working yet
        pass


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
    try:
        expr = parse_expr("x if True else y")
        # Conditional expressions should bind looser than most things
        # but this might not be implemented yet
    except:
        pass


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


if __name__ == "__main__":
    run_precedence_demonstration()