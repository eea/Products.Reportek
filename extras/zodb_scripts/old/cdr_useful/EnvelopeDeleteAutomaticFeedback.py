l_feedback2delete = [x.id for x in context.objectValues('Report Feedback') if x.automatic == 1 and x.activity_id == '']
context.manage_delObjects(l_feedback2delete)
