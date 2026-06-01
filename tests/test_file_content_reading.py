import unittest
import os
import tempfile
import sys

# Add tools directory to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tools'))

from opennotebook_sources import _detect_and_prepare


class TestFileContentReading(unittest.TestCase):
    """Test that _detect_and_prepare correctly reads file content instead of passing file paths."""

    def setUp(self):
        """Create test files for use in tests."""
        self.test_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test files."""
        import shutil
        shutil.rmtree(self.test_dir)

    def test_local_file_path_reads_content(self):
        """Verify that a local file path results in reading the file content."""
        # Create a test file with specific content
        test_file = os.path.join(self.test_dir, 'test.txt')
        test_content = 'This is test file content for verification.'
        with open(test_file, 'w') as f:
            f.write(test_content)

        # Call _detect_and_prepare with the file path
        source_type, request_data = _detect_and_prepare(test_file, '', 'test_notebook')

        # Verify the content is the actual file content, not the path
        self.assertEqual(source_type, 'text')
        self.assertEqual(request_data['content'], test_content)
        self.assertNotEqual(request_data['content'], test_file)
        self.assertEqual(request_data['type'], 'text')

    def test_title_auto_set_from_filename(self):
        """Verify that title is auto-set to filename when not provided."""
        test_file = os.path.join(self.test_dir, 'my_document.txt')
        with open(test_file, 'w') as f:
            f.write('content')

        source_type, request_data = _detect_and_prepare(test_file, '', 'test_notebook')

        # Title should be 'my_document' (filename without extension)
        self.assertEqual(request_data['title'], 'my_document')

    def test_explicit_title_overrides_filename(self):
        """Verify that explicit title overrides filename auto-detection."""
        test_file = os.path.join(self.test_dir, 'file.txt')
        with open(test_file, 'w') as f:
            f.write('content')

        source_type, request_data = _detect_and_prepare(test_file, 'Custom Title', 'test_notebook')

        # Title should be the explicit one, not filename-derived
        self.assertEqual(request_data['title'], 'Custom Title')

    def test_non_existent_file_raises_error(self):
        """Verify that attempting to read a non-existent file raises ValueError."""
        non_existent = os.path.join(self.test_dir, 'does_not_exist.txt')

        with self.assertRaises(ValueError) as context:
            _detect_and_prepare(non_existent, '', 'test_notebook')

        self.assertIn('File not found', str(context.exception))

    def test_markdown_file_handling(self):
        """Verify that markdown files are handled correctly."""
        test_file = os.path.join(self.test_dir, 'test.md')
        md_content = '# Heading\n\nThis is markdown content.'
        with open(test_file, 'w') as f:
            f.write(md_content)

        source_type, request_data = _detect_and_prepare(test_file, '', 'test_notebook')

        self.assertEqual(source_type, 'text')
        self.assertEqual(request_data['content'], md_content)

    def test_url_still_works(self):
        """Verify that URLs still work correctly (not broken by the fix)."""
        url = 'https://example.com/page'
        source_type, request_data = _detect_and_prepare(url, '', 'test_notebook')

        self.assertEqual(source_type, 'link')
        self.assertEqual(request_data['type'], 'link')
        self.assertEqual(request_data['url'], url)

    def test_raw_text_still_works(self):
        """Verify that raw text input still works correctly."""
        raw_text = 'This is just some text without a file extension'
        source_type, request_data = _detect_and_prepare(raw_text, '', 'test_notebook')

        self.assertEqual(source_type, 'text')
        self.assertEqual(request_data['type'], 'text')
        self.assertEqual(request_data['content'], raw_text)


if __name__ == '__main__':
    unittest.main()