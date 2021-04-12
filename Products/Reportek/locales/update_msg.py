#!/usr/bin/env python
""" Update empty msgstr with msgid
"""

import os


def update(pofile):
    """ Update po file
    """
    print "Updating po file: %s" % pofile

    newfile = []
    msgid = ""
    msgstr = ""
    count = 0
    with open(pofile, 'r') as pobj:
        lines = pobj.readlines()
        for line in lines:
            if not (line.startswith('msgid') or line.startswith("msgstr")):
                newfile.append(line)

            if line.startswith("msgid"):
                msgid = line
                newfile.append(line)
                continue

            if line.startswith("msgstr"):
                if line.strip() != 'msgstr ""':
                    newfile.append(line)
                    continue
                else:
                    msgstr = msgid.replace("msgid", "msgstr", 1)
                    newfile.append(msgstr)
                    count += 1
                    continue

    os.rename(pofile, pofile + '.old')
    with open(pofile, 'w') as pobj:
        pobj.writelines(newfile)

    print "\t changed %s broken msgstr" % count


def main():
    """ Main
    """
    langs = os.listdir('.')
    for lang in langs:
        if not os.path.isdir(lang):
            continue

        lc = os.path.join(lang, 'LC_MESSAGES')
        if not os.path.isdir(lc):
            continue

        pos = [po for po in os.listdir(lc) if po.endswith('.po')]
        for po in pos:
            path = os.path.join(lc, po)
            update(path)


if __name__ == "__main__":
    main()
