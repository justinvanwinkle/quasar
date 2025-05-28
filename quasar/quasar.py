import tokenize
from io import StringIO
from tokenize import tok_name as token_names

from quasar.parser import MuleParser
from quasar.token_defs import all_ops

statements = {'def', 'class', 'assert'}


def tokenizer(s):
    tokenize_tokens = tokenize.generate_tokens(
        StringIO(s).readline)

    yield Token('module', '')
    for tokenize_token in tokenize_tokens:
        token = Token.from_tokenize(tokenize_token)
        print(token)
        yield token


class Token:
    def __init__(self, type, value):
        self.type = type
        self.value = value

    @classmethod
    def from_tokenize(cls, tokenize_token):
        type = token_names[tokenize_token.type]
        value = tokenize_token.string
        if type == 'op':
            type = value
        elif type == 'name' and value in statements:
            type = value
        return cls(type, tokenize_token.string)

    def __repr__(self):
        return f'Token {self.type} {self.value!r}'


class Quasar:
    def __init__(self, fn):
        self.fn = fn
        self.source = tokenize.open(fn).read()

    def parse(self):
        parser = MuleParser(self.source, all_ops, filename=self.fn)
        return parser.parse()


def main(args):
    pyfile = Quasar(args.fn)
    pyfile.parse()


if __name__ == '__main__':
    import argparse

    argparser = argparse.ArgumentParser(
        description='Python code (re)formatter')
    argparser.add_argument('fn', help='input file')
    argparser.add_argument('-d', '--debug',
                           action='store_true',
                           help='debug output')
    args = argparser.parse_args()

    main(args)
