all_ops = []


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
        if n.left.name == 'self':
            assignments.append(n.name.name)

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


def register(cls):
    all_ops.append(cls)
    return cls


def fmt_args(lst):
    return ', '.join(arg.cl() for arg in lst)


def fmt_kwargs(lst):
    return ', '.join(f'{name}={val}' for name, val in lst)


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
        return self.cl()

    def clmap(self, forms):
        return ['%s' % x for x in forms]

    def cl(self):
        return f'NODE {self.kind}'


class PythonTrue(FSTNode):
    def cl(self):
        return '_True_'


class PythonFalse(FSTNode):
    def cl(self):
        return '_False_'


class DictLiteral(FSTNode):
    def __init__(self, pairs):
        self.pairs = pairs

    def cl(self):
        pair_cl = ', '.join(f'{key}: {val}' for key, val in self.pairs)
        return f'DictLiteral<{pair_cl}>'


class SetLiteral(FSTNode):
    def __init__(self, values):
        self.values = values

    def cl(self):
        return f'SetLiteral<{self.values}>'


class Comment(FSTNode):
    kind = 'comment'

    def __init__(self, comment):
        self.comment = comment

    def cl(self):
        return f'_#{self.comment}_'


class Raise(FSTNode):
    kind = 'raise'

    def __init__(self, exception=None):
        self.exception = exception

    def cl(self):
        return f'Raise<{self.exception}>'


class Quote(FSTNode):
    kind = 'quote'

    def __init__(self, form):
        self.form = form

    def cl(self):
        return "'%s" % self.form


class PythonBody(FSTNode):
    kind = 'body'

    def __init__(self, forms):
        self.forms = forms

    def cl(self, indent='    '):
        rep = ''
        for form in self.forms:
            lines = form.cl().splitlines()
            for line in lines:
                rep += indent + line + '\n'

        return rep


class PythonModule(FSTNode):
    kind = 'package'

    def __init__(self, module_name, body):
        self.module_name = module_name
        self.body = body

    def cl(self):
        return f'MODULE<{self.module_name}>\n' + self.body.cl(indent='')


class Method(FSTNode):
    kind = 'defun'

    def __init__(self, defun, class_name=None):
        self.defun = defun
        self.class_name = class_name
        self.first_arg = defun.arg_names[0]


    def cl(self):
        return f'Method {self.defun}'


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

    def cl_method(self, defun):
        return Method(defun, self.name)

    def cl_methods(self):
        return ' '.join(self.cl_method(defun).cl() for defun in self.methods)

    def cl_bases(self):
        return '(%s)' % ' '.join(base.cl() for base in self.bases)

    def cl_slot(self, slot):
        return '|%s|' % slot

    def cl_slots(self):
        if self.slots:
            return '(%s)' % ' '.join(self.cl_slot(slot) for slot in self.slots)
        else:
            return 'NIL'

    def cl_init_call(self):
        if not self.constructor:
            return ''
        return '(|init| |self| %s)' % self.cl_init_args()

    def cl_init_args(self):
        if self.constructor is None:
            return ''
        return self.constructor.cl_args(skip_first=True)

    def cl_constructor(self):
        if self.constructor:
            body_forms = self.constructor.body.forms
            arg_names = self.constructor.arg_names[1:]
            kw_args = self.constructor.kw_args
        else:
            body_forms = []
            arg_names = []
            kw_args = []
        forms = list(body_forms) + [Symbol('self')]
        body = Let(
            Symbol('self'),
            LispLiteral("(CL:MAKE-INSTANCE '%s)" % self.name),
            PythonBody(forms))

        defun = Def(self.name, arg_names, kw_args, PythonBody([body]))

        return "%s" % defun

    def cl(self):
        defclass = 'CLASS <%s %s %s>' % (
            self.name.cl(),
            self.cl_bases(),
            self.cl_slots())
        if self.methods:
            defclass += ' '
            defclass += self.cl_methods()
        defclass += ' '
        defclass += self.cl_constructor()

        return defclass


