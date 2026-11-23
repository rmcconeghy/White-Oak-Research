import sys
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_home import build, excerpt


class HomeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "writing").mkdir()
        shutil.copytree(ROOT / "writing/why-write", self.root / "writing/why-write")
        shutil.copytree(ROOT / "scripts/templates", self.root / "scripts/templates")
        self.original = (self.root / "writing/why-write/index.html").read_text(encoding="utf-8")

    def publish_fixture(self, slug, day, title):
        folder = self.root / "writing" / slug
        folder.mkdir()
        content = (self.original.replace('2026-11-14', f'2026-11-{day:02d}')
                   .replace('November 14, 2026', f'November {day}, 2026')
                   .replace('0. Why Write?', title))
        (folder / "index.html").write_text(content, encoding="utf-8")

    def test_generate_homepage_and_preserve_original(self):
        result = build(self.root)
        self.assertIn("Making Sense of the", result)
        self.assertIn("Data.</em>", result)
        self.assertIn('href="./writing/why-write/"', result)
        self.assertIn("1 essays", result)
        self.assertEqual(result, build(self.root))
        self.assertEqual(self.original, (self.root / "writing/why-write/index.html").read_text(encoding="utf-8"))

    def test_latest_featured_four_previews_and_archive_link(self):
        for day in (15, 16, 17, 18, 19):
            self.publish_fixture(f"test-{day}", day, f"Test essay {day}")
        result = build(self.root)
        self.assertIn("6 essays", result)
        self.assertEqual(result.count('class="essay-preview'), 4)
        self.assertEqual(result.count('class="essay-preview essay-preview--latest"'), 1)
        self.assertIn("Test essay 19", result)
        self.assertNotIn("Test essay 15", result)
        self.assertLess(result.index("Test essay 19"), result.index("Test essay 18"))
        self.assertIn('href="./writing/"', result)

    def test_drafts_ignored_and_html_escaped(self):
        draft = self.root / "writing/draft"
        draft.mkdir()
        (draft / "index.html").write_text('<article data-status="draft"><h1>Ignore</h1></article>', encoding="utf-8")
        result = build(self.root)
        self.assertNotIn("Ignore", result)
        self.assertNotIn("https://", excerpt('<article><p>Some text https://example.com/ more text.</p></article>'))
        self.assertEqual("A &amp; B", excerpt('<article><p>A &amp; B</p></article>').replace("&", "&amp;"))

    def test_invalid_publication_date_rejected(self):
        folder = self.root / "writing/broken"
        folder.mkdir()
        (folder / "index.html").write_text(self.original.replace('data-published="2026-11-14"', 'data-published="2026-11-20"'), encoding="utf-8")
        with self.assertRaises(ValueError):
            build(self.root)


if __name__ == "__main__":
    unittest.main()
