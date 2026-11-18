"""The files of a zip archive: listed, and downloaded one at a time.

An archive is read from its end, where the list is, and a file of it from its
own place, so what is read must not depend on how big the archive is.
"""

import zipfile
from io import BytesIO, IOBase
from unittest.mock import Mock, patch

from AccessControl import SpecialUsers
from plone.protect.interfaces import IDisableCSRFProtection
from zope.interface import alsoProvides
from AccessControl.SecurityManagement import newSecurityManager, noSecurityManager
from zExceptions import BadRequest, NotFound, Unauthorized

from Products.Reportek import Document
from Products.Reportek.Document import (
    ArchiveTooBig,
    ZipMemberReader,
    _attachment,
)

from .common import BaseUnitTest
from .utils import create_upload_file

BIG = bytes(range(256)) * 8192  # 2 MB


def make_zip(files, compression=zipfile.ZIP_STORED, encrypted=()):
    out = BytesIO()
    with zipfile.ZipFile(out, "w", compression) as archive:
        for name, data in files:
            info = zipfile.ZipInfo(name)
            info.compress_type = compression
            archive.writestr(info, data)
    data = bytearray(out.getvalue())
    # writestr clears the flag, so it is set in the central directory
    position = data.find(b"PK\x01\x02")
    while position != -1:
        name_length = int.from_bytes(data[position + 28 : position + 30], "little")
        name = bytes(data[position + 46 : position + 46 + name_length]).decode()
        if name in encrypted:
            data[position + 8] |= 0x1
        position = data.find(b"PK\x01\x02", position + 1)
    return bytes(data)


class CountingFile:
    """What the document opens: counts the bytes that are read."""

    def __init__(self, data):
        self._file = BytesIO(data)
        self.bytes_read = 0
        self.closed = False

    def read(self, *args):
        data = self._file.read(*args)
        self.bytes_read += len(data)
        return data

    def seek(self, *args):
        return self._file.seek(*args)

    def tell(self):
        return self._file.tell()

    def seekable(self):
        return True

    def readable(self):
        return True

    def close(self):
        self.closed = True


class ZipDocumentTest(BaseUnitTest):
    def setUp(self):
        # the files of an archive are for the users that are logged in
        newSecurityManager(None, SpecialUsers.system)
        self.addCleanup(noSecurityManager)

    def document(
        self,
        data,
        name="archive.zip",
        content_type="application/zip",
        compress="no",
        spy=True,
    ):
        doc = Document.Document(name, "Document for Test")
        doc.content_type = content_type
        doc.data_file._toCompress = compress
        with patch.object(
            doc, "getWorkitemsActiveForMe", Mock(return_value=[]), create=True
        ):
            doc.manage_file_upload(create_upload_file(data, name))
        doc.absolute_url = Mock(return_value="http://x/env/" + name)
        # from the envelope: whether its content can be seen
        doc.canViewContent = Mock(return_value=True)
        self.opened = []
        real_open = doc.data_file.open

        def spy_open(*args, **kwargs):
            real = real_open(*args, **kwargs)
            try:
                handle = CountingFile(real.read())
            finally:
                real.close()
            self.opened.append(handle)
            return handle

        def record_open(*args, **kwargs):
            handle = real_open(*args, **kwargs)
            self.opened.append(handle)
            return handle

        if spy == "real":
            doc.data_file.open = record_open
        elif spy:
            doc.data_file.open = spy_open
        return doc

    def download(self, doc, name, if_modified_since=None):
        request = Mock()
        request.get_header = lambda key, default=None: (
            if_modified_since if key == "If-Modified-Since" else default
        )
        response = Mock()
        return doc.zip_member(name, request, response), response

    def headers(self, response):
        return {c.args[0]: c.args[1] for c in response.setHeader.call_args_list}

    def body(self, body):
        """What the server sends: the file, that it closes at the end."""
        try:
            return body.read()
        finally:
            body.close()


class ListMembersTest(ZipDocumentTest):
    def test_the_files_of_the_archive_are_listed_with_their_size(self):
        doc = self.document(make_zip([("a.xml", b"<a/>"), ("b.txt", b"hello")]))
        members = doc.get_zip_members()
        self.assertEqual([m["name"] for m in members], ["a.xml", "b.txt"])
        self.assertEqual([m["size"] for m in members], [4, 5])
        self.assertEqual(
            members[0]["url"], "http://x/env/archive.zip/zip_member?name=a.xml"
        )

    def test_folders_are_not_listed_and_the_files_in_them_are_listed_with_their_path(
        self,
    ):
        data = make_zip(
            [
                ("folder/", b""),
                ("folder/in.txt", b"x"),
                ("out.txt", b"y"),
                ("w\\in.txt", b"z"),
            ]
        )
        members = self.document(data).get_zip_members()
        self.assertEqual(
            [m["name"] for m in members], ["folder/in.txt", "out.txt", "w\\in.txt"]
        )

    def test_a_shapefile_in_a_folder_without_a_folder_entry_is_listed(self):
        # an archive of a GIS export has no entry for the folder, only the paths
        names = ["Area/Area.%s" % ext for ext in ("cpg", "dbf", "prj", "shp", "shx")]
        members = self.document(make_zip([(n, b"x") for n in names])).get_zip_members()
        self.assertEqual([m["name"] for m in members], names)

    def test_a_name_is_quoted_in_its_link(self):
        members = self.document(make_zip([("a b&c.txt", b"x")])).get_zip_members()
        self.assertTrue(members[0]["url"].endswith("?name=a%20b%26c.txt"))

    def test_a_name_that_is_in_the_archive_twice_is_listed_once(self):
        with self.assertWarns(UserWarning):
            data = make_zip([("a.txt", b"first"), ("a.txt", b"second one")])
        members = self.document(data).get_zip_members()
        self.assertEqual([(m["name"], m["size"]) for m in members], [("a.txt", 10)])

    def test_a_file_that_is_not_a_zip_has_no_files(self):
        doc = self.document(b"not a zip at all", name="data.zip")
        self.assertEqual(doc.get_zip_members(), [])
        self.assertTrue(self.opened[0].closed)

    def test_a_file_that_is_not_an_archive_by_type_or_name_is_not_opened(self):
        doc = self.document(
            make_zip([("a", b"x")]), "data.bin", "application/x-unknown"
        )
        self.assertFalse(doc.is_zip())
        self.assertEqual(doc.get_zip_members(), [])
        self.assertEqual(self.opened, [])

    def test_a_zip_with_the_type_of_any_file_is_known_by_its_name(self):
        doc = self.document(
            make_zip([("a", b"x")]), "data.ZIP", "application/octet-stream"
        )
        self.assertTrue(doc.is_zip())
        self.assertEqual(len(doc.get_zip_members()), 1)

    def test_only_the_end_of_the_archive_is_read_to_list_it(self):
        data = make_zip([("one.bin", BIG), ("two.bin", BIG), ("three.bin", BIG)])
        doc = self.document(data)
        self.assertEqual(len(doc.get_zip_members()), 3)
        self.assertLess(self.opened[0].bytes_read, 4096)
        self.assertTrue(self.opened[0].closed)

    def test_an_archive_that_is_stored_compressed_is_listed(self):
        doc = self.document(
            make_zip([("a.xml", b"<a/>")]),
            content_type="application/octet-stream",
            compress="yes",
            spy=False,
        )
        self.assertTrue(doc.is_compressed())
        self.assertEqual([m["name"] for m in doc.get_zip_members()], ["a.xml"])

    def test_encrypted_and_too_big_files_are_marked(self):
        data = make_zip([("s.txt", b"x"), ("b.bin", b"y" * 10)], encrypted=("s.txt",))
        with patch.object(Document, "ZIP_MEMBER_MAX_SIZE", 5):
            members = {m["name"]: m for m in self.document(data).get_zip_members()}
        self.assertTrue(members["s.txt"]["encrypted"])
        self.assertFalse(members["s.txt"]["too_big"])
        self.assertTrue(members["b.bin"]["too_big"])


