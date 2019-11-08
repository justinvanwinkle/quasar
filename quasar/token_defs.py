
all_ops = []


def register(cls):
    all_ops.append(cls)
    return cls


class AST(object):
    kind = 'node'

    def __repr__(self):
        return self.cl()

    def clmap(self, forms):
        return [f'{x}' for x in forms]

    def cl(self):
        return '(%s-XXX XXX)' % self.kind


class Comment(AST):
    kind = 'comment'

    def __init__(self, comment):
        self.comment = comment

    def cl(self):
        return f'# {self.comment}'


class Body(AST):
    kind = 'body'

    def __init__(self, forms):
        self.forms = forms

    def cl(self):
        return '\n'.join(self.clmap(self.forms)) + '\n'


class PythonModule(AST):
    kind = 'module'

    def __init__(self, module_name, block):
        self.module_name = module_name
        self.block = block

    def cl(self):
        forms = []
        forms.append(self.block.cl())
        return ''.join(forms)


class Method(AST):
    kind = 'defun'

    def __init__(self, defun, class_name=None):
        self.defun = defun
        self.class_name = class_name
        self.first_arg = defun.arg_names[0]

    def cl(self):
        return 'def %s(%s):\n%s' % (
            self.defun.name,
            self.defun.cl_args(),
            self.defun.body.cl())


class Class(AST):
    kind = 'class'

    def __init__(self, name, bases=(), slots=(), members=(), methods=()):
        self.name = name
        self.bases = list(bases)
        self.methods = list(methods)
        self.constructor = None

    def add_form(self, form):
        if form.kind == 'defun':
            self.methods.append(form)

    def cl_method(self, defun):
        return Method(defun, self.name)

    def cl_methods(self):
        return ' '.join(self.cl_method(defun).cl() for defun in self.methods)

    def cl_bases(self):
        if not self.bases:
            return ''

        return '(%s)' % ', '.join(base.cl() for base in self.bases)

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
        body = Body(forms)

        defun = Defun(
            self.name,
            arg_names,
            kw_args,
            Body([body]))

        return "%s\n" % defun

    def cl(self):
        defclass = 'class %s%s:\n' % (
            self.name.cl(),
            self.cl_bases())
        if self.methods:
            defclass += ' '
            defclass += self.cl_methods()
        defclass += ' '

        return defclass


class Defun(AST):
    kind = 'defun'

    def __init__(self, name, arg_names, kw_args, body):
        self.name = name
        self.arg_names = arg_names
        self.kw_args = kw_args
        self.body = body

    def cl_kw_args(self):
        if not self.kw_args:
            return ''
        forms = []
        for key, default in self.kw_args:
            forms.append('(%s %s)' % (key, default))
        return 'CL:&KEY %s' % ''.join(forms)

    def cl_args(self, skip_first=False):
        forms = []
        splat = ''
        for arg in self.arg_names:
            if arg.kind == 'splat':
                splat = 'CL:&REST %s' % arg.right
            elif arg.kind == 'type':
                forms.append('(%s %s)' % (arg.left, arg.type))
            else:
                forms.append('%s' % arg)
        if skip_first:
            forms = forms[1:]
        return '%s %s %s' % (
            ' '.join(forms), self.cl_kw_args(), splat)

    def cl(self):
        defun = '(CL:DEFUN %s (%s) \n%s)' % (
            self.name,
            self.cl_args(),
            self.body.cl())
        return defun


class FletLambda(Defun):
    def __init__(self, defun, right):
        self.defun = defun
        self.right = right

    def cl(self):
        return '(CL:FLET ((%s (%s) %s)) %s)' % (
            self.defun.name,
            self.defun.cl_args(),
            self.defun.body.cl(),
            self.right.cl())


class Import(AST):
    kind = 'import'

    def __init__(self, module, symbols):
        self.module = module
        self.symbols = symbols

    def cl(self):
        symbols = ' '.join('%s:%s' % (self.module, s) for s in self.symbols)
        return "(CL:IMPORT '(%s))" % symbols


class Export(AST):
    kind = 'export'

    def __init__(self, values):
        self.values = values

    def cl(self):
        return "(CL:EXPORT '(%s))" % ' '.join(self.clmap(self.values))


class ForLoop(AST):
    kind = 'for'

    def __init__(self, in_node, body):
        self.in_node = in_node
        self.body = body

    def cl(self):
        collection = self.in_node.collection
        if ((collection.kind == 'call' and
             collection.name.name in ('range', 'xrange'))):
            args = collection.args
            if len(args) == 1:
                start = 0
                step = 1
                stop = args[0]
            elif len(args) == 2:
                step = 1
                start, stop = args
            elif len(args) == 3:
                start, stop, step = args
            domain = "FROM %s BELOW %s BY %s" % (
                start, stop, step)
        else:
            domain = '%s' % collection

        if self.in_node.thing.kind == 'type':
            var = self.in_node.thing.of_type_cl()
        else:
            var = self.in_node.thing.cl()
        return 'for %s in %s:\n %s)' % (
            var,
            domain,
            self.body.cl())


