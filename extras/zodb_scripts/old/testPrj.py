# flake8: noqa
# Script (Python) "testPrj"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=
# title=
##
request = context.REQUEST
request.RESPONSE.write('start')

for x in context.Catalog(meta_type='Report Document'):
    y = x.getObject()
    if y.id.find('.prj') != -1 and 'http://rod.eionet.europa.eu/obligations/269' in y.dataflow_uris:

        request.RESPONSE.write('%s\t%s\t%s\n' % (
            y.get_size(), y.getCountryName(), y.absolute_url()))
