import unittest

import xlwt

from Products.Reportek.ReportekEngine import ReportekEngine

# Magic bytes of the OLE2 compound document that xlwt emits and Excel expects.
OLE2_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


class DummyResponse:
    def __init__(self):
        self.headers = {}

    def setHeader(self, name, value):
        self.headers[name.lower()] = value


class DummyRequest:
    def __init__(self):
        self.response = DummyResponse()


class DummyEngine:
    """Just enough engine to exercise download_xls on its own."""

    download_xls = ReportekEngine.download_xls

    def __init__(self):
        self.REQUEST = DummyRequest()


class TestXlsDownload(unittest.TestCase):
    """xlwt writes bytes, so the buffer it saves into must be a BytesIO.

    Regression: a StringIO made every .xls export (ReportekEngine/xls_export
    and Envelope/xls) fail on Python 3 with
    ``TypeError: string argument expected, got 'bytes'``.
    """

    def _workbook(self):
        wb = xlwt.Workbook()
        sheet = wb.add_sheet("Results")
        sheet.write(0, 0, "envelope")
        return wb

    def test_download_xls_returns_a_binary_workbook(self):
        engine = DummyEngine()

        payload = engine.download_xls(self._workbook(), "searchresults.xls")

        self.assertIsInstance(payload, bytes)
        self.assertEqual(payload[:8], OLE2_MAGIC)

    def test_download_xls_sets_the_excel_download_headers(self):
        engine = DummyEngine()

        engine.download_xls(self._workbook(), "envelope-1.xls")

        headers = engine.REQUEST.response.headers
        self.assertIn("ms-excel", headers["content-type"])
        self.assertEqual(
            headers["content-disposition"],
            "attachment; filename=envelope-1.xls",
        )


if __name__ == "__main__":
    unittest.main()


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestXlsDownload))
    return suite
