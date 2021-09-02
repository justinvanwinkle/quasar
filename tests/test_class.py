from pprint import pprint

from quasar.token_defs import all_ops
from quasar.parser import MuleParser

simple_class = """\
class MuhClass:
    pass
"""


def test_simple_class():
    p = MuleParser(simple_class, all_ops, filename='class_.py')
    root = p.parse()

    pprint(root.to_dict(), sort_dicts=False)
    expected_body = {'kind': 'body',
                     'forms': [
                         {'kind': 'class',
                          'name': {'kind': 'symbol', 'name': 'MuhClass'},
                          'bases': [],
                          'slots': [],
                          'members': [],
                          'methods': [],
                          'constructor': None}]}

    assert root.to_dict()['body'] == expected_body


class_with_method = '''\
class MuhClass:
    def foo(self):
        print('bar')
'''


def test_class_with_method():
    p = MuleParser(class_with_method, all_ops, filename='class_.py')
    root = p.parse()

    pprint(root.to_dict(), sort_dicts=False)
    expected_body = {'kind': 'body',
                     'forms': [
                         {'kind': 'class',
                          'name': {'kind': 'symbol', 'name': 'MuhClass'},
                          'bases': [],
                          'slots': [],
                          'members': [],
                          'methods': [],
                          'constructor': None}]}

    assert root.to_dict()['body'] == expected_body
