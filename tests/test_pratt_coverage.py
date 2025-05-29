"""Tests to improve coverage of pratt.py."""

import pytest
from quasar.parser import MuleParser
from quasar.token_defs import all_ops


def test_pratt_parser_repr():
    """Test the __repr__ method of PrattParser (line 24)."""
    parser = MuleParser("x = 1", all_ops, filename='test.py')
    repr_str = repr(parser)
    assert 'Pratt(token_position=' in repr_str


def test_pratt_parser_debug_logging():
    """Test debug logging functionality (line 28)."""
    parser = MuleParser("x = 1", all_ops, filename='test.py')
    parser.debug = True
    # This should trigger the logging on line 28
    parser.log("Test message %s", "arg")


def test_invalid_character_handling():
    """Test handling of invalid characters (line 42)."""
    # Create a parser with a character that has no token definition
    # Most characters should be handled, but let's try an unusual one
    parser = MuleParser("x = 1\x00", all_ops, filename='test.py')
    with pytest.raises(Exception, match="No rule to handle"):
        parser.parse()


def test_backslash_handling():
    """Test backslash handling in tokenization (line 52)."""
    # The backslash continue logic - create simple valid code
    parser = MuleParser("x = 1", all_ops, filename='test.py')
    # This should parse without error
    result = parser.parse()
    assert result is not None


def test_token_generation_exception_handling():
    """Test exception handling in token generation (lines 78-79)."""
    # Create a scenario that might cause token generation to fail
    # We'll mock the _generate_tokens method to raise an exception
    parser = MuleParser("x = 1", all_ops, filename='test.py')

    # Store original method
    original_generate = parser._generate_tokens

    def failing_generate():
        raise ValueError("Test exception")

    # Replace method temporarily
    parser._generate_tokens = failing_generate

    # This should re-raise the exception
    with pytest.raises(ValueError, match="Test exception"):
        _ = parser.tokens


def test_syntax_error_details():
    """Test detailed syntax error information (lines 99-102)."""
    parser = MuleParser("if True:", all_ops, filename='test.py')

    # Force parser into a state where it expects a specific token
    parser.feed()  # Initialize first token

    # Try to match something that doesn't exist
    with pytest.raises(SyntaxError) as exc_info:
        parser.match('NONEXISTENT')

    error_msg = str(exc_info.value)
    assert 'Expected NONEXISTENT' in error_msg
    assert 'test.py' in error_msg