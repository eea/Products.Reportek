"""Tests for the downloads of files and zips, which are streamed.

response.write() does not stream under WSGI: the publisher keeps what was
written in memory until the request is done. Only a body that is a file or a
stream iterator is sent while it is read, so the downloads have to return one.
A file is handed to the server (wsgi.file_wrapper), which sends it from its own
loop, without a thread waiting for a slow client, and closes it. A file that
has to be decoded while it is read is sent with a stream iterator.
"""

import tempfile
import zipfile
from gzip import GzipFile
from gzip import compress as gzip_compress
from io import BytesIO, IOBase
from time import localtime
from unittest.mock import Mock, call, patch

from zope.datetime import rfc1123_date
from ZPublisher.Iterators import IUnboundStreamIterator

from Products.Reportek import Document, RepUtils
from Products.Reportek.blob import FileContainer, OfsBlobFile

from .common import BaseUnitTest
from .utils import (
    add_document,
    create_envelope,
    create_fake_root,
    create_upload_file,
)

MTIME = 1700000000
DATA = bytes(range(256)) * 1200  # 307200 bytes, more than two chunks


class SpyFile(BytesIO):
    """A file that counts what is read from it."""

    def __init__(self, data):
        super().__init__(data)
        self.reads = 0

    def read(self, *args):
        self.reads += 1
        return super().read(*args)


def request_with(if_modified_since=None, accept_encoding=None):
    request = Mock()
    headers = {"If-Modified-Since": if_modified_since}
    request.get_header = lambda name, default=None: headers.get(name, default)
    request.getHeader = Mock(return_value=accept_encoding)
    return request


class StreamIteratorTest(BaseUnitTest):
    def setUp(self):
        self.closed = []

    def stream(self, chunks):
        return RepUtils.StreamIterator(chunks, lambda: self.closed.append(1))

    def test_it_is_a_stream_for_the_publisher(self):
        self.assertTrue(IUnboundStreamIterator.providedBy(self.stream([])))

    def test_the_chunks_are_sent_and_the_source_is_closed_at_the_end(self):
        self.assertEqual(list(self.stream([b"a", b"b", b"c"])), [b"a", b"b", b"c"])
        self.assertEqual(self.closed, [1])

    def test_nothing_is_read_before_it_is_iterated(self):
        read = []

        def chunks():
            read.append(1)
            yield b"a"

        stream = self.stream(chunks())
        self.assertEqual(read, [])
        self.assertEqual(next(stream), b"a")
        self.assertEqual(read, [1])

    def test_closing_before_the_end_closes_the_source_once(self):
        stream = self.stream([b"a", b"b"])
        next(stream)
        stream.close()
        stream.close()
        self.assertEqual(self.closed, [1])

    def test_the_source_is_closed_when_reading_fails(self):
        def chunks():
            yield b"a"
            raise OSError("the file cannot be read")

        stream = self.stream(chunks())
        next(stream)
        with self.assertRaises(OSError):
            next(stream)
        self.assertEqual(self.closed, [1])

    def test_it_has_no_close_function_to_call_for_a_source_without_one(self):
        stream = RepUtils.StreamIterator([b"a"])
        self.assertEqual(list(stream), [b"a"])
        stream.close()


