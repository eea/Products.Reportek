## Script (Python) "cs"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=Redirect to Serbia
##
raise 'Redirect', container.REQUEST.BASE0 + '/rs/' + '/'.join(traverse_subpath)
