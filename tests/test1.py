w.x.y.z = 'bub'


def foo(bub):
    print('foo')


y = 0
x = y + 1
x = x * 2 + 1.1
z = foo(bub=y)
# comment!

z = x['somekey']()
z = x['somekey'](x['somekey']())


def bar(a, b):
    print(a, b,
          'bar')
