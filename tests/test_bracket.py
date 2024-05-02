

code = """\
l = []

l = [[]]

x = l[0][1]

l = [x for x in range(10)]

l = [[] for _ in []]

l = [[] for _ in [] if False]

l = [[] for _ in [] if []]

l = [[] for _ in [] * 20 if [] * 10]


l = [[[[]]].bub for x in [[[], []]] if True]


for x in [x for x in l if x.is_good]:
    print(x)
"""
