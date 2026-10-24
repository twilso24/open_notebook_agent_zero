from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SLOT = ROOT / 'extensions' / 'webui' / 'chat-input-progress-start' / 'open_notebook-context.html'
STORE = ROOT / 'webui' / 'a0-context-store-v2.js'
TOOL = ROOT / 'tools' / 'opennotebook_chat.py'
STATUS_MAP = ROOT / 'tools' / 'context_selection.py'


def test_chip_slot_file_exists():
    assert SLOT.exists(), 'chip must live in the model-context-strip-end slot'


def test_chip_labelled_notebooks():
    src = SLOT.read_text()
    assert 'Notebooks' in src


def test_drilldown_has_notebook_checkboxes_source_modes_insights_and_notes():
    src = SLOT.read_text()
    assert 'type="checkbox"' in src
    assert "'off'" in src and "'full'" in src and "'insights'" in src
    assert 'notes' in src


def test_notebook_row_is_button_based_with_stop_click():
    src = SLOT.read_text()
    start = src.index('<button type="button" class="on-ctx-nb__row"')
    row = src[start:start + 700]
    assert '<button type="button"' in row, 'row must be a button for reliable mobile taps'
    assert '@click.prevent.stop="$store.openNotebookContext.toggleNotebook(nb.id)"' in row, 'one tap must toggle exactly once and stop propagation'
    assert '<input' not in row, 'no native checkbox (mobile never ticks / double-activates)'
    assert '<label' not in row, 'no native label wrapper'
    assert 'role="checkbox"' in row
    assert ':aria-checked="$store.openNotebookContext.isNotebookSelected(nb.id)"' in row
    assert 'on-ctx-nb__box' in row, 'row must show a visual checkmark'

def test_notebook_row_has_touch_manipulation_css():
    src = SLOT.read_text()
    assert 'touch-action: manipulation' in src, 'rows must suppress mobile tap delay zoom'


def test_mapping_module_maps_selection_to_context_config():
    assert STATUS_MAP.exists(), 'tools/context_selection.py must define the selection-to-context mapping'
    src = STATUS_MAP.read_text()
    assert 'full content' in src
    assert 'insights' in src
    assert 'not in' in src


def test_ask_refuses_without_selected_notebook():
    src = TOOL.read_text() if TOOL.exists() else ''
    assert 'pick notebooks' in src.lower() or 'select notebooks' in src.lower(), 'ask must not fall back to all sources'


def test_selector_store_syncs_selection_to_server_endpoint():
    src = STORE.read_text()
    assert 'syncToServer' in src
    assert 'context_selection' in src
    assert 'window.getContext' in src
    assert 'context_id: ctxId' in src
    assert 'selection: this.selection' in src


def test_mobile_panel_uses_fixed_overlay_and_viewport_width():
    src = SLOT.read_text()
    assert 'position: fixed' in src
    assert 'calc(100vw - 16px)' in src


def test_chip_store_has_mount_probe():
    src = STORE.read_text()
    assert 'mountOk' in src
    assert 'this.mountOk = true' in src


def test_store_save_does_not_sync_to_server():
    src = STORE.read_text()
    start = src.index('save() {')
    body = src[start:start + 160]
    assert 'syncToServer' not in body, 'save() must not sync; syncing belongs to user actions'


def test_store_save_guards_localstorage_errors():
    src = STORE.read_text()
    start = src.index('save() {')
    body = src[start:start + 300]
    assert 'try {' in body, 'save() must not throw when localStorage is unavailable (mobile private mode)'
    assert 'catch' in body


def test_store_loads_server_selection_when_local_empty():
    src = STORE.read_text()
    assert 'loadFromServer' in src
    assert '!Object.keys(this.selection).length' in src


def test_user_actions_commit_to_server_not_only_save():
    src = STORE.read_text()
    for method in ['toggleNotebook(nbId) {', 'setSourceMode(nbId, srcId, mode) {', 'toggleInsight(nbId, srcId, insId) {', 'toggleNote(nbId, noteId) {']:
        start = src.index(method)
        body = src[start:start + 900]
        assert 'this.commit()' in body, method + ' must commit so deselection reaches the server'


def test_panel_shows_store_error_on_screen():
    src = SLOT.read_text()
    panel = src[src.index('on-ctx-panel__body'):src.index('on-ctx-panel__foot')]
    assert 'storeError' in panel, 'panel must show the error text so mobile users can read failures'


def test_load_notebooks_records_error_for_display():
    src = STORE.read_text()
    start = src.index('async loadNotebooks() {')
    body = src[start:start + 600]
    assert 'this.storeError =' in body


def test_toggle_notebook_records_error_for_display():
    src = STORE.read_text()
    start = src.index('toggleNotebook(nbId) {')
    body = src[start:start + 700]
    assert 'catch' in body, 'a tap must not fail silently on mobile'
    assert 'this.storeError =' in body, 'tap failures must be shown on screen'


def test_close_is_quiet_and_does_not_write_error_text():
    src = STORE.read_text()
    start = src.index('close() {')
    body = src[start:start + 80]
    assert 'this.isOpen = false' in body
    assert 'storeError' not in body, 'close() must not write diagnostic text into the visible error line'


def test_sync_guards_context_lookup_errors():
    src = STORE.read_text()
    start = src.index('syncToServer() {')
    body = src[start:start + 600]
    assert 'try {' in body
    assert 'catch' in body
    assert body.index('window.getContext') > body.index('try {')


def test_panel_is_not_teleported_in_progress_slot():
    src = SLOT.read_text()
    assert 'x-teleport' not in src, 'panel stays inside the chip root in the progress slot; teleport caused duplicate lists'


def test_panel_has_no_outside_click_close():
    src = SLOT.read_text()
    assert '@click.outside' not in src, 'outside-close misfires on mobile row taps'
    assert '@click="$store.openNotebookContext.close()"' in src, 'the close button must still close the panel'





def test_panel_fixed_overlay_capped_to_chat_column():
    src = (ROOT / 'extensions' / 'webui' / 'chat-input-progress-start' / 'open_notebook-context.html').read_text()
    panel_css = src[src.index('.on-ctx-panel {'):src.index('.on-ctx-panel__head')]
    assert 'position: fixed' in panel_css
    assert 'left: 8px' in panel_css
    assert 'min(380px, calc(100vw - 16px))' in panel_css, 'panel width must be capped to the chat column'