class DownloadMemberTest(ZipDocumentTest):
    def test_the_file_is_sent_as_it_is_in_the_archive(self):
        for compression in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
            doc = self.document(
                make_zip([("a.xml", b"<a>text</a>"), ("b.txt", b"other")], compression)
            )
            body, _ = self.download(doc, "a.xml")
            self.assertEqual(self.body(body), b"<a>text</a>")

    def test_the_body_is_a_file_for_the_server_to_send(self):
        body, response = self.download(
            self.document(make_zip([("a.txt", b"hello")])), "a.txt"
        )
        self.assertIsInstance(body, IOBase)
        self.assertEqual(body.tell(), 0)
        response.write.assert_not_called()
        self.assertEqual(self.body(body), b"hello")

    def test_nothing_waits_for_the_client_the_archive_is_closed_when_it_is_copied(
        self,
    ):
        doc = self.document(make_zip([("a.txt", b"x" * 1000)]))
        body, _ = self.download(doc, "a.txt")
        # the file of the blob is closed already: the body is a copy
        self.assertTrue(self.opened[0].closed)
        self.assertFalse(body.closed)
        self.assertEqual(len(self.body(body)), 1000)
        self.assertTrue(body.closed)

    def test_the_copy_is_in_memory_when_it_is_small_and_in_the_zip_cache_when_not(
        self,
    ):
        doc = self.document(make_zip([("a.txt", b"x")]))
        with patch.object(
            Document.tempfile,
            "SpooledTemporaryFile",
            wraps=Document.tempfile.SpooledTemporaryFile,
        ) as spooled, patch.object(
            Document.RepUtils, "get_zip_cache", return_value="/the/zip/cache"
        ):
            body, _ = self.download(doc, "a.txt")
        spooled.assert_called_once_with(
            max_size=Document.ZIP_SPOOL_SIZE, dir="/the/zip/cache"
        )
        self.assertEqual(self.body(body), b"x")

    def test_a_big_file_goes_to_a_file_and_is_sent_whole(self):
        doc = self.document(make_zip([("big.bin", BIG)]))
        with patch.object(Document, "ZIP_SPOOL_SIZE", 1024):
            body, _ = self.download(doc, "big.bin")
        # over the size that stays in memory: it is a file on the disk now
        self.assertTrue(body._rolled)
        self.assertEqual(self.body(body), BIG)

    def test_the_headers_tell_what_is_sent(self):
        doc = self.document(make_zip([("report.xml", b"<a/>")]))
        _, response = self.download(doc, "report.xml")
        headers = self.headers(response)
        self.assertEqual(headers["Content-Length"], 4)
        self.assertEqual(headers["Content-Type"], "text/xml")
        self.assertTrue(headers["Content-Disposition"].startswith("attachment;"))
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")

    def test_a_type_that_is_not_known_is_a_download(self):
        doc = self.document(make_zip([("data.qqq", b"x")]))
        _, response = self.download(doc, "data.qqq")
        self.assertEqual(
            self.headers(response)["Content-Type"], "application/octet-stream"
        )

    def test_only_the_file_that_is_asked_for_is_read(self):
        data = make_zip([("one.bin", BIG), ("two.bin", b"small"), ("three.bin", BIG)])
        doc = self.document(data)
        body, _ = self.download(doc, "two.bin")
        self.assertEqual(self.body(body), b"small")
        self.assertLess(self.opened[0].bytes_read, 8192)

    def test_the_copy_is_closed_when_the_server_closes_it(self):
        doc = self.document(make_zip([("a.txt", b"x")]))
        body, _ = self.download(doc, "a.txt")
        self.assertFalse(body.closed)
        body.close()
        self.assertTrue(body.closed)
        self.assertTrue(self.opened[0].closed)

    def test_a_file_that_is_not_in_the_archive_is_not_found(self):
        doc = self.document(make_zip([("a.txt", b"x"), ("d/", b"")]))
        for name in ("missing.txt", "d/", "../a.txt", "d/a.txt", ""):
            with self.assertRaises(NotFound):
                self.download(doc, name)
            self.assertTrue(self.opened[-1].closed)

    def test_a_file_in_a_folder_is_sent_and_saved_with_its_own_name(self):
        doc = self.document(make_zip([("Area/sub/Area.shp", b"shape")]))
        body, response = self.download(doc, "Area/sub/Area.shp")
        self.assertEqual(self.body(body), b"shape")
        disposition = self.headers(response)["Content-Disposition"]
        self.assertIn('filename="Area.shp"', disposition)
        self.assertIn("filename*=UTF-8''Area.shp", disposition)
        self.assertNotIn("sub", disposition)

    def test_a_file_that_is_not_an_archive_is_not_found(self):
        doc = self.document(b"not a zip at all", name="data.zip")
        with self.assertRaises(NotFound):
            self.download(doc, "a.txt")
        self.assertTrue(self.opened[0].closed)

    def test_an_encrypted_file_is_refused(self):
        doc = self.document(make_zip([("s.txt", b"x")], encrypted=("s.txt",)))
        with self.assertRaises(BadRequest):
            self.download(doc, "s.txt")
        self.assertTrue(self.opened[0].closed)

    def test_a_file_that_is_too_big_is_refused(self):
        doc = self.document(make_zip([("b.bin", b"y" * 10)]))
        with patch.object(Document, "ZIP_MEMBER_MAX_SIZE", 5):
            with self.assertRaises(BadRequest):
                self.download(doc, "b.bin")
        self.assertTrue(self.opened[0].closed)

    def test_an_archive_that_is_stored_compressed_is_served(self):
        doc = self.document(
            make_zip([("a.txt", b"hello")]),
            content_type="application/octet-stream",
            compress="yes",
            spy=False,
        )
        self.assertTrue(doc.is_compressed())
        body, _ = self.download(doc, "a.txt")
        self.assertEqual(self.body(body), b"hello")

    def test_a_file_that_was_not_modified_has_no_body_and_is_closed(self):
        doc = self.document(make_zip([("a.txt", b"x")]))
        from zope.datetime import rfc1123_date

        body, response = self.download(
            doc, "a.txt", if_modified_since=rfc1123_date(doc.data_file.mtime + 10)
        )
        self.assertEqual(body, "")
        response.setStatus.assert_called_with(304)
        self.assertTrue(self.opened[0].closed)

    def test_the_permission_is_the_one_to_view_the_file(self):
        for name in ("zip_member", "zip_contents", "get_zip_members"):
            self.assertEqual(
                getattr(Document.Document, name + "__roles__")._p,
                Document.Document.index_html__roles__._p,
                name,
            )