class ResponseWithFileTest(BaseUnitTest):
    def respond(self, data=DATA, **request_args):
        self.file = SpyFile(data)
        self.request = request_with(**request_args)
        self.response = Mock()
        return RepUtils.http_response_with_file(
            self.request,
            self.response,
            self.file,
            "text/plain",
            len(data),
            MTIME,
        )

    def respond_gzip(self, data=DATA):
        self.file = GzipFile(fileobj=BytesIO(gzip_compress(data)), mode="rb")
        self.response = Mock()
        return RepUtils.http_response_with_file(
            request_with(),
            self.response,
            self.file,
            "text/plain",
            len(data),
            MTIME,
        )

    def test_a_file_is_the_body_for_the_server_to_send(self):
        body = self.respond()
        self.assertIs(body, self.file)
        self.assertIsInstance(body, IOBase)

    def test_the_file_is_not_read_or_closed_by_the_response(self):
        body = self.respond()
        self.assertEqual(self.file.reads, 0)
        self.assertFalse(self.file.closed)
        self.assertEqual(body.read(), DATA)

    def test_a_file_decoded_while_it_is_read_is_streamed(self):
        body = self.respond_gzip()
        self.assertIsNot(body, self.file)
        self.assertTrue(IUnboundStreamIterator.providedBy(body))
        chunks = list(body)
        self.assertEqual(b"".join(chunks), DATA)
        self.assertGreater(len(chunks), 1)

    def test_a_decoded_file_is_not_read_until_the_body_is_sent(self):
        body = self.respond_gzip()
        self.assertFalse(self.file.closed)
        self.assertEqual(self.file.fileobj.tell(), 0)
        list(body)
        self.assertTrue(self.file.closed)

    def test_a_decoded_file_is_closed_when_the_response_is_closed_early(self):
        body = self.respond_gzip()
        next(body)
        body.close()
        self.assertTrue(self.file.closed)

    def test_nothing_is_written_to_the_response(self):
        list(self.respond())
        list(self.respond_gzip())
        self.response.write.assert_not_called()

    def test_the_headers_are_set(self):
        self.respond()
        self.assertEqual(
            self.response.setHeader.call_args_list,
            [
                call("Last-Modified", rfc1123_date(MTIME)),
                call("Content-Type", "text/plain"),
                call("Content-Length", len(DATA)),
            ],
        )

    def test_a_file_that_was_not_modified_has_no_body(self):
        body = self.respond(if_modified_since=rfc1123_date(MTIME))
        self.assertEqual(body, "")
        self.response.setStatus.assert_called_once_with(304)
        self.assertTrue(self.file.closed)
        self.assertEqual(self.file.reads, 0)

    def test_a_file_that_is_older_than_the_date_of_the_client_has_no_body(
        self,
    ):
        body = self.respond(if_modified_since=rfc1123_date(MTIME + 3600))
        self.assertEqual(body, "")
        self.response.setStatus.assert_called_once_with(304)

    def test_a_file_that_is_newer_than_the_date_of_the_client_is_sent(self):
        body = self.respond(if_modified_since=rfc1123_date(MTIME - 3600))
        self.assertEqual(b"".join(body), DATA)
        self.response.setStatus.assert_not_called()

    def test_a_date_that_is_not_valid_is_ignored(self):
        body = self.respond(if_modified_since="not a date")
        self.assertEqual(b"".join(body), DATA)

    def test_the_file_is_closed_when_the_headers_fail(self):
        file = SpyFile(DATA)
        response = Mock()
        response.setHeader.side_effect = ValueError("bad header")
        with self.assertRaises(ValueError):
            RepUtils.http_response_with_file(
                request_with(), response, file, "text/plain", len(DATA), MTIME
            )
        self.assertTrue(file.closed)


