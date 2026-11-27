"""Zip archives uploaded to an envelope: limits on what they unpack to, and
reads capped to what the archive says."""

import hashlib
import io
import struct
import zipfile
from contextlib import ExitStack
from unittest.mock import patch

from Acquisition import aq_base

from Products.Reportek import config
from Products.Reportek import EnvelopeCustomDataflows
from Products.Reportek.exceptions import UploadValidationException
from Products.Reportek.zip_content import ZipUploadRefused, check_upload_archive

from .common import BaseTest
from .utils import create_temp_reposit

MB = 1024 * 1024
BOMB = b"<r>" + b"a" * (20 * MB) + b"</r>"
GIS_FILES = ("map.shp", "map.shx", "map.dbf", "map.prj", "map.xml")


def make_zip(files, name="upload.zip"):
    """An uploaded zip file, with the (name, data) files given."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as archive:
        for member, data in files:
            archive.writestr(member, data)
    buf.seek(0)
    buf.filename = name
    return buf


def declare_size(upload, size):
    """Make the (only) file of the archive say it unpacks to `size` bytes."""
    data = bytearray(upload.getvalue())
    data[22:26] = struct.pack("<I", size)  # the local header
    central = data.index(b"PK\x01\x02")
    data[central + 24 : central + 28] = struct.pack("<I", size)
    lying = io.BytesIO(bytes(data))
    lying.filename = upload.filename
    return lying


class CheckUploadArchiveTest(BaseTest):
    def check(self, files):
        with zipfile.ZipFile(make_zip(files)) as archive:
            check_upload_archive(archive)

    def test_an_ordinary_archive_passes(self):
        self.check([("a.xml", b"<a>%s</a>" % (b"data " * 1000)), ("b.txt", b"x")])

    def test_too_many_files(self):
        with patch.object(config, "ZIP_UPLOAD_MAX_FILES", 2):
            self.check([("a", b""), ("b", b"")])
            with self.assertRaisesRegex(ZipUploadRefused, "3 files; at most 2"):
                self.check([("a", b""), ("b", b""), ("c", b"")])

    def test_a_file_too_big(self):
        with patch.object(config, "ZIP_UPLOAD_MAX_MEMBER_SIZE", 1000):
            with self.assertRaisesRegex(ZipUploadRefused, "big.txt .* at most"):
                self.check([("small.txt", b"x" * 1000), ("big.txt", b"x" * 1001)])

    def test_too_much_together(self):
        with patch.object(config, "ZIP_UPLOAD_MAX_TOTAL_SIZE", 1500):
            with self.assertRaisesRegex(ZipUploadRefused, "at once"):
                self.check([("a.txt", b"x" * 1000), ("b.txt", b"x" * 1000)])

    def test_a_bomb(self):
        with self.assertRaisesRegex(ZipUploadRefused, "bomb.xml .*unpacks to"):
            self.check([("bomb.xml", BOMB)])

    def test_small_files_may_compress_well(self):
        # below ZIP_UPLOAD_RATIO_MIN_SIZE the ratio is not looked at
        self.check([("blank.txt", b" " * MB)])


class ZipUploadTestBase(BaseTest):
    """An envelope to upload to; no tests here."""

    def afterSetUp(self):
        super().afterSetUp()
        self._cleanup_temp_reposit = create_temp_reposit()
        self.createStandardDependencies()
        self.createStandardCollection()
        self.envelope = self.createStandardEnvelope()
        self.patches = ExitStack()
        for module in ("Envelope", "EnvelopeCustomDataflows"):
            self.patches.enter_context(
                patch("Products.Reportek.%s.transaction.commit" % module)
            )
        self.dialog = self.patches.enter_context(
            patch.object(aq_base(self.envelope).__class__, "messageDialog", create=True)
        )

    def beforeTearDown(self):
        self.patches.close()
        self._cleanup_temp_reposit()

    def documents(self):
        return sorted(self.envelope.objectIds("Report Document"))

    def message(self):
        return self.dialog.call_args[1]["message"]


class ZipUploadTest(ZipUploadTestBase):
    def test_an_archive_is_unpacked(self):
        content = b"<a>%s</a>" % (b"data " * 1000)
        self.envelope.manage_addzipfile(
            make_zip([("a.xml", content), ("b.txt", b"text")])
        )
        self.assertEqual(self.documents(), ["a.xml", "b.txt"])
        # read in full despite the cap
        document = self.envelope["a.xml"]
        self.assertEqual(document.hash, hashlib.sha256(content).hexdigest())

    def test_a_bomb_is_refused_before_anything_is_added(self):
        self.envelope.manage_addzipfile(
            make_zip([("ok.txt", b"text"), ("bomb.xml", BOMB)])
        )
        self.assertEqual(self.documents(), [])
        self.assertRegex(self.message(), "bomb.xml .*unpacks to")

    def test_too_many_files_are_refused(self):
        with patch.object(config, "ZIP_UPLOAD_MAX_FILES", 1):
            self.envelope.manage_addzipfile(make_zip([("a", b""), ("b", b"")]))
        self.assertEqual(self.documents(), [])
        self.assertIn("at most 1", self.message())

    def test_a_file_bigger_than_it_says_is_refused(self):
        for name in ("data.txt", "data.xml"):
            data = b"<r>%s</r>" % (b"a" * MB)
            # more than is read to guess its type: Python's zipfile itself
            # refuses a file that ends before that
            upload = declare_size(make_zip([(name, data)]), 100 * 1024)
            with self.assertRaisesRegex(UploadValidationException, name):
                self.envelope.manage_addzipfile(upload)

    def test_dd_zip_refuses_a_bomb(self):
        result = self.envelope.manage_addDDzipfile(
            file=make_zip([("bomb.xml", BOMB)]), verbose=True
        )
        self.assertEqual(result[0], 0)
        self.assertRegex(result[1], "bomb.xml .*unpacks to")
        self.assertEqual(self.documents(), [])

    def test_gis_zip_refuses_a_bomb(self):
        files = [(name, b"<a/>") for name in GIS_FILES[:-1]]
        files.append(("map.xml", BOMB))
        self.assertEqual(self.envelope.uploadGISZIPfiles(make_zip(files)), 0)
        self.assertEqual(self.documents(), [])

    def test_gis_zip_still_needs_all_its_files_the_second_time(self):
        complete = make_zip([(name, b"<a/>") for name in GIS_FILES])
        self.assertEqual(self.envelope.uploadGISZIPfiles(complete), 1)
        self.assertEqual(
            EnvelopeCustomDataflows.ESRI_EXTRAEXTENSIONS,
            [".shp", ".shx", ".dbf", ".prj", ".xml"],
        )
        incomplete = make_zip([("other.shp", b"x")])
        self.assertEqual(self.envelope.uploadGISZIPfiles(incomplete), 0)


class UploadedHashTest(ZipUploadTestBase):
    """The hash of a file unpacked from an archive is the sha256 of the file,
    the same as without the cap on the reads."""

    BLOCK = 65536
    CONTENTS = {
        "empty.txt": b"",
        "one.txt": b"x",
        "block_minus_one.txt": b"a" * (BLOCK - 1),
        "block.txt": b"b" * BLOCK,
        "block_plus_one.txt": b"c" * (BLOCK + 1),
        "three_blocks.bin": bytes(range(256)) * (3 * BLOCK // 256),
        "random.bin": __import__("os").urandom(3 * MB + 17),
        "data.xml": b"<r>%s</r>" % (b"<v>12.5</v>" * 200000),
    }

    def assertHashes(self, names=None):
        for name in names or self.CONTENTS:
            document = self.envelope[name]
            expected = hashlib.sha256(self.CONTENTS[name]).hexdigest()
            self.assertEqual(document.hash, expected, name)
            # and as it is computed without a cap
            document.generate_hash()
            self.assertEqual(document.hash, expected, name)

    def make(self, names=None, compression=zipfile.ZIP_DEFLATED):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", compression) as archive:
            for name in names or self.CONTENTS:
                archive.writestr(name, self.CONTENTS[name])
        buf.seek(0)
        buf.filename = "upload.zip"
        return buf

    def test_zip_upload_deflated(self):
        self.envelope.manage_addzipfile(self.make())
        self.assertHashes()

    def test_zip_upload_stored(self):
        self.envelope.manage_addzipfile(self.make(compression=zipfile.ZIP_STORED))
        self.assertHashes()

    def test_dd_zip_upload(self):
        self.envelope.manage_addDDzipfile(file=self.make(), verbose=True)
        self.assertHashes()

    def test_gis_zip_upload(self):
        names = ["map.shp", "map.shx", "map.dbf", "map.prj", "map.xml"]
        self.CONTENTS = dict(
            self.CONTENTS,
            **{
                "map.shp": self.CONTENTS["random.bin"],
                "map.shx": self.CONTENTS["block.txt"],
                "map.dbf": self.CONTENTS["block_plus_one.txt"],
                "map.prj": b"PROJCS[]",
                "map.xml": self.CONTENTS["data.xml"],
            },
        )
        self.assertEqual(self.envelope.uploadGISZIPfiles(self.make(names)), 1)
        self.assertHashes(names)

    def test_plain_upload_is_not_capped(self):
        upload = io.BytesIO(self.CONTENTS["random.bin"])
        upload.filename = "plain.bin"
        self.envelope.manage_addProduct["Reportek"].manage_addDocument(
            "plain.bin", "", upload
        )
        document = self.envelope["plain.bin"]
        self.assertEqual(
            document.hash, hashlib.sha256(self.CONTENTS["random.bin"]).hexdigest()
        )
