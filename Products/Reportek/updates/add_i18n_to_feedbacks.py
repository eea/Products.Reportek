# Use this update script from ./bin/instance debug
# from Products.Reportek.updates import add_i18n_to_feedbacks
# add_i18n_to_feedbacks.update(app)
# you will need a feedbacks specific default.pot file in the directory you are
# running from
#
# Please note that the task this script tries to accomplish is not trivial
# and this script will not cover all the cases
# It will basically add i18n tags to prerendered feedback htmls stored
# in Data.fs
# Those html feedbacks were produced by us using python scripts
# or have been delivred to us from external services
# In both cases, the transalation messages we are aware of reflect the actual
# and present cases and cannot cover former, historical versions of such
# prerendered feedback messages.
# This scripts assumes a html layout not more complicated than this:
#  <a_tag attrs="x"> text <inner_tag attrs="x">inner text</inner_tag> text
# <inner_tag_2 attrs="">inner text 2</inner_tag_2> text </a_tag>
# The msgid is also our input data (taken from feedback specific .pot) and is
# of form:
#  msgid "text ${var-name-1} text ${var-name-2} text"
# The output is:
#  <a_tag attrs="x" i18n:translate=""> text
# <inner_tag attrs="x" i18n:name="var-name-1">inner text</inner_tag> text
# <inner_tag_2 attrs="" i18n:name="var-name-2">inner text 2</inner_tag_2>
# text </a_tag>
# Please note:
# 1. the input html can be part of a bigger html and is not required to
# separated from it before input
# 2. any number of inner tags may appear, but not nested!
# 3. If inner html appears they must have a matching var-name-n in the .pot
#    file, otherwise the regex will not match
# 4. messages that won't match will be visible as
#    not translated, and require manual modification (and to be told apart from
#    historical messages that have no corresoinding message in the current
#    .pot file
#    but not from new messages as these will have the proper i18n tags, even
#    if not working
#    because they are not translated in the po/mo file)
# 5. This script will not attempt any substitution if i18n is already present
#    in the initial open tag of a match
import transaction
from Products.Reportek.locales.poParser import po_load
from bs4 import BeautifulSoup as bs
import re

__all__ = ['update']

g_translatable_vars = ['feedback-not-acceptable']


