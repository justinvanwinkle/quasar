from enum import IntEnum


class Precedence(IntEnum):
    """
    Python operator precedence levels for the Pratt parser.
    Higher values = higher precedence (bind more tightly).

    Based on Python's official operator precedence:
    https://docs.python.org/3/reference/expressions.html#operator-precedence
    """
    # Parsing contexts (what level of expression to accept)
    FULL_EXPRESSION = 0      # Parse any expression, including tuple comma
    STATEMENT_LEVEL = 5      # For statement contexts (conditions, assignments) - lowest precedence
    RETURN_YIELD = 10        # For return/yield values (above assignment)
    COMMA = 15              # , (tuple creation)
    COMPREHENSION = 20      # for in comprehensions
    LAMBDA = 25             # lambda
    CONDITIONAL = 30        # if-else (ternary)
    FUNCTION_ARG = 30       # Function argument parsing
    OR = 35                 # or
    AND = 40                # and
    NOT = 50                # not
    IN_IS = 60              # in, not in, is, is not, comparisons
    BITWISE_OR = 70         # |
    NAME_CONTEXT = 80       # Traditional level for parsing names in context
    BITWISE_AND = 90        # &
    SHIFTS = 100            # << >>
    ADDITION = 110          # + -
    MULTIPLICATION = 120    # * / // %
    UNARY = 130             # +x -x ~x
    EXPONENTIATION = 140    # **
    ATTRIBUTE_CALL_INDEX = 150  # . () []
    NAME_LITERAL = 160      # Names, literals (for parsing names without consuming calls)
    TYPE_ANNOTATION = 200   # :: (type annotations)

    # Aliases for clarity
    ASSIGNMENT = STATEMENT_LEVEL  # = += -= etc.
    BITWISE_XOR = NAME_CONTEXT    # ^ (also used for name parsing)

all_ops = []


def syntax_error_with_location(message, parser=None, token=None):
    """Create a SyntaxError with line and column information."""
    if token is None and parser is not None:
        token = getattr(parser, 'token_handler', None)

    if token is not None:
        line = getattr(token, 'line', 'unknown')
        column = getattr(token, 'column', 'unknown')
    else:
        line = 'unknown'
        column = 'unknown'

    if parser is not None:
        filename = getattr(parser, 'filename', 'unknown')
    else:
        filename = 'unknown'

    return SyntaxError(f'{message} at {filename}:{line}:{column}')


def find_self_assignments(n):
    assignments = []
    if n.kind == 'body':
        for form in n.forms:
            assignments.extend(find_self_assignments(form))
    elif n.kind in ('defun', 'condclause', 'while', 'for'):
        assignments.extend(find_self_assignments(n.body))
    elif n.kind == 'setf':
        assignments.extend(find_self_assignments(n.left))
    elif n.kind == 'cond':
        for clause in n.clauses:
            assignments.extend(find_self_assignments(clause))
    elif n.kind == 'getattr':
        if hasattr(n.left, 'name') and n.left.name == 'self':
            assignments.append(n.name)

    return assignments


def unbox_arglist(t):
    args = []
    kwargs = []
    if t.kind != 'tuple':
        t = Tuple([t])
    for arg in t.values:
        if arg.kind == 'setf':
            kwargs.append((arg.left, arg.right))
        else:
            args.append(arg)

    return args, kwargs


def parse_comprehension(parser, expr, comp_type='list'):
    """
    Parse a comprehension after seeing 'expr for'.
    Returns a Comprehension node.

    Handles: expr for var in iterable [if condition]
    """
    # Parse the 'var in iterable' part
    in_node = parser.expression()

    # Extract var and iterable from the 'in' node
    if hasattr(in_node, 'kind') and in_node.kind == 'in':
        var = in_node.thing
        iterable = in_node.collection
    else:
        # Fallback - assume the in_node is the full expression
        # This might need adjustment based on how 'in' is parsed
        var = in_node  # This is probably wrong, but let's see
        iterable = None

    # Parse optional 'if condition'
    condition = None
    if parser.maybe_match('IF'):
        condition = parser.expression()

    return Comprehension(expr, var, iterable, condition, comp_type)


def register(cls):
    all_ops.append(cls)
    return cls


def fmt_args(lst):
    return ', '.join(arg.py() for arg in lst)


def fmt_kwargs(lst):
    return ', '.join(f'{name.py()}={val.py()}' for name, val in lst)


def fmt_argspec(args, kw_args):
    arg_rep = fmt_args(args)
    kw_arg_rep = fmt_kwargs(kw_args)

    if arg_rep and kw_arg_rep:
        return f'{arg_rep}, {kw_arg_rep}'
    elif arg_rep:
        return f'{arg_rep}'
    elif kw_arg_rep:
        return f'{kw_arg_rep}'
    else:
        return ''


class FSTNode:
    kind = 'node'

    def __repr__(self):
        return '<<' + repr(self.to_dict()) + '>>'


    def _convert_to_dict(self, value):
        """Recursively convert nested structures to dictionaries."""
        if hasattr(value, 'to_dict'):
            return value.to_dict()
        elif isinstance(value, list):
            return [self._convert_to_dict(item) for item in value]
        elif isinstance(value, tuple):
            return tuple(self._convert_to_dict(item) for item in value)
        else:
            return value

    def to_dict(self):
        d = {}
        d['kind'] = self.kind

        for key, value in self.__dict__.items():
            d[key] = self._convert_to_dict(value)
        return d


class PythonTrue(FSTNode):
    kind = 'symbol'

    def __init__(self):
        self.name = 'True'

    def py(self):
        return 'True'


class PythonFalse(FSTNode):
    kind = 'symbol'

    def __init__(self):
        self.name = 'False'

    def py(self):
        return 'False'


