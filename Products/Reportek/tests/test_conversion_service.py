from unittest.mock import MagicMock, Mock, patch
from pathlib import Path

from Products.Reportek import conversion_registry
from Products.Reportek.Converter import LocalHttpConverter, _strip_hop_by_hop_headers
from Products.Reportek.Converters import Converters

from .common import BaseTest, BaseUnitTest
from .utils import create_fake_root


def CONVERTER_PARAMS():
    return dict(
        {
            "id": "http_rar2list",
            "title": "List contents",
            "convert_url": "convert/rar2list",
            "ct_input": "",
            "ct_output": "",
            "ct_schema": "",
            "ct_extraparams": "",
            "description": "",
            "suffix": "",
        }
    )


class ConversionServiceTest(BaseUnitTest):
    def setUp(self):
        self.app = create_fake_root()
        self.app._setObject("Converters", Converters())
        self.prefix = "http_"
        from ZPublisher.BaseRequest import RequestContainer

        self.app = self.app.__of__(
            RequestContainer(REQUEST=BaseTest.create_mock_request())
        )

    def test_strip_hop_by_hop_headers(self):
        headers = {
            "Content-Type": "text/plain",
            "Connection": "keep-alive, X-Internal-Header",
            "Keep-Alive": "timeout=5",
            "Transfer-Encoding": "chunked",
            "TE": "trailers",
            "Upgrade": "websocket",
            "X-Internal-Header": "remove-me",
            "X-Application-Header": "keep-me",
        }

        self.assertEqual(
            {
                "Content-Type": "text/plain",
                "X-Application-Header": "keep-me",
            },
            _strip_hop_by_hop_headers(headers),
        )

    def test_strip_hop_by_hop_headers_of_a_response(self):
        from requests.structures import CaseInsensitiveDict

        headers = CaseInsensitiveDict(
            {
                "content-type": "text/plain",
                "CONNECTION": "Keep-Alive, x-internal-header",
                "keep-alive": "timeout=5",
                "Transfer-Encoding": "chunked",
                "X-Internal-Header": "remove-me",
                "X-Application-Header": "keep-me",
            }
        )

        result = _strip_hop_by_hop_headers(headers)

        self.assertIs(result, headers)
        self.assertEqual(
            {"content-type": "text/plain", "x-application-header": "keep-me"},
            {key.lower(): value for key, value in result.items()},
        )

    def test_strip_hop_by_hop_headers_without_headers_to_strip(self):
        headers = {"Content-Type": "text/plain", "X-Other": "kept"}
        self.assertEqual(
            {"Content-Type": "text/plain", "X-Other": "kept"},
            _strip_hop_by_hop_headers(dict(headers)),
        )
        self.assertEqual({}, _strip_hop_by_hop_headers({}))

    @patch.object(Converters, "_get_local_converters")
    def test_only_http_converters(self, mock_local_converters):
        """no local converters, only http"""
        converters = [
            LocalHttpConverter(**CONVERTER_PARAMS()).__of__(self.app.Converters)
        ]
        params = CONVERTER_PARAMS()
        params.update({"id": "http_list_7zip"})
        converters.append(LocalHttpConverter(**params).__of__(self.app.Converters))
        mock_local_converters.return_value = converters
        local_converters = self.app.Converters._get_local_converters()
        self.assertEqual(
            ["%srar2list" % self.prefix, "%slist_7zip" % self.prefix],
            [conv.id for conv in local_converters],
        )

    @patch.object(Converters, "_get_local_converters")
    @patch("Products.Reportek.Converter.requests")
    def test_http_converter(self, mock_requests, mock_local_converters):
        from Products.Reportek.Document import Document

        document = Document("testfile", "", content_type="application/x-rar-compressed")
        self.app._setObject("testfile", document)
        with self.app.testfile.data_file.open("wb") as datafile:
            tests = Path(__file__).parent.absolute()
            datafile.write((tests / "onefile.rar").read_bytes())

        mock_local_converters.return_value = [
            LocalHttpConverter(**CONVERTER_PARAMS()).__of__(self.app.Converters)
        ]
        local_converters = self.app.Converters._get_local_converters()

        # assert Anonymous is unauthorized to see this file
        import zExceptions

        with self.assertRaises(zExceptions.Unauthorized):
            local_converters[0](
                file_url=self.app.testfile.absolute_url(),
                converter_id="http_rar2list",
            )

        # override normal behaviour
        # allow current user (Anonymous) to see this file
        self.app.testfile._View_Permission = ("Anonymous",)

        # no exception should be raised now
        mock_requests.post.return_value = Mock(
            content="fisier.txt", headers={"content-type": "mock/type"}
        )
        result = local_converters[0](
            file_url=self.app.testfile.absolute_url(),
            converter_id="http_rar2list",
        ).content
        self.assertIn("fisier.txt", result)

    @patch.object(Converters, "_get_local_converters")
    @patch("Products.Reportek.Converter.requests")
    def test_run_conversion_http(self, mock_requests, mock_local_converters):
        from Products.Reportek.Document import Document

        mock_local_converters.return_value = [
            LocalHttpConverter(**CONVERTER_PARAMS()).__of__(self.app.Converters)
        ]
        document = Document("testfile", "", content_type="application/x-rar-compressed")
        self.app._setObject("testfile", document)
        with self.app.testfile.data_file.open("wb") as datafile:
            tests = Path(__file__).parent.absolute()
            datafile.write((tests / "onefile.rar").read_bytes())

        from Products.Reportek.constants import CONVERTERS_ID

        converters = getattr(self.app, CONVERTERS_ID)

        # override normal behaviour
        # allow current user (Anonymous) to see this file
        self.app.testfile._View_Permission = ("Anonymous",)
        mock_requests.post.return_value = Mock(
            content="mock conversion", headers={"content-type": "mock/type"}
        )
        result = converters.run_conversion(
            self.app.testfile.absolute_url(),
            converter_id="%srar2list" % self.prefix,
            source="local",
        )
        self.assertEqual("mock conversion", result)

    @patch("Products.Reportek.Converter.requests")
    def test_run_conversion_remote(self, mock_requests):
        from Products.Reportek.Document import Document

        document = Document("testfile", "", content_type="application/x-rar-compressed")
        self.app.Converters._setObject("testfile", document)

        with self.app.Converters.testfile.data_file.open("wb") as datafile:
            datafile.write(b"test file")

        mock_resp = MagicMock()
        mock_resp.iter_content = Mock(return_value=["txtesrever"])
        mock_requests.configure_mock(**{"post.return_value": mock_resp})
        self.app.REQUEST = Mock(SESSION="")

        params = {
            "file_url": "Converters/testfile",
            "converter_id": "",
            "source": "remote",
            "REQUEST": {
                "source": "remote",
                "file_url": "Converters/testfile",
                "conv": "",
            },
        }
        # assert Anonymous is unauthorized to see this file
        import zExceptions

        with self.assertRaises(zExceptions.Unauthorized):
            self.app.Converters.run_conversion(**params)

        # override normal behaviour
        # allow current user (Anonymous) to see this file
        self.app.Converters.testfile._View_Permission = ("Anonymous",)
        self.app.Converters.note = Mock(return_value="")
        result = self.app.Converters.run_conversion(**params)
        self.assertFalse(self.app.REQUEST.RESPONSE.write.called)
        self.assertEqual(["txtesrever"], list(result))
        self.assertTrue(mock_resp.close.called)

    def _remote_convert(self, mock_requests, headers, chunks, error=None):
        from requests.structures import CaseInsensitiveDict

        from Products.Reportek.Converter import RemoteConverter
        from Products.Reportek.Document import Document

        if "testfile" in self.app.Converters.objectIds():
            self.app.Converters._delObject("testfile")
        document = Document("testfile", "", content_type="application/x-rar")
        self.app.Converters._setObject("testfile", document)
        mock_resp = MagicMock()
        mock_resp.headers = CaseInsensitiveDict(headers)
        mock_resp.iter_content = Mock(return_value=iter(chunks))
        mock_resp.raise_for_status = Mock(side_effect=error)
        mock_requests.post.return_value = mock_resp
        conv = RemoteConverter("remote_conv").__of__(self.app.Converters)
        conv.api_url = "http://converters.test"
        request = self.app.REQUEST = Mock(SESSION=Mock())
        request.RESPONSE.headers = {}
        file_obj = self.app.Converters.testfile
        file_obj.note = Mock(return_value="note")
        return conv, file_obj, mock_resp, request

    @patch("Products.Reportek.Converter.requests")
    def test_remote_conversion_is_streamed(self, mock_requests):
        conv, file_obj, mock_resp, request = self._remote_convert(
            mock_requests,
            {"Content-Type": "text/plain", "Content-Length": "6"},
            [b"abc", b"def"],
        )
        result = conv.convert(file_obj)
        self.assertTrue(mock_requests.post.call_args[1]["stream"])
        self.assertFalse(request.RESPONSE.write.called)
        self.assertFalse(mock_resp.close.called)
        self.assertEqual(b"abcdef", b"".join(result))
        self.assertTrue(mock_resp.close.called)
        self.assertEqual("text/plain", request.RESPONSE.headers["Content-Type"])
        self.assertEqual("6", request.RESPONSE.headers["Content-Length"])

    @patch("Products.Reportek.Converter.requests")
    def test_remote_conversion_closed_when_not_consumed(self, mock_requests):
        conv, file_obj, mock_resp, request = self._remote_convert(
            mock_requests, {"Content-Type": "text/plain"}, [b"abc", b"def"]
        )
        result = conv.convert(file_obj)
        next(result)
        result.close()
        self.assertEqual(1, mock_resp.close.call_count)

    @patch("Products.Reportek.Converter.requests")
    def test_remote_conversion_gzip_content_length(self, mock_requests):
        conv, file_obj, mock_resp, request = self._remote_convert(
            mock_requests,
            {
                "Content-Type": "text/plain",
                "Content-Encoding": "gzip",
                "Content-Length": "3",
            },
            [b"abcdef"],
        )
        conv.convert(file_obj)
        headers = request.RESPONSE.headers
        self.assertEqual("none", headers["Content-Encoding"])
        self.assertNotIn("Content-Length", headers)

    @patch("Products.Reportek.Converter.requests")
    def test_remote_conversion_decoded_content_headers(self, mock_requests):
        for encoding in ("gzip", "deflate", "GZIP", "br"):
            conv, file_obj, mock_resp, request = self._remote_convert(
                mock_requests,
                {
                    "Content-Type": "text/plain",
                    "Content-Encoding": encoding,
                    "Content-Length": "3",
                },
                [b"abcdef"],
            )
            conv.convert(file_obj)
            headers = request.RESPONSE.headers
            self.assertEqual("none", headers["Content-Encoding"], encoding)
            self.assertNotIn("Content-Length", headers, encoding)

    @patch("Products.Reportek.Converter.requests")
    def test_remote_conversion_not_encoded_keeps_the_length(self, mock_requests):
        conv, file_obj, mock_resp, request = self._remote_convert(
            mock_requests,
            {"Content-Encoding": "identity", "Content-Length": "6"},
            [b"abcdef"],
        )
        conv.convert(file_obj)
        headers = request.RESPONSE.headers
        self.assertEqual("identity", headers["Content-Encoding"])
        self.assertEqual("6", headers["Content-Length"])

    @patch("Products.Reportek.Converter.requests")
    def test_remote_conversion_does_not_copy_date_and_server(self, mock_requests):
        conv, file_obj, mock_resp, request = self._remote_convert(
            mock_requests,
            {
                "Content-Type": "text/plain",
                "Date": "Thu, 12 Nov 2026 20:34:25 GMT",
                "Server": "BaseHTTP/0.6",
                "X-Other": "kept",
            },
            [b"abc"],
        )
        conv.convert(file_obj)
        headers = request.RESPONSE.headers
        self.assertNotIn("Date", headers)
        self.assertNotIn("Server", headers)
        self.assertEqual("kept", headers["X-Other"])

    @patch("Products.Reportek.Converter.requests")
    def test_remote_conversion_http_error(self, mock_requests):
        from requests import HTTPError

        conv, file_obj, mock_resp, request = self._remote_convert(
            mock_requests, {}, [], error=HTTPError("boom")
        )
        mock_requests.HTTPError = HTTPError
        mock_resp.text = "converter failed"
        request.__getitem__ = Mock(return_value="/referer")
        self.assertEqual("note", conv.convert(file_obj))
        self.assertTrue(mock_resp.close.called)
        notes = dict(c[0] for c in request.SESSION.set.call_args_list)
        self.assertIn("converter failed", notes["note_text"])

    @patch("Products.Reportek.Converter.requests")
    def test_remote_conversion_connection_error(self, mock_requests):
        from requests import ConnectionError, HTTPError

        conv, file_obj, mock_resp, request = self._remote_convert(mock_requests, {}, [])
        mock_requests.HTTPError = HTTPError
        mock_requests.post.side_effect = ConnectionError("<down>")
        request.__getitem__ = Mock(return_value="/referer")
        self.assertEqual("note", conv.convert(file_obj))
        notes = dict(c[0] for c in request.SESSION.set.call_args_list)
        self.assertIn("down", notes["note_text"])
        self.assertNotIn("<", notes["note_text"].split("<br />")[-1])

    @patch.object(Converters, "_http_params")
    def test_converter_ct_extraparams_attribute(self, mock_http_params):
        mock_http_params.return_value = [
            [
                "prettyxml",
                "Pretty XML",
                "convert/xml2txt",
                ["text/plain"],
                "text/plain",
                "",
                ["country_code"],
                "",
                "xml",
            ]
        ]
        [conv] = self.app.Converters._get_local_converters()
        self.assertEqual(["country_code"], conv.ct_extraparams)

    @patch.object(conversion_registry, "get_country_code")
    @patch.object(Converters, "_http_params")
    def test_conversion_registry_with_good_key(
        self, mock_http_params, mock_get_country_code
    ):
        mock_http_params.return_value = [
            [
                "prettyxml",
                "Pretty XML",
                "convert/xml2txt",
                ["text/plain"],
                "text/plain",
                "",
                ["country_code"],
                "",
                "xml",
            ]
        ]

        mock_get_country_code.return_value = "AT"
        [conv] = self.app.Converters._get_local_converters()
        self.assertEqual(
            ["AT"], conversion_registry.request_params(conv.ct_extraparams)
        )

    @patch.object(conversion_registry, "get_country_code")
    @patch.object(Converters, "_http_params")
    def test_conversion_registry_with_non_existing_key(
        self, mock_http_params, mock_get_country_code
    ):
        mock_http_params.return_value = [
            [
                "prettyxml",
                "Pretty XML",
                "convert/xml2txt",
                ["text/plain"],
                "text/plain",
                "",
                ["bad_key"],
                "",
                "xml",
            ]
        ]

        [conv] = self.app.Converters._get_local_converters()
        self.assertRaises(
            NotImplementedError,
            conversion_registry.request_params,
            conv.ct_extraparams,
        )

    @patch.object(conversion_registry, "get_country_code")
    @patch.object(Converters, "_http_params")
    @patch("Products.Reportek.Converter.requests")
    def test_conversion_output_with_extraparams(
        self, mock_requests, mock_http_params, mock_get_country_code
    ):
        mock_http_params.return_value = [
            [
                "rar2list",
                "Pretty XML",
                "convert/xml2txt",
                ["text/plain"],
                "text/plain",
                "",
                ["country_code"],
                "",
                "xml",
            ]
        ]

        mock_get_country_code.return_value = "AT"
        [conv] = self.app.Converters._get_local_converters()
        from Products.Reportek.Document import Document

        document = Document("testfile", "", content_type="application/x-rar-compressed")
        self.app.Converters._setObject("testfile", document)

        with self.app.Converters.testfile.data_file.open("wb") as datafile:
            datafile.write(b"test file")

        self.app.Converters.testfile._View_Permission = ("Anonymous",)
        file_url = "/Converters/testfile"
        converter_id = conv.id
        conv(file_url, converter_id)
        files = mock_requests.mock_calls[0][2]["files"]
        data = mock_requests.mock_calls[0][2]["data"]
        assert files["file"]
        self.assertEqual({"extraparams": ["AT"]}, data)

    @patch.object(Converters, "_http_params")
    @patch("Products.Reportek.Converter.requests")
    def test_shp_conversionr(self, mock_requests, mock_http_params):
        mock_http_params.return_value = [
            [
                "shp2img",
                "Show shapefile as image",
                "convert/shp2img",
                ["application/x-shp"],
                "image/jpeg",
                "",
                [],
                "",
            ]
        ]

        [shp_conv] = self.app.Converters._get_local_converters()
        from Products.Reportek.Document import Document

        document = Document("test.shp", "", content_type="application/x-shp")
        self.app.Converters._setObject("test.shp", document)

        document = Document("test.shx", "", content_type="application/x-shx")
        self.app.Converters._setObject("test.shx", document)

        document = Document("test.dbf", "", content_type="application/dbf")
        self.app.Converters._setObject("test.dbf", document)
        for item in self.app.Converters.objectValues():
            item._View_Permission = ("Anonymous",)
            with item.data_file.open("wb") as datafile:
                datafile.write(b"test file")

        # Capture file contents when requests.post is called,
        # before files are closed
        captured_files = {}

        def capture_files(*args, **kwargs):
            files = kwargs.get("files", {})
            for key, fh in files.items():
                captured_files[key] = fh.read()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.reason = "OK"
            mock_response.headers = {"content-type": "image/jpeg"}
            return mock_response

        mock_requests.post.side_effect = capture_files

        file_url = "/Converters/test.shp"
        shp_conv(file_url, shp_conv.id)
        self.assertEqual(set(["file", "shx", "dbf"]), set(captured_files.keys()))
        for content in captured_files.values():
            self.assertEqual(b"test file", content)


class ConversionRegistryTest(BaseUnitTest):
    def setUp(self):
        self.app = create_fake_root()
        self.app._setObject("Converters", Converters())
        # self.prefix = 'http_'
        # from ZPublisher.BaseRequest import RequestContainer
        # self.app = self.app.__of__(
        # RequestContainer(REQUEST=create_mock_request()))

    @patch.object(Converters, "_http_params")
    def test_get_country_code(self, mock_http_params):
        mock_http_params.return_value = [
            [
                "rar2list",
                "Pretty XML",
                "convert/xml2txt",
                ["text/plain"],
                "text/plain",
                "",
                ["country_code"],
                "",
                "xml",
            ]
        ]
        [conv] = self.app.Converters._get_local_converters()
        file_obj = Mock()
        envelope = Mock()
        envelope.getCountryCode = Mock(return_value="AT")
        file_obj.getParentNode = Mock(return_value=envelope)
        self.assertEqual(
            ["AT"],
            conversion_registry.request_params(["country_code"], obj=file_obj),
        )
