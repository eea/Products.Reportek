def inline_replace(x):
   x['uri'] = x['uri'].replace('eionet.europa.eu','eionet.eu.int')
   return x

return map(inline_replace, container.dataflow_rod())