class DictLiteral(FSTNode):
    kind = 'dict'

    def __init__(self, pairs):
        self.pairs = pairs

    def py(self):
        pair_py = ', '.join(f'{key.py()}: {val.py()}' for key, val in self.pairs)
        return f'{{{pair_py}}}'


class SetLiteral(FSTNode):
    kind = 'set'

    def __init__(self, values):
        self.values = values

    def py(self):
        if not self.values:
            return 'set()'
        values_py = ', '.join(val.py() for val in self.values)
        return f'{{{values_py}}}'


class Comment(FSTNode):
    kind = 'comment'

    def __init__(self, comment):
        self.comment = comment

    def py(self):
        return f'#{self.comment}'


class Raise(FSTNode):
    kind = 'raise'

    def __init__(self, exception=None):
        self.exception = exception

    def py(self):
        if self.exception:
            return f'raise {self.exception.py()}'
        return 'raise'


class Quote(FSTNode):
    kind = 'quote'

    def __init__(self, form):
        self.form = form

    def py(self):
        return f"'{self.form.py()}'"


class PythonBody(FSTNode):
    kind = 'body'

    def __init__(self, forms):
        self.forms = forms

    def py(self, indent='    '):
        rep = ''
        for form in self.forms:
            lines = form.py().splitlines()
            for line in lines:
                rep += indent + line + '\n'
        return rep

    def to_dict(self):
        return {'kind': self.kind,
                'forms': [form.to_dict() for form in self.forms]}


class PythonModule(FSTNode):
    kind = 'package'

    def __init__(self, module_name, body):
        self.module_name = module_name
        self.body = body

    def py(self):
        return self.body.py(indent='')


class Method(FSTNode):
    kind = 'defun'

    def __init__(self, defun, class_name=None):
        self.defun = defun
        self.class_name = class_name
        self.first_arg = defun.arg_names[0]

    def py(self):
        return self.defun.py()


class CLOSClass(FSTNode):
    kind = 'class'

    def __init__(self, name, bases=(), slots=(), members=(), methods=()):
        self.name = name
        self.bases = list(bases)
        self.slots = list(slots)
        self.members = list(members)
        self.methods = list(methods)
        self.constructor = None

    def add_form(self, form):
        if form.kind == 'defun':
            if form.name.name == '__init__':
                self.constructor = form
                self.slots = find_self_assignments(form)
            else:
                self.methods.append(form)
        elif form.kind == 'decorator':
            # Check if the decorated item is a method
            if form.wrapped.kind == 'defun':
                if form.wrapped.name.name == '__init__':
                    self.constructor = form
                    self.slots = find_self_assignments(form.wrapped)
                else:
                    self.methods.append(form)
            else:
                # Non-method decorated items (rare in classes)
                self.methods.append(form)


    def py(self):
        bases_str = ''
        if self.bases:
            bases_py = ', '.join(base.py() for base in self.bases)
            bases_str = f'({bases_py})'

        class_header = f'class {self.name.py()}{bases_str}:'

        body_parts = []
        if self.constructor:
            # Indent each line of the constructor
            constructor_lines = self.constructor.py().splitlines()
            body_parts.extend('    ' + line for line in constructor_lines)

        for method in self.methods:
            # Indent each line of the method
            method_lines = method.py().splitlines()
            body_parts.extend('    ' + line for line in method_lines)

        if not body_parts:
            body_parts.append('    pass')

        body = '\n'.join(body_parts)
        return f'{class_header}\n{body}'


class Condition(CLOSClass):
    def py(self):
        # Conditions are special exception classes in Python
        bases_str = '(Exception)'
        if self.bases:
            bases_py = ', '.join(base.py() for base in self.bases)
            bases_str = f'({bases_py})'

        return f'class {self.name.py()}{bases_str}:\n    pass'


class Decorator(FSTNode):
    kind = 'decorator'

    def __init__(self, decorator_expr, wrapped):
        self.decorator_expr = decorator_expr
        self.wrapped = wrapped

    def py(self):
        return f'@{self.decorator_expr.py()}\n{self.wrapped.py()}'


class Def(FSTNode):
    kind = 'defun'

    def __init__(self, name, arg_names, kw_args, body):
        self.name = name
        self.arg_names = arg_names
        self.kw_args = kw_args
        self.body = body

    def py(self):
        args_py = fmt_args(self.arg_names)
        kwargs_py = fmt_kwargs(self.kw_args)

        params = []
        if args_py:
            params.append(args_py)
        if kwargs_py:
            params.append(kwargs_py)

        params_str = ', '.join(params)

        return f'def {self.name.py()}({params_str}):\n{self.body.py()}'


class Import(FSTNode):
    kind = 'import'

    def __init__(self, module, symbols=None, alias=None):
        self.module = module
        self.symbols = symbols
        self.alias = alias

    def py(self):
        if self.symbols:
            if len(self.symbols) == 1 and self.symbols[0].name == '*':
                import_str = f'from {self.module.py()} import *'
            else:
                symbols_py = ', '.join(sym.py() for sym in self.symbols)
                import_str = f'from {self.module.py()} import {symbols_py}'
        else:
            import_str = f'import {self.module.py()}'

        if self.alias:
            import_str += f' as {self.alias.py()}'

        return import_str


class Export(FSTNode):
    kind = 'export'

    def __init__(self, values):
        self.values = values

    def py(self):
        # Python doesn't have explicit exports, so we'll use __all__
        values_py = ', '.join(repr(val.py()) for val in self.values)
        return f'__all__ = [{values_py}]'


