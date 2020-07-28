from pprint import pprint

from quasar.token_defs import all_ops
from quasar.parser import MuleParser


def test_attr():
    code = "w.x.y.z = []"

    p = MuleParser(code, all_ops, filename='test.py')
    root = p.parse()

    pprint(root.to_dict(), sort_dicts=False)
    expected = {
        'kind': 'package',
        'module_name': 'test.py',
        'body': {'kind': 'body',
                 'forms': [
                     {'kind': 'setf',
                      'left': {'kind': 'getattr',
                               'name': 'z',
                               'left': {'kind': 'getattr',
                                        'name': 'y',
                                        'left': {'kind': 'getattr',
                                                 'name': 'x',
                                                 'left': {'kind': 'symbol',
                                                          'name': 'w'}}}},
                      'right': {'kind': 'list', 'values': []}}]}}

    assert root.to_dict() == expected


def test_attr_call():
    code = "foo().bar"

    p = MuleParser(code, all_ops, filename='test.py')

    root = p.parse()

    pprint(root.to_dict(), sort_dicts=False)
    print(root)

    expected = {
        'kind': 'package',
        'module_name': 'test.py',
        'body': {'kind': 'body',
                 'forms': [{'kind': 'getattr',
                            'name': 'bar',
                            'left': {'kind': 'call',
                                     'left': {'kind': 'symbol', 'name': 'foo'},
                                     'args': [],
                                     'kw_args': []}}]}}

    assert root.to_dict() == expected
