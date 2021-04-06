# Script (Python) "localities_table"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=
# title=
##
def inline_replace(x):
    x['uri'] = x['uri'].replace('eionet.eu.int', 'eionet.europa.eu')
    return x


try:
    return map(inline_replace, container.localities_rod())
except:
    return []