class ForLoop(FSTNode):
    kind = 'for'

    def __init__(self, in_node, body):
        self.in_node = in_node
        self.body = body

    def py(self):
        return f'for {self.in_node.py()}:\n{self.body.py()}'


class ConditionalExpression(FSTNode):
    kind = 'conditional'

    def __init__(self, true_expr, condition, false_expr):
        self.true_expr = true_expr
        self.condition = condition
        self.false_expr = false_expr

    def py(self):
        return f'{self.true_expr.py()} if {self.condition.py()} else {self.false_expr.py()}'


class Comprehension(FSTNode):
    kind = 'comprehension'

    def __init__(self, expr, var, iterable, condition=None, comp_type='list'):
        self.expr = expr  # The expression being generated
        self.var = var    # The variable in the for clause
        self.iterable = iterable  # What we're iterating over
        self.condition = condition  # Optional if condition
        self.comp_type = comp_type  # 'list', 'set', 'dict', 'generator'

    def py(self):
        if self.comp_type == 'dict' and isinstance(self.expr, tuple):
            # Dictionary comprehension: {k: v for ...}
            key, value = self.expr
            comprehension = f'{key.py()}: {value.py()} for {self.var.py()} in {self.iterable.py()}'
        else:
            # List, set, or generator comprehension
            comprehension = f'{self.expr.py()} for {self.var.py()} in {self.iterable.py()}'

        if self.condition:
            comprehension += f' if {self.condition.py()}'

        if self.comp_type == 'list':
            return f'[{comprehension}]'
        elif self.comp_type == 'set':
            return f'{{{comprehension}}}'
        elif self.comp_type == 'dict':
            return f'{{{comprehension}}}'
        else:  # generator
            return f'({comprehension})'


class ForExpression(FSTNode):
    kind = 'for_expression'

    def __init__(self, view, in_node, condition=None):
        self.view = view
        self.in_node = in_node
        self.condition = condition

    def py(self):
        comprehension = f'{self.view.py()} for {self.in_node.py()}'
        if self.condition:
            comprehension += f' if {self.condition.py()}'
        return f'[{comprehension}]'


class CondClause(FSTNode):
    kind = 'condclause'

    def __init__(self, condition, body):
        self.condition = condition
        self.body = body

    def py(self):
        return f'{self.condition.py()}:\n{self.body.py()}'


class Cond(FSTNode):
    kind = 'cond'

    def __init__(self, clauses):
        self.clauses = clauses

    def py(self):
        if not self.clauses:
            return ''

        result = []
        for i, clause in enumerate(self.clauses):
            if i == 0:
                result.append(f'if {clause.py()}')
            else:
                # Check if this is an 'else' clause (condition is LispLiteral 't')
                if (hasattr(clause.condition, 'literal') and clause.condition.literal == 't'):
                    # For else clause, just use the body part
                    result.append(f'else:\n{clause.body.py()}')
                else:
                    result.append(f'elif {clause.py()}')

        return '\n'.join(result)


class UnwindProtect(FSTNode):
    def __init__(self, body_form, cleanup_form):
        self.body_form = body_form
        self.cleanup_form = cleanup_form

    def py(self):
        return f'try:\n{self.body_form.py()}\nfinally:\n{self.cleanup_form.py()}'


class Try(FSTNode):
    kind = 'try'

    def __init__(self, try_body, excepts):
        self.try_body = try_body
        self.excepts = excepts

    def py(self):
        result = f'try:\n{self.try_body.py()}'
        for except_clause in self.excepts:
            result += f'\n{except_clause.py()}'
        return result


class Except(FSTNode):
    def __init__(self, body, exception_class=None, exception_name=None):
        self.exception_class = exception_class
        self.body = body
        self.exception_name = exception_name

    def py(self):
        except_line = 'except'
        if self.exception_class:
            except_line += f' {self.exception_class.py()}'
            if self.exception_name:
                except_line += f' as {self.exception_name.py()}'
        except_line += ':'
        return f'{except_line}\n{self.body.py()}'


class Return(FSTNode):
    kind = 'return'

    def __init__(self, return_expr):
        self.return_expr = return_expr

    def py(self):
        return f'return {self.return_expr.py()}'


class Yield(FSTNode):
    kind = 'yield'

    def __init__(self, return_expr):
        self.return_expr = return_expr

    def py(self):
        return f'yield {self.return_expr.py()}'


class Symbol(FSTNode):
    kind = 'symbol'

    def __init__(self, name):
        self.name = name

    def py(self):
        return self.name


class WhileLoop(FSTNode):
    kind = 'while'

    def __init__(self, test, body):
        self.test = test
        self.body = body

    def py(self):
        return f'while {self.test.py()}:\n{self.body.py()}'


class In(FSTNode):
    kind = 'in'

    def __init__(self, thing, collection):
        self.thing = thing
        self.collection = collection

    def py(self):
        return f'{self.thing.py()} in {self.collection.py()}'


class Find(In):
    kind = 'find'

    def py(self):
        return f'{self.thing.py()} in {self.collection.py()}'


class Nil(FSTNode):
    kind = 'nil'

    def py(self):
        return 'None'


class UsePackage(FSTNode):
    kind = 'use'

    def __init__(self, right):
        self.right = right

    def py(self):
        return f'# USE-PACKAGE {self.right.name}'


class List(FSTNode):
    kind = 'list'

    def __init__(self, values):
        self.values = values

    def py(self):
        values_py = ', '.join(val.py() for val in self.values)
        return f'[{values_py}]'


class GetItem(FSTNode):
    kind = 'getitem'

    def __init__(self, left, key):
        self.left = left
        self.key = key

    def py(self):
        return f'{self.left.py()}[{self.key.py()}]'


