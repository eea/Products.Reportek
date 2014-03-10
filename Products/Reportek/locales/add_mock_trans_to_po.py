# -*- coding: utf-8 -*-
import sys
reload(sys)
sys.setdefaultencoding('utf-8')
#sys.path.insert(0, '.')
import codecs

from poParser import po_load


def usage():
    "\tUsage: %s <po file>\n\tThe result will be in <po file>.out" % sys.argv[0]

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print usage
        sys.exit(1)

    po_file = sys.argv[1]
    out_po = codecs.open(po_file + '.out', 'w', 'utf-8')

    po_header = []
    byMsgid = {}
    po_load(po_file, poHeader=po_header, byMsgid=byMsgid)

    # add header to output file
    out_po.write(u'\n'.join(po_header))
    out_po.write(u'\n')
    for key, block in byMsgid.iteritems():
        if not block.translated:
            #block.replaceTranslation("__translated__" + block.srcMsg.strip('"') + "__translated__")
            block.replaceTranslationPreserveVars()
        out_po.write(block.getBlockText())
        out_po.write(u'\n')

    out_po.close()
