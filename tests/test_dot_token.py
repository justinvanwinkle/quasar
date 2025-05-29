"""Tests for Dot token functionality."""

import pytest
from quasar.parser import MuleParser
from quasar.token_defs import all_ops


def test_ellipsis():
    """Test ellipsis (...) parsing."""
    code = "..."
    parser = MuleParser(code, all_ops, filename='test.py')
    result = parser.parse()

    ellipsis_node = result.body.forms[0]
    assert ellipsis_node.kind == 'symbol'
    assert ellipsis_node.name == '...'
    assert ellipsis_node.py() == '...'


def test_attribute_access():
    """Test attribute access with dots."""
    code = "obj.attr"
    parser = MuleParser(code, all_ops, filename='test.py')
    result = parser.parse()

    attr_node = result.body.forms[0]
    assert attr_node.kind == 'getattr'
    assert 'obj.attr' in attr_node.py()


def test_float_numbers():
    """Test floating point number parsing."""
    test_cases = [
        ("123.456", "123.456"),
        ("0.5", "0.5"),
        ("42.0", "42.0"),
    ]

    for code, expected in test_cases:
        parser = MuleParser(code, all_ops, filename='test.py')
        result = parser.parse()
        number_node = result.body.forms[0]
        assert number_node.kind == 'number'
        assert number_node.py() == expected


def test_dot_in_from_import():
    """Test single dot in from import context."""
    code = "from . import module"
    parser = MuleParser(code, all_ops, filename='test.py')
    result = parser.parse()

    # Should parse without error
    assert result is not None
    import_node = result.body.forms[0]
    assert import_node.kind == 'import'


def test_method_chaining():
    """Test method chaining with multiple dots."""
    code = "obj.method().attr"
    parser = MuleParser(code, all_ops, filename='test.py')
    result = parser.parse()

    # Should parse without error
    assert result is not None
    py_output = result.py()
    assert 'obj.method().attr' in py_output


def test_number_formats():
    """Test various number formats."""
    test_cases = [
        "0x1a2b",  # hex
        "0o755",   # octal
        "0b1010",  # binary
        "123.456", # float
        "1e10",    # exponential
        "1.5e-3",  # exponential with decimal
    ]

    for code in test_cases:
        parser = MuleParser(code, all_ops, filename='test.py')
        result = parser.parse()
        number_node = result.body.forms[0]
        assert number_node.kind == 'number'
        assert number_node.py() == code