def do_update(o, app, bySrc, safeMatchOnly=True):
    feedbacktext = o.feedbacktext
    try:
        feedbacktext = feedbacktext.decode('utf-8')
    except (UnicodeDecodeError, UnicodeEncodeError):
        pass
    # some messages are not prettyfied
    feedbacktext = bs(feedbacktext.encode('utf-8')).prettify()
    try:
        feedbacktext = feedbacktext.decode('utf-8')
    except (UnicodeDecodeError, UnicodeEncodeError):
        pass

    lines = feedbacktext.split('\n')
    feedbacktext = ''.join([ln.strip() for ln in lines])
    for src, block in bySrc.iteritems():
        # for the complicated, unsafe match, the regex looks like this,
        # but the initial text is being escaped, so a plain . is \.
        # r'<(?P<initial_open_tag>[^<>]+)>
        #   The following delivery has been submitted for
        # <(?P<inner_open_tag_1>[^<>]+)>
        #   (?P<var_default_1>[^<>]+)</(?P<inner_close_tag_1>[^<>]+)> and was
        # finalized on
        #   <(?P<inner_open_tag_2>[^<>]+)>(?P<var_default_2>[^<>]+)</(?P<inner_close_tag_2>[^<>]+)>
        #   .</(?P<initial_close_tag>[^<>]+)>'
        toFindSafe = None
        varPat = None
        replStr = None
        inner_open_tags_regrefs = []
        inner_close_tags_regrefs = []
        var_defaults_regrefs = []
        lookForThis = block.msgidOrSrc_parts[0]
        if not block.i18n_vars:
            # don't use block.lookForThis - the longest part, but the first
            toFindSafe = '>' + lookForThis + '<'
        elif not safeMatchOnly:
            varPat = r'<(?P<initial_open_tag>[^<>]+)>'
            replStr = (r'<\g<initial_open_tag> i18n:translate="%s">'
                       % block.msgidOrSrc)
            for i, var in enumerate(block.i18n_vars):
                inner_open_tags_regrefs.append('inner_open_tag_' + str(i + 1))
                inner_close_tags_regrefs.append(
                    'inner_close_tag_' + str(i + 1))
                var_defaults_regrefs.append('var_default_' + str(i + 1))
                varPat += (re.escape(block.msgidOrSrc_parts[i].strip())
                           + r'<(?P<%s>[^<>]+)>' % inner_open_tags_regrefs[-1]
                           + r'(?P<%s>[^<>]*)' % var_defaults_regrefs[-1]
                           + (r'</(?P<%s>[^<>]+)>'
                              % inner_close_tags_regrefs[-1]))
                tr = ''
                if var in g_translatable_vars:
                    tr = ' i18n:translate="%s"' % var
                replStr += (block.msgidOrSrc_parts[i]
                            + r'<\g<%s> i18n:name="%s"%s>' % (
                                inner_open_tags_regrefs[-1], var, tr)
                            + r'\g<%s>' % var_defaults_regrefs[-1]
                            + r'</\g<%s>>' % inner_close_tags_regrefs[-1])
            # add last msg part
            varPat += re.escape(block.msgidOrSrc_parts[-1].strip())
            replStr += block.msgidOrSrc_parts[-1]
            # add initial closing tag
            varPat += r'</(?P<initial_close_tag>[^<>]+)>'
            replStr += r'</\g<initial_close_tag>>'
            try:
                varPat = re.compile(varPat)
            except Exception as e:
                print varPat.pattern
                print unicode(e)

        # avoid wrong msgids like: "L", "K+L+M"
        if (toFindSafe and toFindSafe in feedbacktext
                and len(lookForThis) > 5):
            # looking for:
            # ...<tag ...>pot text<...
            #    ^loab    ^part1
            pot_text_idx = feedbacktext.find(lookForThis)
            part1 = feedbacktext[:pot_text_idx]
            last_open_angular_bracket_idx = part1.rfind('<')
            if last_open_angular_bracket_idx < 0:
                # weird
                continue
            part_including_tag = feedbacktext[last_open_angular_bracket_idx:
                                              pot_text_idx]
            if 'i18n' in part_including_tag:
                continue
            part_including_tag = part_including_tag.replace(
                '>', ' i18n:translate="">')
            feedbacktext = (feedbacktext[:last_open_angular_bracket_idx]
                            + part_including_tag + feedbacktext[pot_text_idx:])
        elif varPat:
            # ...<tag ...>some pot text...var...some pot text...var2...some pot
            # t</tag>
            # TODO do fine grain check for i18n attrs here,
            # rather than in the whole feedback message
            # ('i18n' in varPat.search.group(0))
            m = varPat.search(feedbacktext)
            if m:
                if 'i18n' in m.group('initial_open_tag'):
                    continue
                feedbacktext = varPat.sub(replStr, feedbacktext)

    # add line endings back
    return bs(feedbacktext.encode('utf-8')).prettify()


def update(app):
    po_filename = 'default.pot'
    po_header = []
    bySrc = {}
    po_load(po_filename, poHeader=po_header,
            bySrc=bySrc, noPerifericQuotes=True)

    for brain in app.Catalog(meta_type='Report Feedback'):
        o = brain.getObject()
        # if o.id not in ['feedback1389098996','feedback1372226406']:
        #    continue
        if 'html' in o.content_type:
            print 'Updating feed:', o.id
            trans = transaction.begin()
            try:
                o.feedbacktext = do_update(o, app, bySrc, safeMatchOnly=False)
                trans.commit()
            except Exception:
                trans.abort()
                print "Error on feed:", o.id
                raise