class Slice(FSTNode):
    kind = 'slice'

    def __init__(self, left, components):
        self.left = left
        self.components = components

    def py(self):
        components_py = ':'.join(comp.py() if comp else '' for comp in self.components)
        return f'{self.left.py()}[{components_py}]'


class Tuple(FSTNode):
    kind = 'tuple'

    def __init__(self, values):
        self.values = values

    def py(self):
        values_py = ', '.join(val.py() for val in self.values)
        if len(self.values) == 1:
            return f'({values_py},)'
        return f'({values_py})'


class Call(FSTNode):
    kind = 'call'

    def __init__(self, left, args=(), kw_args=()):
        self.left = left
        self.args = args
        self.kw_args = kw_args

    def py(self):
        arg_spec = fmt_argspec(self.args, self.kw_args)
        return f'{self.left.py()}({arg_spec})'


class Type(FSTNode):
    kind = 'type'

    def __init__(self, type, left):
        self.type = type
        self.left = left

    @property
    def name(self):
        return self.left.name

    def py(self):
        return f'{self.left.py()}: {self.type.py()}'


class Equality(FSTNode):
    kind = 'equal'

    def __init__(self, left, right):
        self.left = left
        self.right = right

    def py(self):
        return f'{self.left.py()} == {self.right.py()}'


class NotEquality(FSTNode):
    kind = 'equal'

    def __init__(self, left, right):
        self.left = left
        self.right = right

    def py(self):
        return f'{self.left.py()} != {self.right.py()}'


class MultipleValueBind(FSTNode):
    kind = 'multiple_value_bind'

    def __init__(self, left, right, body):
        self.left = left
        self.right = right
        self.body = body

    def py(self):
        vars_py = ', '.join(val.py() for val in self.left.values)
        return f'{vars_py} = {self.right.py()}\n{self.body.py()}'


class Setf(FSTNode):
    kind = 'setf'

    def __init__(self, left, right):
        self.left = left
        self.right = right

    def py(self):
        return f'{self.left.py()} = {self.right.py()}'


class Let(FSTNode):
    kind = 'let'

    def __init__(self, left, right, body):
        self.pairs = [(left, right)]
        self.body = body

    def py(self):
        rep = ''
        for left, right in self.pairs:
            rep += f'{left.py()} = {right.py()}\n'
        rep += self.body.py()
        return rep


class SetItem(FSTNode):
    kind = 'setitem'

    def __init__(self, left, right):
        self.left = left
        self.right = right

    def py(self):
        return f'{self.left.py()} = {self.right.py()}'


class Number(FSTNode):
    kind = 'number'

    def __init__(self, value):
        self.value = value

    def py(self):
        return self.value


class BinaryOperator(FSTNode):
    kind = 'binary_op'

    def __init__(self, op, left, right):
        self.op = op
        self.left = left
        self.right = right

    def py(self):
        return f'{self.left.py()} {self.op} {self.right.py()}'


class Parentheses(FSTNode):
    kind = 'parentheses'

    def __init__(self, expr):
        self.expr = expr

    def py(self):
        return f'({self.expr.py()})'


class AttrLookup(FSTNode):
    kind = 'getattr'

    def __init__(self, left, name):
        self.name = name.name
        self.left = left

    def py(self):
        return f'{self.left.py()}.{self.name}'


class Splat(FSTNode):
    kind = 'splat'

    def __init__(self, right):
        self.right = right


class String(FSTNode):
    kind = 'string'

    def __init__(self, value):
        self.value = value

    def py(self):
        return repr(self.value)


class FString(FSTNode):
    kind = 'fstring'

    def __init__(self, value):
        self.value = value  # Should be the full f-string like f"hello {name}"

    def py(self):
        return self.value  # Return as-is since it's already properly formatted


class LispLiteral(FSTNode):
    kind = 'cl_literal'

    def __init__(self, literal):
        self.literal = literal
        self.name = literal

    def py(self):
        return self.literal


class Token:
    name = None
    lbp = 0
    lbp_map = {}
    start_chars = set()
    rest_chars = set()

    def __init__(self, value='', line=None, column=None):
        self.value = value
        self.line = line
        self.column = column

    def spawn(self, token_class=None, name=None, lbp=None):
        if token_class is None:
            token_class = Token
        token = token_class(self.value)
        if name is not None:
            token.name = name
        if lbp is not None:
            token.lbp = lbp
        return token

    @classmethod
    def can_start(cls, c):
        return c in cls.start_chars

    def match(self, c):
        if c in self.rest_chars:
            return True
        return False

    def complete(self):
        return True

    def handle(self, c):
        self.value += c
        return self

    def nud(self, parser, value):
        line = getattr(self, 'line', 'unknown')
        column = getattr(self, 'column', 'unknown')
        filename = getattr(parser, 'filename', 'unknown')
        token_class = self.__class__.__name__
        raise NotImplementedError(f'No nud implementation for {token_class} token "{value}" at {filename}:{line}:{column}')

    def __repr__(self):
        return '( %r %s )' % (self.value, self.name)


class EnumeratedToken(Token):
    lbp_map = {}

    @classmethod
    def can_start(cls, c):
        for symbol in cls.lbp_map:
            if symbol.startswith(c):
                return True
        return False

    def match(self, c):
        for symbol in self.lbp_map:
            if symbol.startswith(self.value + c):
                return True
        return False

    def handle(self, c):
        self.value += c
        return self

    def complete(self):
        if self.value in self.lbp_map:
            self.name = self.value
            self.lbp = self.lbp_map[self.value]
            return True
        return False


@register
class NoDispatchTokens(EnumeratedToken):
    lbp_map = {
        ')': 0,
        ']': 0,
        '}': 0}

    def nud(self, parser, value):
        raise syntax_error_with_location(f'Unexpected token {value} in expression context', parser)


