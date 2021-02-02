import io

import requests
import transaction
from BeautifulSoup import BeautifulSoup as bs
from OFS.SimpleItem import SimpleItem
from Products.Reportek import zip_content


class BaseRemoteApplication(SimpleItem):
    def extract_metadata(self, fb):
        fb_status = 'UNKNOWN'
        fb_message = 'N/A'
        f = getattr(fb, 'feedbacktext', None)
        if f:
            soup = bs(f)
            log_sum = soup.find('span', attrs={'id': 'feedbackStatus'})
            if log_sum:
                fb_status = log_sum.get('class', 'UNKNOWN')
                fb_message = log_sum.text
        return fb_status, fb_message

    def add_zip_feedback(self, archive, fb, files, wk, l_file_id, l_ret, restricted=False):
        """"""
        envelope = self.aq_parent
        feedback_id = '{0}_{1}'.format(self.app_name, fb)
        if l_file_id == 'xml':
            l_filename = ' result for: '
        else:
            l_filename = ' result for file %s: ' % l_file_id
        fb_title = ''.join([self.app_name,
                            l_filename,
                            l_ret['SCRIPT_TITLE']])
        envelope.manage_addFeedback(id=feedback_id,
                                    title=fb_title,
                                    activity_id=wk.activity_id,
                                    automatic=1,
                                    document_id=l_file_id,
                                    restricted=restricted)
        feedback_ob = envelope[feedback_id]
        for f in files:
            archive.setcurrentfile(f)
            f_name = envelope.cook_file_id(f)
            if f_name:
                if f_name.endswith('.html'):
                    feedback_ob.feedbacktext = archive.read()
                    feedback_ob.content_type = 'text/html'
                    fb_status, fb_message = self.extract_metadata(feedback_ob)
                    feedback_ob.feedback_status = fb_status
                    feedback_ob.message = fb_message
                else:
                    feedback_ob.manage_uploadFeedback(archive, filename=f_name)

    def handle_remote_file(self, url, l_file_id, workitem_id, l_ret):
        """"""
        wk = getattr(self, workitem_id)
        env = wk.getMySelf()
        file = env.get(l_file_id)
        restricted = False
        if file.isRestricted():
            restricted = True
        try:
            r = requests.get(url, allow_redirects=True,
                             headers={'Authorization': self.token},
                             verify=False)
            from contextlib import closing
            zip = io.BytesIO(r.content)
            with closing(r), zip_content.ZZipFile(zip) as archive:
                fbs = {}
                for name in archive.namelist():
                    k = name.split('/')[-1].split('.')[0]
                    if k:
                        if k not in fbs.keys():
                            fbs[k] = [name]
                        else:
                            fbs[k].append(name)
                for fb in fbs:
                    self.add_zip_feedback(archive, fb, fbs[fb], wk,
                                          l_file_id, l_ret, restricted=restricted)
                transaction.commit()
        except Exception:
            raise
