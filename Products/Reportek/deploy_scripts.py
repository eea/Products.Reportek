from collections import Counter
from OFS.Folder import Folder
from OFS.SimpleItem import SimpleItem

class MoveApp(Exception):
    """Raised when WorkflowEngine needs to be updated for the current app"""

    def __init__(self, app_obj):
        super(MoveApp, self).__init__()
        self.app_obj = app_obj


def move_apps(root, grouped_apps=None,
              host_folder='Applications',
              log=None,
              commit=False, delete=False):
    import StringIO
    messages = StringIO.StringIO()
    host_folder_obj = getattr(root, host_folder, None)
    actions = ['Create', 'Move', 'Update']
    len_act = len(max(actions, key=len))
    len_obj = 0
    wrong_ids = set()
    good_ids = []
    total_processed = 0
    root_len_before = len(root.objectIds())
    host_folder_created = False
    for app in apps_list(root).keys():
        if app in root.objectIds():
            good_ids.append(getattr(root, app).meta_type)
        else:
            wrong_ids.add(app)

    len_obj = max(len(max(good_ids, key=len)), len('WorkflowEngine')) if good_ids else 0

    create_message = ' '.join([actions[0].ljust(len_act), '%s', '|', '%s\n'])

    move_message = ' '.join([actions[1].ljust(len_act), '%s', '|', '%s -> %s\n'])

    update_workflow_message = ' '.join([actions[2].ljust(len_act), 'WorkflowEngine'.ljust(len_obj), '|', '%s\n'])
    if not host_folder_obj:
        host_folder_created = True
        obj = Folder(host_folder)
        root._setObject(host_folder, obj)
        messages.write(create_message %(obj.meta_type.ljust(len_obj), '/%s' %host_folder))

        host_folder_obj = getattr(root, host_folder)
        obj = Folder('Common')
        host_folder_obj._setObject('Common', obj)
        messages.write(create_message %(obj.meta_type.ljust(len_obj), '/%s/Common' %host_folder))

    if not grouped_apps:
        grouped_apps = group_apps_by_process(root)

    wf = root.WorkflowEngine
    for proc, apps in grouped_apps:
        for app in apps:
            app_obj = getattr(root, app, None)
            path = '%s/%s/%s' %(host_folder, proc, app)
            target_string = proc
            if app_obj:
                try:
                    if apps_list(root)[app] == 1:
                        if not getattr(host_folder_obj, proc, None):
                            obj = Folder(proc)
                            host_folder_obj._setObject(proc, obj)
                            messages.write(create_message %(obj.meta_type.ljust(len_obj),
                                                            '/%s/%s' %(host_folder, proc)))
                        raise MoveApp(app_obj)
                    else:
                        path = '%s/Common/%s' %(host_folder, app)
                        target_string = 'Common'
                        ob = root.unrestrictedTraverse(path)
                        if ob.absolute_url() == app:
                            raise MoveApp(app_obj)
                except MoveApp as ex:
                    total_processed+=1
                    from zExceptions import BadRequest
                    target_folder = getattr(host_folder_obj, target_string)
                    try:
                        target_folder._setObject(app, app_obj)
                    except BadRequest:
                        target_folder._delObject(app)
                        target_folder._setObject(app, app_obj)
                    if delete:
                        root._delObject(app)
                    messages.write(move_message %(app_obj.meta_type.ljust(len_obj),
                                                  '/%s' %app_obj.absolute_url(),
                                                  '/%s' %path))
                    wf.editApplication(app, path)
                    messages.write(update_workflow_message %app)

    messages.write('\n')

    if wrong_ids:
        _ids = [_id for _id in wrong_ids if _id]
        messages.write('Not found'.ljust(len_act+len_obj+1) + ' | %s\n' %', '.join(_ids))
    used_apps = set(apps_list(root).keys())
    defined_apps = set(ap['link'].split('/')[-1] for ap in wf.listApplications())
    not_used_apps = defined_apps - used_apps
    if not_used_apps:
        _ids = [_id for _id in not_used_apps if _id]
        messages.write('Not used'.ljust(len_act+len_obj+1) + ' | %s\n' %', '.join(_ids))

    import sys
    root_len_after = len(root.objectIds())
    if host_folder_created:
        root_len_after-=1
    messages.write('Processed: %s, Deleted: %s\n'
                    %(total_processed, root_len_before - root_len_after))

    sys.stdout.write(messages.getvalue())
    if log:
        with log:
            log.write(messages.getvalue())

    if commit:
        import transaction
        transaction.commit()

def group_apps_by_process(app):
    wf = app.WorkflowEngine
    p_ids = wf.objectIds()
    procs = [getattr(wf, p_id) for p_id in p_ids]
    results = list()
    [results.append(
        (proc.id,
         map(lambda act: getattr(proc, act).application, proc.listActivities())
        )
     )
     for proc in procs
    ]
    return results

def apps_list(app):
    wf = app.WorkflowEngine
    p_ids = wf.objectIds()
    procs = [getattr(wf, p_id) for p_id in p_ids]
    results = list()
    for proc in procs:
        for act_id in proc.listActivities():
            act_obj = getattr(proc, act_id)
            results.append(act_obj.application)
    return Counter(results)