@register
class BinOpToken(EnumeratedToken):
    lbp_map = {
        '%': Precedence.MULTIPLICATION,
        '&': Precedence.BITWISE_AND,
        '*': Precedence.MULTIPLICATION,
        '**': Precedence.EXPONENTIATION,
        '+': Precedence.ADDITION,
        '-': Precedence.ADDITION,
        '/': Precedence.MULTIPLICATION,
        '//': Precedence.MULTIPLICATION,
        '<': Precedence.IN_IS,
        '<=': Precedence.IN_IS,
        '<<': Precedence.SHIFTS,
        '>': Precedence.IN_IS,
        '>=': Precedence.IN_IS,
        '>>': Precedence.SHIFTS,
        '^': Precedence.BITWISE_XOR,
        '|': Precedence.BITWISE_OR}

    op_map = {
        '^': 'LOGXOR',
        '%': 'MOD'}

    def led(self, parser, left):
        op = self.op_map.get(self.value, self.value)
        # Exponentiation is right-associative
        if self.value == '**':
            right_precedence = self.lbp_map[self.value] - 1
        else:
            right_precedence = self.lbp_map[self.value]
        return BinaryOperator(op,
                              left,
                              parser.expression(right_precedence))

    def nud(self, parser, value):
        if value == '*':
            return Splat(parser.expression())
        elif value == '-':
            return Call('-', [parser.expression()])
        raise Exception('Cannot get here?')


@register
class AugAssign(EnumeratedToken):
    lbp_map = {
        '%=': 0,
        '&=': 0,
        '*=': 0,
        '**=': 0,
        '+=': 0,
        '-=': 0,
        '//=': 0,
        '<<=': 0,
        '<=': 0,
        '>>=': 0,
        '>=': 0,
        '/=': 0,
        '^=': 0,
        '|=': 0}


@register
class Colon(Token):
    start_chars = {':'}
    name = ':'

    def match(self, c):
        # Only match : to create :: for type annotations
        if self.value == ':' and c == ':':
            return True
        return False

    def complete(self):
        if self.value == '::':
            self.lbp = Precedence.TYPE_ANNOTATION
            self.name = '::'
        elif self.value == ':':
            # Single colon for type annotations - must be lower than STATEMENT_LEVEL
            # so that statement parsing doesn't consume it
            self.lbp = Precedence.STATEMENT_LEVEL - 1
            self.name = ':'
        else:
            self.lbp = 0
        return True

    def nud(self, parser, value):
        return LispLiteral(value[1:])

    def led(self, parser, left):
        if self.value in (':', '::'):
            right = parser.expression(Precedence.TYPE_ANNOTATION)
            return Type(right, left)
        raise syntax_error_with_location(f'Unexpected colon token: {self.value}', parser)


@register
class AssignOrEquals(EnumeratedToken):
    lbp_map = {
        '==': Precedence.IN_IS,
        '=': Precedence.ASSIGNMENT}

    def nud(self, parser, value):
        raise syntax_error_with_location(f'Unexpected {value} at start of expression', parser)

    def led(self, parser, left):
        if self.value == '=':
            if left.kind == 'tuple':
                right = parser.expression(Precedence.STATEMENT_LEVEL)  # Assignment context
                parser.maybe_match('NEWLINE')
                parser.ns.push_new()
                for val in left.values:
                    parser.ns.add(val.name)
                mvb_node = MultipleValueBind(
                    left,
                    right,
                    PythonBody(parser.parse_rest_of_body()))
                parser.ns.pop()
                return mvb_node
            else:
                right = parser.expression(Precedence.STATEMENT_LEVEL)  # Assignment context
                # Check for ternary if expression: x if condition else y
                if parser.maybe_match('IF'):
                    condition = parser.expression(Precedence.OR)
                    parser.match('ELSE')
                    false_expr = parser.expression(Precedence.STATEMENT_LEVEL)
                    # Recursively handle nested ternary expressions
                    while parser.maybe_match('IF'):
                        nested_condition = parser.expression(Precedence.OR)
                        parser.match('ELSE')
                        nested_false_expr = parser.expression(Precedence.STATEMENT_LEVEL)
                        false_expr = ConditionalExpression(false_expr, nested_condition, nested_false_expr)
                    right = ConditionalExpression(right, condition, false_expr)
                parser.maybe_match('NEWLINE')
                parser.ns.push_new()
                parser.ns.add(left)
                return Setf(left, right)

        else:
            return Equality(left, parser.expression(self.lbp_map['==']))


@register
class NotEqual(EnumeratedToken):
    lbp_map = {'!=': Precedence.IN_IS}

    def led(self, parser, left):
        return NotEquality(left, parser.expression(self.lbp_map['!=']))


@register
class Module(Token):
    name = 'MODULE'

    def nud(self, parser, value):
        parser.ns.push_new()
        package = PythonModule(parser.filename, parser.expression())
        parser.ns.pop()
        return package


@register
class Block(Token):
    lbp = 0
    name = 'BLOCK'

    def nud(self, parser, value):
        forms = parser.parse_rest_of_body()
        parser.match('ENDBLOCK')
        return PythonBody(forms)


@register
class Endblock(Token):
    lbp = 0
    name = 'ENDBLOCK'

    def nud(self, parser, value):
        raise syntax_error_with_location('Unexpected end of block in expression context', parser)