class DispositionTest(BaseUnitTest):
    def test_the_name_cannot_end_the_header(self):
        value = _attachment('a"b\r\nSet-Cookie: x=1.txt')
        self.assertNotIn("\r", value)
        self.assertNotIn("\n", value)
        self.assertEqual(value.count('"'), 2)

    def test_the_real_name_is_in_utf8(self):
        self.assertIn(
            "filename*=UTF-8''r%C3%A9sum%C3%A9.txt", _attachment("résumé.txt")
        )
        self.assertIn('filename="r_sum_.txt"', _attachment("résumé.txt"))


class ZipMemberReaderTest(BaseUnitTest):
    def test_it_does_not_give_more_than_the_size_of_the_entry(self):
        closed = []
        reader = ZipMemberReader(BytesIO(b"0123456789"), 4, lambda: closed.append(1))
        self.assertEqual(reader.read(3), b"012")
        self.assertEqual(reader.read(), b"3")
        self.assertEqual(reader.read(10), b"")

    def test_it_closes_the_archive_once(self):
        closed = []
        reader = ZipMemberReader(BytesIO(b"x"), 1, lambda: closed.append(1))
        reader.close()
        reader.close()
        self.assertEqual(closed, [1])

    def test_it_closes_the_archive_when_the_entry_does_not_close(self):
        closed = []
        member = Mock()
        member.close.side_effect = OSError("broken")
        reader = ZipMemberReader(member, 1, lambda: closed.append(1))
        with self.assertRaises(OSError):
            reader.close()
        self.assertEqual(closed, [1])


class HostileArchiveTest(ZipDocumentTest):
    """What the server does with archives that are made to hurt it."""

    def stored(self, name, data, **changes):
        """An archive with one stored file, and the central directory changed:
        what the entry says about its size."""
        raw = bytearray(make_zip([(name, data)]))
        position = raw.find(b"PK\x01\x02")
        if "file_size" in changes:
            raw[position + 24 : position + 28] = changes["file_size"].to_bytes(
                4, "little"
            )
        return bytes(raw)

    def assert_refused_as_damaged(self, doc, name):
        """Nothing is sent: the file is copied before the response."""
        with patch.object(
            Document.tempfile,
            "SpooledTemporaryFile",
            wraps=Document.tempfile.SpooledTemporaryFile,
        ) as spooled:
            with self.assertRaises(BadRequest) as raised:
                self.download(doc, name)
        self.assertIn("damaged", str(raised.exception))
        self.assertTrue(self.opened[0].closed)
        return spooled

    def test_a_file_that_is_bigger_than_the_entry_says_is_refused(self):
        doc = self.document(self.stored("lie.txt", b"A" * 100, file_size=5))
        self.assert_refused_as_damaged(doc, "lie.txt")

    def test_a_file_that_is_shorter_than_the_entry_says_is_refused(self):
        doc = self.document(self.stored("short.txt", b"A" * 100, file_size=200))
        self.assert_refused_as_damaged(doc, "short.txt")

    def test_a_file_with_a_wrong_checksum_is_refused(self):
        raw = bytearray(make_zip([("crc.txt", b"hello world")]))
        raw[raw.find(b"hello world")] ^= 0xFF
        self.assert_refused_as_damaged(self.document(bytes(raw)), "crc.txt")

    def test_a_damaged_file_does_not_leave_its_copy_open(self):
        doc = self.document(self.stored("short.txt", b"A" * 100, file_size=200))
        closed = []
        real = Document.tempfile.SpooledTemporaryFile

        class Spy(real):
            def close(self):
                closed.append(1)
                super().close()

        with patch.object(Document.tempfile, "SpooledTemporaryFile", Spy):
            with self.assertRaises(BadRequest):
                self.download(doc, "short.txt")
        self.assertEqual(closed, [1])

    def test_the_reader_breaks_when_the_entry_ends_before_its_size(self):
        reader = ZipMemberReader(BytesIO(b"abc"), 10, lambda: None)
        self.assertEqual(reader.read(2), b"ab")
        self.assertEqual(reader.read(2), b"c")
        with self.assertRaises(zipfile.BadZipFile):
            reader.read(2)

    def test_only_a_zip_is_opened_by_the_download(self):
        doc = self.document(
            make_zip([("a.txt", b"x")]), "data.bin", "application/x-unknown"
        )
        with self.assertRaises(NotFound):
            self.download(doc, "a.txt")
        self.assertEqual(self.opened, [])

    def test_a_name_that_is_a_list_is_not_found(self):
        doc = self.document(make_zip([("a.txt", b"x")]))
        with self.assertRaises(NotFound):
            self.download(doc, ["a.txt"])
        self.assertEqual(self.opened, [])

    def test_a_file_without_a_name_is_not_listed_or_sent(self):
        doc = self.document(make_zip([("", b"x"), ("a.txt", b"y")]))
        self.assertEqual([m["name"] for m in doc.get_zip_members()], ["a.txt"])
        with self.assertRaises(NotFound):
            self.download(doc, "")

    def test_the_files_that_are_listed_are_limited(self):
        doc = self.document(make_zip([("f%d.txt" % i, b"x") for i in range(5)]))
        with patch.object(Document, "ZIP_MAX_LISTED", 3):
            self.assertEqual(len(doc.get_zip_members()), 3)
            self.assertEqual(doc.zip_listing_limit(), 3)

    def test_an_archive_stored_compressed_that_is_too_big_is_not_read(self):
        doc = self.document(
            make_zip([("a.txt", b"x")]),
            content_type="application/octet-stream",
            compress="yes",
            spy="real",
        )
        with patch.object(Document, "ZIP_SPOOL_MAX_SIZE", 1):
            self.assertEqual(doc.get_zip_members(), [])
            with self.assertRaises(BadRequest):
                self.download(doc, "a.txt")
            with self.assertRaises(ArchiveTooBig):
                doc._open_zip()
        self.assertEqual(self.opened, [])


