import os
import time

cwd = os.environ['CDR_DEMUPLOADS_LOG']


def logtheupload(REQUEST):
    """ Log a line """
    f = open(cwd, 'a')
    f.write("\nNew upload at %s\n" % time.ctime())
    f.write("User: %s\n" % REQUEST.AUTHENTICATED_USER.getUserName())
    f.write("Content length: %s\n" % REQUEST['CONTENT_LENGTH'])
    f.write("Client IP: %s\n" % REQUEST['HTTP_X_FORWARDED_FOR'])
    if REQUEST.has_key('title'):
        f.write("Title: %s\n" % REQUEST['title'])
    if REQUEST.has_key('country'):
        f.write("Country: %s\n" % REQUEST['country'])
    f.close()


def logtheend(finalurl='not disclosed'):
    """ Log a line """
    f = open(cwd, 'a')
    f.write("Uploaded to: %s\n" % finalurl)
    f.write("Finished at %s\n" % time.ctime())
    f.close()


def showlog():
    """ Show the log """
    ret = open(cwd).read()
    return ret.split('\n\n')
