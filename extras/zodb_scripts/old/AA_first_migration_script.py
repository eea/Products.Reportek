for env_cat in container.Catalog(meta_type='Report Envelope'):
    env = container.Catalog.getobject(env_cat.data_record_id_)
    # read the log and add workitems 
    l_count = 0
    l_logs = []
    if len(env.objectValues('Workitem')) == 0:
        for rec in env.activitylog:
            l_logs.append({'count': l_count+1, 'time': DateTime(rec[:rec.find('/')]), 'user': rec[rec.find('/')+1:rec.find(':  ')], 'log': rec[rec.find(':  ')+3:]})
        l_lenght = len(l_logs)
        print env.absolute_url(1) + ': ' + str(l_lenght)

        l_report = {}
        for l_log in l_logs:
            if l_log['log'] == 'Envelope created':
                env.initiation_log.append({'start':l_log['time'].timeTime(),'end':None,'comment':'creation','actor':''})
                env.setStatus(status='running', actor=l_log['user'], p_time=l_log['time'].timeTime())
                if l_lenght > l_log['count']:
                    l_report = {'activity_id': 'Draft', 'actor':l_log['user'], 'time1':l_log['time'], 'activity_from':'', 'activity_to':'Release'}
                else:
                    env.addWorkitemManually(activity_id='Draft', actor='', time1=l_log['time'], activity_from='')
            elif l_log['log'] == 'Released':

                env.setStatus(status='active', actor=l_report['actor'], p_time=l_report['time1'].timeTime())
                env.addWorkitemManually(activity_id=l_report['activity_id'], actor=l_report['actor'], time1=l_report['time1'], activity_from=l_report['activity_from'], activity_to=l_report['activity_to'], time2=l_log['time'])
                env.setStatus(status='running', actor=l_report['actor'], p_time=l_report['time1'].timeTime())
                l_report = {}

                env.setStatus(status='active', actor='openflow_engine', p_time=l_log['time'].timeTime())
                env.addWorkitemManually(activity_id='Release', actor='openflow_engine', time1=l_log['time'], activity_from='Draft', time2=l_log['time'], activity_to='Released')
                env.setStatus(status='running', actor='openflow_engine', p_time=l_log['time'].timeTime())

                if l_lenght > l_log['count']:
                    l_report = {'activity_id':'Released', 'actor':l_log['user'], 'time1':l_log['time'], 'activity_from':'Release', 'activity_to':'RevokeRelease'}
                else:
                    env.addWorkitemManually(activity_id='Released', actor=l_log['user'], time1=l_log['time'], activity_from='Release')

            elif l_log['log'] == 'Release status revoked':

                env.setStatus(status='active', actor=l_report['actor'], p_time=l_report['time1'].timeTime())
                env.addWorkitemManually(activity_id=l_report['activity_id'], actor=l_report['actor'], time1=l_report['time1'], activity_from=l_report['activity_from'], activity_to=l_report['activity_to'], time2=l_log['time'])
                env.setStatus(status='running', actor=l_report['actor'], p_time=l_report['time1'].timeTime())
                l_report = {}

                env.setStatus(status='active', actor='openflow_engine', p_time=l_log['time'].timeTime())
                env.addWorkitemManually(activity_id='RevokeRelease', actor='openflow_engine', time1=l_log['time'], activity_from='Released', time2=l_log['time'], activity_to='Draft')
                env.setStatus(status='running', actor='openflow_engine', p_time=l_log['time'].timeTime())

                if l_lenght > l_log['count']:
                    l_report = {'activity_id':'Draft', 'actor':l_log['user'], 'time1':l_log['time'], 'activity_from':'RevokeRelease', 'activity_to':'Release'}
                else:
                    env.addWorkitemManually(activity_id='Draft', actor=l_log['user'], time1=l_log['time'], activity_from='RevokeRelease')

        if l_report:
            env.addWorkitemManually(activity_id=l_report['activity_id'], actor='', time1=l_report['time1'], activity_from=l_report['activity_from'])
        l_report = {}

return printed
