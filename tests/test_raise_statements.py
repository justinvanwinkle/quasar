"""Tests for raise statement functionality."""

import pytest
from quasar.parser import MuleParser
from quasar.token_defs import all_ops


def test_bare_raise():
    """Test bare raise statement."""
    code = "raise"
    parser = MuleParser(code, all_ops, filename='test.py')
    result = parser.parse()

    # Should be a raise with no exception
    raise_stmt = result.body.forms[0]
    assert raise_stmt.kind == 'raise'
    assert raise_stmt.exception is None
    assert raise_stmt.py() == 'raise'


def test_raise_with_newline():
    """Test raise followed immediately by newline."""
    code = """raise
pass"""
    parser = MuleParser(code, all_ops, filename='test.py')
    result = parser.parse()

    # Should be a bare raise
    raise_stmt = result.body.forms[0]
    assert raise_stmt.kind == 'raise'
    assert raise_stmt.exception is None
    assert raise_stmt.py() == 'raise'


def test_raise_simple_exception():
    """Test raise with simple exception class."""
    code = "raise ValueError"
    parser = MuleParser(code, all_ops, filename='test.py')
    result = parser.parse()

    raise_stmt = result.body.forms[0]
    assert raise_stmt.kind == 'raise'
    assert raise_stmt.exception is not None
    assert raise_stmt.py() == 'raise ValueError'


def test_raise_exception_with_message():
    """Test raise with exception and message."""
    code = "raise ValueError('error message')"
    parser = MuleParser(code, all_ops, filename='test.py')
    result = parser.parse()

    raise_stmt = result.body.forms[0]
    assert raise_stmt.kind == 'raise'
    assert raise_stmt.exception is not None
    # The exception should be a Call object
    assert raise_stmt.exception.kind == 'call'
    py_output = raise_stmt.py()
    assert 'raise ValueError(' in py_output
    assert "'error message'" in py_output


def test_raise_exception_with_multiple_args():
    """Test raise with exception and multiple arguments."""
    code = "raise ValueError('message', 42)"
    parser = MuleParser(code, all_ops, filename='test.py')
    result = parser.parse()

    raise_stmt = result.body.forms[0]
    assert raise_stmt.kind == 'raise'
    assert raise_stmt.exception.kind == 'call'
    py_output = raise_stmt.py()
    assert 'raise ValueError(' in py_output
    assert "'message'" in py_output
    assert '42' in py_output


def test_raise_exception_with_keyword_args():
    """Test raise with exception and keyword arguments."""
    code = "raise CustomError(message='test', code=500)"
    parser = MuleParser(code, all_ops, filename='test.py')
    result = parser.parse()

    raise_stmt = result.body.forms[0]
    assert raise_stmt.kind == 'raise'
    assert raise_stmt.exception.kind == 'call'
    py_output = raise_stmt.py()
    assert 'raise CustomError(' in py_output
    assert 'message=' in py_output
    assert 'code=' in py_output


def test_raise_mixed_args():
    """Test raise with both positional and keyword arguments."""
    code = "raise MyError('msg', code=404, debug=True)"
    parser = MuleParser(code, all_ops, filename='test.py')
    result = parser.parse()

    raise_stmt = result.body.forms[0]
    assert raise_stmt.kind == 'raise'
    py_output = raise_stmt.py()
    assert 'raise MyError(' in py_output
    assert "'msg'" in py_output
    assert 'code=404' in py_output
    assert 'debug=True' in py_output


def test_raise_with_complex_expression():
    """Test raise with complex exception expression."""
    code = "raise errors.ValidationError"
    parser = MuleParser(code, all_ops, filename='test.py')
    result = parser.parse()

    raise_stmt = result.body.forms[0]
    assert raise_stmt.kind == 'raise'
    py_output = raise_stmt.py()
    assert 'raise errors.ValidationError' in py_output


def test_raise_in_try_except():
    """Test raise statement within try/except block."""
    code = """try:
    x = 1
except:
    raise ValueError('something went wrong')"""

    parser = MuleParser(code, all_ops, filename='test.py')
    result = parser.parse()

    # Should parse without error
    assert result is not None
    py_output = result.py()
    assert 'raise ValueError(' in py_output


def test_raise_attributes():
    """Test raise statement object attributes."""
    from quasar.token_defs import Raise, Symbol, Call

    # Test bare raise
    bare_raise = Raise()
    assert bare_raise.kind == 'raise'
    assert bare_raise.exception is None
    assert bare_raise.py() == 'raise'

    # Test raise with exception
    exception = Symbol('ValueError')
    raise_with_exc = Raise(exception)
    assert raise_with_exc.kind == 'raise'
    assert raise_with_exc.exception == exception
    assert raise_with_exc.py() == 'raise ValueError'

    # Test raise with call
    call = Call(Symbol('RuntimeError'), [Symbol("'error'")])
    raise_with_call = Raise(call)
    assert raise_with_call.py() == "raise RuntimeError('error')"


def test_raise_edge_cases():
    """Test edge cases for raise statements."""
    test_cases = [
        "raise",
        "raise Exception",
        "raise Exception()",
        "raise Exception('test')",
        "raise my_module.MyError",
        "raise get_exception_class()",
    ]

    for code in test_cases:
        try:
            parser = MuleParser(code, all_ops, filename='test.py')
            result = parser.parse()
            assert result is not None
            raise_stmt = result.body.forms[0]
            assert raise_stmt.kind == 'raise'
            py_output = raise_stmt.py()
            assert py_output.startswith('raise')
        except Exception as e:
            pytest.fail(f"Failed to parse raise statement '{code}': {e}")


def test_raise_multiline_args():
    """Test raise with multiline arguments."""
    code = """raise ValueError(
    'This is a long error message',
    some_variable
)"""

    parser = MuleParser(code, all_ops, filename='test.py')
    result = parser.parse()

    raise_stmt = result.body.forms[0]
    assert raise_stmt.kind == 'raise'
    py_output = raise_stmt.py()
    assert 'raise ValueError(' in py_output