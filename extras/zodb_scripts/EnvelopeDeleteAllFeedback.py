context.manage_delObjects([x for x in context.objectIds('Report Feedback') if not x.startswith('conversion_log')])