class CondClause(AST):
    kind = 'condclause'

    def __init__(self, condition, body):
        self.condition = condition
        self.body = body

    def cl(self):
        return '%s:\n %s' % (self.condition, self.body)


class Cond(AST):
    kind = 'cond'

    def __init__(self, clauses):
        self.clauses = clauses

    def cl(self):
        return 'if %s' % ' '.join('%s' % c for c in self.clauses)


class UnwindProtect(AST):
    def __init__(self, body_form, cleanup_form):
        self.body_form = body_form
        self.cleanup_form = cleanup_form

    def cl(self):
        return '(CL:UNWIND-PROTECT %s %s)' % (
            self.body_form, self.cleanup_form)


class HandlerCase(AST):
    def __init__(self, try_body, excepts, finally_body):
        self.try_body = try_body
        self.excepts = excepts
        self.finally_body = finally_body

    def cl(self):
        try_cl = 'try:\n %s' % self.try_body.cl()

        excepts_cl = ''
        if self.excepts:
            excepts_cl = '\n'.join([ex.cl() for ex in self.excepts])

        finally_cl = ''
        if self.finally_body:
            finally_cl = 'finally:\n %s' % self.finally_body.cl()
        return try_cl + excepts_cl + finally_cl


class Except(AST):
    def __init__(self, body, exception_call=None, alias=None):
        self.exception_call = exception_call
        self.alias = alias
        self.body = body

    def cl(self):
        call = '%s' % self.exception_call
        if self.alias:
            call += ' as %s' % self.alias
        return 'except %s:\n %s' % (call, self.body)


class Return(AST):
    kind = 'return'

    def __init__(self, return_expr, return_name):
        self.return_expr = return_expr
        self.return_name = return_name

    def cl(self):
        return '(CL:RETURN-FROM %s %s)' % (self.return_name, self.return_expr)


class Symbol(AST):
    kind = 'symbol'

    def __init__(self, name):
        self.name = name

    def cl(self):
        return '%s' % self.name


class WhileLoop(AST):
    kind = 'while'

    def __init__(self, test, body):
        self.test = test
        self.body = body

    def cl(self):
        return '(CL:LOOP WHILE %s DO %s)' % (
            self.test.cl(),
            self.body.cl())


class In(AST):
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


class Nil(AST):
    kind = 'nil'

    def cl(self):
        return 'NIL'


class UsePackage(AST):
    kind = 'use'

    def __init__(self, right):
        self.right = right

    def cl(self):
        return '(CL:USE-PACKAGE "%s")' % self.right.name


class List(AST):
    kind = 'list'

    def __init__(self, values):
        self.values = values

    def cl(self):
        return ("(|list| '(%s))" % ' '.join(self.clmap(self.values)))


class GetItem(AST):
    kind = 'getitem'

    def __init__(self, left, key):
        self.left = left
        self.key = key

    def cl(self):
        return '(|getitem| %s %s)' % (self.left, self.key)


class Slice(AST):
    kind = 'slice'

    def __init__(self, left, components):
        self.left = left
        self.components = components

    def cl(self):
        return '[%s]' % ':'.join(self.components)


class Tuple(AST):
    kind = 'tuple'

    def __init__(self, values):
        self.values = values

    def cl(self):
        return "(%s,)" % ', '.join(self.clmap(self.values))


class Raise(AST):
    kind = 'raise'

    def __init__(self, exception):
        self.exception = exception

    def cl(self):
        if self.exception is None:
            return 'raise'
        return f'raise {self.exception}'

class Call(AST):
    kind = 'call'

    def __init__(self, name, args=(), kw_args=()):
        self.name = name
        self.args = args
        self.kw_args = kw_args

    def cl_kw_args(self):
        forms = []
        for k, v in self.kw_args:
            forms.append('%s=%s' % (k, v))
        return ', '.join(forms)

    def cl(self):
        args = ', '.join(self.clmap(self.args))
        if self.kw_args:
            args += ', '.join(self.clmap(self.kw_args))
        return '%s(%s)' % (self.name, args)


class Type(AST):
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


class Equality(AST):
    kind = 'equal'

    def __init__(self, left, right):
        self.left = left
        self.right = right

    def cl(self):
        return '%s==%s' % (self.left.cl(), self.right.cl())