class Condition(CLOSClass):
    def cl(self):
        defclass = '(CL:DEFINE-CONDITION %s %s %s)' % (
            self.name.cl(),
            self.cl_bases(),
            self.cl_slots())

        return defclass


class Def(FSTNode):
    kind = 'defun'

    def __init__(self, name, arg_names, kw_args, body):
        self.name = name
        self.arg_names = arg_names
        self.kw_args = kw_args
        self.body = body

    def cl(self):
        defun = (f'Def {self.name} ({self.arg_names}, {self.kw_args})\n'
                 f'{self.body.cl()}')

        return defun


class Import(FSTNode):
    kind = 'import'

    def __init__(self, module, symbols=None, alias=None):
        self.module = module
        self.symbols = symbols
        self.alias = alias

    def cl(self):
        return (f'Import<'
                f'from={self.module}, '
                f'symbols={self.symbols}, '
                f'as={self.alias}>')


class Export(FSTNode):
    kind = 'export'

    def __init__(self, values):
        self.values = values

    def cl(self):
        return "(CL:EXPORT '(%s))" % ' '.join(self.clmap(self.values))


class ForLoop(FSTNode):
    kind = 'for'

    def __init__(self, in_node, body):
        self.in_node = in_node
        self.body = body

    def cl(self):
        return f'FOR {self.in_node}\n{self.body}'


class ForExpression(FSTNode):
    kind = 'for_expression'

    def __init__(self, view, in_node, condition=None):
        self.view = view
        self.in_node = in_node
        self.condition = condition

    def cl(self):
        return (f'ForExpression<{self.view} '
                f'FOR {self.in_node} IF {self.condition}>')


class CondClause(FSTNode):
    kind = 'condclause'

    def __init__(self, condition, body):
        self.condition = condition
        self.body = body

    def cl(self):
        return '%s:\n %s' % (self.condition, self.body)


class Cond(FSTNode):
    kind = 'cond'

    def __init__(self, clauses):
        self.clauses = clauses

    def cl(self):
        return 'if %s' % ' '.join('%s' % c for c in self.clauses)


class UnwindProtect(FSTNode):
    def __init__(self, body_form, cleanup_form):
        self.body_form = body_form
        self.cleanup_form = cleanup_form

    def cl(self):
        return '(CL:UNWIND-PROTECT %s %s)' % (
            self.body_form, self.cleanup_form)


class Try(FSTNode):
    def __init__(self, try_body, excepts):
        self.try_body = try_body
        self.excepts = excepts

    def cl(self):
        return 'Try:\n%s \n%s' % (
            self.try_body.cl(),
            '\n'.join(self.clmap(self.excepts)))


class Except(FSTNode):
    def __init__(self, body, exception_class=None, exception_name=None):
        self.exception_class = exception_class
        self.body = body
        self.exception_name = exception_name

    def cl(self):
        return (f'Except<{self.exception_class}>'
                f'[AS={self.exception_name}]\n{self.body}')


class Return(FSTNode):
    kind = 'return'

    def __init__(self, return_expr):
        self.return_expr = return_expr

    def cl(self):
        return f'Return<{self.return_expr}>'


class Yield(FSTNode):
    kind = 'yield'

    def __init__(self, return_expr):
        self.return_expr = return_expr

    def cl(self):
        return f'Yield<{self.return_expr}>'


class Symbol(FSTNode):
    kind = 'symbol'

    def __init__(self, name):
        self.name = name

    def cl(self):
        return f'Name<{self.name}>'


class WhileLoop(FSTNode):
    kind = 'while'

    def __init__(self, test, body):
        self.test = test
        self.body = body

    def cl(self):
        return f'While<{self.test.cl()}>\n' + self.body.cl()


class In(FSTNode):
    kind = 'in'

    def __init__(self, thing, collection):
        self.thing = thing
        self.collection = collection

    def cl(self):
        return '%s in %s' % (self.thing, self.collection)


class Find(In):
    kind = 'find'

    def cl(self):
        return '(find %s %s)' % (self.thing, self.collection)


class Nil(FSTNode):
    kind = 'nil'

    def cl(self):
        return 'NIL'


