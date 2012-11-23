from collections import Counter
from OFS.Folder import Folder

def move_apps(root, grouped_apps=None, host_folder='Applications', commit=False):
    host_folder_obj = getattr(root, host_folder, None)
    if not host_folder_obj:
        root._setObject(host_folder, Folder(host_folder))
        host_folder_obj = getattr(root, host_folder)
        host_folder_obj._setObject('Common', Folder('Common'))
    if not grouped_apps:
        grouped_apps = group_apps_by_process(root)
    for proc, apps in grouped_apps:
        for app in apps:
            app_obj = getattr(root, app, None)
            path = '%s/%s/%s' %(host_folder, proc, app)
            if app_obj:
                if apps_list(root)[app] == 1:
                    if not getattr(host_folder_obj, proc, None):
                        host_folder_obj._setObject(proc, Folder(proc))
                    getattr(host_folder_obj, proc)._setObject(app, app_obj)
                else:
                    path = '%s/Common/%s' %(host_folder, app)
                    try:
                        ob = root.unrestrictedTraverse(path)
                        if ob.absolute_url() == app:
                            raise KeyError
                    except KeyError:
                        getattr(host_folder_obj, 'Common')._setObject(app, app_obj)

                wf = root.WorkflowEngine
                wf.editApplication(app, path)
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
