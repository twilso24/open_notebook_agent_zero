// Behavior test: row-menu placement must flip above the trigger when there is
// no room below, use the real menu size, and stay inside the viewport.
// Slice-runs the store body (same harness as test_send_to_chat.mjs).
// Run with: node tests/test_menu_placement.mjs
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
    return new Function(`${body}\nreturn { model };`)();
}

const { model } = loadModel();
const EDGE = 8;
const GAP = 4;

const VP_PHONE = { width: 390, height: 844 };
const MENU_2 = { width: 180, height: 82 };
const MENU_6 = { width: 196, height: 246 };

// Row near the top: plenty of room below.
const TOP_ROW = { top: 200, bottom: 244, left: 330, right: 374 };
// Row low on a phone: no room for a 6-item menu below.
const BOTTOM_ROW = { top: 760, bottom: 804, left: 330, right: 374 };
// Row on the left edge.
const LEFT_ROW = { top: 300, bottom: 344, left: 10, right: 54 };

function testOpensBelowWhenThereIsRoom() {
    const pos = model._computeMenuPos(TOP_ROW, MENU_2, VP_PHONE);
    assert.equal(pos.top, TOP_ROW.bottom + GAP, 'menu must open just below the trigger when it fits');
    assert.ok(pos.top + MENU_2.height <= VP_PHONE.height - EDGE, 'menu must stay inside the viewport');
    console.log('ok - opens below when there is room');
}

function testFlipsAboveWhenNoRoomBelow() {
    const pos = model._computeMenuPos(BOTTOM_ROW, MENU_6, VP_PHONE);
    assert.equal(pos.top, BOTTOM_ROW.top - MENU_6.height - GAP, 'menu must flip above the trigger when it cannot fit below');
    assert.ok(pos.top >= EDGE, 'flipped menu must stay inside the viewport top edge');
    console.log('ok - flips above when there is no room below');
}

function testNeverCoversItsOwnTrigger() {
    const pos = model._computeMenuPos(BOTTOM_ROW, MENU_6, VP_PHONE);
    const overlaps = pos.top < BOTTOM_ROW.bottom && pos.top + MENU_6.height > BOTTOM_ROW.top;
    assert.ok(!overlaps, `menu must not overlap its own trigger row (top=${pos.top})`);
    console.log('ok - never covers its own trigger');
}

function testClampsInsideShortViewport() {
    const shortVp = { width: 390, height: 300 };
    const row = { top: 120, bottom: 164, left: 330, right: 374 };
    const pos = model._computeMenuPos(row, MENU_6, shortVp);
    assert.ok(pos.top >= EDGE, 'menu top must respect the viewport edge');
    assert.ok(pos.top + MENU_6.height <= shortVp.height - EDGE, 'menu bottom must stay inside a short viewport');
    console.log('ok - clamps inside a short viewport');
}

function testRightAlignsToTrigger() {
    const pos = model._computeMenuPos(TOP_ROW, MENU_2, VP_PHONE);
    assert.equal(pos.left + MENU_2.width, TOP_ROW.right, 'menu right edge must align with the trigger right edge');
    console.log('ok - right-aligns to the trigger');
}

function testClampsLeftEdge() {
    const pos = model._computeMenuPos(LEFT_ROW, MENU_2, VP_PHONE);
    assert.ok(pos.left >= EDGE, 'menu must not be pushed off the left edge');
    assert.ok(pos.left + MENU_2.width <= VP_PHONE.width - EDGE, 'menu must stay inside the right edge');
    console.log('ok - clamps at the left edge');
}

function testMenuWiderThanViewport() {
    const tinyVp = { width: 200, height: 600 };
    const wideMenu = { width: 260, height: 100 };
    const pos = model._computeMenuPos({ top: 100, bottom: 144, left: 20, right: 64 }, wideMenu, tinyVp);
    assert.equal(pos.left, EDGE, 'oversized menu must pin to the left edge');
    console.log('ok - oversized menu pins to the left edge');
}

// The panel list is `overflow:hidden`, so a menu that only respects the window
// still gets clipped. Placement must clamp inside the visible container.
function testStaysInsideScrollContainer() {
    const container = { top: 300, bottom: 620, left: 0, right: 390 };
    const row = { top: 560, bottom: 604, left: 330, right: 374 };
    const pos = model._computeMenuPos(row, MENU_6, VP_PHONE, container);
    assert.ok(pos.top + MENU_6.height <= container.bottom - EDGE,
        `menu bottom ${pos.top + MENU_6.height} must stay inside container bottom ${container.bottom}`);
    assert.ok(pos.top >= container.top + EDGE, 'menu top must stay inside the container top');
    console.log('ok - stays inside the scroll container');
}

function testFlipsUpInsideContainerEvenWhenWindowHasRoom() {
    const container = { top: 300, bottom: 620, left: 0, right: 390 };
    const row = { top: 540, bottom: 584, left: 330, right: 374 };
    const pos = model._computeMenuPos(row, MENU_6, VP_PHONE, container);
    assert.ok(pos.top < row.top, 'menu must flip above the row when the container has no room below');
    console.log('ok - flips up because of the container, not the window');
}

