## Script (Python) "EUETS"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=Redirects to the Article 21 manual, requested by the Commission
##
request = container.REQUEST

request.response.redirect('http://cdr.eionet.europa.eu/help/EUETS_Art21_ReportingManual_V2.pdf')