class RealBlobTest(ZipDocumentTest):
    """With the file of the blob itself, not a copy in memory."""

    def test_the_file_of_the_blob_is_closed_after_the_listing(self):
        doc = self.document(make_zip([("a.txt", b"x")]), spy="real")
        self.assertEqual(len(doc.get_zip_members()), 1)
        self.assertEqual(len(self.opened), 1)
        self.assertTrue(self.opened[0].closed)

    def test_the_file_of_the_blob_is_closed_after_the_download(self):
        doc = self.document(make_zip([("a.txt", b"hello")]), spy="real")
        body, _ = self.download(doc, "a.txt")
        # the file of the blob is not kept while the body is sent
        self.assertTrue(self.opened[0].closed)
        self.assertEqual(self.body(body), b"hello")

    def test_the_file_of_the_blob_is_closed_when_the_file_is_not_found(self):
        doc = self.document(make_zip([("a.txt", b"hello")]), spy="real")
        with self.assertRaises(NotFound):
            self.download(doc, "b.txt")
        self.assertTrue(self.opened[0].closed)

    def test_a_big_archive_is_read_only_at_its_end_and_where_the_file_is(self):
        data = make_zip([("one.bin", BIG), ("two.bin", b"small"), ("three.bin", BIG)])
        doc = self.document(data, spy="real")
        reads = []
        real_open = doc.data_file.open

        def counting_open(*args, **kwargs):
            handle = real_open(*args, **kwargs)
            original = handle.read

            def read(*a):
                chunk = original(*a)
                reads.append(len(chunk))
                return chunk

            handle.read = read
            return handle

        doc.data_file.open = counting_open
        self.assertEqual(len(doc.get_zip_members()), 3)
        self.assertLess(sum(reads), 4096)
        del reads[:]
        body, _ = self.download(doc, "two.bin")
        self.assertEqual(self.body(body), b"small")
        self.assertLess(sum(reads), 8192)


def set_central_name_flag_and_byte(raw, name, flag, byte_at, byte):
    """Change the central directory entry of `name`: set a flag bit, and one
    byte of the name."""
    raw = bytearray(raw)
    position = raw.find(b"PK\x01\x02")
    while position != -1:
        length = int.from_bytes(raw[position + 28 : position + 30], "little")
        if bytes(raw[position + 46 : position + 46 + length]) == name:
            raw[position + 8 : position + 10] = (
                int.from_bytes(raw[position + 8 : position + 10], "little") | flag
            ).to_bytes(2, "little")
            if byte is not None:
                raw[position + 46 + byte_at] = byte
            return bytes(raw)
        position = raw.find(b"PK\x01\x02", position + 1)
    raise AssertionError("no such entry")


class NamesAndSizesTest(ZipDocumentTest):
    """Names in other encodings, and archives with more than 64K files or a
    file that is described with 64 bits: the ones that only a big archive has."""

    def test_a_name_in_the_old_dos_encoding_is_listed_and_sent(self):
        # no flag for utf-8: the name is in cp437, where 0x82 is an e with an acute
        raw = make_zip([("cafX.txt", b"caf")]).replace(b"cafX.txt", b"caf\x82.txt")
        doc = self.document(raw)
        self.assertEqual([m["name"] for m in doc.get_zip_members()], ["café.txt"])
        body, response = self.download(doc, "café.txt")
        self.assertEqual(self.body(body), b"caf")
        self.assertIn(
            "filename*=UTF-8''caf%C3%A9.txt",
            self.headers(response)["Content-Disposition"],
        )

    def test_a_name_that_says_it_is_utf8_and_is_not_hides_the_list(self):
        raw = set_central_name_flag_and_byte(
            make_zip([("abc.txt", b"x"), ("ok.txt", b"y")]), b"abc.txt", 0x800, 0, 0xFF
        )
        doc = self.document(raw)
        # the archive cannot be read as a whole: the list is empty and the
        # download is not found, not an error of the server
        self.assertEqual(doc.get_zip_members(), [])
        with self.assertRaises(NotFound):
            self.download(doc, "ok.txt")
        self.assertTrue(all(handle.closed for handle in self.opened))

    def test_a_file_described_with_64_bits_is_listed_and_sent(self):
        out = BytesIO()
        with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED) as archive:
            with archive.open("big.bin", "w", force_zip64=True) as member:
                member.write(b"b" * 100)
            archive.writestr("small.txt", b"s")
        self.assertIn(b"\x01\x00", out.getvalue())  # the zip64 extra field
        doc = self.document(out.getvalue())
        members = {m["name"]: m["size"] for m in doc.get_zip_members()}
        self.assertEqual(members, {"big.bin": 100, "small.txt": 1})
        body, response = self.download(doc, "big.bin")
        self.assertEqual(self.headers(response)["Content-Length"], 100)
        self.assertEqual(self.body(body), b"b" * 100)

    def test_an_archive_with_more_than_64k_files_is_listed_up_to_the_limit(self):
        files = 70000
        out = BytesIO()
        with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED) as archive:
            for number in range(files):
                info = zipfile.ZipInfo("f%05d.txt" % number)
                archive.writestr(info, b"")
            archive.writestr("last.txt", b"the last one")
        # the end of the central directory is the one for 64 bits
        self.assertIn(b"PK\x06\x06", out.getvalue())
        doc = self.document(out.getvalue())
        members = doc.get_zip_members()
        self.assertEqual(len(members), Document.ZIP_MAX_LISTED)
        self.assertEqual(members[0]["name"], "f00000.txt")
        # a file at the end of the list is sent, though it is not listed
        body, _ = self.download(doc, "last.txt")
        self.assertEqual(self.body(body), b"the last one")
        self.assertTrue(all(handle.closed for handle in self.opened))


