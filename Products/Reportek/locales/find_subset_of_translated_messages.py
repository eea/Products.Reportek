#!/usr/bin/env python
from poParser import po_load
import codecs
import sys
reload(sys)
sys.setdefaultencoding('utf-8')
#sys.path.insert(0, '.')


def usage():
    "\tUsage: %s <big po file with tr messages> <small po file that should have msgstr translated>\n\tThe result will be in <po file>.out" % sys.argv[
        0]


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print usage
        sys.exit(1)

    po_file_tr = sys.argv[1]
    po_file_untr = sys.argv[2]
    out_po = codecs.open(po_file_untr + '.out', 'w', 'utf-8')

    po_header_tr = []
    byMsgid_tr = {}
    po_load(po_file_tr, poHeader=po_header_tr, byMsgid=byMsgid_tr)
    po_header_untr = []
    byMsgid_untr = {}
    po_load(po_file_untr, poHeader=po_header_untr, byMsgid=byMsgid_untr)

    # add header to output file
    out_po.write(u'\n'.join(po_header_untr))
    out_po.write(u'\n')
    for key, block in byMsgid_untr.iteritems():
        if not block.translated:
            tr_block = byMsgid_tr.get(block.msgidOrSrc, block)
        else:
            tr_block = block
        out_po.write(tr_block.getBlockText())
        out_po.write(u'\n')

    out_po.close()