@register
class Name(Token):
    lbp = 0
    name = 'NAME'
    start_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_')
    rest_chars = start_chars | set('0123456789')

    @classmethod
    def can_start(cls, c):
        # Check if character can start an identifier (ASCII or Unicode)
        return c in cls.start_chars or (c.isalpha() and c.isprintable())

    def match(self, c):
        # Check if character can continue an identifier
        return (c in self.rest_chars or
                (c.isalnum() and c.isprintable()) or
                c == '_')

    def complete(self):
        value = self.value
        if value == 'in':
            self.name = 'IN'
            self.lbp = Precedence.IN_IS
        elif value == 'is':
            self.name = 'IS'
            self.lbp = Precedence.IN_IS
        elif value == 'for':
            self.name = 'for'
            self.lbp = Precedence.COMPREHENSION
        elif value == 'elif':
            self.name = 'ELIF'
        elif value == 'else':
            self.name = 'ELSE'
        elif value == 'try':
            self.name = 'TRY'
        elif value == 'except':
            self.name = 'EXCEPT'
        elif value == 'finally':
            self.name = 'FINALLY'
        elif value == 'as':
            self.name = 'AS'
        elif value == 'and':
            self.name = 'AND'
            self.lbp = Precedence.AND
        elif value == 'if':
            self.name = 'IF'
            self.lbp = 0
        elif value == 'not':
            self.name = 'NOT'
            self.lbp = Precedence.NOT

        return True

    def nud(self, parser, value):
        if value == 'raise':
            if parser.maybe_match('NEWLINE'):
                return Raise()
            exception_class = parser.expression(Precedence.NAME_CONTEXT)
            if parser.maybe_match('('):
                while parser.watch(')'):
                    args = []
                    kw_args = []
                    arg_name = parser.expression(Precedence.AND)
                    if parser.maybe_match('='):
                        kw_args.append((arg_name, parser.expression(Precedence.AND)))
                    else:
                        args.append(arg_name)
                        parser.maybe_match('NEWLINE')
                        parser.maybe_match(',')
                        parser.maybe_match('NEWLINE')

            return Raise(Call(exception_class, args, kw_args))
        if value == 'try':
            parser.match(':')
            parser.ns.push_new()
            try_body = parser.expression()
            parser.ns.pop()
            finally_body = None
            excepts = []
            while parser.maybe_match('EXCEPT'):
                exc_class = None
                exc_name = None
                parser.ns.push_new()
                if not parser.maybe_match(':'):
                    exc_class = parser.expression(Precedence.NAME_CONTEXT)
                    if parser.maybe_match('AS'):
                        exc_name = parser.expression(Precedence.NAME_CONTEXT)
                    parser.match(':')
                body = parser.expression()
                excepts.append(Except(body, exc_class, exc_name))
                parser.ns.pop()
            if parser.maybe_match('FINALLY'):
                parser.ns.push_new()
                parser.match(':')
                finally_body = parser.expression()
                parser.ns.pop()

            body = try_body
            if excepts:
                body = Try(try_body, excepts)
            if finally_body:
                body = UnwindProtect(body, finally_body)
            return body
        elif value == 'import':
            module = parser.expression(Precedence.NAME_CONTEXT)
            alias = None
            if parser.maybe_match('AS'):
                alias = parser.expression(Precedence.FULL_EXPRESSION)

            return Import(module, alias=alias)

        elif value == 'from':
            relative = 0

            while parser.maybe_match('DOT'):
                relative += 1

            module = parser.expression(Precedence.NAME_CONTEXT)

            import_ = parser.match('NAME')
            assert import_.value == 'import'

            # Handle star import specially
            if parser.token_handler.name == '*':
                parser.match('*')
                values = [Symbol('*')]  # Create a symbol for star import
            else:
                seq = parser.expression()
                if seq.kind in ('symbol', 'cl_literal'):
                    values = [seq]
                else:
                    values = seq.values

            alias = None
            if parser.maybe_match('AS'):
                alias = parser.expression(Precedence.FULL_EXPRESSION)

            parser.maybe_match('NEWLINE')
            return Import(module, values, alias=alias)

        elif value == 'export':
            seq = parser.expression()
            if seq.kind in ('symbol', 'cl_literal'):
                values = [seq]
            else:
                values = seq.values
            return Export(values)
        elif value == 'load':
            return ''
        elif value == 'assert':
            return Call(Symbol('muleassert'), [parser.expression()])
        elif value == 'True':
            return PythonTrue()
        elif value == 'False':
            return PythonFalse()
        elif value == 'if':
            cond_clauses = []
            parser.ns.push_new()
            condition = parser.expression(Precedence.STATEMENT_LEVEL)  # Parse full condition
            parser.match(':')
            parser.match('NEWLINE')
            body = parser.expression()
            parser.ns.pop()
            cond_clauses.append(CondClause(condition, body))
            while parser.maybe_match('ELIF'):
                parser.ns.push_new()
                condition = parser.expression(Precedence.STATEMENT_LEVEL)  # Parse full condition
                parser.match(':')
                parser.match('NEWLINE')
                body = parser.expression()
                parser.ns.pop()
                cond_clauses.append(CondClause(condition, body))
            if parser.maybe_match('ELSE'):
                parser.ns.push_new()
                condition = LispLiteral('t')
                parser.match(':')
                parser.match('NEWLINE')
                body = parser.expression()
                parser.ns.pop()
                cond_clauses.append(CondClause(condition, body))
            return Cond(cond_clauses)

        elif value == 'pass':
            return Nil()

        elif value == 'while':
            # parser.ns.push_new()
            test = parser.expression(Precedence.STATEMENT_LEVEL)  # Parse full test condition
            parser.match(':')
            parser.match('NEWLINE')
            body = parser.expression()
            # parser.ns.pop()
            return WhileLoop(test, body)

        elif value == 'None':
            return Nil()

        elif value == 'return':
            if parser.maybe_match('NEWLINE'):
                return_expr = Nil()
            else:
                return_expr = parser.expression(Precedence.RETURN_YIELD)
            return Return(return_expr)

        elif value == 'yield':
            if parser.maybe_match('NEWLINE'):
                return_expr = Nil()
            else:
                return_expr = parser.expression(Precedence.RETURN_YIELD)
            return Yield(return_expr)

        elif value == 'class':
            name = parser.expression(Precedence.NAME_LITERAL)  # Parse just the class name
            cc = CLOSClass(name)
            if parser.maybe_match('('):
                while parser.watch(')'):
                    cc.bases.append(parser.expression(Precedence.AND))
                    parser.maybe_match(',')
            parser.match(':')
            parser.match('NEWLINE')
            parser.ns.push_new(class_top_level=True)
            body = parser.expression()
            parser.ns.pop()
            for form in body.forms:
                cc.add_form(form)
            return cc

        elif value == 'def':
            name = parser.expression(Precedence.NAME_LITERAL)
            parser.ns.push_new(return_name=name)
            parser.match('(')
            parser.maybe_match('NEWLINE')
            arg_names = []
            kw_args = []

            while parser.watch(')'):
                arg_name = parser.expression(Precedence.AND)
                if parser.maybe_match('='):
                    kw_args.append((arg_name, parser.expression(Precedence.AND)))
                else:
                    arg_names.append(arg_name)
                parser.maybe_match('NEWLINE')
                parser.maybe_match(',')
                parser.maybe_match('NEWLINE')
            parser.match(':')
            parser.match('NEWLINE')
            body = parser.expression()
            parser.ns.pop()
            defun = Def(name, arg_names, kw_args, body)
            if parser.ns.top_level or parser.ns.class_top_level:
                return defun

            parser.ns.push_new()
            parser.ns.add(defun.name)
            flet_node = defun
            parser.ns.pop()
            return flet_node
        elif value == 'for':
            in_node = parser.expression(Precedence.AND)
            parser.match(':')
            parser.match('NEWLINE')
            body = parser.expression(Precedence.STATEMENT_LEVEL)  # Parse for body
            # parser.ns.pop()
            return ForLoop(in_node, body)
        elif value == 'use':
            right = parser.expression(Precedence.RETURN_YIELD)
            return UsePackage(right)
        elif value == 'not':
            right = parser.expression(Precedence.NOT)
            return Call('NOT', [right])
        elif value == 'f' and parser.token_handler.name == 'STRING':
            # Handle f-strings: f"..." or f'...'
            string_token = parser.token_handler
            parser.feed()  # consume the string token
            # Create an f-string by prefixing the string value with 'f'
            return FString(f'f{string_token.value}')
        else:
            if value == value.upper():
                value = value.replace('_', '-')
            return Symbol(value)

    def led(self, parser, left):
        if self.value == 'in':
            return In(left, parser.expression(Precedence.IN_IS))
        elif self.value == 'is':
            return BinaryOperator('eq', left, parser.expression(Precedence.IN_IS))
        elif self.value == 'for':
            in_node = parser.expression()
            return ForExpression(left, in_node)
        elif self.value == 'and':
            return BinaryOperator('and', left, parser.expression(Precedence.AND))
        elif self.value == 'if':
            # Parse: left if condition else right
            condition = parser.expression(Precedence.OR)  # Use OR precedence for condition
            parser.match('ELSE')
            false_expr = parser.expression(Precedence.CONDITIONAL - 1)
            return ConditionalExpression(left, condition, false_expr)
        raise Exception('Cannot get here?')