class DocumentDownloadTest(BaseUnitTest):
    def document(self, data=DATA, compression="no"):
        doc = Document.Document("testdoc", "Document for Test")
        doc.data_file._toCompress = compression
        with patch.object(
            doc, "getWorkitemsActiveForMe", Mock(return_value=[]), create=True
        ):
            doc.manage_file_upload(create_upload_file(data))
        self.handles = []
        real_open = doc.data_file.open

        def spy_open(*args, **kwargs):
            handle = real_open(*args, **kwargs)
            self.handles.append(handle)
            return handle

        doc.data_file.open = spy_open
        return doc

    def download(self, doc, **request_args):
        request = request_with(**request_args)
        response = Mock()
        return doc.index_html(request, response), response

    def test_the_file_is_sent_by_the_server(self):
        body, response = self.download(self.document())
        self.assertIsInstance(body, IOBase)
        self.assertEqual(body.read(), DATA)
        response.write.assert_not_called()

    def test_the_size_is_in_the_headers(self):
        _, response = self.download(self.document())
        self.assertIn(
            call("Content-Length", len(DATA)),
            response.setHeader.call_args_list,
        )

    def test_the_file_stays_open_until_the_server_closes_it(self):
        body, _ = self.download(self.document())
        self.assertEqual(len(self.handles), 1)
        self.assertIs(body, self.handles[0])
        self.assertEqual(body.read(), DATA)
        self.assertFalse(body.closed)
        body.close()
        self.assertTrue(self.handles[0].closed)

    def test_the_file_is_closed_if_the_response_is_dropped(self):
        body, _ = self.download(self.document())
        body.close()
        self.assertTrue(self.handles[0].closed)

    def test_a_file_stored_compressed_is_decoded_as_it_is_streamed(self):
        doc = self.document(compression="yes")
        self.assertTrue(doc.is_compressed())
        body, response = self.download(doc)
        self.assertTrue(IUnboundStreamIterator.providedBy(body))
        self.assertEqual(b"".join(body), DATA)
        self.assertTrue(self.handles[0].closed)
        self.assertNotIn(
            call("content-encoding", "gzip"), response.setHeader.call_args_list
        )

    def test_a_client_that_accepts_gzip_gets_the_stored_compressed_file(self):
        doc = self.document(compression="yes")
        body, response = self.download(doc, accept_encoding="gzip,deflate")
        self.assertIsInstance(body, IOBase)
        compressed = body.read()
        self.assertEqual(len(compressed), doc.data_file.compressed_size)
        self.assertLess(len(compressed), len(DATA))
        self.assertIn(
            call("content-encoding", "gzip"), response.setHeader.call_args_list
        )
        self.assertIn(
            call("Content-Length", doc.data_file.compressed_size),
            response.setHeader.call_args_list,
        )

    def test_a_file_that_was_not_modified_is_closed_and_has_no_body(self):
        doc = self.document()
        body, response = self.download(
            doc, if_modified_since=rfc1123_date(doc.data_file.mtime + 60)
        )
        self.assertEqual(body, "")
        response.setStatus.assert_called_once_with(304)
        self.assertTrue(self.handles[0].closed)

    def test_the_icon_is_sent_by_the_server(self):
        doc = self.document()
        body = doc.icon_gif(request_with(), Mock())
        self.assertIsInstance(body, IOBase)
        self.assertTrue(body.read().startswith(b"GIF8"))
        body.close()

    def test_the_icon_is_returned_by_the_file_with_the_icon_argument(self):
        doc = self.document()
        body = doc.index_html(request_with(), Mock(), icon=1)
        self.assertTrue(body.read().startswith(b"GIF8"))
        body.close()


class EmptyFileTest(BaseUnitTest):
    """An empty file has the size 0, also when it is stored compressed: a
    compressed empty file is a gzip stream of some bytes, which was its size,
    and so the Content-Length of its download, that has no content."""

    def document(self, data, compression):
        return DocumentDownloadTest.document(self, data, compression)

    def test_the_size_of_an_empty_document_is_zero(self):
        for compression in ("yes", "no"):
            doc = self.document(b"", compression)
            self.assertEqual(doc.data_file.size, 0, compression)

    def test_the_stored_size_of_an_empty_compressed_document(self):
        doc = self.document(b"", "yes")
        self.assertTrue(doc.is_compressed())
        self.assertGreater(doc.data_file.compressed_size, 0)

    def test_the_download_of_an_empty_document_has_no_content_and_length_0(
        self,
    ):
        for compression in ("yes", "no"):
            doc = self.document(b"", compression)
            response = Mock()
            body = doc.index_html(request_with(), response)
            self.assertEqual(
                body.read() if hasattr(body, "read") else b"".join(body), b""
            )
            self.assertIn(call("Content-Length", 0), response.setHeader.call_args_list)

    def test_a_client_that_accepts_gzip_gets_the_stored_stream_with_its_length(
        self,
    ):
        doc = self.document(b"", "yes")
        response = Mock()
        body = doc.index_html(request_with(accept_encoding="gzip"), response)
        stored = body.read()
        self.assertEqual(len(stored), doc.data_file.compressed_size)
        self.assertEqual(GzipFile(fileobj=BytesIO(stored)).read(), b"")
        self.assertIn(
            call("Content-Length", doc.data_file.compressed_size),
            response.setHeader.call_args_list,
        )

    def test_the_size_that_the_caller_computed_is_the_size(self):
        data_file = FileContainer(compress="yes")
        with data_file.open("wb", orig_size=1234) as handle:
            handle.write(b"x" * 10)
        self.assertEqual(data_file.size, 1234)

    def test_without_a_size_the_size_is_the_one_of_the_file(self):
        data_file = FileContainer(compress="no")
        with data_file.open("wb") as handle:
            handle.write(b"x" * 10)
        self.assertEqual(data_file.size, 10)

    def test_an_empty_file_that_is_not_compressed_has_the_size_0(self):
        data_file = FileContainer(compress="no")
        with data_file.open("wb", orig_size=0):
            pass
        self.assertEqual(data_file.size, 0)