class LoginRequiredTest(ZipDocumentTest):
    """The files of an archive are only for the users that are logged in."""

    def anonymous(self):
        noSecurityManager()

    def test_a_user_that_is_not_logged_in_cannot_list_the_files(self):
        doc = self.document(make_zip([("a.txt", b"x")]))
        self.anonymous()
        with self.assertRaises(Unauthorized):
            doc.zip_contents()
        self.assertEqual(self.opened, [])

    def test_a_user_that_is_not_logged_in_cannot_get_a_file(self):
        doc = self.document(make_zip([("a.txt", b"x")]))
        self.anonymous()
        with self.assertRaises(Unauthorized):
            self.download(doc, "a.txt")
        self.assertEqual(self.opened, [])

    def test_a_user_that_is_not_logged_in_is_not_told_that_a_file_is_missing(self):
        doc = self.document(make_zip([("a.txt", b"x")]))
        self.anonymous()
        with self.assertRaises(Unauthorized):
            self.download(doc, "missing.txt")

    def test_a_user_that_is_logged_in_can_browse_a_zip(self):
        self.assertTrue(self.document(make_zip([("a", b"x")])).can_browse_zip())

    def test_a_user_that_is_not_logged_in_cannot_browse_a_zip(self):
        doc = self.document(make_zip([("a", b"x")]))
        self.anonymous()
        self.assertFalse(doc.can_browse_zip())

    def test_a_file_that_is_not_a_zip_cannot_be_browsed(self):
        doc = self.document(
            make_zip([("a", b"x")]), "data.bin", "application/x-unknown"
        )
        self.assertFalse(doc.can_browse_zip())

    def test_a_user_that_cannot_view_the_file_cannot_browse_it(self):
        doc = self.document(make_zip([("a", b"x")]))
        manager = Mock()
        manager.getUser.return_value.getUserName.return_value = "someone"
        manager.checkPermission.return_value = False
        with patch.object(Document, "getSecurityManager", return_value=manager):
            self.assertFalse(doc.can_browse_zip())
        manager.checkPermission.assert_called_with("View", doc)

    def test_the_templates_can_ask_about_any_file(self):
        # a file that the user cannot view is on the list too: asking is public
        self.assertIsNone(Document.Document.can_browse_zip__roles__)


class EnvelopeContentTest(ZipDocumentTest):
    """As the zip of an envelope: only where the content of the envelope can be
    seen, besides the login and the permission to view the file."""

    def hidden(self):
        doc = self.document(make_zip([("a.txt", b"x")]))
        doc.canViewContent = Mock(return_value=False)
        return doc

    def test_the_files_cannot_be_listed_when_the_content_of_the_envelope_is_hidden(
        self,
    ):
        doc = self.hidden()
        with self.assertRaises(Unauthorized):
            doc.zip_contents()
        self.assertEqual(self.opened, [])

    def test_a_file_cannot_be_got_when_the_content_of_the_envelope_is_hidden(self):
        doc = self.hidden()
        with self.assertRaises(Unauthorized):
            self.download(doc, "a.txt")
        self.assertEqual(self.opened, [])

    def test_the_archive_cannot_be_browsed_when_the_content_is_hidden(self):
        self.assertFalse(self.hidden().can_browse_zip())


def make_mixed_zip(files):
    """Files with their own compression: (name, data, compression)."""
    out = BytesIO()
    with zipfile.ZipFile(out, "w") as archive:
        for name, data, compression in files:
            info = zipfile.ZipInfo(name, (2024, 3, 9, 14, 30, 10))
            info.compress_type = compression
            archive.writestr(info, data)
    return out.getvalue()


def raw_data(archive_bytes, name):
    """The compressed bytes of a file of an archive, as they are in it."""
    archive = zipfile.ZipFile(BytesIO(archive_bytes))
    info = archive.getinfo(name)
    # the lengths of the name and of the extra data are in the header
    name_length = int.from_bytes(
        archive_bytes[info.header_offset + 26 : info.header_offset + 28], "little"
    )
    extra_length = int.from_bytes(
        archive_bytes[info.header_offset + 28 : info.header_offset + 30], "little"
    )
    start = info.header_offset + 30 + name_length + extra_length
    return archive_bytes[start : start + info.compress_size]


class PostRequest:
    method = "POST"

    def get_header(self, name, default=None):
        return default


def post_request(csrf_checked=False):
    request = PostRequest()
    if not csrf_checked:
        alsoProvides(request, IDisableCSRFProtection)
    return request


class SelectionBase(ZipDocumentTest):
    """The archive and the helpers of the tests of the choice of files."""

    FILES = [
        ("a.xml", b"<a>" + b"x" * 5000 + b"</a>", zipfile.ZIP_DEFLATED),
        ("b.bin", bytes(range(256)) * 4, zipfile.ZIP_STORED),
        ("Area/c.txt", b"in a folder " * 50, zipfile.ZIP_DEFLATED),
        ("d.txt", b"last", zipfile.ZIP_STORED),
    ]

    def archive(self, **kwargs):
        self.source = make_mixed_zip(self.FILES)
        return self.document(self.source, **kwargs)

    def select(self, doc, names, request=None):
        response = Mock()
        body = doc.zip_selection(request or post_request(), response, names=names)
        self.response = response
        return body

    def chosen(self, doc, names):
        data = self.body(self.select(doc, names))
        return data, zipfile.ZipFile(BytesIO(data))


