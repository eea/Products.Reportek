"""A downloaded blob file is sent after the request is done.

The publisher commits the transaction and closes the ZODB connection before
the server sends a file that the response holds. The file has to work then:
it is closed from another thread, with no connection, while the connection is
used by other requests, and the document can be replaced meanwhile.

These tests use a real ZODB with blobs, with a FileStorage and with ZEO, as in
production. The data is dummy.
"""

import os
import tempfile
import threading
import unittest
from gzip import GzipFile
from io import IOBase

import transaction
import ZODB
from ZODB.FileStorage import FileStorage

from Products.Reportek import RepUtils
from Products.Reportek.blob import FileContainer

try:
    import ZEO
except ImportError:  # pragma: no cover
    ZEO = None

DATA = b"dummy data, version one. " * 40000  # about 1 MB, several chunks
NEW_DATA = b"dummy data, the new version. " * 10


def in_thread(function):
    """Run function in another thread, like the server that sends the file."""
    outcome = {}

    def run():
        try:
            outcome["result"] = function()
        except BaseException as error:  # noqa: B036
            outcome["error"] = error
        # an implicit transaction that is joined here would be seen here
        outcome["joined"] = len(transaction.manager.get()._resources)

    thread = threading.Thread(target=run)
    thread.start()
    thread.join()
    return outcome