// ── DOM wiring ────────────────────────────────────────────────────────────
// After the menu is teleported to <body>, it is no longer a child of the row,
// so lookup by row has to fall back to the document-scoped key.
function makeDom({ menuHeight = 246, menuWidth = 196 } = {}) {
    const menuEl = {
        _style: 'display:none',
        getAttribute() { return this._style; },
        setAttribute(_n, v) { this._style = v; },
        getBoundingClientRect() { return { width: menuWidth, height: menuHeight, top: 0, left: 0, bottom: menuHeight, right: menuWidth }; },
        querySelector() { return null; },
    };
    const btn = {
        getBoundingClientRect() { return { top: 760, bottom: 804, left: 330, right: 374, height: 44, width: 44 }; },
        // Menu lives inside the row that owns the trigger (teleport reverted).
        parentElement: { querySelector(sel) { return sel.includes('on-context-menu') ? menuEl : null; } },
        closest() { return null; },
    };
    const queries = [];
    globalThis.document = {
        querySelector(sel) { queries.push(sel); return sel.includes('data-menu-key') ? menuEl : null; },
        querySelectorAll() { return []; },
    };
    globalThis.window = { innerWidth: 390, innerHeight: 844 };
    return { btn, menuEl, queries };
}

function stubChain(specs) {
    const nodes = specs.map((s) => ({
        parentElement: null,
        getBoundingClientRect() { return { top: s.rect.top, left: s.rect.left, width: 0, height: 0 }; },
        _cs: {
            transform: s.transform || 'none',
            filter: s.filter || 'none',
            backdropFilter: s.backdropFilter || 'none',
            perspective: s.perspective || 'none',
            willChange: s.willChange || 'auto',
            contain: s.contain || 'none',
        },
    }));
    for (let i = 0; i < nodes.length - 1; i++) nodes[i].parentElement = nodes[i + 1];
    globalThis.getComputedStyle = (el) => el._cs;
    return nodes[0];
}

function testOpenUsesRealMenuHeightToFlipUp() {
    const dom = makeDom();
    model._menuPos = { top: 0, left: 0 };
    model._openRowMenu('note-43', { currentTarget: dom.btn, target: dom.btn });
    assert.ok(model._menuPos.top < 760, `menu must flip above a row at 760 with no room below, got top=${model._menuPos.top}`);
    console.log('ok - uses the measured menu height to flip up');
}

function testNoOffsetWithoutTransformAncestor() {
    const el = stubChain([
        { transform: 'none', rect: { top: 0, left: 0 } },
        { transform: 'none', rect: { top: 100, left: 16 } },
    ]);
    const off = model._containingBlockOffset(el);
    assert.deepEqual(off, { top: 0, left: 0 }, 'no transform ancestor means no compensation');
    console.log('ok - no offset without a transformed ancestor');
}

function testOffsetFromTransformedAncestor() {
    const el = stubChain([
        { transform: 'none', rect: { top: 563, left: 33 } },
        { transform: 'none', rect: { top: 247, left: 33 } },
        { transform: 'matrix(1, 0, 0, 1, -179.4, -320.7)', rect: { top: 101, left: 16 } },
    ]);
    const off = model._containingBlockOffset(el);
    assert.deepEqual(off, { top: 101, left: 16 }, 'transformed ancestor origin must be returned');
    console.log('ok - offset taken from the transformed ancestor');
}

function testOffsetFromFilterAncestor() {
    const el = stubChain([
        { transform: 'none', filter: 'blur(2px)', rect: { top: 40, left: 12 } },
    ]);
    const off = model._containingBlockOffset(el);
    assert.deepEqual(off, { top: 40, left: 12 }, 'filter also establishes a containing block');
    console.log('ok - offset taken from a filtered ancestor');
}

function testLocalPosSubtractsOffset() {
    const local = model._toLocalMenuPos({ top: 500, left: 200 }, { top: 101, left: 16 });
    assert.deepEqual(local, { top: 399, left: 184 }, 'viewport position must be shifted into the ancestor space');
    console.log('ok - local position subtracts the offset');
}

// The trigger sits inside a wrapper inside the row, so the menu is NOT on
// btn.parentElement — it is on the row. Without this lookup the menu cannot be
// measured, so it never flips above and can open off the bottom of the pane.
function testFindsMenuOnTheRowAncestor() {
    const menuEl = {};
    const row = { querySelector(sel) { return sel.includes('on-context-menu') ? menuEl : null; } };
    const btn = {
        parentElement: { querySelector() { return null; } },
        closest(sel) { return sel.includes('on-list-item') ? row : null; },
    };
    const found = model._findRowMenu('note-1', btn);
    assert.equal(found, menuEl, 'must find the menu on the row ancestor when it is not on the immediate parent');
    console.log('ok - finds the menu on the row ancestor');
}

