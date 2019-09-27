lst = []
for _ in range(10):
    lst.append([])

for i in range(20):
    for j in range(10):
        if i % (j+1) == 0:
            lst[j].append(i)
print(lst)