class BlobDownloadAfterRequestMixin:
    """The tests, for a kind of database that make_db returns."""

    compress = "no"

    def make_db(self, path):
        raise NotImplementedError

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = self.make_db(self.tmp.name)
        self.addCleanup(self.db.close)
        self.store(DATA)

    def store(self, data):
        """Create or replace the file of the document, in a transaction."""
        manager = transaction.TransactionManager()
        connection = self.db.open(transaction_manager=manager)
        root = connection.root()
        if "doc" not in root:
            root["doc"] = FileContainer(compress=self.compress)
        with root["doc"].open("wb", orig_size=len(data)) as handle:
            handle.write(data)
        manager.commit()
        connection.close()

    def request(self, skip_decompress=False):
        """Open the file as a download does, and end the request."""
        manager = transaction.TransactionManager()
        connection = self.db.open(transaction_manager=manager)
        handle = connection.root()["doc"].open(skip_decompress=skip_decompress)
        manager.abort()
        connection.close()
        return handle, connection

    def touch_all_connections(self):
        """Use the connections of the pool, which process the invalidations."""
        connections = [self.db.open() for _ in range(3)]
        for connection in connections:
            connection.sync()
        for connection in connections:
            connection.close()

    def test_the_file_can_be_read_after_the_request(self):
        handle, _ = self.request()
        self.assertEqual(handle.read(), DATA)

    def test_the_file_is_closed_from_another_thread_after_the_request(self):
        handle, _ = self.request()
        outcome = in_thread(handle.close)
        self.assertNotIn("error", outcome)
        self.assertTrue(handle.closed)

    def test_closing_the_file_does_not_join_a_transaction(self):
        handle, _ = self.request()
        self.assertEqual(in_thread(handle.close)["joined"], 0)

    def test_closing_the_file_does_not_change_the_pooled_connection(self):
        handle, connection = self.request()
        in_thread(handle.close)
        self.assertEqual(connection._registered_objects, [])
        self.assertEqual(connection._creating, {})
        self.touch_all_connections()
        # nothing was written: the document is the one that was stored
        self.assertEqual(self.read_stored(), DATA)

    def test_a_file_that_was_closed_is_not_closed_twice_by_the_server(self):
        handle, _ = self.request()
        handle.close()
        in_thread(handle.close)
        self.assertTrue(handle.closed)

    def read_stored(self):
        connection = self.db.open()
        try:
            with connection.root()["doc"].open() as handle:
                return handle.read()
        finally:
            connection.close()

    def test_the_download_goes_on_when_the_document_is_replaced_elsewhere(
        self,
    ):
        handle, request_connection = self.request()
        first = handle.read(100)

        # another connection replaces the document, while the download is open
        connections = [self.db.open() for _ in range(2)]
        writer = [c for c in connections if c is not request_connection][0]
        with writer.root()["doc"].open("wb", orig_size=len(NEW_DATA)) as out:
            out.write(NEW_DATA)
        transaction.commit()
        for connection in connections:
            connection.close()

        # the connections of the pool process the invalidation of the blob
        self.touch_all_connections()
        self.assertEqual(first + handle.read(), DATA)
        self.assertEqual(self.read_stored(), NEW_DATA)

    def test_the_document_can_be_replaced_while_it_is_downloaded(self):
        handle, _ = self.request()
        first = handle.read(100)
        # the connection of the download is the one that is used again
        self.store(NEW_DATA)
        self.assertEqual(self.read_stored(), NEW_DATA)
        self.assertEqual(first + handle.read(), DATA)
        self.touch_all_connections()
        in_thread(handle.close)
        self.assertTrue(handle.closed)

    def test_several_downloads_of_the_same_document_at_once(self):
        handles = [self.request()[0] for _ in range(3)]
        self.store(NEW_DATA)
        self.touch_all_connections()
        for handle in handles:
            self.assertEqual(handle.read(), DATA)
            in_thread(handle.close)
            self.assertTrue(handle.closed)

    def test_the_file_is_the_body_for_the_server(self):
        handle, _ = self.request()
        self.assertIsInstance(handle, IOBase)
        self.assertTrue(handle.seekable())
        handle.seek(0, 2)
        self.assertEqual(handle.tell(), len(DATA))
        handle.seek(0)

    def test_a_file_written_in_the_transaction_can_be_read_before_the_commit(
        self,
    ):
        manager = transaction.TransactionManager()
        connection = self.db.open(transaction_manager=manager)
        doc = connection.root()["doc"]
        with doc.open("wb", orig_size=len(NEW_DATA)) as out:
            out.write(NEW_DATA)
        with doc.open() as handle:
            self.assertEqual(handle.read(), NEW_DATA)
        manager.abort()
        connection.close()

    def test_the_file_is_read_when_its_file_is_removed_from_the_disk(self):
        # a pack, or the eviction of the blob cache of a ZEO client, removes
        # the file while it is sent: the open file goes on
        handle, _ = self.request()
        first = handle.read(1000)
        os.remove(handle.name)
        self.assertEqual(first + handle.read(), DATA)
        handle.close()

    def test_the_file_is_like_the_one_that_the_blob_gives(self):
        # what the readers of the files use: the name, the mode, the seeking,
        # the lines and the iteration
        manager = transaction.TransactionManager()
        connection = self.db.open(transaction_manager=manager)
        doc = connection.root()["doc"]
        with (
            doc._blob.open("r") as blob_file,
            doc.open(skip_decompress=True) as handle,
        ):
            self.assertEqual(handle.name, blob_file.name)
            self.assertEqual(handle.mode, blob_file.mode)
            for method in ("seekable", "readable", "writable", "isatty"):
                self.assertEqual(
                    getattr(handle, method)(), getattr(blob_file, method)()
                )
            self.assertEqual(handle.fileno() >= 0, blob_file.fileno() >= 0)
            self.assertEqual(handle.readline(), blob_file.readline())
            self.assertEqual(handle.tell(), blob_file.tell())
            handle.seek(100)
            blob_file.seek(100)
            self.assertEqual(handle.read(50), blob_file.read(50))
            self.assertEqual(list(handle), list(blob_file))
            buffer, other = bytearray(64), bytearray(64)
            handle.seek(0)
            blob_file.seek(0)
            self.assertEqual(handle.readinto(buffer), blob_file.readinto(other))
            self.assertEqual(buffer, other)
        manager.abort()
        connection.close()


class CompressedBlobDownloadAfterRequestMixin(BlobDownloadAfterRequestMixin):
    compress = "yes"

    def test_the_file_is_the_body_for_the_server(self):
        # a file that is decoded while it is read is not sent as a file
        handle, _ = self.request()
        self.assertIsInstance(handle, GzipFile)

    def test_the_decoded_file_is_closed_from_another_thread(self):
        handle, _ = self.request()
        raw = handle.fileobj
        self.assertEqual(handle.read(10), DATA[:10])
        outcome = in_thread(handle.close)
        self.assertNotIn("error", outcome)
        self.assertTrue(handle.closed)
        self.assertTrue(raw.closed)

    def test_the_stored_file_that_a_client_that_accepts_gzip_gets(self):
        handle, _ = self.request(skip_decompress=True)
        self.assertNotIsInstance(handle, GzipFile)
        self.assertIsInstance(handle, IOBase)
        self.assertEqual(GzipFile(fileobj=handle).read(), DATA)
        in_thread(handle.close)
        self.assertTrue(handle.closed)