function testOpeningFlipsUpWhenTheRowIsNearThePaneBottom() {
    const menuHeight = 134;
    const menuEl = {
        _style: 'display:none',
        getAttribute() { return this._style; },
        setAttribute(_n, v) { this._style = v; },
        getBoundingClientRect() { return { width: 180, height: menuHeight, top: 0, left: 0, bottom: menuHeight, right: 180 }; },
    };
    const pane = { getBoundingClientRect() { return { top: 247, bottom: 726 }; } };
    const row = { querySelector(sel) { return sel.includes('on-context-menu') ? menuEl : null; } };
    const btn = {
        getBoundingClientRect() { return { top: 573, bottom: 617, left: 293, right: 337, width: 44, height: 44 }; },
        parentElement: { querySelector() { return null; } },
        closest(sel) {
            if (sel.includes('on-list-item')) return row;
            if (sel.includes('on-scroll')) return pane;
            return null;
        },
    };
    globalThis.window = { innerWidth: 390, innerHeight: 844 };
    globalThis.getComputedStyle = () => ({});
    model._menuPos = { top: 0, left: 0 };
    model._openRowMenu('note-9', { currentTarget: btn, target: btn });
    assert.ok(model._menuPos.top < 573, `menu must open above a row at 573 with no room below, got top=${model._menuPos.top}`);
    console.log('ok - flips above when the row is near the pane bottom');
}

// ── Close guard must be target-based, not time-based ─────────────────────
// A tap on mobile can deliver its away-click more than 250ms after the open
// (tap-to-click delay), so a Date.now() window is fragile. Decide by what was
// clicked instead.
function testTapOnMenuTriggerDoesNotClose() {
    const trigger = { closest: (sel) => (sel.includes('on-menu-trigger') ? { tag: 'BUTTON' } : null) };
    model._activeMenuId = 'note-70';
    model._closeRowMenu({ target: trigger });
    assert.equal(model._activeMenuId, 'note-70', 'a tap on the trigger must not close the menu it opens');
    console.log('ok - tap on trigger does not close');
}

function testTapInsideMenuDoesNotClose() {
    const inside = { closest: (sel) => (sel.includes('on-context-menu') ? { tag: 'DIV' } : null) };
    model._activeMenuId = 'note-71';
    model._closeRowMenu({ target: inside });
    assert.equal(model._activeMenuId, 'note-71', 'a tap inside the menu must not close it');
    console.log('ok - tap inside menu does not close');
}

function testTapElsewhereClosesRegardlessOfTiming() {
    const outside = { closest: () => null };
    model._activeMenuId = 'note-72';
    model._menuOpenedAt = Date.now(); // even immediately after opening
    model._closeRowMenu({ target: outside });
    assert.equal(model._activeMenuId, null, 'a tap outside must close, independent of elapsed time');
    console.log('ok - outside tap closes regardless of timing');
}

// Measuring a closed menu temporarily makes it visible off-screen. If that
// measurement throws (slow mobile layout, detached node), the temporary
// visibility:hidden must NOT be left behind or the menu never appears.
function testMeasureRestoresStyleWhenMeasurementThrows() {
    let style = 'display:none';
    let reads = 0;
    const menuEl = {
        getAttribute() { return style; },
        setAttribute(_n, v) { style = v; },
        getBoundingClientRect() {
            reads += 1;
            if (reads > 1) throw new Error('layout unavailable');
            return { width: 0, height: 0, top: 0, left: 0, bottom: 0, right: 0 };
        },
    };
    let threw = false;
    try { model._measureMenu(menuEl); } catch (_e) { threw = true; }
    assert.equal(style, 'display:none', `menu style must be restored even if measuring throws, got: ${style}`);
    console.log('ok - restores menu style when measurement throws' + (threw ? ' (and may rethrow)' : ''));
}

const results = [];
for (const [name, fn] of [
    ['opens below when there is room', testOpensBelowWhenThereIsRoom],
    ['flips above when no room below', testFlipsAboveWhenNoRoomBelow],
    ['never covers its own trigger', testNeverCoversItsOwnTrigger],
    ['clamps inside short viewport', testClampsInsideShortViewport],
    ['right-aligns to trigger', testRightAlignsToTrigger],
    ['clamps left edge', testClampsLeftEdge],
    ['oversized menu pins left', testMenuWiderThanViewport],
    ['stays inside scroll container', testStaysInsideScrollContainer],
    ['flips up because of container', testFlipsUpInsideContainerEvenWhenWindowHasRoom],
    ['uses measured height to flip up', testOpenUsesRealMenuHeightToFlipUp],
    ['no offset without transform', testNoOffsetWithoutTransformAncestor],
    ['offset from transformed ancestor', testOffsetFromTransformedAncestor],
    ['offset from filter ancestor', testOffsetFromFilterAncestor],
    ['local pos subtracts offset', testLocalPosSubtractsOffset],
    ['finds menu on the row ancestor', testFindsMenuOnTheRowAncestor],
    ['flips above near pane bottom', testOpeningFlipsUpWhenTheRowIsNearThePaneBottom],
    ['tap on trigger does not close', testTapOnMenuTriggerDoesNotClose],
    ['tap inside menu does not close', testTapInsideMenuDoesNotClose],
    ['outside tap closes regardless of timing', testTapElsewhereClosesRegardlessOfTiming],
    ['restores style when measuring throws', testMeasureRestoresStyleWhenMeasurementThrows],
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