class UsePackage(FSTNode):
    kind = 'use'

    def __init__(self, right):
        self.right = right

    def cl(self):
        return '(CL:USE-PACKAGE "%s")' % self.right.name


class List(FSTNode):
    kind = 'list'

    def __init__(self, values):
        self.values = values

    def cl(self):
        return f"List{self.values}"


class GetItem(FSTNode):
    kind = 'getitem'

    def __init__(self, left, key):
        self.left = left
        self.key = key

    def cl(self):
        return f'GetItem<{self.left}>[{self.key}]'


class Slice(FSTNode):
    kind = 'slice'

    def __init__(self, left, components):
        self.left = left
        self.components = components

    def cl(self):
        return '[%s]' % ':'.join(self.components)


class Tuple(FSTNode):
    kind = 'tuple'

    def __init__(self, values):
        self.values = values

    def cl(self):
        return "(%s,)" % ', '.join(self.clmap(self.values))


class Call(FSTNode):
    kind = 'call'

    def __init__(self, left, args=(), kw_args=()):
        self.left = left
        self.args = args
        self.kw_args = kw_args

    def cl(self):
        arg_spec = fmt_argspec(self.args, self.kw_args)
        return f'Call<{self.left}>({arg_spec})'


class Type(FSTNode):
    kind = 'type'

    def __init__(self, type, left):
        self.type = type
        self.left = left

    @property
    def name(self):
        return self.left.name

    def cl(self):
        return '(the %s %s)' % (self.type, self.left)

    def of_type_cl(self):
        return '%s of-type %s' % (self.left, self.type)


class Equality(FSTNode):
    kind = 'equal'

    def __init__(self, left, right):
        self.left = left
        self.right = right

    def cl(self):
        return '%s == %s' % (self.left.cl(), self.right.cl())


class NotEquality(FSTNode):
    kind = 'equal'

    def __init__(self, left, right):
        self.left = left
        self.right = right

    def cl(self):
        return '(CL:NOT (|__eq__| %s %s))' % (self.left.cl(), self.right.cl())


class MultipleValueBind(FSTNode):
    kind = 'multiple_value_bind'

    def __init__(self, left, right, body):
        self.left = left
        self.right = right
        self.body = body

    def cl(self):
        return '(CL:MULTIPLE-VALUE-BIND (%s) %s %s)' % (
            ' '. join(self.clmap(self.left.values)),
            self.right,
            self.body.cl())


class Setf(FSTNode):
    kind = 'setf'

    def __init__(self, left, right):
        self.left = left
        self.right = right

    def cl(self):
        return f'ASSIGN {self.left} = {self.right}'


class Let(FSTNode):
    kind = 'let'

    def __init__(self, left, right, body):
        self.pairs = [(left, right)]
        self.body = body

    def cl(self):
        rep = ''
        for left, right in self.pairs:
            rep += f'ASSIGN {left} = {right}\n'
        rep += self.body.cl()
        return rep


class SetItem(FSTNode):
    kind = 'setitem'

    def __init__(self, left, right):
        self.left = left
        self.right = right

    def cl(self):
        return f'SET_ITEM {self.left} = {self.right}'


class Number(FSTNode):
    kind = 'number'

    def __init__(self, value):
        self.value = value

    def cl(self):
        return f'NUMBER<{self.value!r}>'


class BinaryOperator(FSTNode):
    kind = 'binary_op'

    def __init__(self, op, left, right):
        self.op = op
        self.left = left
        self.right = right

    def cl(self):
        return f'({self.left} {self.op} {self.right})'



class AttrLookup(FSTNode):
    kind = 'getattr'

    def __init__(self, left, name):
        self.left = left
        self.name = name

    def cl(self):
        return f"AttrLookup<{self.left}.{self.name}>"


class Splat(FSTNode):
    kind = 'splat'

    def __init__(self, right):
        self.right = right


class String(FSTNode):
    kind = 'string'

    def __init__(self, value):
        self.value = value

    def cl(self):
        return f'{self.value!r}'


