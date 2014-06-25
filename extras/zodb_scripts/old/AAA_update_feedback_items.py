## Script (Python) "AAA_update_feedback_items"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=changes the process 
##
request = container.REQUEST

#http://cdr.eionet.europa.eu/recent_etc?RA_ID=602

#for x in context.Catalog(meta_type='Report Envelope', dataflow_uris=['http://rod.eionet.europa.eu/obligations/602']):
for x in ['at/eu/fhrm/coluwx87w/envuyflqa', 'at/eu/fhrm/coluwx9fg/envux12xa', 'at/eu/fhrm/coluwxww/envux12qa', 'be/eu/fhrm/envuya2dg', 'be/eu/fhrm/envuya2wa', 'be/eu/fhrm/envuyhzha', 'cz/eu/fhrm/envuylt6a', 'cz/eu/fhrm/envuylthw', 'de/eu/fhrm/envuyba5q', 'de/eu/fhrm/envuyba8w', 'de/eu/fhrm/envuybaq', 'de/eu/fhrm/envuybatq', 'de/eu/fhrm/envuybayw', 'de/eu/fhrm/envuybbbg', 'de/eu/fhrm/envuybbcq', 'de/eu/fhrm/envuybbha', 'de/eu/fhrm/envuybbmw', 'de/eu/fhrm/envuybbva', 'nl/eu/fhrm/envuxhfzg', 'ro/eu/fhrm/envuycc_q', 'ro/eu/fhrm/envuycdaw', 'ro/eu/fhrm/envuycdcg', 'ro/eu/fhrm/envuycdeg', 'ro/eu/fhrm/envuycdha', 'ro/eu/fhrm/envuycdma', 'ro/eu/fhrm/envuycdnw', 'ro/eu/fhrm/envuycdpw', 'ro/eu/fhrm/envuycdrg', 'ro/eu/fhrm/envuycdtg', 'ro/eu/fhrm/envuycdvw', 'ro/eu/fhrm/envuycdzw', 'sk/eu/fhrm/envuym_kq', 'sk/eu/fhrm/envuym_nq' ]:
  e = context.restrictedTraverse(x)
  print e.absolute_url(), e.process_path
  e.setProcess('WorkflowEngine/default_with_confirmation')
  print e.process_path

return printed