@register
class LParen(Token):
    name = '('
    lbp = Precedence.ATTRIBUTE_CALL_INDEX
    start_chars = {'('}
    callable_lefts = {'getitem',
                      'getattr',
                      'symbol',
                      'call',
                      'lookup',
                      'cl_literal'}

    def led(self, parser, left):
        if left.kind in self.callable_lefts:
            parser.ns.push_new(inside_form=True)
            args = []
            kw_args = []
            while parser.watch(')'):
                arg = parser.expression(Precedence.FUNCTION_ARG)
                # Check if this is a generator expression: expr for var in iterable [if condition]
                if parser.maybe_match('for'):
                    # This is a generator expression
                    generator_expr = parse_comprehension(parser, arg, 'generator')
                    args.append(generator_expr)
                elif parser.maybe_match('='):
                    kw_args.append((arg, parser.expression(Precedence.FUNCTION_ARG)))
                else:
                    args.append(arg)
                parser.maybe_match('NEWLINE')
                parser.maybe_match(',')
                parser.maybe_match('NEWLINE')

            parser.ns.pop()
            return Call(left, args, kw_args)
        raise Exception(f'No rule to handle {left}')

    def nud(self, parser, value):
        values = []
        comma_seen = False
        while parser.watch(')'):
            # Parse with precedence higher than comma to handle it manually
            values.append(parser.expression(Precedence.COMMA + 1))
            if parser.maybe_match(','):
                comma_seen = True
        if comma_seen or not values:
            return Tuple(values)
        else:
            # Single expression in parentheses - preserve the parentheses
            return Parentheses(values[0])


