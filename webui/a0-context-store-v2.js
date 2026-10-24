// Agent Zero chat context selector store for Open Notebook.
// Feeds the Notebooks chip in the chat-input progress row.
// Selection is kept per browser in localStorage; the server mirror is a follow-up step.

const STORAGE_KEY = 'open_notebook:a0-context';
const PROXY_URL = '/api/plugins/open_notebook/proxy';

function doFetch(...args) {
  return (window.smartFetch || window.fetch)(...args);
}

async function api(method, path, body) {
  const resp = await doFetch(PROXY_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ method: method, path: path, body: body ?? null, headers: {} }),
  });
  if (!resp.ok) throw new Error('HTTP ' + resp.status);
  return resp.json();
}

function makeStore() {
  return {
    isOpen: false,
    loadingNotebooks: false,
    notebooks: [],
    storeError: '',
    mountOk: false,
    // selection[notebookId] = { sources: {id: 'off'|'full'|'insights'}, insights: {srcId: {insId: bool}}, notes: {id: bool} }
    selection: {},
    // cache for loaded lists, not persisted
    cache: { sources: {}, notes: {}, insights: {} },

    onMount() {
      try {
        this.selection = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}') || {};
      } catch (e) {
        this.selection = {};
      }
      this.mountOk = true;
      if (!Object.keys(this.selection).length) this.loadFromServer();
      Object.keys(this.selection).forEach((nb) => this.loadNotebookData(nb));
    },

    cleanup() {},

    save() {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(this.selection));
      } catch (e) {
        this.storeError = 'Could not save selection: ' + e.message;
      }
    },

    // Persist and mirror to the server. Only user actions call this.
    commit() {
      try {
        this.save();
      } catch (e) {
        this.storeError = 'save failed: ' + e.message;
      }
      try {
        this.syncToServer();
      } catch (e) {
        this.storeError = 'sync failed: ' + e.message;
      }
    },

    // Adopt the server mirror when local storage is empty (for example, a new browser).
    async loadFromServer() {
      const ctxId = (typeof window.getContext === 'function' && window.getContext()) || '';
      if (!ctxId) return;
      try {
        const resp = await doFetch('/api/plugins/open_notebook/context_selection?context_id=' + encodeURIComponent(ctxId));
        if (!resp.ok) return;
        const data = await resp.json();
        if (!Object.keys(this.selection).length && data && data.selection && typeof data.selection === 'object') {
          this.selection = data.selection;
          this.save();
        }
      } catch (e) {
        console.warn('[OpenNotebook] server selection load failed:', e.message);
      }
    },

    // Mirror the selection to the server, keyed by the active chat's context id,
    // so the opennotebook_chat tool can read it. Failures are non-fatal.
    syncToServer() {
      let ctxId = '';
      try {
        ctxId = (typeof window.getContext === 'function' && window.getContext()) || '';
      } catch (e) {
        console.warn('[OpenNotebook] context lookup failed:', e.message);
        return;
      }
      if (!ctxId) return;
      doFetch('/api/plugins/open_notebook/context_selection', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ context_id: ctxId, selection: this.selection }),
      }).catch((e) => console.warn('[OpenNotebook] context sync failed:', e.message));
    },

    toggleOpen() {
      this.isOpen = !this.isOpen;
      if (this.isOpen) this.loadNotebooks();
    },

    close() {
      this.isOpen = false;
    },

    async loadNotebooks() {
      this.loadingNotebooks = true;
      try {
        const data = await api('GET', '/api/notebooks');
        this.notebooks = Array.isArray(data) ? data : (data.data || []);
      } catch (e) {
        console.warn('[OpenNotebook] load notebooks failed:', e.message);
        this.notebooks = [];
        this.storeError = 'Could not load notebooks: ' + e.message;
      } finally {
        this.loadingNotebooks = false;
      }
    },

    async loadNotebookData(nbId) {
      try {
        const sources = await api('GET', '/api/sources?notebook_id=' + encodeURIComponent(nbId));
        const notes = await api('GET', '/api/notes?notebook_id=' + encodeURIComponent(nbId));
        const srcList = Array.isArray(sources) ? sources : (sources.data || []);
        const noteList = Array.isArray(notes) ? notes : (notes.data || []);
        this.cache.sources[nbId] = srcList;
        this.cache.notes[nbId] = noteList;
        const state = this.ensureState(nbId);
        for (const src of srcList) {
          await this.loadInsights(src.id);
          src.has_insights = (this.cache.insights[src.id] || []).length > 0;
          if (!state.sources[src.id]) {
            state.sources[src.id] = src.has_insights ? 'insights' : 'full';
          }
        }
        for (const note of noteList) {
          if (state.notes[note.id] === undefined) state.notes[note.id] = true;
        }
        this.save();
      } catch (e) {
        console.warn('[OpenNotebook] load notebook data failed:', e.message);
      }
    },

    async loadInsights(srcId) {
      if (this.cache.insights[srcId]) return;
      try {
        const data = await api('GET', '/api/sources/' + encodeURIComponent(srcId) + '/insights');
        this.cache.insights[srcId] = Array.isArray(data) ? data : (data.data || []);
      } catch (e) {
        this.cache.insights[srcId] = [];
      }
    },

    ensureState(nbId) {
      if (!this.selection[nbId]) {
        this.selection[nbId] = { sources: {}, insights: {}, notes: {} };
      }
      return this.selection[nbId];
    },

    isNotebookSelected(nbId) {
      return !!this.selection[nbId];
    },

    toggleNotebook(nbId) {
      try {
        if (this.selection[nbId]) {
          delete this.selection[nbId];
          this.commit();
        } else {
          this.ensureState(nbId);
          this.commit();
          this.loadNotebookData(nbId);
        }
      } catch (e) {
        this.storeError = 'Notebook toggle failed: ' + e.message;
      }
    },

    sourcesFor(nbId) {
      return this.cache.sources[nbId] || [];
    },

    notesFor(nbId) {
      return this.cache.notes[nbId] || [];
    },

    insightsFor(nbId, srcId) {
      return this.cache.insights[srcId] || [];
    },

    sourceMode(nbId, srcId) {
      const state = this.selection[nbId];
      return (state && state.sources[srcId]) || 'off';
    },

    setSourceMode(nbId, srcId, mode) {
      this.ensureState(nbId).sources[srcId] = mode;
      this.commit();
      if (mode === 'insights') this.loadInsights(srcId);
    },

    isInsightEnabled(nbId, srcId, insId) {
      const state = this.selection[nbId];
      const map = state && state.insights[srcId];
      return !map || map[insId] !== false;
    },

    toggleInsight(nbId, srcId, insId) {
      const state = this.ensureState(nbId);
      state.insights[srcId] = state.insights[srcId] || {};
      state.insights[srcId][insId] = !this.isInsightEnabled(nbId, srcId, insId);
      this.commit();
    },

    isNoteEnabled(nbId, noteId) {
      const state = this.selection[nbId];
      return !state || state.notes[noteId] !== false;
    },

    toggleNote(nbId, noteId) {
      const state = this.ensureState(nbId);
      state.notes[noteId] = !this.isNoteEnabled(nbId, noteId);
      this.commit();
    },

    get selectedCount() {
      return Object.keys(this.selection).length;
    },

    get chipTitle() {
      return this.selectedCount ? 'Notebook context: ' + this.countsLabel : 'Choose notebook context';
    },

    get countsLabel() {
      let full = 0;
      let insights = 0;
      let notes = 0;
      Object.keys(this.selection).forEach((nb) => {
        const state = this.selection[nb];
        Object.values(state.sources).forEach((mode) => {
          if (mode === 'full') full += 1;
        });
        Object.keys(state.sources).forEach((srcId) => {
          if (state.sources[srcId] !== 'insights') return;
          (this.cache.insights[srcId] || []).forEach((ins) => {
            if (this.isInsightEnabled(nb, srcId, ins.id)) insights += 1;
          });
        });
        Object.values(state.notes).forEach((on) => {
          if (on !== false) notes += 1;
        });
      });
      return this.selectedCount + ' notebook(s), ' + full + ' full, ' + insights + ' insights, ' + notes + ' notes';
    },
  };
}

if (window.Alpine) {
  Alpine.store('openNotebookContext', makeStore());
  console.info('[OpenNotebookContext] store registered (direct)');
} else {
  document.addEventListener('alpine:init', () => {
    Alpine.store('openNotebookContext', makeStore());
  });
}

export const store = null;
