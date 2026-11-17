import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('writing', ROOT / 'scripts/build_writing.py')
writing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(writing)


class WritingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        # Keep fixtures isolated from new publications: production essays are checked by the build.
        (self.root / 'writing').mkdir()
        shutil.copytree(ROOT / 'writing/why-write', self.root / 'writing/why-write')
        shutil.copytree(ROOT / 'scripts/templates', self.root / 'scripts/templates')
        self.original = (self.root / 'writing/why-write/index.html').read_text()

    def test_full_original_article_and_permalink(self):
        output = writing.build(self.root)
        parsed = writing.EssayParser(self.original)
        self.assertIn(self.original[parsed.start:parsed.end], output)
        self.assertIn('href="./why-write/"', output)
        self.assertIn('This is the first essay.', output)
        self.assertEqual((self.root / 'writing/why-write/index.html').read_text(), self.original)
        self.assertEqual(output, writing.build(self.root))

    def test_new_essay_promotes_and_removal_restores(self):
        original_index = writing.build(self.root)
        # Reuse the existing text as a temporary fixture, never publish new prose.
        fixture = self.original.replace('2026-11-14', '2026-11-15').replace('November 14, 2026', 'November 15, 2026').replace('0. Why Write?', 'Temporary verification fixture')
        directory = self.root / 'writing/temporary-test'
        directory.mkdir()
        (directory / 'index.html').write_text(fixture)
        output = writing.build(self.root)
        self.assertIn('<h1>Temporary verification fixture</h1>', output)
        self.assertNotIn('<h1>0. Why Write?</h1>', output)
        self.assertIn('<li><a href="./why-write/">0. Why Write?</a>', output)
        self.assertIn('<time datetime="2026-11-14">November 14, 2026</time></li>', output)
        shutil.rmtree(directory)
        self.assertEqual(writing.build(self.root), original_index)

    def test_drafts_ignored_and_missing_date_fails(self):
        directory = self.root / 'writing/draft'
        directory.mkdir()
        (directory / 'index.html').write_text('<article data-status="draft"><h1>Draft</h1></article>')
        self.assertNotIn('<h1>Draft</h1>', writing.build(self.root))
        (directory / 'index.html').write_text('<article><h1>Undated</h1></article>')
        with self.assertRaises(ValueError):
            writing.build(self.root)

    def test_relative_links_rebased_without_changing_words(self):
        source = '<article><p>Exact words &amp; punctuation.</p><a href="../why-write/#note">Link</a><img src="image.png" alt=""/><a href="#note">Note</a><a href="https://example.org/">External</a></article>'
        output = writing.RebaseLinks(source, 'second').result()
        self.assertIn('href="why-write/#note"', output)
        self.assertIn('src="second/image.png"', output)
        self.assertIn('<p>Exact words &amp; punctuation.</p>', output)
        self.assertIn('href="#note"', output)
        self.assertIn('href="https://example.org/"', output)


if __name__ == '__main__':
    unittest.main()