@register
class LBracket(Token):
    lbp = Precedence.ATTRIBUTE_CALL_INDEX
    start_chars = {'['}
    name = '['

    def nud(self, parser, value):
        values = []
        while parser.watch(']'):
            expr = parser.expression(Precedence.FUNCTION_ARG)
            # Check if this is a comprehension: expr for var in iterable [if condition]
            if parser.maybe_match('for'):
                # This is a list comprehension
                comprehension = parse_comprehension(parser, expr, 'list')
                # Consume the closing ]
                parser.match(']')
                return comprehension
            values.append(expr)
            parser.maybe_match(',')
        return List(values)

    def led(self, parser, left):
        components = []
        is_slice = False

        # Parse the index/slice expression
        while parser.token_handler.name != ']':
            # Parse component if there is one
            if parser.token_handler.name not in (':', '::'):
                component = parser.expression(Precedence.FUNCTION_ARG)
                components.append(component)
            else:
                components.append(None)

            # Check for colon (slice indicator)
            if parser.maybe_match(':'):
                is_slice = True
                # After colon, continue to parse next component
            elif parser.maybe_match('::'):
                # :: is equivalent to two colons, so add an extra None component
                is_slice = True
                components.append(None)
                # Continue to parse step component
            else:
                # No colon, we're done
                break

        # Consume the closing ]
        parser.match(']')

        # If it's a simple index access (no colons), return GetItem
        if not is_slice and len(components) == 1 and components[0] is not None:
            return GetItem(left, components[0])
        else:
            return Slice(left, components)


@register
class LBrace(Token):
    lbp = 0   # Dict/set literals are primary expressions
    start_chars = {'{'}
    name = '{'

    def nud(self, parser, value):
        key_vals = []
        cls = 'set'
        while parser.watch('}'):
            key = parser.expression(Precedence.AND)
            if parser.maybe_match(':'):
                cls = 'dict'
                val = parser.expression(Precedence.AND)
                # Check for dict comprehension: {k: v for var in iterable}
                if parser.maybe_match('for'):
                    comprehension = parse_comprehension(parser, (key, val), 'dict')
                    parser.match('}')
                    return comprehension
            else:
                val = None
                # Check for set comprehension: {expr for var in iterable}
                if parser.maybe_match('for'):
                    comprehension = parse_comprehension(parser, key, 'set')
                    parser.match('}')
                    return comprehension
            key_vals.append((key, val))
            parser.maybe_match(',')
        if cls == 'dict':
            return DictLiteral(key_vals)
        else:
            return SetLiteral([key_val[0] for key_val in key_vals])


@register
class NumberToken(Token):
    start_chars = set('0123456789')
    rest_chars = start_chars | set('ex')
    name = 'NUMBER'

    def nud(self, parser, value):
        return Number(value)


@register
class Dot(Token):
    lbp = Precedence.ATTRIBUTE_CALL_INDEX
    start_chars = {'.'}
    name = 'DOT'

    def led(self, parser, left):
        right = parser.expression(Precedence.ATTRIBUTE_CALL_INDEX)
        if right.kind == 'number' and left.kind == 'number':
            return Number(f'{left.value}.{right.value}')
        return AttrLookup(left, right)


@register
class At(EnumeratedToken):
    lbp_map = {
        '@': 0}  # Decorators are statement-level
    name = '@'

    def nud(self, parser, value):
        decorator_call = parser.expression()
        parser.match('NEWLINE')
        wrapped = parser.expression()
        return Decorator(decorator_call, wrapped)


class EscapingToken(Token):
    def __init__(self, c='', line=None, column=None):
        super(EscapingToken, self).__init__(c, line, column)


@register
class StringToken(EscapingToken):
    start_chars = {'"', "'", "`"}
    name = 'STRING'

    def multiline(self, c=None):
        if c in self.start_chars and len(self.value) < 3:
            return True
        elif self.value.startswith(self.value[0] * 3):
            return True
        return False

    def match(self, c):
        if self.multiline(c):
            min_len, escape_pos, slice_size = (6, -4, 3)
        else:
            min_len, escape_pos, slice_size = (2, -2, 1)
        if len(self.value) < min_len:
            return True
        elif self.value[escape_pos] == '\\':
            return True
        elif self.value[:slice_size] != self.value[-slice_size:]:
            return True
        else:
            return False

    def nud(self, parser, value):
        slice_off = 1
        if self.multiline():
            slice_off = 3
        value = value[slice_off:-slice_off]
        if self.value[0] == '`':
            return LispLiteral(value)
        return String(value)


@register
class Tilde(EscapingToken):
    start_chars = {'~'}
    name = 'TILDE'

    def match(self, c):
        if self.value.endswith('\n~~'):
            return False
        return True

    def nud(self, parser, value):
        return LispLiteral(''.join(value.splitlines()[1:-1]))


@register
class Newline(Token):
    name = 'NEWLINE'
    start_chars = {'\n'}

    def nud(self, parser, value):
        return parser.expression()


@register
class Comma(Token):
    name = ','
    start_chars = ','
    lbp = Precedence.COMMA

    def led(self, parser, left):
        # This handles: left, ...
        # Could be: x, y, z  or  x,  (trailing comma)
        values = [left]

        # Check if this is a trailing comma case (followed by assignment or end)
        if parser.token_handler.name in ('=', 'ENDBLOCK', 'NEWLINE'):
            # Trailing comma case: "x, = ..." or "x = 1,"
            return Tuple(values)

        # Parse next expression for regular comma
        values.append(parser.expression(Precedence.COMMA))

        # Continue parsing comma-separated values
        while parser.maybe_match(','):
            # Check for trailing comma after each comma
            if parser.token_handler.name in ('=', 'ENDBLOCK', 'NEWLINE'):
                break
            values.append(parser.expression(Precedence.COMMA))

        return Tuple(values)


@register
class Whitespace(Token):
    name = 'WHITESPACE'
    start_chars = {' '}
    rest_chars = start_chars


@register
class CommentToken(EscapingToken):
    start_chars = {'#'}

    def match(self, c):
        if self.value[-1] == '\n':
            return False
        return True

    def nud(self, parser, value):
        return Comment(value[1:].strip())