class LispLiteral(FSTNode):
    kind = 'cl_literal'

    def __init__(self, literal):
        self.literal = literal
        self.name = literal

    def cl(self):
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


@register
class BinOpToken(EnumeratedToken):
    lbp_map = {
        '%': 60,
        '&': 0,
        '*': 60,
        '**': 0,
        '+': 50,
        '-': 50,
        '/': 60,
        '//': 60,
        '<': 40,
        '<<': 0,
        '>': 40,
        '>=': 40,
        '>>': 0,
        '^': 45,
        '|': 0}

    op_map = {
        '^': 'LOGXOR',
        '%': 'MOD'}

    def led(self, parser, left):
        op = self.op_map.get(self.value, self.value)
        return BinaryOperator(op,
                              left,
                              parser.expression(self.lbp_map[self.value]))

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
        if c not in ' \n()' and self.value != '::':
            return True
        return False

    def complete(self):
        if self.value == '::':
            self.lbp = 200
            self.name = '::'
        else:
            self.lbp = 0
        return True

    def nud(self, parser, value):
        return LispLiteral(value[1:])

    def led(self, parser, left):
        right = parser.expression(200)
        return Type(right, left)


@register
class AssignOrEquals(EnumeratedToken):
    lbp_map = {
        '==': 40,
        '=': 10}

    def led(self, parser, left):
        if self.value == '=':
            if left.kind == 'tuple':
                right = parser.expression(10)
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
                right = parser.expression(10)
                parser.maybe_match('NEWLINE')
                parser.ns.push_new()
                parser.ns.add(left)
                return Setf(left, right)

        else:
            return Equality(left, parser.expression())


@register
class NotEqual(EnumeratedToken):
    lbp_map = {'!=': 40}

    def led(self, parser, left):
        return NotEquality(left, parser.expression())


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


@register
class Name(Token):
    lbp = 0
    name = 'NAME'
    start_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_')
    rest_chars = start_chars | set('0123456789')

    def complete(self):
        value = self.value
        if value == 'in':
            self.name = 'IN'
            self.lbp = 150
        elif value == 'is':
            self.name = 'IS'
            self.lbp = 140
        elif value == 'for':
            self.name = 'for'
            self.lbp = 120
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
            self.lbp = 20
        elif value == 'not':
            self.name = 'NOT'
            self.lbp = 50

        return True

    def nud(self, parser, value):
        if value == 'raise':
            if parser.maybe_match('NEWLINE'):
                return Raise()
            exception_class = parser.expression(80)
            if parser.maybe_match('('):
                while parser.watch(')'):
                    args = []
                    kw_args = []
                    arg_name = parser.expression(40)
                    if parser.maybe_match('='):
                        kw_args.append((arg_name, parser.expression(40)))
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
                    exc_class = parser.expression(80)
                    if parser.maybe_match('AS'):
                        exc_name = parser.expression(80)
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
            module = parser.expression(80)
            alias = None
            if parser.maybe_match('AS'):
                alias = parser.expression(0)

            return Import(module, alias=alias)

        elif value == 'from':
            relative = 0

            while parser.maybe_match('DOT'):
                relative += 1

            module = parser.expression(80)

            import_ = parser.match('NAME')
            assert import_.value == 'import'
            seq = parser.expression()
            if seq.kind in ('symbol', 'cl_literal'):
                values = [seq]
            else:
                values = seq.values

            alias = None
            if parser.maybe_match('AS'):
                alias = parser.expression(0)

            parser.match('NEWLINE')
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
            condition = parser.expression(10)
            parser.match(':')
            parser.match('NEWLINE')
            body = parser.expression()
            parser.ns.pop()
            cond_clauses.append(CondClause(condition, body))
            while parser.maybe_match('ELIF'):
                parser.ns.push_new()
                condition = parser.expression(10)
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
            test = parser.expression(10)
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
                return_expr = parser.expression(5)
            return Return(return_expr)

        elif value == 'yield':
            if parser.maybe_match('NEWLINE'):
                return_expr = Nil()
            else:
                return_expr = parser.expression(5)
            return Yield(return_expr)

        elif value in ('class', 'condition'):
            name = parser.expression(80)
            if value == 'class':
                cc = CLOSClass(name)
            else:
                cc = Condition(name)
            if parser.maybe_match('('):
                while parser.watch(')'):
                    cc.bases.append(parser.expression(40))
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
            name = parser.expression(100)
            parser.ns.push_new(return_name=name)
            parser.match('(')
            parser.maybe_match('NEWLINE')
            arg_names = []
            kw_args = []

            while parser.watch(')'):
                arg_name = parser.expression(40)
                if parser.maybe_match('='):
                    kw_args.append((arg_name, parser.expression(40)))
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
            in_node = parser.expression(40)
            parser.match(':')
            parser.match('NEWLINE')
            body = parser.expression(10)
            # parser.ns.pop()
            return ForLoop(in_node, body)
        elif value == 'use':
            right = parser.expression(5)
            return UsePackage(right)
        elif value == 'not':
            right = parser.expression(50)
            return Call('NOT', [right])
        else:
            if value == value.upper():
                value = value.replace('_', '-')
            return Symbol(value)

    def led(self, parser, left):
        if self.value == 'in':
            return In(left, parser.expression())
        elif self.value == 'is':
            return BinaryOperator('eq', left, parser.expression())
        elif self.value == 'for':
            in_node = parser.expression()
            breakpoint()

            return ForExpression(left, in_node)
        elif self.value == 'and':
            return BinaryOperator('AND', left, parser.expression())
        raise Exception('Cannot get here?')



