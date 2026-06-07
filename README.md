# Open Notebook Plugin for Agent Zero

A knowledge management plugin that integrates [Open Notebook](https://github.com/lfnovo/open_notebook) into Agent Zero's WebUI, providing notebooks, source management, name-based fuzzy lookup, notes, and podcast generation — all from a sidebar panel.

## Features

### Notebooks
- Browse notebooks and inspect notebook details
- Name-based source and note lookup
- Notebook-scoped workflows for browsing, adding, and querying content
- Notebook creation accepts routed aliases such as `name`, `title`, and `notebook_name`
- Natural-language create requests like `create a notebook named tester` and `open notebook tester` map to the create flow

### Sources
- Import by **URL**, **text**, or **local file path**
- View processing status with colored badges
- Retry failed source processing
- Delete sources from the panel

#### Supported Local File Types
When using the `opennotebook_sources:add` tool, local files with the following extensions are automatically detected, read, and uploaded as text:

| Category | Extensions |
|----------|------------|
| Documents | `.pdf`, `.doc`, `.docx`, `.odt`, `.rtf`, `.epub` |
| Text & Web | `.txt`, `.md`, `.html`, `.htm` |
| Data | `.csv` |

**Behavior:**
- Content is read from the local filesystem and uploaded to the Open Notebook backend.
- The title defaults to the filename if one is not provided.
- Errors (e.g., permission denied, file not found) return actionable guidance.