class SelectionTest(SelectionBase):
    """Some of the files of an archive in a new one, as they are: the compressed
    bytes are copied, nothing is compressed or decompressed."""

    def test_the_chosen_files_are_in_the_new_archive_in_the_order_of_the_choice(self):
        data, new = self.chosen(self.archive(), ["d.txt", "a.xml"])
        self.assertEqual(new.namelist(), ["d.txt", "a.xml"])
        self.assertEqual(new.read("d.txt"), b"last")
        self.assertEqual(new.read("a.xml"), self.FILES[0][1])
        self.assertIsNone(new.testzip())

    def test_the_new_archive_is_a_valid_one_for_other_programs(self):
        data, new = self.chosen(self.archive(), ["a.xml", "b.bin", "Area/c.txt"])
        # testzip reads every file and checks its checksum
        self.assertIsNone(new.testzip())
        for name, content, _ in self.FILES[:3]:
            self.assertEqual(new.read(name), content)

    def test_the_compressed_bytes_are_the_ones_of_the_archive(self):
        doc = self.archive()
        data, new = self.chosen(doc, ["a.xml", "b.bin", "Area/c.txt"])
        old = zipfile.ZipFile(BytesIO(self.source))
        for name in ("a.xml", "b.bin", "Area/c.txt"):
            self.assertEqual(raw_data(data, name), raw_data(self.source, name), name)
            self.assertEqual(new.getinfo(name).CRC, old.getinfo(name).CRC)
            self.assertEqual(
                new.getinfo(name).compress_type, old.getinfo(name).compress_type
            )
            self.assertEqual(
                new.getinfo(name).compress_size, old.getinfo(name).compress_size
            )
            self.assertEqual(new.getinfo(name).file_size, old.getinfo(name).file_size)
            self.assertEqual(new.getinfo(name).date_time, old.getinfo(name).date_time)

    def test_nothing_is_compressed_or_decompressed_to_make_it(self):
        doc = self.archive()

        def not_allowed(*args, **kwargs):
            raise AssertionError("the data must be copied as it is")

        with patch.object(zipfile.zlib, "compressobj", not_allowed), patch.object(
            zipfile.zlib, "decompressobj", not_allowed
        ), patch.object(zipfile.ZipFile, "open", not_allowed), patch.object(
            zipfile.ZipFile, "read", not_allowed
        ):
            data = self.body(self.select(doc, ["a.xml", "Area/c.txt"]))
        self.assertEqual(
            zipfile.ZipFile(BytesIO(data)).namelist(), ["a.xml", "Area/c.txt"]
        )

    def test_a_name_with_letters_that_are_not_ascii_is_kept(self):
        files = [
            ("Zone/r\u00e9sum\u00e9.txt", "caf\u00e9".encode(), zipfile.ZIP_DEFLATED),
            ("Zone/\u00fcber.txt", b"other", zipfile.ZIP_STORED),
        ]
        doc = self.document(make_mixed_zip(files))
        names = ["Zone/r\u00e9sum\u00e9.txt", "Zone/\u00fcber.txt"]
        _, new = self.chosen(doc, names)
        self.assertEqual(new.namelist(), names)
        self.assertEqual(new.read(names[0]), "caf\u00e9".encode())
        self.assertIsNone(new.testzip())

    def test_a_file_that_is_chosen_twice_is_in_once(self):
        _, new = self.chosen(self.archive(), ["a.xml", "d.txt", "a.xml"])
        self.assertEqual(new.namelist(), ["a.xml", "d.txt"])

    def test_one_file_is_sent_as_it_is_and_not_in_an_archive(self):
        doc = self.archive()
        body = self.select(doc, ["d.txt"])
        self.assertEqual(self.body(body), b"last")
        headers = self.headers(self.response)
        self.assertEqual(headers["Content-Type"], "text/plain")
        self.assertIn('filename="d.txt"', headers["Content-Disposition"])

    def test_one_file_that_is_chosen_twice_is_sent_as_it_is(self):
        body = self.select(self.archive(), ["d.txt", "d.txt"])
        self.assertEqual(self.body(body), b"last")

    def test_the_headers_tell_what_is_sent(self):
        doc = self.archive()
        data = self.body(self.select(doc, ["d.txt", "b.bin"]))
        headers = self.headers(self.response)
        self.assertEqual(headers["Content-Type"], "application/zip")
        self.assertEqual(headers["Content-Length"], len(data))
        self.assertIn(
            'filename="archive-selection.zip"', headers["Content-Disposition"]
        )
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")

    def test_the_body_is_a_file_for_the_server_and_the_archive_is_closed(self):
        body = self.select(self.archive(), ["a.xml", "d.txt"])
        self.assertIsInstance(body, IOBase)
        self.assertEqual(body.tell(), 0)
        self.assertTrue(self.opened[0].closed)
        body.close()

    def test_an_archive_that_is_stored_compressed_is_read_too(self):
        doc = self.archive(
            content_type="application/octet-stream", compress="yes", spy=False
        )
        self.assertTrue(doc.is_compressed())
        _, new = self.chosen(doc, ["a.xml", "d.txt"])
        self.assertEqual(new.namelist(), ["a.xml", "d.txt"])
        self.assertIsNone(new.testzip())

    def test_the_new_archive_is_in_the_zip_cache_when_it_is_big(self):
        with patch.object(Document, "ZIP_SPOOL_SIZE", 100):
            body = self.select(self.archive(), ["a.xml", "b.bin"])
        self.assertTrue(body._rolled)
        self.assertIsNone(zipfile.ZipFile(BytesIO(self.body(body))).testzip())

    def test_the_files_that_cannot_be_chosen_are_marked_in_the_list(self):
        files = [
            ("ok.txt", b"x", zipfile.ZIP_DEFLATED),
            ("bz.txt", b"y" * 100, zipfile.ZIP_BZIP2),
            ("big.txt", b"z" * 10, zipfile.ZIP_STORED),
        ]
        doc = self.document(make_mixed_zip(files))
        with patch.object(Document, "ZIP_MEMBER_MAX_SIZE", 50):
            members = {m["name"]: m["selectable"] for m in doc.get_zip_members()}
        self.assertEqual(members, {"ok.txt": True, "bz.txt": False, "big.txt": True})
        with patch.object(Document, "ZIP_MEMBER_MAX_SIZE", 5):
            members = {m["name"]: m["selectable"] for m in doc.get_zip_members()}
        self.assertEqual(members["big.txt"], False)


