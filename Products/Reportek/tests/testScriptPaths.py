"""The paths that the administration scripts get on the command line.

A path can lead anywhere with .. or with a link, so the scripts only read what
is in the places they are meant to read from. The files are dummy.
"""

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from Products.Reportek.config import DEPLOYMENT_BDR
from Products.Reportek.updates import import_ecas_plugin

LOCALES = Path(import_ecas_plugin.__file__).parents[1] / "locales"


class ScratchDirectory(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(os.path.realpath(tmp.name))
        self.allowed = self.root / "allowed"
        self.allowed.mkdir()
        self.outside = self.root / "outside"
        self.outside.mkdir()

    def write(self, directory, name, content="{}"):
        path = directory / name
        path.write_text(content)
        return path


class EcasExportPathTest(ScratchDirectory):
    def setUp(self):
        super().setUp()
        env = patch.dict(
            os.environ, {"ECAS_EXPORT_DIR": str(self.allowed)}, clear=False
        )
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop("ECAS_EXPORT_PATH", None)

    def test_a_file_of_an_allowed_directory(self):
        path = self.write(self.allowed, "ecas_export.json")
        self.assertEqual(import_ecas_plugin._find_export_path(str(path)), str(path))

    def test_a_file_of_the_current_directory(self):
        path = self.write(self.outside, "ecas_export.json")
        with patch("os.getcwd", return_value=str(self.outside)):
            self.assertEqual(import_ecas_plugin._find_export_path(str(path)), str(path))

    def test_a_path_that_leaves_the_allowed_directory_with_dots(self):
        self.write(self.outside, "ecas_export.json")
        (self.allowed / "sub").mkdir()
        path = self.allowed / "sub" / ".." / ".." / "outside" / "ecas_export.json"
        with self.assertRaises(ValueError):
            import_ecas_plugin._find_export_path(str(path))

    def test_a_link_that_leads_out_of_the_allowed_directory(self):
        target = self.write(self.outside, "secret.json")
        link = self.allowed / "ecas_export.json"
        os.symlink(target, link)
        with self.assertRaises(ValueError):
            import_ecas_plugin._find_export_path(str(link))

    def test_a_file_that_is_not_json(self):
        path = self.write(self.allowed, "ecas_export.txt")
        with self.assertRaises(ValueError):
            import_ecas_plugin._find_export_path(str(path))

    def test_a_directory(self):
        (self.allowed / "dir.json").mkdir()
        with self.assertRaises(ValueError):
            import_ecas_plugin._find_export_path(str(self.allowed / "dir.json"))

    def test_a_file_that_does_not_exist(self):
        with self.assertRaises(ValueError):
            import_ecas_plugin._find_export_path(str(self.allowed / "no.json"))

    def test_the_path_of_the_environment_is_checked_too(self):
        path = self.write(self.outside, "ecas_export.json")
        with patch.dict(os.environ, {"ECAS_EXPORT_PATH": str(path)}):
            with patch("os.getcwd", return_value=str(self.root)):
                # the current directory is the parent of both directories
                self.assertEqual(import_ecas_plugin._find_export_path(), str(path))
            with patch("os.getcwd", return_value=str(self.allowed)):
                with self.assertRaises(ValueError):
                    import_ecas_plugin._find_export_path()

    def test_the_directories_of_the_environment_are_separated_by_colons(self):
        path = self.write(self.outside, "ecas_export.json")
        directories = os.pathsep.join([str(self.allowed), str(self.outside)])
        with patch.dict(os.environ, {"ECAS_EXPORT_DIR": directories}):
            with patch("os.getcwd", return_value=str(self.allowed)):
                self.assertEqual(
                    import_ecas_plugin._find_export_path(str(path)), str(path)
                )

    def test_the_id_of_the_plugin_is_checked(self):
        path = self.write(
            self.allowed,
            "ecas_export.json",
            json.dumps({"format": "reportek-ecas-export-v1"}),
        )
        with patch.object(import_ecas_plugin, "REPORTEK_DEPLOYMENT", DEPLOYMENT_BDR):
            for plugin_id in ("../x", "a b", "9a", "a/b", "x;y"):
                with self.assertRaises(ValueError, msg=plugin_id):
                    import_ecas_plugin.update(
                        Mock(), export_path=str(path), plugin_id=plugin_id
                    )

    def test_the_ids_of_the_plugins_that_are_valid(self):
        for plugin_id in ("eCas", "ecas_plugin", "eCas-2", "CAS"):
            self.assertTrue(
                import_ecas_plugin.PLUGIN_ID_PATTERN.match(plugin_id), plugin_id
            )


class PageBasedPoPathTest(ScratchDirectory):
    def setUp(self):
        super().setUp()
        spec = importlib.util.spec_from_file_location(
            "page_based_po", LOCALES / "page-based-po.py"
        )
        self.script = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.script)

    def test_the_script_can_be_imported_and_says_how_to_use_it(self):
        self.assertIn("<main.po>", self.script.usage())

    def test_a_po_file(self):
        path = self.write(self.allowed, "main.po")
        self.assertEqual(
            self.script.checked_file(str(path), (".po", ".pot")), str(path)
        )

    def test_a_file_that_is_not_a_po_file(self):
        path = self.write(self.allowed, "main.txt")
        with self.assertRaises(ValueError):
            self.script.checked_file(str(path), (".po", ".pot"))

    def test_a_file_that_does_not_exist(self):
        with self.assertRaises(ValueError):
            self.script.checked_file(str(self.allowed / "no.po"), (".po",))

    def test_a_directory(self):
        self.assertEqual(
            self.script.checked_dir(str(self.allowed) + "/"), str(self.allowed)
        )
        with self.assertRaises(ValueError):
            self.script.checked_dir(str(self.allowed / "no"))
        with self.assertRaises(ValueError):
            self.script.checked_dir(str(self.write(self.allowed, "a.po")))

    def test_the_path_is_the_real_one(self):
        (self.allowed / "sub").mkdir()
        path = self.allowed / "sub" / ".." / "sub"
        self.assertEqual(self.script.checked_dir(str(path)), str(self.allowed / "sub"))

    def test_the_files_of_a_directory_without_the_links_that_leave_it(self):
        inside = self.write(self.allowed, "a.html")
        self.write(self.allowed, "b.html")
        (self.allowed / "subdir").mkdir()
        outside = self.write(self.outside, "secret.html")
        os.symlink(outside, self.allowed / "link.html")
        os.symlink(inside, self.allowed / "inner-link.html")
        found = list(self.script.files_of(str(self.allowed)))
        self.assertIn(str(inside), found)
        self.assertNotIn(str(outside), found)
        self.assertEqual(sorted(Path(f).name for f in found), ["a.html", "b.html"])