class NotEquality(AST):
    kind = 'equal'

    def __init__(self, left, right):
        self.left = left
        self.right = right

    def cl(self):
        return '(CL:NOT (|__eq__| %s %s))' % (self.left.cl(), self.right.cl())


class DefParameter(AST):
    kind = 'defparameter'

    def __init__(self, left, right):
        self.left = left
        self.right = right

    def cl(self):
        return '(CL:DEFPARAMETER %s %s)' % (self.left.cl(), self.right.cl())


class MultipleValueBind(AST):
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


class Setf(AST):
    kind = 'setf'

    def __init__(self, left, right):
        self.left = left
        self.right = right

    def cl(self):
        return '%s = %s' % (self.left, self.right)


class Let(AST):
    kind = 'let'

    def __init__(self, left, right):
        self.pairs = [(left, right)]

    def cl(self):
        pairs = []
        for l, r in self.pairs:
            if l.kind == 'type':
                declares.append(Call('DECLARE',
                                     [Call('TYPE', [l.type, l.left])]))
                pairs.append((l.left, r))
            else:
                pairs.append((l, r))

        return '\n'.join('%s = %s' % (l, r) for l, r in pairs)


class SetItem(AST):
    kind = 'setitem'

    def __init__(self, left, right):
        self.left = left
        self.right = right

    def cl(self):
        return '(|setitem| %s %s %s)' % (
            self.left.left, self.left.key, self.right)


class Number(AST):
    kind = 'number'

    def __init__(self, value):
        self.value = value

    def cl(self):
        return '%s' % self.value


class BinaryOperator(AST):
    kind = 'binary_op'

    def __init__(self, op, left, right):
        self.op = op
        self.left = left
        self.right = right

    def cl(self):
        return '(%s %s %s)' % (self.op, self.left.cl(), self.right.cl())


class AttrLookup(AST):
    kind = 'getattr'

    def __init__(self, object_name, attribute_name):
        self.object_name = object_name
        self.attribute_name = attribute_name

    def cl(self):
        return "%s.%s" % (self.object_name, self.attribute_name)


class Splat(AST):
    kind = 'splat'

    def __init__(self, right):
        self.right = right


class String(AST):
    kind = 'string'

    def __init__(self, value):
        self.value = value

    def cl(self):
        return '"%s"' % self.value


class Literal(AST):
    kind = 'cl_literal'

    def __init__(self, literal):
        self.literal = literal
        self.name = literal

    def cl(self):
        return self.literal


class Token(object):
    name = None
    lbp = 0
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
    def can_start(self, c):
        return c in self.start_chars

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
    def can_start(self, c):
        for symbol in self.lbp_map:
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
        '**': 80,
        '/': 60,
        '//': 60,
        '*': 60,
        '%': 60,
        '+': 50,
        '-': 50,
        '<<': 45,
        '>>': 45,
        '&': 40,
        '^': 45,
        '|': 40,
        '<': 40,
        '>': 40,
        '>=': 40,
        '<=': 40,
    }

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
        return Literal(value[1:])

    def led(self, parser, left):
        right = parser.expression(200)
        return Type(right, left)


@register
class AssignOrEquals(EnumeratedToken):
    lbp_map = {
        '==': 40,
        '=': 1}

    def led(self, parser, left):
        if self.value == '=':
            right = parser.expression()
            let_node = Let(left, right)
            return let_node
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
        package = PythonModule(parser.filename, parser.expression())
        return package


@register
class Block(Token):
    name = 'BLOCK'

    def nud(self, parser, value):
        forms = parser.parse_rest_of_body()
        return Body(forms)