class BlobFileDownloadTest(BaseUnitTest):
    def blob_file(self, content_type, data=DATA):
        blob_file = OfsBlobFile("blobfile")
        blob_file.data_file.content_type = content_type
        with blob_file.data_file.open("wb", orig_size=len(data)) as handle:
            handle.write(data)
        return blob_file

    def test_the_file_is_sent_by_the_server(self):
        response = Mock()
        body = self.blob_file("application/octet-stream").index_html(
            request_with(), response
        )
        self.assertIsInstance(body, IOBase)
        self.assertEqual(body.read(), DATA)
        body.close()
        response.write.assert_not_called()

    def test_the_headers_have_the_size_and_the_type(self):
        response = Mock()
        self.blob_file("application/octet-stream").index_html(request_with(), response)
        self.assertIn(
            call("Content-Length", len(DATA)),
            response.setHeader.call_args_list,
        )
        self.assertIn(
            call("Content-Type", "application/octet-stream"),
            response.setHeader.call_args_list,
        )

    def test_the_view_of_a_page_is_streamed_between_the_header_and_the_footer(
        self,
    ):
        blob_file = self.blob_file("text/html", b"<p>the content</p>")
        response = Mock()
        with patch.object(
            OfsBlobFile,
            "_view_tmpl",
            Mock(return_value="<body>HEADER-FOOTER-SPLIT</body>"),
        ):
            body = blob_file.view(request_with(), response)
        self.assertTrue(IUnboundStreamIterator.providedBy(body))
        self.assertEqual(b"".join(body), b"<body><p>the content</p></body>")
        response.write.assert_not_called()

    def test_the_file_of_the_view_is_closed_when_it_is_dropped(self):
        blob_file = self.blob_file("text/html", b"<p>the content</p>")
        with patch.object(
            OfsBlobFile, "_view_tmpl", Mock(return_value="HEADER-FOOTER-SPLIT")
        ):
            body = blob_file.view(request_with(), Mock())
        next(body)
        body.close()


