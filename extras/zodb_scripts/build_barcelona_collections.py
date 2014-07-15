## Script (Python) "build_barcelona_collections"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=
##
for x in container.objectValues('Report Collection'):
  if not hasattr(x,'un'):
    print '>>%s' % x.absolute_url()
    #x.manage_addCollection(title='United Nations (UN)', descr='', year='', endyear='', 
    #                    partofyear='', country=x.id, locality='', 
    #                    dataflow_uris=[], allow_collections=1, 
    #                    allow_envelopes=0, id='un')
   

  elif not hasattr(x.un, 'bc'):
    x.un.manage_addCollection(title='Barcelona Convention', descr='', year='', endyear='', 
                        partofyear='', country=x.id, locality='', 
                        dataflow_uris=['http://rod.eionet.europa.eu/obligations/424', 'http://rod.eionet.europa.eu/obligations/425',
'http://rod.eionet.europa.eu/obligations/426', 'http://rod.eionet.europa.eu/obligations/427',
'http://rod.eionet.europa.eu/obligations/428', 'http://rod.eionet.europa.eu/obligations/429',
'http://rod.eionet.europa.eu/obligations/430'
], allow_collections=0, 
                        allow_envelopes=1, id='bc')
    print x.un.bc.absolute_url(1)
 
return printed
