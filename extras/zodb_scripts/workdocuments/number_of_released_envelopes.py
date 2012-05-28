## Script (Python) "number_of_released_envelopes"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=
##
print len(container.Catalog(meta_type='Report Envelope', released=1))
return printed
