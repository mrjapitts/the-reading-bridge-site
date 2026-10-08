"""Unit-suite entry point for the headless-Chrome admin smoke test.

The heavy lifting lives in ``scripts/browser_smoke.py`` so it can also be run
directly (``python scripts/browser_smoke.py``). This module makes the same check
part of ``python -m unittest discover -s tests``; it skips only when the host
has no local Chrome/Chromium binary, because the point of the check is to run
the real vendored bundle in a real browser.
"""

import unittest
from pathlib import Path

from scripts import browser_smoke


class BrowserSmokeUnavailable(Exception):
    pass


class AdminBrowserSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.chrome = browser_smoke.find_chrome()
        if not cls.chrome:
            raise unittest.SkipTest("no local Chrome/Chromium binary available")

    def test_admin_cms_initializes_without_manual_init_or_config_errors(self):
        report, failures = browser_smoke.run_smoke(chrome=self.chrome)
        report_path = Path(report["out"]) / "report.json"
        self.assertEqual(failures, [], "browser smoke failed: %s (report: %s)" % (failures, report_path))

        page = report["page"]
        self.assertNotIn("CMS_MANUAL_INIT", page["scriptSources"])
        self.assertEqual(page["cmsManualInitType"], "undefined", "CMS_MANUAL_INIT must not be set")
        self.assertEqual(page["scriptSources"], ["vendor/decap-cms.js"])
        self.assertGreaterEqual(page["mountDescendants"], 5, "the Decap mount rendered nothing")
        self.assertGreaterEqual(page["mountControls"], 1, "the admin UI rendered no interactive controls")
        self.assertFalse(page["configErrorVisible"], "Decap showed its config-error screen")

        config = report["config"]
        self.assertIsNone(config["parseError"])
        self.assertEqual(config["collectionCount"], 2)
        self.assertEqual(config["backend"], "git-gateway")
        for collection in config["collections"]:
            self.assertFalse(collection["singularFile"], "invalid singular top-level 'file:' reintroduced")
            self.assertNotEqual(
                collection["hasFiles"],
                collection["hasFolder"],
                "each collection needs exactly one of 'files:' or 'folder:'",
            )

        self.assertEqual(report["exceptions"], [])
        self.assertEqual(report["configPhaseExceptions"], [])


if __name__ == "__main__":
    unittest.main()
