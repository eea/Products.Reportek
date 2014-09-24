import gzip


class GzipFileRaw(gzip.GzipFile):
    # inherit GzipFile init. give both filenam and fileobj opened for writing
    def __init__(self, filename=None, mode=None,
                 compresslevel=9, fileobj=None, mtime=None, crc=None, orig_size=None):
        if mode != 'w' and mode != 'wb':
            raise NotImplementedError("GzipFileRaw is only for writing")
        #if not (filename and fileobj):
        #    raise ValueError("Need to know the name of the file inside zip. provide both filename and fileobj")
        # TODO: wecould also compute the CRC ourselves
        if not (crc and orig_size):
            ValueError("Supply CRC and original size from the already compressed archive the content stems from")
        super(GzipFileRaw, self).__init__(filename, mode, compresslevel, fileobj, mtime)
        self.crc = crc
        self.size = orig_size

    def write(self, compressedBuffer):
        self._check_closed()
        if self.mode != gzip.WRITE:
            import errno
            raise IOError(errno.EBADF, "write() on read-only GzipFile object")

        if len(compressedBuffer) > 0:
            self.fileobj.write(compressedBuffer)
            self.offset += len(compressedBuffer)

        return len(compressedBuffer)

    def close(self):
        if self.fileobj is None:
            return
        self.fileobj.flush()
        gzip.write32u(self.fileobj, self.crc)
        gzip.write32u(self.fileobj, self.size & 0xffffffffL)
        self.fileobj = None
        if self.myfileobj:
            self.myfileobj.close()
            self.myfileobj = None

    def seekable(self):
        return False

    def seek(self, offset, whence=0):
        raise NotImplementedError

    def rewind(self):
        raise NotImplementedError

    def read(self, size=-1):
        raise NotImplementedError

    def readline(self, size=-1):
        raise NotImplementedError

    def flush(self):
        raise NotImplementedError
