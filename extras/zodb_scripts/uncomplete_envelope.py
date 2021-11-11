# flake8: noqa
# Script (Python) "uncomplete_envelope"
# bind container=container
# bind context=context
# bind namespace=
# bind script=script
# bind subpath=traverse_subpath
# parameters=
# title=To be run against a completed envelope to re-open it again
##
for w in context.objectValues('Workitem'):
    if w.activity_id == 'End':
        last = w.id
        previous_w_id = w.workitems_from[0]

previous_w = getattr(context, previous_w_id)

previous_w.edit(status='inactive', actor='', workitems_to=[])
if previous_w.completion_log:
    del(previous_w.completion_log[-1])
previous_w.manage_changeProperties({'active_time': 0})
context.manage_delObjects(last)
for j in range(5):
    del(previous_w.event_log[-1])
context.setStatus(status='running', actor='')

return 1
