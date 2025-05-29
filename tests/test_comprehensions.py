"""Tests for Comprehension class py() method."""

import pytest
from quasar.token_defs import Comprehension, Symbol, Number


def test_list_comprehension():
    """Test list comprehension py() method."""
    # [x for x in range(10)]
    expr = Symbol('x')
    var = Symbol('x')
    iterable = Symbol('range(10)')
    
    comp = Comprehension(expr, var, iterable, comp_type='list')
    result = comp.py()
    assert result == '[x for x in range(10)]'


def test_list_comprehension_with_condition():
    """Test list comprehension with if condition."""
    # [x for x in range(10) if x > 5]
    expr = Symbol('x')
    var = Symbol('x')
    iterable = Symbol('range(10)')
    condition = Symbol('x > 5')
    
    comp = Comprehension(expr, var, iterable, condition=condition, comp_type='list')
    result = comp.py()
    assert result == '[x for x in range(10) if x > 5]'


def test_set_comprehension():
    """Test set comprehension py() method."""
    # {x for x in range(10)}
    expr = Symbol('x')
    var = Symbol('x')
    iterable = Symbol('range(10)')
    
    comp = Comprehension(expr, var, iterable, comp_type='set')
    result = comp.py()
    assert result == '{x for x in range(10)}'


def test_set_comprehension_with_condition():
    """Test set comprehension with if condition."""
    # {x for x in range(10) if x % 2 == 0}
    expr = Symbol('x')
    var = Symbol('x')
    iterable = Symbol('range(10)')
    condition = Symbol('x % 2 == 0')
    
    comp = Comprehension(expr, var, iterable, condition=condition, comp_type='set')
    result = comp.py()
    assert result == '{x for x in range(10) if x % 2 == 0}'


def test_dict_comprehension():
    """Test dictionary comprehension py() method."""
    # {k: v for k, v in items}
    key = Symbol('k')
    value = Symbol('v')
    expr = (key, value)  # Dictionary comprehensions use tuples for key-value pairs
    var = Symbol('k, v')
    iterable = Symbol('items')
    
    comp = Comprehension(expr, var, iterable, comp_type='dict')
    result = comp.py()
    assert result == '{k: v for k, v in items}'


def test_dict_comprehension_with_condition():
    """Test dictionary comprehension with if condition."""
    # {k: v for k, v in items if k != 'skip'}
    key = Symbol('k')
    value = Symbol('v')
    expr = (key, value)
    var = Symbol('k, v')
    iterable = Symbol('items')
    condition = Symbol("k != 'skip'")
    
    comp = Comprehension(expr, var, iterable, condition=condition, comp_type='dict')
    result = comp.py()
    assert result == "{k: v for k, v in items if k != 'skip'}"


def test_generator_comprehension():
    """Test generator comprehension py() method."""
    # (x for x in range(10))
    expr = Symbol('x')
    var = Symbol('x')
    iterable = Symbol('range(10)')
    
    comp = Comprehension(expr, var, iterable, comp_type='generator')
    result = comp.py()
    assert result == '(x for x in range(10))'


def test_generator_comprehension_with_condition():
    """Test generator comprehension with if condition."""
    # (x * 2 for x in range(10) if x > 3)
    expr = Symbol('x * 2')
    var = Symbol('x')
    iterable = Symbol('range(10)')
    condition = Symbol('x > 3')
    
    comp = Comprehension(expr, var, iterable, condition=condition, comp_type='generator')
    result = comp.py()
    assert result == '(x * 2 for x in range(10) if x > 3)'


def test_comprehension_default_type():
    """Test that default comp_type is 'list'."""
    expr = Symbol('x')
    var = Symbol('x')
    iterable = Symbol('items')
    
    # Default should be list comprehension
    comp = Comprehension(expr, var, iterable)
    result = comp.py()
    assert result == '[x for x in items]'


def test_comprehension_complex_expressions():
    """Test comprehensions with complex expressions."""
    # [x.upper() for x in names if len(x) > 3]
    expr = Symbol('x.upper()')
    var = Symbol('x')
    iterable = Symbol('names')
    condition = Symbol('len(x) > 3')
    
    comp = Comprehension(expr, var, iterable, condition=condition, comp_type='list')
    result = comp.py()
    assert result == '[x.upper() for x in names if len(x) > 3]'


def test_nested_dict_comprehension():
    """Test dictionary comprehension with complex key-value pairs."""
    # {func(k): process(v) for k, v in data.items()}
    key = Symbol('func(k)')
    value = Symbol('process(v)')
    expr = (key, value)
    var = Symbol('k, v')
    iterable = Symbol('data.items()')
    
    comp = Comprehension(expr, var, iterable, comp_type='dict')
    result = comp.py()
    assert result == '{func(k): process(v) for k, v in data.items()}'


def test_comprehension_attributes():
    """Test that comprehension attributes are set correctly."""
    expr = Symbol('x')
    var = Symbol('i')
    iterable = Symbol('range(5)')
    condition = Symbol('i % 2')
    
    comp = Comprehension(expr, var, iterable, condition=condition, comp_type='set')
    
    assert comp.expr == expr
    assert comp.var == var
    assert comp.iterable == iterable
    assert comp.condition == condition
    assert comp.comp_type == 'set'
    assert comp.kind == 'comprehension'