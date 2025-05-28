from quasar.parser import MuleParser
from quasar.token_defs import all_ops


def test_simple_assignment():
    original_code = "x = 42"

    # Parse original
    p1 = MuleParser(original_code, all_ops, filename='test.py')
    original_ast = p1.parse()

    # Generate code
    generated_code = original_ast.py()

    # Check exact string output for simple case
    assert generated_code == "x = 42\n"

    # Parse generated code
    p2 = MuleParser(generated_code, all_ops, filename='test.py')
    regenerated_ast = p2.parse()

    # Compare ASTs
    assert original_ast.to_dict() == regenerated_ast.to_dict()


def test_list_assignment():
    original_code = "items = [1, 2, 'hello', True]"

    p1 = MuleParser(original_code, all_ops, filename='test.py')
    original_ast = p1.parse()

    generated_code = original_ast.py()

    # Check exact string output for simple case
    assert generated_code == "items = [1, 2, 'hello', True]\n"

    p2 = MuleParser(generated_code, all_ops, filename='test.py')
    regenerated_ast = p2.parse()

    assert original_ast.to_dict() == regenerated_ast.to_dict()


def test_dict_assignment():
    original_code = "data = {'name': 'Alice', 'age': 30}"

    p1 = MuleParser(original_code, all_ops, filename='test.py')
    original_ast = p1.parse()

    generated_code = original_ast.py()

    # Check exact string output for simple case
    assert generated_code == "data = {'name': 'Alice', 'age': 30}\n"

    p2 = MuleParser(generated_code, all_ops, filename='test.py')
    regenerated_ast = p2.parse()

    assert original_ast.to_dict() == regenerated_ast.to_dict()


def test_simple_function():
    original_code = """def greet(name):
    return 'Hello'"""

    p1 = MuleParser(original_code, all_ops, filename='test.py')
    original_ast = p1.parse()

    generated_code = original_ast.py()

    p2 = MuleParser(generated_code, all_ops, filename='test.py')
    regenerated_ast = p2.parse()

    assert original_ast.to_dict() == regenerated_ast.to_dict()


def test_function_with_defaults():
    original_code = """def greet(name, greeting='Hello'):
    return greeting"""

    p1 = MuleParser(original_code, all_ops, filename='test.py')
    original_ast = p1.parse()

    generated_code = original_ast.py()

    p2 = MuleParser(generated_code, all_ops, filename='test.py')
    regenerated_ast = p2.parse()

    assert original_ast.to_dict() == regenerated_ast.to_dict()


def test_if_statement():
    original_code = """if x > 0:
    print('positive')
else:
    print('not positive')"""

    p1 = MuleParser(original_code, all_ops, filename='test.py')
    original_ast = p1.parse()

    generated_code = original_ast.py()

    p2 = MuleParser(generated_code, all_ops, filename='test.py')
    regenerated_ast = p2.parse()

    assert original_ast.to_dict() == regenerated_ast.to_dict()


def test_while_loop():
    original_code = """while count < 10:
    count = count + 1"""

    p1 = MuleParser(original_code, all_ops, filename='test.py')
    original_ast = p1.parse()

    generated_code = original_ast.py()

    p2 = MuleParser(generated_code, all_ops, filename='test.py')
    regenerated_ast = p2.parse()

    assert original_ast.to_dict() == regenerated_ast.to_dict()


def test_for_loop():
    original_code = """for item in items:
    print(item)"""

    p1 = MuleParser(original_code, all_ops, filename='test.py')
    original_ast = p1.parse()

    generated_code = original_ast.py()

    p2 = MuleParser(generated_code, all_ops, filename='test.py')
    regenerated_ast = p2.parse()

    assert original_ast.to_dict() == regenerated_ast.to_dict()


def test_simple_class():
    original_code = """class Person:
    def __init__(self, name):
        self.name = name

    def greet(self):
        return 'Hello'"""

    p1 = MuleParser(original_code, all_ops, filename='test.py')
    original_ast = p1.parse()

    generated_code = original_ast.py()

    p2 = MuleParser(generated_code, all_ops, filename='test.py')
    regenerated_ast = p2.parse()

    assert original_ast.to_dict() == regenerated_ast.to_dict()


def test_try_except():
    original_code = """try:
    result = risky_operation()
except ValueError as e:
    print('Error')"""

    p1 = MuleParser(original_code, all_ops, filename='test.py')
    original_ast = p1.parse()

    generated_code = original_ast.py()

    p2 = MuleParser(generated_code, all_ops, filename='test.py')
    regenerated_ast = p2.parse()

    assert original_ast.to_dict() == regenerated_ast.to_dict()


