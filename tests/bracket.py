

lst = []

lst = [[]]

x = lst[0][1]

lst = [x for x in range(10)]

lst = [[] for _ in []]

lst = [[] for _ in [] if False]

lst = [[] for _ in [] if []]

lst = [[] for _ in [] * 20 if [] * 10]


lst = [[[[]]].bub for x in [[[], []]] if True]


for x in [x for x in lst if x.is_good]:
    print(x)
