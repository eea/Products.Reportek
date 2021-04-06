# Script (Python) "testQA"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=
# title=
##
request = container.REQUEST

for x in context.objectValues('Report Document'):
    if x.xml_schema_location == 'http://biodiversity.eionet.europa.eu/schemas/dir9243eec/gml_art17.xsd' and not hasattr(context, "feedback_%s" % x.id):
        l_res = context.runQAScript(p_file_url=x.absolute_url(
        ), p_script_id='loc_gml_qa', REQUEST=request, return_inline=1)
        context.manage_addFeedback(id="feedback_%s" % x.id, title="Automatic AutomaticQA result for file: %s" %
                                   x.id, feedbacktext=str(l_res), content_type='text/html', automatic=1)
        context.comtr()

return 1
