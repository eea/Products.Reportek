l = container.REQUEST.HTTP_ACCEPT_LANGUAGE
llist = l.lower().split(",")
p = llist[0].split('-')
return p[0]