def test_import_statement():
    original_code = "import os"

    p1 = MuleParser(original_code, all_ops, filename='test.py')
    original_ast = p1.parse()

    generated_code = original_ast.py()

    # Check exact string output for simple case
    assert generated_code == "import os\n"

    p2 = MuleParser(generated_code, all_ops, filename='test.py')
    regenerated_ast = p2.parse()

    assert original_ast.to_dict() == regenerated_ast.to_dict()


def test_from_import():
    original_code = "from datetime import datetime, timedelta"

    p1 = MuleParser(original_code, all_ops, filename='test.py')
    original_ast = p1.parse()

    generated_code = original_ast.py()

    # Check exact string output for simple case
    assert generated_code == "from datetime import datetime, timedelta\n"

    p2 = MuleParser(generated_code, all_ops, filename='test.py')
    regenerated_ast = p2.parse()

    assert original_ast.to_dict() == regenerated_ast.to_dict()


def test_binary_operations():
    original_code = "result = (x + y) * (a - b)"

    p1 = MuleParser(original_code, all_ops, filename='test.py')
    original_ast = p1.parse()

    generated_code = original_ast.py()

    p2 = MuleParser(generated_code, all_ops, filename='test.py')
    regenerated_ast = p2.parse()

    assert original_ast.to_dict() == regenerated_ast.to_dict()


def test_function_call():
    original_code = "result = math.sqrt(x + y)"

    p1 = MuleParser(original_code, all_ops, filename='test.py')
    original_ast = p1.parse()

    generated_code = original_ast.py()

    p2 = MuleParser(generated_code, all_ops, filename='test.py')
    regenerated_ast = p2.parse()

    assert original_ast.to_dict() == regenerated_ast.to_dict()


def test_list_indexing():
    original_code = """first = items[0]
slice_result = items[1:5]"""

    p1 = MuleParser(original_code, all_ops, filename='test.py')
    original_ast = p1.parse()

    generated_code = original_ast.py()

    p2 = MuleParser(generated_code, all_ops, filename='test.py')
    regenerated_ast = p2.parse()

    assert original_ast.to_dict() == regenerated_ast.to_dict()


def test_conditional_expression():
    original_code = "value = x if x > 0 else 0"

    p1 = MuleParser(original_code, all_ops, filename='test.py')
    original_ast = p1.parse()

    generated_code = original_ast.py()

    p2 = MuleParser(generated_code, all_ops, filename='test.py')
    regenerated_ast = p2.parse()

    assert original_ast.to_dict() == regenerated_ast.to_dict()


def test_tuple_assignment():
    original_code = """coords = (1, 2, 3)
single = (42,)"""

    p1 = MuleParser(original_code, all_ops, filename='test.py')
    original_ast = p1.parse()

    generated_code = original_ast.py()

    p2 = MuleParser(generated_code, all_ops, filename='test.py')
    regenerated_ast = p2.parse()

    assert original_ast.to_dict() == regenerated_ast.to_dict()


def test_type_annotation():
    original_code = """x :: int = 5
name :: str"""

    p1 = MuleParser(original_code, all_ops, filename='test.py')
    original_ast = p1.parse()

    generated_code = original_ast.py()

    # Check exact string output
    expected = """x: int = 5
name: str
"""
    assert generated_code == expected

    p2 = MuleParser(generated_code, all_ops, filename='test.py')
    regenerated_ast = p2.parse()

    assert original_ast.to_dict() == regenerated_ast.to_dict()


def test_return_statement():
    original_code = """def get_value():
    return 42"""

    p1 = MuleParser(original_code, all_ops, filename='test.py')
    original_ast = p1.parse()

    generated_code = original_ast.py()

    p2 = MuleParser(generated_code, all_ops, filename='test.py')
    regenerated_ast = p2.parse()

    assert original_ast.to_dict() == regenerated_ast.to_dict()


def test_multiple_statements():
    original_code = """x = 1
y = 2
z = x + y
print(z)"""

    p1 = MuleParser(original_code, all_ops, filename='test.py')
    original_ast = p1.parse()

    generated_code = original_ast.py()

    p2 = MuleParser(generated_code, all_ops, filename='test.py')
    regenerated_ast = p2.parse()

    assert original_ast.to_dict() == regenerated_ast.to_dict()


def test_roundtrip_factorial():
    original_code = """def factorial(n):
    if n <= 1:
        return 1
    else:
        return n * factorial(n - 1)

result = factorial(5)
print(result)"""

    p1 = MuleParser(original_code, all_ops, filename='test.py')
    original_ast = p1.parse()

    generated_code = original_ast.py()

    p2 = MuleParser(generated_code, all_ops, filename='test.py')
    regenerated_ast = p2.parse()

    assert original_ast.to_dict() == regenerated_ast.to_dict()