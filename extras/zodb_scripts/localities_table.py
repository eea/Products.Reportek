def inline_replace(x):
    x['uri'] = x['uri'].replace('eionet.europa.eu','eionet.eu.int')
    return x

try: 
    return map(inline_replace, container.localities_rod())
except:
    return []