class FileStorageBlobDownloadTest(BlobDownloadAfterRequestMixin, unittest.TestCase):
    def make_db(self, path):
        return ZODB.DB(
            FileStorage(
                os.path.join(path, "Data.fs"),
                blob_dir=os.path.join(path, "blobs"),
            )
        )


class FileStorageCompressedBlobDownloadTest(
    CompressedBlobDownloadAfterRequestMixin, unittest.TestCase
):
    make_db = FileStorageBlobDownloadTest.make_db


@unittest.skipIf(ZEO is None, "ZEO is not installed")
class ZEOBlobDownloadTest(BlobDownloadAfterRequestMixin, unittest.TestCase):
    def make_db(self, path):
        # a server and a client with its own blob cache, as in production
        address, stop = ZEO.server(
            path=os.path.join(path, "zeo.fs"),
            blob_dir=os.path.join(path, "server-blobs"),
            threaded=True,
        )
        self.addCleanup(stop)
        return ZEO.DB(
            address,
            blob_dir=os.path.join(path, "client-blobs"),
            shared_blob_dir=False,
        )


@unittest.skipIf(ZEO is None, "ZEO is not installed")
class ZEOCompressedBlobDownloadTest(
    CompressedBlobDownloadAfterRequestMixin, unittest.TestCase
):
    make_db = ZEOBlobDownloadTest.make_db


class ResponseWithFileAfterRequestTest(unittest.TestCase):
    """The helper that sets the headers returns the file for the server."""

    def test_the_file_of_a_blob_goes_through_the_response_helper(self):
        from unittest.mock import Mock

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        db = ZODB.DB(
            FileStorage(
                os.path.join(tmp.name, "Data.fs"),
                blob_dir=os.path.join(tmp.name, "blobs"),
            )
        )
        self.addCleanup(db.close)
        manager = transaction.TransactionManager()
        connection = db.open(transaction_manager=manager)
        doc = connection.root()["doc"] = FileContainer(compress="no")
        with doc.open("wb", orig_size=len(DATA)) as out:
            out.write(DATA)
        manager.commit()
        handle = doc.open()
        request = Mock()
        request.get_header = lambda name, default=None: default
        body = RepUtils.http_response_with_file(
            request, Mock(), handle, "text/plain", len(DATA), 1700000000
        )
        manager.abort()
        connection.close()
        self.assertIs(body, handle)
        self.assertEqual(body.read(), DATA)
        in_thread(body.close)
        self.assertTrue(handle.closed)


class SharedBlobDirMixin:
    """The blob directory of the ZEO server is mounted in the client:
    zeoSharedBlobDir in the deployment."""

    def make_db(self, path):
        address, stop = ZEO.server(
            path=os.path.join(path, "zeo.fs"),
            blob_dir=os.path.join(path, "blobs"),
            threaded=True,
        )
        self.addCleanup(stop)
        return ZEO.DB(
            address,
            blob_dir=os.path.join(path, "blobs"),
            shared_blob_dir=True,
        )


@unittest.skipIf(ZEO is None, "ZEO is not installed")
class ZEOSharedBlobDirDownloadTest(
    SharedBlobDirMixin, BlobDownloadAfterRequestMixin, unittest.TestCase
):
    def test_the_file_is_the_file_of_the_shared_directory(self):
        handle, _ = self.request()
        self.assertTrue(handle.name.startswith(self.tmp.name))
        self.assertIn("blobs", handle.name)
        handle.close()


@unittest.skipIf(ZEO is None, "ZEO is not installed")
class ZEOSharedBlobDirCompressedDownloadTest(
    SharedBlobDirMixin,
    CompressedBlobDownloadAfterRequestMixin,
    unittest.TestCase,
):
    pass


def test_suite():
    return unittest.TestSuite(
        [
            unittest.defaultTestLoader.loadTestsFromTestCase(case)
            for case in (
                FileStorageBlobDownloadTest,
                FileStorageCompressedBlobDownloadTest,
                ZEOBlobDownloadTest,
                ZEOCompressedBlobDownloadTest,
                ZEOSharedBlobDirDownloadTest,
                ZEOSharedBlobDirCompressedDownloadTest,
                ResponseWithFileAfterRequestTest,
            )
        ]
    )
