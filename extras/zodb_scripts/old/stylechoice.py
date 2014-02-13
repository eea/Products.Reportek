## Script (Python) "stylechoice"
##bind container=container
##bind context=context
##bind namespace=
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=Check or set the preferred stylesheet
##
REQUEST = context.REQUEST
session=REQUEST.SESSION
if REQUEST.has_key('mystyle'):
    session['mystyle'] = REQUEST['mystyle']
if session.has_key('mystyle'):
    return session['mystyle']
else:
    return 'default'
