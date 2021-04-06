import transaction


def decode_feedbacktext(root):
    for item in root.Catalog({'meta_type': 'Report Feedback'}):
        feedback = item.getObject()
        text = feedback.feedbacktext
        if not isinstance(text, unicode):
            try:
                feedback.feedbacktext = text.decode('utf8')
            except UnicodeDecodeError as err:
                feedback.feedbacktext = text.decode('latin-1')
    ans = raw_input('Commit?\n')
    if ans == 'yes':
        transaction.commit()
