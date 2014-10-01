import unittest
from path import path
from mock import Mock

from Products.Reportek.zip_content import ZZipFile, ZZipFileRaw

FILE1_NAME = 'sample.xls'
FILE1_CRC = 811920726
FILE2_NAME = 'plant_catalog.xml'
FILE2_CRC = 2392975974

class TestZZipFile(unittest.TestCase):
    def setUp(self):
        self.inputZipPath = path(__file__).parent.abspath() / 'zipMany.zip'
        #fh = open(self.inputZipPath)
        #self.zf = ZZipFile(fh)

    def tearDown(self):
        i = 1

    def test_open_zip_fd(self):
        fh = open(self.inputZipPath)
        zf = ZZipFile(fh)
        #zf = self.zf
        fileInZip = zf.namelist()[0]
        self.assertEqual(fileInZip, FILE1_NAME)

        # setcurrentfile should not open it
        zf.setcurrentfile(fileInZip)
        self.assertFalse(zf.should_close)

        # close will reset the close flag, to avoid double close
        zf.close()
        self.assertFalse(zf.should_close)
        self.assertFalse(fh.closed)
        fh.close()

    def test_open_zip_path(self):
        zf = ZZipFile(self.inputZipPath)
        fileInZip = zf.namelist()[0]
        self.assertEqual(fileInZip, FILE1_NAME)

        # setcurrentfile will also open the subfile
        zf.setcurrentfile(fileInZip)
        self.assertTrue(zf.should_close)

        # close will reset the close flag, to avoid double close
        zf.close()
        self.assertFalse(zf.should_close)

    def test_read_ok(self):
        zf = ZZipFile(self.inputZipPath)
        filesInZip = zf.namelist()
        self.assertEqual(filesInZip[0], FILE1_NAME)
        zf.setcurrentfile(FILE1_NAME)
        zf.read()
        self.assertEqual(zf.getinfo(FILE1_NAME).CRC, FILE1_CRC)
        self.assertEqual(filesInZip[1], FILE2_NAME)
        zf.setcurrentfile(FILE2_NAME)
        zf.read()
        self.assertEqual(zf.getinfo(FILE2_NAME).CRC, FILE2_CRC)
        zf.close()

    def test_read_toomuch(self):
        zf = ZZipFile(self.inputZipPath)
        filesInZip = zf.namelist()
        self.assertEqual(filesInZip[1], FILE2_NAME)
        zf.setcurrentfile(FILE2_NAME)
        zi = zf.getinfo(FILE2_NAME)
        content = zf.read(1000000)
        self.assertEqual(len(content), zi.file_size)
        self.assertEqual(FILE2_CRC, zi.CRC)

    def test_read_part(self):
        zf = ZZipFile(self.inputZipPath)
        filesInZip = zf.namelist()
        self.assertEqual(filesInZip[1], FILE2_NAME)
        zf.setcurrentfile(FILE2_NAME)
        zi = zf.getinfo(FILE2_NAME)
        content = zf.read(100)
        self.assertEqual(len(content), 100)
        content2 = zf.read(100000000)
        self.assertEqual(len(content)+len(content2), zi.file_size)

    def test_read_seek(self):
        zf = ZZipFile(self.inputZipPath)
        filesInZip = zf.namelist()
        self.assertEqual(filesInZip[1], FILE2_NAME)
        zf.setcurrentfile(FILE2_NAME)
        content = zf.read(100)
        zf.seek()
        contentSame = zf.read(100)
        self.assertEqual(content, contentSame)

class TestZZipFileRaw(unittest.TestCase):
    def setUp(self):
        self.inputZipPath = path(__file__).parent.abspath() / 'zipMany.zip'


    def test_raw_open_zip_fd(self):
        fh = open(self.inputZipPath)
        zf = ZZipFileRaw(fh)
        fileInZip = zf.namelist()[0]
        self.assertEqual(fileInZip, FILE1_NAME)

        # setcurrentfile will not need to open it
        zf.setcurrentfile(fileInZip)
        self.assertTrue(zf.allowRaw)
        self.assertFalse(zf.should_close_raw)

        # close will reset the close flag, to avoid double close
        zf.close()
        self.assertFalse(zf.should_close)
        self.assertFalse(fh.closed)
        fh.close()

    def test_raw_open_zip_path(self):
        zf = ZZipFileRaw(self.inputZipPath)
        fileInZip = zf.namelist()[0]
        self.assertEqual(fileInZip, FILE1_NAME)

        # setcurrentfile will open it
        zf.setcurrentfile(fileInZip)
        self.assertTrue(zf.allowRaw)
        self.assertTrue(zf.should_close_raw)

        # close will reset the close flag, to avoid double close
        zf.close()
        self.assertFalse(zf.should_close)
