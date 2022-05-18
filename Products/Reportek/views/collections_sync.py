from operator import itemgetter
from base_admin import BaseAdmin
import json
from Products.Reportek.constants import ENGINE_ID
from Products.Reportek.rabbitmq import send_message

class CollectionsSync(BaseAdmin):
    def __call__(self, *args, **kwargs):
        super(CollectionsSync, self).__call__(*args, **kwargs)
        if self.request.get('btn.publish'):
            self.collections_sync()
        return self.index()

    def is_sync_enabled(self):
        engine = getattr(self.context, ENGINE_ID)
        return getattr(engine, 'col_sync_rmq', False)

    def collections_sync(self):
        engine = getattr(self.context, ENGINE_ID)
        result = []
        pub_colls = self.request.get('collections', [])
        if self.request.get('btn.publish') and not pub_colls:
            self.request['op_results'] = []

        if pub_colls:
            results = []
            if self.is_sync_enabled():
                for collection in pub_colls:
                    try:
                        col_url = '/'.join([self.request.SERVER_URL,
                                            collection])
                        send_message(col_url, queue='collections_sync')
                        results.append({
                            'collection': col_url,
                            'published': True,
                            'error': None
                        })
                    except Exception as e:
                        results.append({
                            'collection': collection,
                            'published': False,
                            'error': Exception(
                                '''Unable to send message to RabbitMQ! '''
                                '''Details: {}'''.format(str(e)))
                        })
            self.request['op_results'] = results

        if getattr(engine, 'col_sync_rmq', False):
            hist = engine.get_col_sync_history()
            for col in hist:
                result.append({
                    'path': col,
                    'modified': hist[col].get('modified'),
                    'ack': hist[col].get('ack')
                })
        return json.dumps(result)
