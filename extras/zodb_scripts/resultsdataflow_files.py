## Script (Python) "resultsdataflow_files"
##bind container=container
##bind context=context
##bind namespace=_
##bind script=script
##bind subpath=traverse_subpath
##parameters=
##title=Support function
##
#from Products.PythonScripts.standard import html_quote

buffer = []

hasPlainFiles = 0
for fileObj in context.objectValues('Report Document'):
    if fileObj.xml_schema_location == '':
        hasPlainFiles = 1
    if fileObj.id[-3:].lower() == 'shp':
        buffer.append('''<a href="%s/manage_document" title="Link to shapefile">%s</a>''' % (fileObj.absolute_url(), fileObj.id))
    else:
        buffer.append(fileObj.id)
    if not _.SecurityCheckPermission('View', fileObj):
        buffer.append('''<img src="/misc_/Reportek/lockicon_gif" alt="No access" width="16" height="16" />''')
    buffer.append('''<br />''')
if len(context.objectValues('Report Document')) == 0:
    buffer.append('''No files uploaded''')

if hasPlainFiles > 0:
    print '''<td style="background-color: yellow">'''
else:
    print '''<td>'''
print '\n'.join(buffer)
print '''</td>'''
return printed
