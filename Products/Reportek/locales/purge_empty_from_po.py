from .poParser import po_load
import codecs
import sys
import importlib
importlib.reload(sys)
sys.setdefaultencoding('utf-8')
# sys.path.insert(0, '.')


def usage():
    "\tUsage: %s <po file>\n\tThe result will be in\
     <po file>.out" % sys.argv[0]


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(usage)
        sys.exit(1)

    po_file = sys.argv[1]
    out_po = codecs.open(po_file + '.out', 'w', 'utf-8')

    po_header = []
    byMsgid = {}
    po_load(po_file, poHeader=po_header, byMsgid=byMsgid)

    # add header to output file
    out_po.write('\n'.join(po_header))
    out_po.write('\n')
    for key, block in byMsgid.items():
        if not block.translated:
            continue
        out_po.write(block.getBlockText())
        out_po.write('\n')

    out_po.close()