class SelectionRefusedTest(SelectionBase):
    def refused(self, doc, names, error, request=None):
        with self.assertRaises(error):
            self.select(doc, names, request)

    def test_nothing_chosen_is_refused(self):
        doc = self.archive()
        for names in (None, [], ""):
            self.refused(doc, names, BadRequest)
        self.assertEqual(self.opened, [])

    def test_names_that_are_not_text_are_refused(self):
        self.refused(self.archive(), ["a.xml", 5], BadRequest)
        self.assertEqual(self.opened, [])

    def test_a_name_in_a_string_is_one_file(self):
        body = self.select(self.archive(), "d.txt")
        self.assertEqual(self.body(body), b"last")

    def test_too_many_files_are_refused_before_the_archive_is_opened(self):
        with patch.object(Document, "ZIP_SELECTION_MAX_FILES", 2):
            self.refused(self.archive(), ["a.xml", "b.bin", "d.txt"], BadRequest)
        self.assertEqual(self.opened, [])

    def test_files_that_are_too_big_together_are_refused(self):
        doc = self.archive()
        with patch.object(Document, "ZIP_SELECTION_MAX_SIZE", 6000):
            self.refused(doc, ["a.xml", "b.bin"], BadRequest)
        self.assertTrue(self.opened[0].closed)

    def test_a_file_that_is_not_in_the_archive_is_not_found(self):
        doc = self.archive()
        self.refused(doc, ["a.xml", "missing.txt"], NotFound)
        self.assertTrue(self.opened[0].closed)

    def test_a_folder_is_not_found(self):
        doc = self.document(
            make_mixed_zip([("d/", b"", zipfile.ZIP_STORED), ("a", b"x", 0)])
        )
        self.refused(doc, ["d/"], NotFound)

    def test_an_encrypted_file_is_refused(self):
        doc = self.document(make_zip([("s.txt", b"x")], encrypted=("s.txt",)))
        self.refused(doc, ["s.txt"], BadRequest)
        self.assertTrue(self.opened[0].closed)

    def test_a_file_that_is_too_big_is_refused(self):
        doc = self.archive()
        with patch.object(Document, "ZIP_MEMBER_MAX_SIZE", 10):
            self.refused(doc, ["a.xml"], BadRequest)

    def test_a_compression_that_is_not_copied_is_refused(self):
        doc = self.document(
            make_mixed_zip([("bz.txt", b"y" * 100, zipfile.ZIP_BZIP2), ("a", b"x", 0)])
        )
        self.refused(doc, ["bz.txt", "a"], BadRequest)

    def test_a_compression_that_is_not_copied_can_be_sent_alone(self):
        doc = self.document(
            make_mixed_zip([("bz.txt", b"y" * 100, zipfile.ZIP_BZIP2), ("a", b"x", 0)])
        )
        self.assertEqual(self.body(self.select(doc, ["bz.txt"])), b"y" * 100)

    def test_a_file_that_is_not_a_zip_is_not_found(self):
        doc = self.document(
            make_zip([("a", b"x")]), "data.bin", "application/x-unknown"
        )
        self.refused(doc, ["a"], NotFound)
        self.assertEqual(self.opened, [])

    def test_the_files_are_chosen_with_post(self):
        request = post_request()
        request.method = "GET"
        self.refused(self.archive(), ["a.xml"], BadRequest, request)
        self.assertEqual(self.opened, [])

    def test_a_user_that_is_not_logged_in_is_refused(self):
        doc = self.archive()
        noSecurityManager()
        self.refused(doc, ["a.xml"], Unauthorized)
        self.assertEqual(self.opened, [])

    def test_a_file_with_the_content_of_the_envelope_hidden_is_refused(self):
        doc = self.archive()
        doc.canViewContent = Mock(return_value=False)
        self.refused(doc, ["a.xml"], Unauthorized)
        self.assertEqual(self.opened, [])

    def test_the_permission_is_the_one_to_view_the_file(self):
        self.assertEqual(
            Document.Document.zip_selection__roles__._p,
            Document.Document.index_html__roles__._p,
        )

    def test_the_request_is_checked_with_the_token_of_the_page(self):
        doc = self.archive()
        authenticator = Mock()
        authenticator.verify.return_value = False
        with patch.object(Document, "getMultiAdapter", return_value=authenticator):
            self.refused(doc, ["a.xml"], Unauthorized, post_request(csrf_checked=True))
        authenticator.verify.assert_called_once_with("zip_selection")
        self.assertEqual(self.opened, [])
        authenticator.verify.return_value = True
        with patch.object(Document, "getMultiAdapter", return_value=authenticator):
            body = self.select(doc, ["a.xml"], post_request(csrf_checked=True))
        self.assertTrue(self.body(body))

    def test_a_file_that_ends_before_its_size_in_the_archive_is_refused(self):
        self.archive()
        raw = bytearray(self.source)
        # the first entry says that it is bigger than it is, by the size of the
        # rest of the archive and more
        position = raw.find(b"PK\x01\x02")
        size = int.from_bytes(raw[position + 20 : position + 24], "little")
        raw[position + 20 : position + 24] = (size + 10**6).to_bytes(4, "little")
        doc = self.document(bytes(raw))
        with self.assertRaises(BadRequest):
            self.select(doc, ["a.xml"])
        self.assertTrue(self.opened[-1].closed)


def attribute_zip(files):
    """Files with a unix mode: (name, data, mode)."""
    out = BytesIO()
    with zipfile.ZipFile(out, "w") as archive:
        for name, data, mode in files:
            info = zipfile.ZipInfo(name)
            info.create_system = 3
            info.external_attr = mode << 16
            archive.writestr(info, data)
    return out.getvalue()


