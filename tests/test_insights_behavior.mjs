// Behavior test: createSourceInsight must not accept pre-existing insights as the
// result of a new generation. Run with: node tests/test_insights_behavior.mjs
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

// Instant timers so the 2s poll delay does not slow the test.
const realSetTimeout = globalThis.setTimeout;
globalThis.setTimeout = (fn) => realSetTimeout(fn, 0);

const { model, setApi } = loadModel();

function stubApi(handler) {
    setApi(async (_pluginPath, opts) => handler(opts));
}

const SRC = 'src-1';

async function testExistingInsightsAreNotTreatedAsNew() {
    // The source already has one insight. Generation never produces a new one.
    model.activeInsightSourceId = SRC;
    model.insightCache = { [SRC]: [{ id: 'old-1', insight_type: 'Summary' }] };
    model.insightsError = {};
    model.insightsLoading = {};
    model.sourceInsights = [{ id: 'old-1', subtype: 'stale' }];

    stubApi(async (opts) => {
        if (opts.method === 'POST' || (opts.method || '').toUpperCase() === 'POST') {
            return { _proxy_status: 202, data: { ok: true } };
        }
        // GET always returns the same single pre-existing insight.
        return { _proxy_status: 200, data: [{ id: 'old-1', insight_type: 'Summary' }] };
    });

    await model.createSourceInsight(SRC, 'preset-1');

    const err = model.insightsError[SRC] || '';
    assert.match(
        err,
        /timed out/i,
        'expected a timeout error when no NEW insight appears, got: ' + JSON.stringify(err)
    );
    assert.equal(model.insightsLoading[SRC], false, 'loading flag must clear');
    console.log('ok - existing insights are not accepted as a new result');
}

async function testNewInsightIsAccepted() {
    model.insightCache = { [SRC]: [{ id: 'old-1' }] };
    model.insightsError = {};
    model.insightsLoading = {};
    model.sourceInsights = [];

    let gets = 0;
    stubApi(async (opts) => {
        if ((opts.method || '').toUpperCase() === 'POST') return { _proxy_status: 202, data: {} };
        gets += 1;
        const list = gets === 1 ? [{ id: 'old-1' }] : [{ id: 'old-1' }, { id: 'new-2' }];
        return { _proxy_status: 200, data: list };
    });

    await model.createSourceInsight(SRC, 'preset-1');

    assert.equal(model.insightsError[SRC], null, 'no error on success');
    assert.equal(model.sourceInsights.length, 2, 'new insight list applied');
    assert.ok(model.sourceInsights.some((i) => i.id === 'new-2'), 'new id present');
    assert.equal(model.insightsLoading[SRC], false, 'loading flag must clear');
    console.log('ok - a genuinely new insight is accepted');
}

async function testFailedLoadDoesNotPoisonTheCache() {
    const other = 'src-2';
    model.insightCache = {};
    model.insightsError = {};

    stubApi(async () => { throw new Error('network down'); });
    await model.loadInsights(other);
    assert.equal(model.insightCache[other], undefined, 'failure must not cache an empty list');
    assert.match(model.insightsError[other] || '', /network down/);

    stubApi(async () => ({ _proxy_status: 200, data: [{ id: 'x' }] }));
    await model.loadInsights(other);
    assert.equal(model.insightCache[other].length, 1, 'retry after failure must fetch');
    console.log('ok - failed load does not poison the cache');
}

const results = [];
for (const [name, fn] of [
    ['existing insights are not treated as new', testExistingInsightsAreNotTreatedAsNew],
    ['new insight is accepted', testNewInsightIsAccepted],
    ['failed load does not poison cache', testFailedLoadDoesNotPoisonTheCache],
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
