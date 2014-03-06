
from collections import defaultdict
import codecs
import re

class PoBlock(object):
    #> #. Default: "Add"
    varPattern = re.compile(r'\${([\S-]+)}')
    #> #: ../../../extras/zodb_scripts/workdocuments/fgasses_feedbacks_i18n.zpt:121
    sourcePattern = re.compile(r'^#: (.*\S):\d+')
    comment = u'#'
    default = u'#. Default:'
    msgid = u'msgid'
    msgstr = u'msgstr'
    # sourcefiles -> set of msgidOrSrc
    source2ids = defaultdict(set)

    def __init__(self, noPerifericQuotes):
        self.noPerifericQuotes = noPerifericQuotes
        self.blockLines = []
        self.default_message = None
        self.default_message_trimmed = None
        self.msgidOrSrc = None
        self.msgidOrSrc_trimmed = None
        # play it safe
        self.translated = True
        self.htmlsIn = []
        self.sources = []
        self.i18n_vars = []
        self.msgidOrSrc_parts = []

    def trim(self, msg):
        # FIXME only one of Default/msgid will have vars?
        if not self.i18n_vars:
            self.i18n_vars = self.varPattern.findall(msg)
        self.msgidOrSrc_parts = self.varPattern.split(msg)
        self.msgidOrSrc_parts = [ x for x in self.msgidOrSrc_parts if x not in self.i18n_vars ]
        # no more stripping  - I want as many char as possible left
        return max(self.msgidOrSrc_parts, key=len)

    def tryRecordSource(self, line):
        m = self.sourcePattern.search(line)
        if m:
            self.sources.append(m.groups()[0])

    def trySetDefault(self, line):
        if line.startswith(self.default):
            self.default_message = line[len(self.default):].strip()
            if self.noPerifericQuotes:
                self.default_message = self.default_message.strip('"')
            self.default_message_trimmed = self.trim(self.default_message)

    def trySetMsgid(self, line):
        if line.startswith(self.msgid):
            self.msgidOrSrc = line[len(self.msgid):].strip()
            if self.noPerifericQuotes:
                self.msgidOrSrc = self.msgidOrSrc.strip('"')
            self.msgidOrSrc_trimmed = self.trim(self.msgidOrSrc)
            self._trackSource()

    def checkIfTranslated(self, line):
        if line.startswith(self.msgstr):
            if not line[len(self.msgstr):].strip('" \t\n'):
                self.translated = False


    def _trackSource(self):
        for s in self.sources:
            self.source2ids[s].add(self.lookForThis)

    def getBlockText(self):
        return u'\n'.join(self.blockLines)

    def foundInHtml(self, html_base_name):
        return html_base_name in self.htmlsIn;

    # we need the real english text, not the msg-id-stuff
    @property
    def lookForThis(self):
        if self.default_message_trimmed:
            return self.default_message_trimmed
        else:
            return self.msgidOrSrc_trimmed

    @property
    def neighbours(self):
        allNeighbours = set()
        for s in self.sources:
            allNeighbours += self.source2ids[s]
        return allNeighbours


def po_load(file_name, poHeader=None, bySrc=None, byMsgid=None, noPerifericQuotes=False):
    # note that in case of bySrc we will have overlappings
    # (because msg-id-stuff was not thoroughly implemented)
    # at the end of the day they reffer to the same message.
    # this overwirting may mismatch the soruces
    # but we will surely find another neighbour leading to all the others

    block = PoBlock(noPerifericQuotes=noPerifericQuotes)
    state = 'header'
    for line in codecs.open(file_name, 'r', 'utf-8'):
        line = line.strip()

        if state == 'header':
            if poHeader is not None:
                poHeader.append(line)
            if not line:
                state = 'comments'
                continue

        if state == 'comments':
            # include empty lines
            if line and not line.startswith(block.comment):
                state = 'msgid'
                # let it flow to the next if
            else:
                block.blockLines.append(line)
                block.trySetDefault(line)
                continue

        if state == 'msgid':
            if line.startswith(block.msgstr):
                state = 'msgstr'
                # let it flow to the next if
            else:
                block.blockLines.append(line)
                block.trySetMsgid(line)
                continue

        if state == 'msgstr':
            # the .po always finishes with an empty line
            if not line or line.startswith(block.comment):
                # don't miss any empty line
                block.blockLines.append(line)

                state = 'comments'
                #if block.lookForThis in bySrc:
                #    print bySrc[block.lookForThis].getBlockText()
                #    print " +++ collision with:"
                #    print block.getBlockText()
                if bySrc is not None:
                    bySrc[block.lookForThis] = block
                if byMsgid is not None:
                    byMsgid[block.msgidOrSrc] = block
                block = PoBlock(noPerifericQuotes=noPerifericQuotes)
                continue
            else:
                block.blockLines.append(line)
                block.checkIfTranslated(line)

    # as I said, the .po always finishes with an empty line
    # so we don't need to add the last block outside of loop
    return

