

from ast import NodeVisitor


class Qompile(NodeVisitor):
    def __init__(self, debug=False):
        self.debug = debug
        self.stats = {"import": [], "from": []}

    def out(self, msg):
        if self.debug:
            print(msg)

    def visit_Import(self, node):
        self.out('Import')
        for alias in node.names:
            self.stats["import"].append(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        self.out('ImportFrom')
        for alias in node.names:
            self.stats["from"].append(alias.name)
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        self.out('ClassDef')
        self.generic_visit(node)


if __name__ == '__main__':
    import argparse
    from ast import parse

    argparser = argparse.ArgumentParser(description='Python code formatter')
    argparser.add_argument('fn', help='input file')
    argparser.add_argument('-d', '--debug',
                           action='store_true',
                           help='debug output')
    args = argparser.parse_args()

    with open(args.fn) as f:
        tree = parse(f.read(), args.fn)

    qompile = Qompile(args.debug)
    qompile.visit(tree)
