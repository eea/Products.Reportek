# flake8: noqa
# this is meant to be run from instance debug
# >>> from Products.Reportek.updates.extract_manual_feedbacks_with_emails import update; update(app)

import re

# taken from validate_email module  and make it match anywhere in text
mail_re = re.compile(r'(?:(?:(?:(?:[ \t]*(?:\r\n))?[ \t]+)?\((?:(?:(?:[ \t]*(?:\r\n))?'
                     '[ \t]+)?(?:[\x01-\x08\x0b\x0c\x0f-\x1f\x7f\x21-\x27\x2a-\x5b\x5d-\x7e]'
                     '|(?:\\.)))*(?:(?:[ \t]*(?:\r\n))?[ \t]+)?\))*(?:(?:(?:[ \t]*(?:\r\n))?'
                     '[ \t]+)?\((?:(?:(?:[ \t]*(?:\r\n))?[ \t]+)?'
                     '(?:[\x01-\x08\x0b\x0c\x0f-\x1f\x7f\x21-\x27\x2a-\x5b\x5d-\x7e]|(?:\\.)))*'
                     '(?:(?:[ \t]*(?:\r\n))?[ \t]+)?\)|(?:(?:[ \t]*(?:\r\n))?[ \t]+))?'
                     '[\w!#$%&\'\*\+\-/=\?\^`\{\|\}~]+(?:\.[\w!#$%&\'\*\+\-/=\?\^`\{\|\}~]+)*'
                     '(?:(?:(?:[ \t]*(?:\r\n))?[ \t]+)?\((?:(?:(?:[ \t]*(?:\r\n))?[ \t]+)?'
                     '(?:[\x01-\x08\x0b\x0c\x0f-\x1f\x7f\x21-\x27\x2a-\x5b\x5d-\x7e]|(?:\\.)))*'
                     '(?:(?:[ \t]*(?:\r\n))?[ \t]+)?\))*(?:(?:(?:[ \t]*(?:\r\n))?[ \t]+)?\('
                     '(?:(?:(?:[ \t]*(?:\r\n))?[ \t]+)?(?:[\x01-\x08\x0b\x0c\x0f-\x1f\x7f\x21-\x27\x2a-\x5b\x5d-\x7e]'
                     '|(?:\\.)))*(?:(?:[ \t]*(?:\r\n))?[ \t]+)?\)|(?:(?:[ \t]*(?:\r\n))?[ \t]+))?|(?:(?:(?:[ \t]*(?:\r\n))?'
                     '[ \t]+)?\((?:(?:(?:[ \t]*(?:\r\n))?[ \t]+)?'
                     '(?:[\x01-\x08\x0b\x0c\x0f-\x1f\x7f\x21-\x27\x2a-\x5b\x5d-\x7e]|(?:\\.)))*'
                     '(?:(?:[ \t]*(?:\r\n))?[ \t]+)?\))*(?:(?:(?:[ \t]*(?:\r\n))?[ \t]+)?'
                     '\((?:(?:(?:[ \t]*(?:\r\n))?[ \t]+)?(?:[\x01-\x08\x0b\x0c\x0f-\x1f\x7f\x21-\x27\x2a-\x5b\x5d-\x7e]'
                     '|(?:\\.)))*(?:(?:[ \t]*(?:\r\n))?[ \t]+)?\)|(?:(?:[ \t]*(?:\r\n))?[ \t]+))?'
                     '"(?:(?:(?:[ \t]*(?:\r\n))?[ \t]+)?(?:[\x01-\x08\x0b\x0c\x0f-\x1f\x7f\x21\x23-\x5b\x5d-\x7e]'
                     '|(?:\\.)))*(?:(?:[ \t]*(?:\r\n))?[ \t]+)?"(?:(?:(?:[ \t]*(?:\r\n))?'
                     '[ \t]+)?\((?:(?:(?:[ \t]*(?:\r\n))?[ \t]+)?'
                     '(?:[\x01-\x08\x0b\x0c\x0f-\x1f\x7f\x21-\x27\x2a-\x5b\x5d-\x7e]|(?:\\.)))*'
                     '(?:(?:[ \t]*(?:\r\n))?[ \t]+)?\))*(?:(?:(?:[ \t]*(?:\r\n))?[ \t]+)?\((?:(?:(?:[ \t]*(?:\r\n))?'
                     '[ \t]+)?(?:[\x01-\x08\x0b\x0c\x0f-\x1f\x7f\x21-\x27\x2a-\x5b\x5d-\x7e]'
                     '|(?:\\.)))*(?:(?:[ \t]*(?:\r\n))?[ \t]+)?\)|(?:(?:[ \t]*(?:\r\n))?[ \t]+))?)'
                     '@(?:(?:(?:(?:[ \t]*(?:\r\n))?[ \t]+)?\((?:(?:(?:[ \t]*(?:\r\n))?[ \t]+)?'
                     '(?:[\x01-\x08\x0b\x0c\x0f-\x1f\x7f\x21-\x27\x2a-\x5b\x5d-\x7e]|(?:\\.)))*'
                     '(?:(?:[ \t]*(?:\r\n))?[ \t]+)?\))*(?:(?:(?:[ \t]*(?:\r\n))?[ \t]+)?'
                     '\((?:(?:(?:[ \t]*(?:\r\n))?[ \t]+)?(?:[\x01-\x08\x0b\x0c\x0f-\x1f\x7f\x21-\x27\x2a-\x5b\x5d-\x7e]'
                     '|(?:\\.)))*(?:(?:[ \t]*(?:\r\n))?[ \t]+)?\)|(?:(?:[ \t]*(?:\r\n))?[ \t]+))?'
                     '[\w!#$%&\'\*\+\-/=\?\^`\{\|\}~]+(?:\.[\w!#$%&\'\*\+\-/=\?\^`\{\|\}~]+)*'
                     '(?:(?:(?:[ \t]*(?:\r\n))?[ \t]+)?\((?:(?:(?:[ \t]*(?:\r\n))?[ \t]+)?'
                     '(?:[\x01-\x08\x0b\x0c\x0f-\x1f\x7f\x21-\x27\x2a-\x5b\x5d-\x7e]|(?:\\.)))*'
                     '(?:(?:[ \t]*(?:\r\n))?[ \t]+)?\))*(?:(?:(?:[ \t]*(?:\r\n))?[ \t]+)?'
                     '\((?:(?:(?:[ \t]*(?:\r\n))?[ \t]+)?(?:[\x01-\x08\x0b\x0c\x0f-\x1f\x7f\x21-\x27\x2a-\x5b\x5d-\x7e]'
                     '|(?:\\.)))*(?:(?:[ \t]*(?:\r\n))?[ \t]+)?\)|(?:(?:[ \t]*(?:\r\n))?[ \t]+))?'
                     '|(?:(?:(?:[ \t]*(?:\r\n))?[ \t]+)?\((?:(?:(?:[ \t]*(?:\r\n))?[ \t]+)?'
                     '(?:[\x01-\x08\x0b\x0c\x0f-\x1f\x7f\x21-\x27\x2a-\x5b\x5d-\x7e]|(?:\\.)))*'
                     '(?:(?:[ \t]*(?:\r\n))?[ \t]+)?\))*(?:(?:(?:[ \t]*(?:\r\n))?[ \t]+)?'
                     '\((?:(?:(?:[ \t]*(?:\r\n))?[ \t]+)?(?:[\x01-\x08\x0b\x0c\x0f-\x1f\x7f\x21-\x27\x2a-\x5b\x5d-\x7e]'
                     '|(?:\\.)))*(?:(?:[ \t]*(?:\r\n))?[ \t]+)?\)|(?:(?:[ \t]*(?:\r\n))?'
                     '[ \t]+))?\[(?:(?:(?:[ \t]*(?:\r\n))?[ \t]+)?(?:[\x01-\x08\x0b\x0c\x0f-\x1f\x7f\x21-\x5a\x5e-\x7e]'
                     '|(?:\\.)))*(?:(?:[ \t]*(?:\r\n))?[ \t]+)?\](?:(?:(?:[ \t]*(?:\r\n))?'
                     '[ \t]+)?\((?:(?:(?:[ \t]*(?:\r\n))?[ \t]+)?'
                     '(?:[\x01-\x08\x0b\x0c\x0f-\x1f\x7f\x21-\x27\x2a-\x5b\x5d-\x7e]|(?:\\.)))*'
                     '(?:(?:[ \t]*(?:\r\n))?[ \t]+)?\))*(?:(?:(?:[ \t]*(?:\r\n))?[ \t]+)?'
                     '\((?:(?:(?:[ \t]*(?:\r\n))?[ \t]+)?(?:[\x01-\x08\x0b\x0c\x0f-\x1f\x7f\x21-\x27\x2a-\x5b\x5d-\x7e]'
                     '|(?:\\.)))*(?:(?:[ \t]*(?:\r\n))?[ \t]+)?\)|(?:(?:[ \t]*(?:\r\n))?[ \t]+))?)')


def update(app, outName='manual_feedbacks_with_emails.txt'):
    out = open(outName, 'w')
    for brain in app.Catalog(meta_type='Report Feedback'):
        try:
            feed = brain.getObject()
            if feed.automatic:
                continue
            if has_email(feed.feedbacktext):
                out.write('cdr.eionet.europa.eu/' +
                          feed.absolute_url(1) + '\r\n')
            else:
                for comment in feed.listComments():
                    if has_email(comment.body):
                        out.write('cdr.eionet.europa.eu/' +
                                  feed.absolute_url(1) + '\r\n')
                        break
        except Exception as e:
            print "For: ", brain.getPath(), " . Error is: ", e.args
    out.close()


def has_email(body):
    if '@' in body:
        # could add some filters here; some emails could not interest us
        if mail_re.search(body):
            return True
    return False
