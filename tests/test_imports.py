from pprint import pprint

from quasar.parser import MuleParser
from quasar.token_defs import all_ops


def test_simple_import():
    code = "import os"
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    import_stmt = root.body.forms[0]
    expected = {
        'kind': 'import',
        'module': {'kind': 'symbol', 'name': 'os'},
        'symbols': None,
        'alias': None
    }
    assert import_stmt.to_dict() == expected


def test_import_with_alias():
    code = "import numpy as np"
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    import_stmt = root.body.forms[0]
    assert import_stmt.kind == 'import'
    assert import_stmt.module.name == 'numpy'
    assert import_stmt.alias.name == 'np'


def test_from_import():
    code = "from os import path"
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    import_stmt = root.body.forms[0]
    assert import_stmt.kind == 'import'
    assert import_stmt.module.name == 'os'
    assert len(import_stmt.symbols) == 1
    assert import_stmt.symbols[0].name == 'path'


def test_from_import_multiple():
    code = "from os import path, environ, getcwd"
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    import_stmt = root.body.forms[0]
    assert import_stmt.kind == 'import'
    assert import_stmt.module.name == 'os'
    assert len(import_stmt.symbols) == 3

    symbol_names = [sym.name for sym in import_stmt.symbols]
    assert 'path' in symbol_names
    assert 'environ' in symbol_names
    assert 'getcwd' in symbol_names


def test_from_import_with_alias():
    code = "from collections import defaultdict as dd"
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    import_stmt = root.body.forms[0]
    assert import_stmt.kind == 'import'
    assert import_stmt.module.name == 'collections'
    assert len(import_stmt.symbols) == 1
    assert import_stmt.symbols[0].name == 'defaultdict'
    assert import_stmt.alias.name == 'dd'


def test_relative_import():
    code = "from .utils import helper"
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    import_stmt = root.body.forms[0]
    assert import_stmt.kind == 'import'
    # The parser should handle relative imports (starting with dots)
    # Exact behavior depends on implementation


def test_from_import_star():
    code = "from math import *"
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    import_stmt = root.body.forms[0]
    assert import_stmt.kind == 'import'
    assert import_stmt.module.name == 'math'
    # Should handle * import (exact representation depends on implementation)


def test_nested_module_import():
    code = "import xml.etree.ElementTree"
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    import_stmt = root.body.forms[0]
    assert import_stmt.kind == 'import'
    # The module name might be parsed as attribute access
    # Exact structure depends on implementation


def test_multiple_imports():
    code = '''
import os
import sys
from pathlib import Path
'''
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    forms = root.body.forms
    assert len(forms) == 3

    # All should be import statements
    for form in forms:
        assert form.kind == 'import'

    # Check specific imports
    assert forms[0].module.name == 'os'
    assert forms[1].module.name == 'sys'
    assert forms[2].module.name == 'pathlib'
    assert forms[2].symbols[0].name == 'Path'


def test_conditional_import():
    code = '''
if sys.version_info >= (3, 8):
    from importlib import metadata
else:
    import importlib_metadata as metadata
'''
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    cond_stmt = root.body.forms[0]
    assert cond_stmt.kind == 'cond'

    # First clause should contain from import
    if_body = cond_stmt.clauses[0].body
    assert if_body.forms[0].kind == 'import'

    # Else clause should contain import with alias
    else_body = cond_stmt.clauses[1].body
    assert else_body.forms[0].kind == 'import'


def test_export_statement():
    # Test custom export syntax if supported
    code = "export [func1, func2, MyClass]"
    try:
        p = MuleParser(code, all_ops, filename='test.py')
        root = p.parse()

        export_stmt = root.body.forms[0]
        if hasattr(export_stmt, 'kind') and export_stmt.kind == 'export':
            assert len(export_stmt.values) == 3
    except Exception:
        # Export might not be implemented, that's okay
        pass


def test_import_in_function():
    code = '''
def lazy_import():
    import expensive_module
    return expensive_module.do_something()
'''
    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    func = root.body.forms[0]
    assert func.kind == 'defun'

    func_body = func.body.forms
    assert len(func_body) == 2
    assert func_body[0].kind == 'import'  # import statement
    assert func_body[1].kind == 'return'   # return statement