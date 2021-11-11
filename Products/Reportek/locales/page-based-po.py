# This is based on the main .po file (obtained from sources on disk
# and those extracted from ZODB) and on given html files.
# It will try to match source messages (not msgids like aa-bb-cc,
# but actual source english text) from .po file to the contents of html.
# When matches are found, all the messages that belong to the same source
# (zpt, py, dtml) are added to that specific html.po

# Note that a message may be found in more than one source, and not knowing
# which of them is used in that particular html, the neighbours from all
# sources will be added to that html.po - creating more text to be translated
# than necessary.
# The neighbour feature is important because an html may conditionally omit
# some messages otherwise found in its underling zpts, pys, dtmls.

# Note that the mixed usage of initial english message for msgid AND symbolic
# msgids (of form msg-id-thing) will cause collisons in alghorithm, and more
# false neighbours adding.
# e.g:

# . Default: Add
#: zpt1:100
# msgid "add-button"
# msgstr "add translation"

#: zpt2:200
# msgid "Add"
# msgstr "add translation"

# This will cause a collision - the "Add" text found in html cand not be
# correctly tracked to its source, thus its neighbours

# Note that the "Some text ${some var} some more text" messages will add
# fuzziness to the matching, and could result in more false neighbours.

# All this eurhistics will make rebuilding the main .po file out of the .xlfs
# received from translators at least tricky, if not slightly unreliable...

# All this happes because, having the html as input - we cannot track
# which zpts, dtml, pys, etc were used to generate it, and scan those.
# Thus we scan the main .po file with the above drawbacks

from poParsing import po_load
import os.path
import os
import codecs
import sys
reload(sys)
sys.setdefaultencoding('utf-8')


g_result_dir = None


def usage():
    "\tUsage: %s <main.po> <html directory>" % sys.argv[0]


def play(po_header, bySrc):
    print '\n'.join(po_header)
    for block in bySrc.itervalues():
        print block.getBlockText()
        # print block.msgidOrSrc
        # print block.msgidOrSrc_trimmed
        # if block.default_message:
        #    print block.default_message
        #    print block.default_message_trimmed


def process_html(html, po_header, bySrc):
    text = codecs.open(html, 'r', 'utf-8').read()
    base_name = os.path.splitext(os.path.basename(html))[0]
    po = codecs.open(g_result_dir + '/' + base_name + '.po', 'w', 'utf-8')
    po.write(u'\n'.join(po_header))
    po.write(u'\n')

    for key, block in bySrc.iteritems():
        if block.foundInHtml(base_name):
            continue
        if key in text:
            po.write(block.getBlockText())
            po.write(u'\n')
            # add all neighbours from the same source
            for neighbour in block.neighbours:
                neighbourBlock = bySrc[neighbour]
                if neighbourBlock.foundInHtml(base_name):
                    continue
                po.write(neighbourBlock.getBlockText())
                po.write(u'\n')
    po.close()


def mk_result_dir(html_dir):
    dir_name = os.path.dirname(html_dir)
    name = os.path.basename(html_dir)
    result_dir = os.path.join(dir_name, name+'.po')
    try:
        os.mkdir(result_dir)
    except Exception:
        print "Failed. Dir %s exists?" % result_dir
        sys.exit(1)

    return result_dir


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print usage()
        sys.exit(1)
    main_po = sys.argv[1]
    html_dir = sys.argv[2]
    if html_dir.endswith('/'):
        html_dir = html_dir[:-1]
    g_result_dir = mk_result_dir(html_dir)

    po_header = []
    bySrc = {}
    po_load(main_po, poHeader=po_header, bySrc=bySrc)
    # play(po_header, bySrc)

    for f in os.listdir(html_dir):
        f = os.path.join(html_dir, f)
        if os.path.isfile(f):
            process_html(f, po_header, bySrc)
