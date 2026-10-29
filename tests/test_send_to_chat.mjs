// Behavior test: send-to-A0-Chat must place content in the core composer store.
// The core WebUI registers its composer store as 'chatInput'; an 'input' event on
// the contenteditable #chat-input re-syncs that store from the editor text, so any
// injected content that only lives in the DOM is silently erased.
// Run with: node tests/test_send_to_chat.mjs
// Override the store under test with STORE_PATH=/path/to/store.js
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import assert from 'node:assert/strict';

const HERE = dirname(fileURLToPath(import.meta.url));
const STORE_PATH = process.env.STORE_PATH || join(HERE, '..', 'webui', 'open_notebook-store.js');

function loadModel() {
    const src = readFileSync(STORE_PATH, 'utf8');
    const start = src.indexOf('let _callJsonApi = null;');
    const modelStart = src.indexOf('const model = {');
    const end = src.indexOf('\n};\n', modelStart);
    if (start < 0 || modelStart < 0 || end < 0) throw new Error('could not slice store body');
    const body = src.slice(start, end + 3);
    const factory = new Function(`${body}\nreturn { model, setApi: (fn) => { _callJsonApi = fn; } };`);
    return factory();
}

// ── Fake core WebUI composer ───────────────────────────────────────────────
// Mirrors the real contracts: #chat-input is a contenteditable div (a .value
// assignment does nothing), the composer store is named 'chatInput', and an
// 'input' event re-syncs the store from the editor's text.
function makeHarness({ withComposer = true, withAttachments = true } = {}) {
    const toastContent = { title: '', message: '' };
    const toastClasses = new Set();

    const editor = {
        value: '',
        textContent: '',
        scrollHeight: 40,
        style: {},
        focused: false,
        events: [],
        focus() { this.focused = true; },
        dispatchEvent(ev) {
            this.events.push(ev.type);
            if (ev.type === 'input') composer.syncFromEditor();
            return true;
        },
    };

    const composer = {
        _message: '',
        get message() { return this._message; },
        set message(v) {
            this._message = String(v ?? '');
            editor.textContent = this._message;
        },
        syncFromEditor() { this._message = editor.textContent; },
        focus() { editor.focused = true; },
        setCaret(offset) { this.caret = offset; },
    };

    const attachments = { added: [], addAttachment(a) { this.added.push(a); } };

    const toast = {
        classList: {
            add(c) { toastClasses.add(c); },
            remove(c) { toastClasses.delete(c); },
            contains(c) { return toastClasses.has(c); },
        },
        querySelector(sel) {
            if (sel === '.toast__title') return { set textContent(v) { toastContent.title = v; }, get textContent() { return toastContent.title; } };
            if (sel === '.toast__message') return { set textContent(v) { toastContent.message = v; }, get textContent() { return toastContent.message; } };
            return { textContent: '' };
        },
    };

    globalThis.document = {
        getElementById(id) {
            if (id === 'chat-input') return editor;
            if (id === 'toast') return toast;
            return null;
        },
    };

    globalThis.Alpine = {
        store(name) {
            if (name === 'chatInput') return withComposer ? composer : undefined;
            if (name === 'chatAttachments') return withAttachments ? attachments : undefined;
            // No 'inputStore' store exists in the core WebUI.
            return undefined;
        },
    };

    return { editor, composer, attachments, toast, toastContent, toastClasses };
}

const { model, setApi } = loadModel();

// ── Tests ─────────────────────────────────────────────────────────────────

async function testShortTextReachesComposerStore() {
    const h = makeHarness();
    model.sendToChat('hello note body', []);
    assert.equal(h.composer.message, 'hello note body', 'short text must land in the chatInput store');
    console.log('ok - short text reaches the composer store');
}

async function testShortTextSurvivesComposerInputEvent() {
    const h = makeHarness();
    model.sendToChat('short note', []);
    // The core composer runs this on every input/focus cycle.
    h.composer.syncFromEditor();
    assert.equal(h.composer.message, 'short note', 'text must not be erased by the composer input cycle');
    console.log('ok - short text survives the composer input cycle');
}

async function testNoteWrapperSendsTitleAndBody() {
    const h = makeHarness();
    model.error = null;
    const seen = [];
    setApi(async (_pluginPath, opts) => {
        seen.push(opts.path);
        return { _proxy_status: 200, data: { title: 'My Note', content: 'Body text' } };
    });
    await model.sendNoteToChat('note-1');
    assert.ok(seen.some((p) => /\/api\/notes\/note-1/.test(String(p))), 'note must be fetched through the proxy, saw: ' + JSON.stringify(seen));
    assert.match(h.composer.message, /My Note/, 'note title must reach the composer');
    assert.match(h.composer.message, /Body text/, 'note body must reach the composer');
    console.log('ok - note wrapper delivers title and body');
}

async function testLongTextIsAttachedAsFile() {
    const h = makeHarness();
    const long = 'x'.repeat(2500);
    model.sendToChat(long, []);
    assert.equal(h.attachments.added.length, 1, 'long text must become one attachment');
    assert.match(h.attachments.added[0].name, /\.md$/, 'attachment must be a markdown file');
    console.log('ok - long text is attached as a file');
}

async function testAttachmentPathFillsComposerPrompt() {
    const h = makeHarness();
    model.sendToChat('y'.repeat(2500), []);
    assert.match(h.composer.message, /Review the attached file/, 'attachment path must prompt in the composer');
    console.log('ok - attachment path fills the composer prompt');
}

async function testMissingComposerShowsErrorInsteadOfDropping() {
    const h = makeHarness({ withComposer: false });
    model.sendToChat('cannot be delivered', []);
    const text = `${h.toastContent.title} ${h.toastContent.message}`;
    assert.ok(h.toastClasses.has('show'), 'a toast must be shown when the composer is unavailable');
    assert.match(text, /chat|composer/i, 'toast must explain the chat composer is unavailable, got: ' + text);
    console.log('ok - missing composer raises a visible error');
}

const results = [];
for (const [name, fn] of [
    ['short text reaches composer store', testShortTextReachesComposerStore],
    ['short text survives input cycle', testShortTextSurvivesComposerInputEvent],
    ['note wrapper delivers title and body', testNoteWrapperSendsTitleAndBody],
    ['long text is attached as file', testLongTextIsAttachedAsFile],
    ['attachment path fills composer prompt', testAttachmentPathFillsComposerPrompt],
    ['missing composer shows error', testMissingComposerShowsErrorInsteadOfDropping],
]) {
    try {
        await fn();
        results.push({ name, ok: true });
    } catch (e) {
        results.push({ name, ok: false, error: e.message });
    }
}

const failed = results.filter((r) => !r.ok);
for (const r of failed) console.error('FAIL - ' + r.name + ': ' + r.error);
console.log(`\n${results.length - failed.length}/${results.length} passed`);
process.exit(failed.length ? 1 : 0);
