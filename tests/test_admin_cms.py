import re
import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADMIN = ROOT / "admin"


class _Resources(HTMLParser):
    """Collects every locally referenced script, stylesheet and inline script."""

    def __init__(self):
        super().__init__()
        self.sources = []
        self.stylesheets = []
        self.inline_scripts = []
        self._in_script = False

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "script":
            self._in_script = True
            if attributes.get("src"):
                self.sources.append(attributes["src"])
        if tag == "link" and attributes.get("href"):
            self.stylesheets.append(attributes["href"])

    def handle_endtag(self, tag):
        if tag == "script":
            self._in_script = False

    def handle_data(self, data):
        if self._in_script and data.strip():
            self.inline_scripts.append(data.strip())


_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)


def _without_comments(markup):
    """Comments may document the old defect; only live markup is asserted on."""
    return _COMMENT.sub("", markup)


def _collection_blocks(config_text):
    lines = config_text.splitlines()
    starts = [
        index
        for index, line in enumerate(lines)
        if re.match(r'^  - name: "[^"]+"\s*$', line)
    ]
    return [
        lines[start : starts[position + 1] if position + 1 < len(starts) else len(lines)]
        for position, start in enumerate(starts)
    ]


class AdminPageTests(unittest.TestCase):
    def setUp(self):
        self.html = (ADMIN / "index.html").read_text(encoding="utf-8")
        self.resources = _Resources()
        self.resources.feed(self.html)

    def test_admin_uses_decap_automatic_initialization_only(self):
        self.assertEqual(self.resources.sources, ["vendor/decap-cms.js"])
        self.assertEqual(self.resources.inline_scripts, [], "the /admin/ CSP forbids inline script")
        markup = _without_comments(self.html)
        self.assertNotIn("CMS_MANUAL_INIT", markup)
        self.assertNotIn("admin-init.js", markup)
        self.assertNotIn("admin-boot.js", markup)
        self.assertNotIn("js-yaml", markup)

    def test_obsolete_manual_bootstrap_files_are_gone(self):
        for obsolete in ("admin-init.js", "admin-boot.js"):
            with self.subTest(obsolete=obsolete):
                self.assertFalse((ADMIN / obsolete).exists())

    def test_every_resource_the_admin_page_references_exists(self):
        for reference in self.resources.sources + self.resources.stylesheets:
            with self.subTest(reference=reference):
                self.assertTrue((ADMIN / reference).is_file())


class AdminConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = (ADMIN / "config.yml").read_text(encoding="utf-8")
        cls.blocks = _collection_blocks(cls.text)

    def test_collections_have_unique_names_and_labels(self):
        names = []
        labels = []
        for block in self.blocks:
            names.append(re.match(r'^  - name: "([^"]+)"$', block[0]).group(1))
            labels.append(
                re.match(r'^    label: "([^"]+)"$', next(line for line in block if line.startswith("    label: "))).group(1)
            )
        self.assertEqual(len(names), 2)
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(len(labels), len(set(labels)))

    def test_every_collection_uses_exactly_one_supported_shape(self):
        for block in self.blocks:
            collection_name = re.match(r'^  - name: "([^"]+)"$', block[0]).group(1)
            top_level_keys = {
                match.group(1)
                for line in block
                if (match := re.match(r"^    ([a-z_]+):", line))
            }
            with self.subTest(collection=collection_name):
                self.assertNotIn("file", top_level_keys)
                self.assertEqual(len(top_level_keys & {"files", "folder"}), 1)

    def test_file_collections_target_both_content_files(self):
        paths = re.findall(r'^        file: "([^"]+)"$', self.text, flags=re.MULTILINE)
        self.assertEqual(paths, ["content/site.json", "content/policies.json"])

    def test_website_file_keeps_its_editor_and_fields(self):
        site_block = next(block for block in self.blocks if block[0] == '  - name: "site"')
        joined = "\n".join(site_block)
        self.assertIn('      - name: "website"', joined)
        self.assertIn('        label: "Website content"', joined)
        self.assertIn('        file: "content/site.json"', joined)
        self.assertIn("        fields:", joined)
        self.assertGreaterEqual(len(re.findall(r'^          - label:', joined, flags=re.MULTILINE)), 15)


if __name__ == "__main__":
    unittest.main()
