import requests
import transaction
from requests.exceptions import ConnectionError
from BeautifulSoup import BeautifulSoup as bs
from OFS.SimpleItem import SimpleItem
from Products.Reportek import zip_content
from Products.Reportek.exceptions import LocalConversionException
from ZODB.POSException import ConflictError

try:
    from cBytesIO import BytesIO
except ImportError:
    try:
        from BytesIO import BytesIO
    except ImportError:
        from io import BytesIO

FEEDBACKTEXT_LIMIT = 1024 * 16  # 16KB


class BaseRemoteApplication(SimpleItem):

    @property
    def wf_state_type(self):
        return getattr(self, '_wf_state_type', 'forwarding')

    @wf_state_type.setter
    def wf_state_type(self, value):
        self._wf_state_type = value

    def extract_metadata(self, fb=None, string_content=None):
        fb_status = 'UNKNOWN'
        fb_message = 'N/A'
        f = getattr(fb, 'feedbacktext', string_content)
        if f:
            soup = bs(f)
            log_sum = soup.find('span', attrs={'id': 'feedbackStatus'})
            if log_sum:
                fb_status = log_sum.get('class', 'UNKNOWN')
                fb_message = log_sum.text
        return fb_status, fb_message

    def add_zip_feedback(self, archive, fb, files, wk, l_file_id, l_ret,
                         job_id, restricted=False):
        """"""
        envelope = self.aq_parent
        feedback_id = '{0}_{1}_{2}'.format(self.app_name, fb, job_id)
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
                    if len(archive.read()) > FEEDBACKTEXT_LIMIT:
                        archive.seek(0)
                        feedback_ob.manage_uploadFeedback(archive,
                                                          filename='qa-output')
                        archive.seek(0)
                        html_header = archive.read(8096)
                        feedback_attach = feedback_ob['qa-output']
                        feedback_attach.data_file.content_type = 'text/html'
                        feedback_ob.feedbacktext = (
                            'Feedback too large for inline display; '
                            '<a href="qa-output/view">see attachment</a>.')
                        feedback_ob.content_type = 'text/html'
                        fb_status, fb_message = self.extract_metadata(
                            string_content=html_header)
                    else:
                        archive.seek(0)
                        feedback_ob.feedbacktext = archive.read()
                        feedback_ob.content_type = 'text/html'
                        fb_status, fb_message = self.extract_metadata(
                            feedback_ob)
                    feedback_ob.feedback_status = fb_status
                    if fb_status == 'BLOCKER':
                        wk.blocker = True
                    if fb_status == 'FAILED':
                        wk.failure = True
                    feedback_ob.message = fb_message
                else:
                    feedback_ob.manage_uploadFeedback(archive, filename=f_name)

    def add_html_feedback(self, rfile, fb, wk, l_file_id, l_ret,
                          job_id, restricted=False):
        """"""
        envelope = self.aq_parent
        feedback_id = '{0}_{1}_{2}'.format(self.app_name, fb, job_id)
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
        content_type = l_ret.get('feedbackContentType')
        content_type = content_type if content_type else 'text/html'

        if len(rfile.read()) > FEEDBACKTEXT_LIMIT:
            rfile.seek(0)
            feedback_ob.manage_uploadFeedback(rfile, filename='qa-output')
            feedback_attach = feedback_ob.objectValues()[0]
            feedback_attach.data_file.content_type = content_type
            feedback_ob.feedbacktext = (
                'Feedback too large for inline display; '
                '<a href="qa-output/view">see attachment</a>.')
            feedback_ob.content_type = 'text/html'

        else:
            rfile.seek(0)
            feedback_ob.feedbacktext = rfile.read()
            feedback_ob.content_type = content_type

        fb_status = l_ret.get('feedbackStatus')
        fb_status = fb_status if fb_status else 'UNKNOWN'
        feedback_ob.feedback_status = fb_status
        if feedback_ob.feedback_status == 'BLOCKER':
            wk.blocker = True
        if feedback_ob.feedback_status == 'FAILED':
            wk.failure = True
        feedback_ob.message = l_ret.get('feedbackMessage')

    def handle_remote_file(self, url, l_file_id, workitem_id, l_ret, job_id,
                           restricted=False):
        """"""
        wk = getattr(self, workitem_id)
        result = {}
        try:
            r = requests.get(url, allow_redirects=True,
                             headers={'Authorization': self.token},
                             verify=False)
            result['status_code'] = r.status_code
            result['url'] = url
            ctype = l_ret.get(
                'feedbackContentType',
                r.headers.get('Content-Type', ''))
            ctype = ctype if ctype else 'text/html'
            result['content_type'] = ctype
            result['content_lenght'] = len(r.content)

            if r.status_code == requests.codes.ok:
                from contextlib import closing
                file_h = BytesIO(r.content)
                if result['content_type'] == 'application/zip':
                    with closing(r), zip_content.ZZipFile(file_h) as archive:
                        self.add_zip_feedback(archive, '', archive.namelist(),
                                              wk, l_file_id, l_ret, job_id,
                                              restricted=restricted)
                elif 'text/html' in result['content_type']:
                    with closing(r), file_h as rfile:
                        self.add_html_feedback(rfile, '', wk,
                                               l_file_id, l_ret, job_id,
                                               restricted=restricted)

            else:
                result['content'] = r.content
                wk.addEvent(
                    'Error while downloading results for job #{} from {}. '
                    'Got {} status.'.format(job_id, url, r.status_code))
                wk.failure = True
        except ConflictError as err:
            # we need to raise this so that it can be retried
            wk.addEvent(
                'Error while saving results for job #{}, retrieved from {}. '
                'It will be retried automatically in a few minutes'.format(
                    job_id, url
                ))
            raise err
        except (LocalConversionException, ConnectionError) as err:
            # we need to raise this so that it can be retried
            wk.addEvent(
                'Error while downloading results for job #{} from {}. '
                'It will be retried automatically in a few minutes'.format(
                    job_id, url))
            raise err
        except Exception as e:
            result['content'] = str(e)
            wk.addEvent(
                'Error while downloading results for job #{} from {}. '
                'Got {} error.'.format(job_id, url, str(e)))
            wk.failure = True

        return result