@register
class Endblock(Token):
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
            self.lbp = 30
        elif value == 'is':
            self.name = 'IS'
            self.lbp = 30
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
            kw_args = []
            if parser.maybe_match('NEWLINE'):
                return Raise(None)
            exception_class = parser.expression()
            return Raise(exception_class)
        if value == 'try':
            parser.match(':')
            parser.match('NEWLINE')
            try_body = parser.expression()
            finally_body = None
            excepts = []
            while parser.maybe_match('EXCEPT'):
                exc_class = None
                exc_name = None
                if not parser.maybe_match(':'):
                    exc_class = parser.expression()
                    if parser.maybe_match('AS'):
                        exc_name = parser.expression()
                    parser.match(':')
                body = parser.expression()
                excepts.append(Except(body, exc_class, exc_name))
            if parser.maybe_match('FINALLY'):
                parser.match(':')
                finally_body = parser.expression()

            return HandlerCase(try_body, excepts, finally_body)
        elif value == 'from':
            module = parser.expression(80)
            import_ = parser.match('NAME')
            assert import_.value == 'import'
            seq = parser.expression()
            if seq.kind in ('symbol', 'cl_literal'):
                values = [seq]
            else:
                values = seq.values
            parser.match('NEWLINE')
            return Import(module, values)
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
            return Literal('True')
        elif value == 'False':
            return Literal('nil')
        elif value == 'if':
            cond_clauses = []
            condition = parser.expression(10)
            parser.match(':')
            parser.match('NEWLINE')
            body = parser.expression()
            cond_clauses.append(CondClause(condition, body))
            while parser.maybe_match('ELIF'):
                condition = parser.expression(10)
                parser.match(':')
                parser.match('NEWLINE')
                body = parser.expression()
                cond_clauses.append(CondClause(condition, body))
            if parser.maybe_match('ELSE'):
                condition = Literal('t')
                parser.match(':')
                parser.match('NEWLINE')
                body = parser.expression()
                cond_clauses.append(CondClause(condition, body))
            return Cond(cond_clauses)
        elif value == 'pass':
            return Nil()
        elif value == 'while':
            test = parser.expression(10)
            parser.match(':')
            parser.match('NEWLINE')
            body = parser.expression()
            return WhileLoop(test, body)
        elif value == 'None':
            return Nil()
        elif value == 'return':
            if parser.maybe_match('NEWLINE'):
                return_expr = Nil()
            else:
                return_expr = parser.expression(5)
            return Return(return_expr, parser.ns.return_name)
        elif value == 'class':
            name = parser.expression(80)
            cc = Class(name)
            if parser.maybe_match('('):
                while parser.watch(')'):
                    cc.bases.append(parser.expression(40))
                    parser.maybe_match(',')
            parser.match(':')
            parser.match('NEWLINE')
            body = parser.expression()
            for form in body.forms:
                cc.add_form(form)
            return cc
        elif value in ('def', 'defmethod'):
            name = parser.expression(100)
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
            defun = Defun(name, arg_names, kw_args, body)
            if value == 'defmethod':
                return Method(defun)
            if parser.ns.top_level or parser.ns.class_top_level:
                return defun

            flet_node = FletLambda(
                defun, Body(parser.parse_rest_of_body()))
            return flet_node
        elif value == 'for':
            in_node = parser.expression()
            parser.match(':')
            parser.match('NEWLINE')
            body = parser.expression(10)
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
        elif self.value == 'and':
            return BinaryOperator('AND', left, parser.expression())


@register
class LParen(Token):
    name = '('
    lbp = 70
    start_chars = {'('}

    def led(self, parser, left):
        if left.kind in ('getattr', 'symbol', 'call', 'lookup', 'cl_literal'):
            name = left
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
            if left.kind == 'getattr':
                name = left.attribute_name
                args.insert(0, left.object_name)
            return Call(name, args, kw_args)

    def nud(self, parser, value):
        values = []
        comma_seen = False
        while parser.watch(')'):
            values.append(parser.expression(200))
            if parser.maybe_match(','):
                comma_seen = True
        if comma_seen or not values:
            return Tuple(values)
        return values[0]


@register
class LBracket(Token):
    lbp = 140
    start_chars = {'['}
    name = '['

    def nud(self, parser, value):
        values = []
        while parser.watch(']'):
            values.append(parser.expression(40))
            parser.maybe_match(',')
        return List(values)

    def led(self, parser, left):
        components = []
        while parser.watch(']'):
            if parser.maybe_match(':'):
                components.append(None)
                continue
            components.append(parser.expression(40))
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
        while parser.watch('}'):
            key = parser.expression()
            parser.match(':')
            val = parser.expression()
            key_vals.append(key, val)
        parser.log('%s', key_vals)


@register
class NumberToken(Token):
    start_chars = set('0123456789')
    rest_chars = start_chars | set('ex')
    name = 'NUMBER'

    def nud(self, parser, value):
        if value.startswith('0x'):
            value = '#' + value[1:]
        return Number(value)


@register
class Dot(Token):
    lbp = 150
    start_chars = {'.'}
    name = 'DOT'

    def led(self, parser, left):
        right = parser.expression(150)
        if right.kind == 'number' and left.kind == 'number':
            return Number(float('%s.%s' % (left.value, right.value)))
        if right.kind == 'call':
            right.args.insert(0, left)
            return right
        return AttrLookup(left, right)


@register
class At(EnumeratedToken):
    lbp_map = {
        '@': 0}
    name = '@'

    def nud(self, parser, value):
        decorator_call = parser.expression()
        parser.match('NEWLINE')
        wrapped = parser.expression()
        return Body([wrapped])


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
            return Literal(value)
        return String(value)


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
    lbp = 10

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
        return Comment(value[1:])
