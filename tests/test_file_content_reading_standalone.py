import unittest
import os
import tempfile

# Known file extensions for auto-detection (copied from tool)
_FILE_EXTENSIONS = {'.pdf', '.doc', '.docx', '.txt', '.md', '.rtf', '.odt', '.epub', '.html', '.htm', '.csv'}

def _detect_and_prepare_standalone(content: str, title: str, notebook_id: str) -> tuple:
    """Standalone version of _detect_and_prepare for testing.
    
    This is the fixed version that reads file content locally.
    """
    # Build base data dict
    request_data = {
        "notebook_id": notebook_id,
        "title": title or "",
        "embed": "true",
        "async_processing": "true",
    }

    # Detect source type from content
    lower_content = content.lower()
    if lower_content.startswith(("http://", "https://")):
        source_type = "link"
        request_data["type"] = "link"
        request_data["url"] = content
    else:
        # Check if content looks like a file path with a known extension
        content_path = content.strip()
        _, ext = os.path.splitext(content_path)
        
        if ext.lower() in _FILE_EXTENSIONS:
            # This looks like a file path with a known extension
            if os.path.isfile(content_path):
                # File exists - read the file content
                try:
                    with open(content_path, 'r', encoding='utf-8', errors='replace') as f:
                        file_content = f.read()
                    source_type = "text"
                    request_data["type"] = "text"
                    request_data["content"] = file_content  # Actual file content, not path
                    # Update title if not provided, use filename
                    if not title:
                        filename = os.path.basename(content_path)
                        request_data["title"] = os.path.splitext(filename)[0]
                except PermissionError:
                    raise ValueError(f"Permission denied reading file: {content_path}")
                except UnicodeDecodeError as e:
                    raise ValueError(f"Cannot decode file content (may be binary): {content_path} - {str(e)}")
                except Exception as e:
                    raise ValueError(f"Error reading file {content_path}: {str(e)}")
            else:
                # File has known extension but doesn't exist
                raise ValueError(f"File not found: {content_path}")
        else:
            # Treat as raw text content
            source_type = "text"
            request_data["type"] = "text"
            request_data["content"] = content_path  # raw text

    return source_type, request_data


class TestFileContentReading(unittest.TestCase):
    """Test that file content is read correctly instead of passing file paths."""

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

        # Call _detect_and_prepare_standalone with the file path
        source_type, request_data = _detect_and_prepare_standalone(test_file, '', 'test_notebook')

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

        source_type, request_data = _detect_and_prepare_standalone(test_file, '', 'test_notebook')

        # Title should be 'my_document' (filename without extension)
        self.assertEqual(request_data['title'], 'my_document')

    def test_explicit_title_overrides_filename(self):
        """Verify that explicit title overrides filename auto-detection."""
        test_file = os.path.join(self.test_dir, 'file.txt')
        with open(test_file, 'w') as f:
            f.write('content')

        source_type, request_data = _detect_and_prepare_standalone(test_file, 'Custom Title', 'test_notebook')

        # Title should be the explicit one, not filename-derived
        self.assertEqual(request_data['title'], 'Custom Title')

    def test_non_existent_file_raises_error(self):
        """Verify that attempting to read a non-existent file raises ValueError."""
        non_existent = os.path.join(self.test_dir, 'does_not_exist.txt')

        with self.assertRaises(ValueError) as context:
            _detect_and_prepare_standalone(non_existent, '', 'test_notebook')

        self.assertIn('File not found', str(context.exception))

    def test_markdown_file_handling(self):
        """Verify that markdown files are handled correctly."""
        test_file = os.path.join(self.test_dir, 'test.md')
        md_content = '# Heading\n\nThis is markdown content.'
        with open(test_file, 'w') as f:
            f.write(md_content)

        source_type, request_data = _detect_and_prepare_standalone(test_file, '', 'test_notebook')

        self.assertEqual(source_type, 'text')
        self.assertEqual(request_data['content'], md_content)

    def test_url_still_works(self):
        """Verify that URLs still work correctly (not broken by the fix)."""
        url = 'https://example.com/page'
        source_type, request_data = _detect_and_prepare_standalone(url, '', 'test_notebook')

        self.assertEqual(source_type, 'link')
        self.assertEqual(request_data['type'], 'link')
        self.assertEqual(request_data['url'], url)

    def test_raw_text_still_works(self):
        """Verify that raw text input still works correctly."""
        raw_text = 'This is just some text without a file extension'
        source_type, request_data = _detect_and_prepare_standalone(raw_text, '', 'test_notebook')

        self.assertEqual(source_type, 'text')
        self.assertEqual(request_data['type'], 'text')
        self.assertEqual(request_data['content'], raw_text)

    def test_file_path_without_known_extension_treated_as_text(self):
        """Verify that a file path without known extension is treated as raw text."""
        # Create a file without known extension
        test_file = os.path.join(self.test_dir, 'test.unknown_ext')
        with open(test_file, 'w') as f:
            f.write('This should not be read as file content')

        source_type, request_data = _detect_and_prepare_standalone(test_file, '', 'test_notebook')

        # Should be treated as raw text (the path itself), not file content
        self.assertEqual(source_type, 'text')
        self.assertEqual(request_data['content'], test_file)

    def test_multiline_file_content(self):
        """Verify that multiline file content is read correctly."""
        test_file = os.path.join(self.test_dir, 'multiline.txt')
        multiline_content = 'Line 1\nLine 2\nLine 3\nLine 4'
        with open(test_file, 'w') as f:
            f.write(multiline_content)

        source_type, request_data = _detect_and_prepare_standalone(test_file, '', 'test_notebook')

        self.assertEqual(request_data['content'], multiline_content)


if __name__ == '__main__':
    unittest.main()