class ZipEnvelopesStreamTest(BaseUnitTest):
    def setUp(self):
        self.root = create_fake_root()
        from .common import BaseTest

        self.engine = BaseTest.create_reportek_engine(self.root)
        self.tmpfiles = []

    def envelope(self, id="envelope", released=True):
        envelope = create_envelope(self.root, id)
        add_document(envelope, create_upload_file(DATA, "big.dat"))
        add_document(envelope, create_upload_file("small", "small.txt"))
        envelope.released = released
        envelope.title = "Title-" + id
        return envelope

    def zip_envelopes(self, paths):
        response = Mock()
        real = tempfile.TemporaryFile

        def spy(*args, **kwargs):
            tmpfile = real(*args, **kwargs)
            self.tmpfiles.append(tmpfile)
            return tmpfile

        with (
            patch("Products.Reportek.ReportekEngine.getSecurityManager"),
            patch("tempfile.TemporaryFile", spy),
        ):
            body = self.engine.zipEnvelopes(paths, Mock(), response)
        return body, response

    def test_the_zip_is_streamed(self):
        self.envelope()
        body, response = self.zip_envelopes(["/envelope"])
        self.assertIsInstance(body, IOBase)
        content = body.read()
        response.write.assert_not_called()
        with zipfile.ZipFile(BytesIO(content)) as archive:
            self.assertEqual(
                archive.namelist(),
                [
                    "Title-envelope/big.dat",
                    "Title-envelope/small.txt",
                    "Title-envelope/metadata.txt",
                    "Title-envelope/README.txt",
                    "Title-envelope/history.txt",
                ],
            )
            self.assertEqual(archive.read("Title-envelope/big.dat"), DATA)
            self.assertEqual(archive.read("Title-envelope/small.txt"), b"small")
            self.assertIsNone(archive.testzip())

    def test_the_documents_are_compressed(self):
        self.envelope()
        body, _ = self.zip_envelopes(["/envelope"])
        with zipfile.ZipFile(BytesIO(body.read())) as archive:
            info = archive.getinfo("Title-envelope/big.dat")
            self.assertEqual(info.compress_type, zipfile.ZIP_DEFLATED)

    def test_the_entries_have_the_current_time_and_the_mode_of_a_file(self):
        self.envelope()
        body, _ = self.zip_envelopes(["/envelope"])
        year = localtime().tm_year
        with zipfile.ZipFile(BytesIO(body.read())) as archive:
            for info in archive.infolist():
                self.assertEqual(info.date_time[0], year, info.filename)
                self.assertEqual(info.external_attr >> 16, 0o100600)

    def test_the_headers_have_the_size_of_the_zip(self):
        self.envelope()
        body, response = self.zip_envelopes(["/envelope"])
        content = body.read()
        self.assertIn(
            call("Content-Length", len(content)),
            response.setHeader.call_args_list,
        )
        self.assertIn(
            call("Content-Type", "application/x-zip"),
            response.setHeader.call_args_list,
        )
        self.assertIn(
            call("Content-Disposition", 'attachment; filename="envelopes.zip"'),
            response.setHeader.call_args_list,
        )

    def test_the_zip_is_the_file_for_the_server_to_send_and_close(self):
        self.envelope()
        body, _ = self.zip_envelopes(["/envelope"])
        self.assertEqual(len(self.tmpfiles), 1)
        self.assertIs(body, self.tmpfiles[0])
        self.assertFalse(body.closed)
        self.assertEqual(body.tell(), 0)
        body.close()
        self.assertTrue(self.tmpfiles[0].closed)

    def test_several_envelopes_are_zipped_together(self):
        self.envelope("first")
        self.envelope("second")
        body, _ = self.zip_envelopes(["/first", "/second"])
        with zipfile.ZipFile(BytesIO(body.read())) as archive:
            names = archive.namelist()
        self.assertEqual(len([n for n in names if n.startswith("Title-first/")]), 5)
        self.assertEqual(len([n for n in names if n.startswith("Title-second/")]), 5)

    def test_an_envelope_that_is_not_released_and_one_that_does_not_exist_are_skipped(
        self,
    ):
        self.envelope("released")
        self.envelope("draft", released=False)
        body, _ = self.zip_envelopes(["/released", "/draft", "/missing"])
        with zipfile.ZipFile(BytesIO(body.read())) as archive:
            self.assertEqual(
                {n.split("/")[0] for n in archive.namelist()},
                {"Title-released"},
            )

    def test_nothing_is_returned_without_envelopes(self):
        body, response = self.zip_envelopes([])
        self.assertIsNone(body)
        response.setHeader.assert_not_called()
        self.assertEqual(self.tmpfiles, [])

    def test_the_file_of_the_zip_is_closed_when_it_cannot_be_built(self):
        self.envelope()
        with (
            patch(
                "Products.Reportek.zip_content.get_metadata_content",
                side_effect=ValueError("no metadata"),
            ),
            self.assertRaises(ValueError),
        ):
            self.zip_envelopes(["/envelope"])
        self.assertEqual(len(self.tmpfiles), 1)
        self.assertTrue(self.tmpfiles[0].closed)