class HardeningTest(SelectionBase):
    """What an archive that is made to hurt can have, in the archive that is
    sent: names above the folder, links, programs, files that share their bytes."""

    UNSAFE = [
        "../../evil.txt",
        "/abs/evil.txt",
        "\\\\server\\share.txt",
        "C:evil.txt",
        "a/../../evil.txt",
        "a\\..\\evil.txt",
    ]

    def test_a_name_that_is_not_safe_to_unpack_cannot_be_chosen(self):
        for name in self.UNSAFE:
            doc = self.document(make_mixed_zip([(name, b"x", 0), ("ok.txt", b"y", 0)]))
            with self.assertRaises(BadRequest, msg=name):
                self.select(doc, [name, "ok.txt"])

    def test_a_name_that_is_not_safe_is_not_offered_for_choosing(self):
        files = [(name, b"x", 0) for name in self.UNSAFE] + [("a/b.txt", b"y", 0)]
        members = {
            m["name"]: m["selectable"]
            for m in self.document(make_mixed_zip(files)).get_zip_members()
        }
        self.assertEqual(
            members, dict({name: False for name in self.UNSAFE}, **{"a/b.txt": True})
        )

    def test_a_name_with_two_dots_that_is_not_a_folder_is_safe(self):
        names = ["a..b/c.txt", "..hidden", "x/file..txt"]
        doc = self.document(make_mixed_zip([(n, b"x", 0) for n in names]))
        _, new = self.chosen(doc, names)
        self.assertEqual(new.namelist(), names)

    def test_a_file_that_is_not_safe_can_still_be_sent_alone_under_its_own_name(self):
        doc = self.document(make_mixed_zip([("../../evil.txt", b"x", 0)]))
        body = self.select(doc, ["../../evil.txt"])
        self.assertEqual(self.body(body), b"x")
        self.assertIn(
            'filename="evil.txt"', self.headers(self.response)["Content-Disposition"]
        )

    def test_links_and_programs_are_plain_files_in_the_new_archive(self):
        files = [
            ("link", b"/etc/passwd", 0o120777),
            ("run.sh", b"#!/bin/sh\n", 0o100755),
            ("dir_like", b"x", 0o040755),
        ]
        _, new = self.chosen(self.document(attribute_zip(files)), [f[0] for f in files])
        for info in new.infolist():
            self.assertEqual(info.external_attr >> 16, 0o100644, info.filename)
            self.assertEqual(info.create_system, 3)
            self.assertEqual(info.internal_attr, 0)
        # what is in them is not touched
        self.assertEqual(new.read("link"), b"/etc/passwd")

    def test_files_that_share_their_bytes_are_refused(self):
        raw = bytearray(make_zip([("a.txt", b"a" * 1000), ("b.txt", b"b" * 1000)]))
        # the second entry of the directory points at the header of the first
        first = raw.find(b"PK\x01\x02")
        second = raw.find(b"PK\x01\x02", first + 1)
        raw[second + 42 : second + 46] = raw[first + 42 : first + 46]
        doc = self.document(bytes(raw))
        with self.assertRaises(BadRequest):
            self.select(doc, ["a.txt", "b.txt"])
        self.assertTrue(self.opened[-1].closed)
        # each one alone is fine
        self.assertEqual(len(self.body(self.select(doc, ["a.txt"]))), 1000)

    def test_a_file_with_a_wrong_checksum_is_copied_and_the_new_archive_says_so(self):
        raw = bytearray(make_zip([("good.txt", b"good"), ("bad.txt", b"hello world")]))
        raw[raw.find(b"hello world")] ^= 0xFF
        doc = self.document(bytes(raw))
        _, new = self.chosen(doc, ["good.txt", "bad.txt"])
        # the checksum is the one of the archive: nothing is read to check it
        self.assertEqual(new.testzip(), "bad.txt")

    def test_a_source_written_to_a_stream_with_data_descriptors_is_copied(self):
        import zipstream

        stream = zipstream.ZipStream(compress_type=zipfile.ZIP_DEFLATED)
        stream.add(iter([b"hello " * 1000]), "s1.txt")
        stream.add(iter([b"world " * 1000]), "s2.txt")
        source = b"".join(stream)
        self.assertTrue(zipfile.ZipFile(BytesIO(source)).infolist()[0].flag_bits & 8)
        _, new = self.chosen(self.document(source), ["s1.txt", "s2.txt"])
        self.assertIsNone(new.testzip())
        self.assertEqual(new.read("s2.txt"), b"world " * 1000)

    def test_a_file_described_with_64_bits_in_the_source_is_copied(self):
        out = BytesIO()
        with zipfile.ZipFile(out, "w") as archive:
            with archive.open("z64.bin", "w", force_zip64=True) as member:
                member.write(b"q" * 1000)
            archive.writestr("plain.txt", b"p")
        _, new = self.chosen(self.document(out.getvalue()), ["z64.bin", "plain.txt"])
        self.assertIsNone(new.testzip())
        self.assertEqual(new.read("z64.bin"), b"q" * 1000)

    def test_a_date_that_is_not_a_date_in_the_source_is_copied(self):
        raw = bytearray(make_zip([("d1.txt", b"1"), ("d2.txt", b"2")]))
        position = raw.find(b"PK\x01\x02")
        while position != -1:
            raw[position + 12 : position + 16] = b"\x00\x00\x00\x00"
            position = raw.find(b"PK\x01\x02", position + 1)
        _, new = self.chosen(self.document(bytes(raw)), ["d1.txt", "d2.txt"])
        self.assertIsNone(new.testzip())

    def test_a_local_header_with_more_extra_data_than_the_directory_says_is_copied(
        self,
    ):
        raw = bytearray(make_zip([("a.txt", b"first"), ("b.txt", b"second")]))
        # b.txt is the last: 4 bytes of extra data in its local header only, and
        # the directory after it is 4 bytes further
        local = raw.rfind(b"PK\x03\x04")
        name_end = local + 30 + 5
        raw[name_end:name_end] = b"\xfe\xca\x00\x00"
        raw[local + 28 : local + 30] = (4).to_bytes(2, "little")
        end = raw.rfind(b"PK\x05\x06")
        raw[end + 16 : end + 20] = (
            int.from_bytes(raw[end + 16 : end + 20], "little") + 4
        ).to_bytes(4, "little")
        _, new = self.chosen(self.document(bytes(raw)), ["a.txt", "b.txt"])
        self.assertIsNone(new.testzip())
        self.assertEqual(new.read("b.txt"), b"second")

    def test_names_in_a_tuple_are_chosen(self):
        _, new = self.chosen(self.archive(), ("a.xml", "d.txt"))
        self.assertEqual(new.namelist(), ["a.xml", "d.txt"])

    def test_more_files_than_the_limit_are_refused_without_a_patch_too(self):
        names = ["f%03d.txt" % i for i in range(Document.ZIP_SELECTION_MAX_FILES + 1)]
        with self.assertRaises(BadRequest):
            self.select(self.archive(), names)
        self.assertEqual(self.opened, [])

    def test_the_page_can_ask_for_the_limit(self):
        self.assertEqual(
            self.archive().zip_selection_limit(), Document.ZIP_SELECTION_MAX_FILES
        )

    def test_the_copy_is_closed_when_the_headers_cannot_be_set(self):
        doc = self.archive()
        response = Mock()
        response.setHeader.side_effect = RuntimeError("no headers")
        closed = []
        real = Document.tempfile.SpooledTemporaryFile

        class Spy(real):
            def close(self):
                closed.append(1)
                super().close()

        with patch.object(Document.tempfile, "SpooledTemporaryFile", Spy):
            with self.assertRaises(RuntimeError):
                doc.zip_selection(post_request(), response, names=["a.xml", "d.txt"])
            with self.assertRaises(RuntimeError):
                doc.zip_member("a.xml", post_request(), response)
        self.assertEqual(closed, [1, 1])
