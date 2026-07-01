import unittest

from Products.Reportek.scripts import get_script_args


class ScriptArgsTest(unittest.TestCase):
    def test_direct_console_script_args(self):
        argv = ["/opt/zope/bin/auto_env_cleanup", "--inactive_for", "30"]

        self.assertEqual(
            ["--inactive_for", "30"], get_script_args("auto_env_cleanup", argv)
        )

    def test_legacy_instance_run_args(self):
        argv = [
            "instance",
            "run",
            "/opt/zope/bin/auto_env_cleanup",
            "--inactive_for",
            "30",
        ]

        self.assertEqual(
            ["--inactive_for", "30"], get_script_args("auto_env_cleanup", argv)
        )

    def test_zconsole_run_args(self):
        argv = [
            "zconsole",
            "run",
            "/opt/zope/etc/zope.conf",
            "/opt/zope/bin/auto_env_cleanup",
            "--inactive_for",
            "30",
            "--limit",
            "10",
        ]

        self.assertEqual(
            ["--inactive_for", "30", "--limit", "10"],
            get_script_args("auto_env_cleanup", argv),
        )

    def test_zconsole_run_python_file_args(self):
        argv = [
            "zconsole",
            "run",
            "/opt/zope/etc/zope.conf",
            "/opt/zope/src/Products.Reportek/Products/Reportek/scripts/auto_env_cleanup.py",
            "--inactive_for",
            "30",
        ]

        self.assertEqual(
            ["--inactive_for", "30"], get_script_args("auto_env_cleanup", argv)
        )

    def test_fallback_to_console_script_semantics(self):
        argv = ["custom-wrapper", "--inactive_for", "30"]

        self.assertEqual(
            ["--inactive_for", "30"], get_script_args("auto_env_cleanup", argv)
        )


if __name__ == "__main__":
    unittest.main()
