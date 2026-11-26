# -*- coding: utf-8 -*-
from unittest.mock import Mock, patch

from Products.Reportek.RemoteFMEConversionApplication import (
    RemoteFMEConversionApplication,
)
from .common import BaseUnitTest


class RemoteFMEConversionApplicationFeedbackContentTest(BaseUnitTest):
    def _make_fme_app(self):
        return RemoteFMEConversionApplication(
            "fme",
            "",
            "https://fme.example",
            "",
            "token",
            "",
            "",
            "",
            "minute",
            "upload",
            "dir",
            "",
            None,
            None,
            False,
            "",
            None,
            True,
            300,
            "fme_app",
        )

    def test_fme_bytes_are_decoded_to_text(self):
        text = "smałl FME feedback"
        app = self._make_fme_app()

        self.assertEqual(app.ensure_text(text.encode("utf-8")), text)

    def test_fme_zip_download_uses_binary_stream(self):
        app = self._make_fme_app()
        env = Mock()
        env.getPhysicalPath.return_value = ("", "cdr", "env")
        env.manage_addDDzipfile.side_effect = lambda file, verbose: (
            file.read(),
            getattr(file, "filename", None),
            verbose,
        )
        workitem = Mock()
        workitem.getMySelf.return_value = env
        setattr(app, "workitem", workitem)
        response = Mock(status_code=200, content=b"zip-bytes")

        with patch(
            "Products.Reportek.RemoteFMEConversionApplication.requests.post",
            return_value=response,
        ):
            result = app.handle_res_zip_download("workitem")

        self.assertEqual(result, (b"zip-bytes", "resources.zip", True))