@register
class LParen(Token):
    name = '('
    lbp = 70
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
                arg = parser.expression(30)
                if parser.maybe_match('='):
                    kw_args.append((arg, parser.expression(30)))
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
            values.append(parser.expression())
            if parser.maybe_match(','):
                comma_seen = True
        if comma_seen or not values:
            return Tuple(values)
        return values[0]


@register
class LBracket(Token):
    lbp = 5
    start_chars = {'['}
    name = '['

    def nud(self, parser, value):
        values = []
        while parser.watch(']'):
            expr = parser.expression(30)
            values.append(expr)
            parser.maybe_match(',')
        return List(values)

    def led(self, parser, left):
        components = []
        while parser.watch(']'):
            if parser.maybe_match(':'):
                components.append(None)
                continue
            component = parser.expression(20)
            components.append(component)
            parser.maybe_match(':')
        if len(components) == 1:
            return GetItem(left, components[0])
        else:
            return Slice(left, components)


@register
class LBrace(Token):
    lbp = 40
    start_chars = {'{'}
    name = '{'

    def nud(self, parser, value):
        key_vals = []
        cls = 'set'
        while parser.watch('}'):
            key = parser.expression()
            if parser.maybe_match(':'):
                cls = 'set'
            if cls == 'dict':
                val = parser.expression()
            else:
                val = None
            key_vals.append((key, val))
        if cls == 'dict':
            return DictLiteral(key_vals)
        else:
            return SetLiteral(key_val[0] for key_val in key_vals)
        parser.log('%s', key_vals)


@register
class NumberToken(Token):
    start_chars = set('0123456789')
    rest_chars = start_chars | set('ex')
    name = 'NUMBER'

    def nud(self, parser, value):
        return Number(value)


@register
class Dot(Token):
    lbp = 150
    start_chars = {'.'}
    name = 'DOT'

    def led(self, parser, left):
        right = parser.expression(150)
        if right.kind == 'number' and left.kind == 'number':
            return Number(f'{left.value}.{right.value}')
        return AttrLookup(left, right)


@register
class At(EnumeratedToken):
    lbp_map = {
        '@': 0}
    name = '@'

    def nud(self, parser, value):
        # decorator_call = parser.expression()
        parser.expression()
        parser.match('NEWLINE')
        wrapped = parser.expression()
        return PythonBody([wrapped])


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
    lbp = 30

    def led(self, parser, left):
        values = [left, parser.expression(30)]
        while parser.maybe_match(','):
            values.append(parser.expression(30))

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
