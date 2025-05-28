from quasar.parser import MuleParser
from quasar.token_defs import all_ops


variable_annotation = """\
x :: int = 5
"""


def test_variable_annotation():
    p = MuleParser(variable_annotation, all_ops, filename='test.py')
    root = p.parse()

    assignment = root.body.forms[0]
    assert assignment.kind == 'setf'
    assert assignment.left.kind == 'type'
    assert assignment.left.left.name == 'x'
    assert assignment.left.type.name == 'int'
    assert assignment.right.value == '5'


variable_annotation_no_value = """\
name :: str
"""


def test_variable_annotation_no_value():
    p = MuleParser(variable_annotation_no_value, all_ops, filename='test.py')
    root = p.parse()

    type_annotation = root.body.forms[0]
    assert type_annotation.kind == 'type'
    assert type_annotation.left.name == 'name'
    assert type_annotation.type.name == 'str'


multiple_variable_annotations = """\
count :: int = 0
message :: str = 'hello'
flag :: bool
"""


def test_multiple_variable_annotations():
    p = MuleParser(multiple_variable_annotations, all_ops, filename='test.py')
    root = p.parse()

    # First annotation with assignment
    assignment1 = root.body.forms[0]
    assert assignment1.kind == 'setf'
    assert assignment1.left.kind == 'type'
    assert assignment1.left.left.name == 'count'
    assert assignment1.left.type.name == 'int'
    assert assignment1.right.value == '0'

    # Second annotation with assignment
    assignment2 = root.body.forms[1]
    assert assignment2.kind == 'setf'
    assert assignment2.left.kind == 'type'
    assert assignment2.left.left.name == 'message'
    assert assignment2.left.type.name == 'str'
    assert assignment2.right.value == 'hello'

    # Third annotation without assignment
    type_annotation = root.body.forms[2]
    assert type_annotation.kind == 'type'
    assert type_annotation.left.name == 'flag'
    assert type_annotation.type.name == 'bool'


complex_type_annotation = """\
data :: List
"""


def test_complex_type_annotation():
    p = MuleParser(complex_type_annotation, all_ops, filename='test.py')
    root = p.parse()

    type_annotation = root.body.forms[0]
    assert type_annotation.kind == 'type'
    assert type_annotation.left.name == 'data'
    assert type_annotation.type.name == 'List'


nested_type_context = """\
def process():
    result :: int = 42
    return result
"""


def test_nested_type_context():
    p = MuleParser(nested_type_context, all_ops, filename='test.py')
    root = p.parse()

    defun = root.body.forms[0]
    assert defun.kind == 'defun'
    assert defun.name.name == 'process'

    # Check that the type annotation is in the function body
    assignment = defun.body.forms[0]
    assert assignment.kind == 'setf'
    assert assignment.left.kind == 'type'
    assert assignment.left.left.name == 'result'
    assert assignment.left.type.name == 'int'


class_member_annotation = """\
class Person:
    name :: str = 'default'
    age :: int
"""


def test_class_member_annotation():
    p = MuleParser(class_member_annotation, all_ops, filename='test.py')
    root = p.parse()

    cls = root.body.forms[0]
    assert cls.kind == 'class'
    assert cls.name.name == 'Person'


type_annotation_with_expression = """\
result :: int = x + y * 2
"""


def test_type_annotation_with_expression():
    p = MuleParser(type_annotation_with_expression, all_ops, filename='test.py')
    root = p.parse()

    assignment = root.body.forms[0]
    assert assignment.kind == 'setf'
    assert assignment.left.kind == 'type'
    assert assignment.left.left.name == 'result'
    assert assignment.left.type.name == 'int'
    assert assignment.right.kind == 'binary_op'


type_annotation_precedence = """\
x :: int, y :: str = 1, 'hello'
"""


def test_type_annotation_precedence():
    p = MuleParser(type_annotation_precedence, all_ops, filename='test.py')
    root = p.parse()

    assignment = root.body.forms[0]
    assert assignment.kind == 'multiple_value_bind'

    # Left side should be a tuple of type annotations
    left_tuple = assignment.left
    assert left_tuple.kind == 'tuple'
    assert len(left_tuple.values) == 2

    # First type annotation
    type1 = left_tuple.values[0]
    assert type1.kind == 'type'
    assert type1.left.name == 'x'
    assert type1.type.name == 'int'

    # Second type annotation
    type2 = left_tuple.values[1]
    assert type2.kind == 'type'
    assert type2.left.name == 'y'
    assert type2.type.name == 'str'