/* Interactive browser for the Polish radiology ASR benchmark.
   Loads a slim SQLite (runs + utterances) with sql.js and computes word-level
   alignment in the browser. Two views: by recording (all models) and by model (all recordings). */

'use strict';

const NEGATIONS = new Set(['nie', 'bez', 'brak']);
const fmt = (v, d = 2) => (v === null || v === undefined || v === '') ? '–' : Number(v).toFixed(d);
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const audioHtml = (rec) => `<div class="audio"><audio controls preload="none" src="audio/${encodeURIComponent(rec)}.ogg"></audio><span class="muted">original dictation</span></div>`;
const ccerOf = (u) => {
  const t = (u.num_n || 0) + (u.neg_n || 0) + (u.side_n || 0);
  return t ? 100 * ((u.num_err || 0) + (u.neg_err || 0) + (u.side_err || 0)) / t : null;
};

let db, runs = [], runById = {}, recIndex = [];
let mode = 'rec';
let selectedRec = null, selectedModelForDiff = null, selectedRun = null;
let modelSort = 'wer_desc', ddModel = null, ddSort = null;

function q(sql, params = []) {
  const st = db.prepare(sql); st.bind(params);
  const out = []; while (st.step()) out.push(st.getAsObject()); st.free(); return out;
}

async function init() {
  try {
    const SQL = await initSqlJs({ locateFile: f => 'vendor/' + f });
    const buf = await (await fetch('data/benchmark.sqlite')).arrayBuffer();
    db = new SQL.Database(new Uint8Array(buf));

    runs = q('SELECT * FROM runs');
    runs.forEach(r => runById[r.run_id] = r);

    recIndex = q(`SELECT recording_id, MIN(ref_norm) AS ref_norm, MIN(category_code) AS category_code,
                         MIN(speaker_id) AS speaker_id, MIN(duration_s) AS duration_s,
                         COUNT(*) AS n_models
                  FROM utterances GROUP BY recording_id ORDER BY recording_id`);

    document.getElementById('loading').hidden = true;
    document.getElementById('overview').hidden = false;
    document.getElementById('browser').hidden = false;

    renderOverview();
    initControls();
    renderRecList('');
    wire();
  } catch (e) {
    const el = document.getElementById('error');
    el.hidden = false;
    el.textContent = 'Failed to load the database: ' + e.message;
    document.getElementById('loading').hidden = true;
  }
}

/* ---------- overview ---------- */
let overviewSort = { key: 'wer', dir: 1 };

function renderOverview() {
  const tbody = document.querySelector('#runs-table tbody');
  const rows = [...runs].sort((a, b) => {
    const k = overviewSort.key; let x = a[k], y = b[k];
    if (k === 'name' || k === 'mode') { return overviewSort.dir * String(x).localeCompare(String(y)); }
    x = x === null ? Infinity : x; y = y === null ? Infinity : y;
    return overviewSort.dir * (x - y);
  });
  tbody.innerHTML = rows.map(r => {
    const tag = r.mode === 'online' ? '<span class="tag">cloud</span>' : '<span class="tag">local</span>';
    return `<tr data-run="${esc(r.run_id)}">
      <td>${esc(r.name)}${tag}</td>
      <td>${esc(r.mode)}</td>
      <td class="num">${fmt(r.wer)}</td>
      <td class="num">${fmt(r.wer_num)}</td>
      <td class="num">${fmt(r.cer)}</td>
      <td class="num">${fmt(r.ter)}</td>
      <td class="num">${fmt(r.gwer)}</td>
      <td class="num">${fmt(r.num_err, 1)}</td>
      <td class="num">${fmt(r.neg_err, 1)}</td>
      <td class="num">${fmt(r.side_err, 1)}</td>
      <td class="num">${fmt(r.ccer)}</td>
      <td class="num">${fmt(r.rtf, 3)}</td>
    </tr>`;
  }).join('');
  tbody.querySelectorAll('tr').forEach(tr => tr.addEventListener('click', () => showModel(tr.dataset.run)));
}

function wire() {
  document.querySelectorAll('#runs-table thead th').forEach(th => {
    th.addEventListener('click', () => {
      const k = th.dataset.sort;
      if (overviewSort.key === k) overviewSort.dir *= -1; else overviewSort = { key: k, dir: (k === 'name' || k === 'mode') ? 1 : 1 };
      renderOverview();
    });
  });
  document.getElementById('tab-rec').addEventListener('click', () => switchTab('rec'));
  document.getElementById('tab-model').addEventListener('click', () => switchTab('model'));
  document.getElementById('rec-search').addEventListener('input', e => renderRecList(e.target.value));
  document.getElementById('model-search').addEventListener('input', () => renderModelTable());
  document.addEventListener('click', () => closeDD());
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeDD(); });
}

function switchTab(m) {
  mode = m;
  document.getElementById('tab-rec').classList.toggle('active', m === 'rec');
  document.getElementById('tab-model').classList.toggle('active', m === 'model');
  document.getElementById('pane-rec').hidden = m !== 'rec';
  document.getElementById('pane-model').hidden = m !== 'model';
  if (m === 'model' && selectedRun) renderModelTable();
}

/* ---------- by recording ---------- */
function renderRecList(query) {
  const ql = query.trim().toLowerCase();
  const list = document.getElementById('rec-list');
  const items = recIndex.filter(r => !ql || r.recording_id.toLowerCase().includes(ql) || (r.ref_norm || '').includes(ql)).slice(0, 400);
  if (!items.length) { list.innerHTML = '<div class="item muted">No recordings match.</div>'; return; }
  list.innerHTML = items.map(r => `
    <div class="item ${r.recording_id === selectedRec ? 'active' : ''}" data-rec="${esc(r.recording_id)}">
      <div class="id">${esc(r.recording_id)}</div>
      <div class="txt">${esc((r.ref_norm || '').slice(0, 90))}</div>
      <div class="meta">${esc(r.category_code)} · ${esc(r.speaker_id)} · ${fmt(r.duration_s, 1)} s</div>
    </div>`).join('');
  list.querySelectorAll('.item[data-rec]').forEach(el => el.addEventListener('click', () => selectRecording(el.dataset.rec)));
}

function selectRecording(rec) {
  selectedRec = rec;
  document.querySelectorAll('#rec-list .item').forEach(e => e.classList.toggle('active', e.dataset.rec === rec));
  renderRecDetail();
}

function renderRecDetail() {
  const rows = q('SELECT * FROM utterances WHERE recording_id=? ORDER BY wer ASC', [selectedRec]);
  if (!rows.length) return;
  const ref = rows[0].ref_norm || '';
  const meta = rows[0];
  const best = rows[0];
  selectedModelForDiff = selectedModelForDiff && rows.find(r => r.run_id === selectedModelForDiff) ? selectedModelForDiff : best.run_id;

  const cmpRows = rows.map(r => {
    const info = runById[r.run_id] || {};
    const isBest = r.run_id === best.run_id;
    return `<tr data-run="${esc(r.run_id)}" class="${r.run_id === selectedModelForDiff ? 'active' : ''}">
      <td>${esc(info.name || r.run_id)}${isBest ? ' <span class="best">best</span>' : ''}</td>
      <td class="num">${fmt(r.wer)}</td>
      <td class="num">${r.S}</td><td class="num">${r.D}</td><td class="num">${r.I}</td>
      <td class="num">${fmt(ccerOf(r))}</td>
      <td class="num">${r.perfect ? '✓' : ''}</td>
    </tr>`;
  }).join('');

  const model = runById[selectedModelForDiff] || {};
  const row = rows.find(r => r.run_id === selectedModelForDiff);
  const dp = diffPair(ref, row ? row.hyp_norm || '' : '');

  document.getElementById('rec-detail').innerHTML = `
    ${audioHtml(selectedRec)}
    <div class="diff-block">
      <p class="diff-label">Reference (${esc(meta.category_code)}, ${esc(meta.speaker_id)}, ${fmt(meta.duration_s, 1)} s)</p>
      <div class="tokens">${ref ? ref.split(/\s+/).map(t => `<span class="tok ok ${catClass(t)}">${esc(t)}</span>`).join(' ') : '<span class="muted">(empty)</span>'}</div>
    </div>
    <h3 style="margin:14px 0 6px">All models on this recording</h3>
    <div class="table-scroll" style="max-height:360px">
      <table class="grid compact"><thead><tr>
        <th>Model</th><th class="num">WER</th><th class="num">S</th><th class="num">D</th><th class="num">I</th><th class="num">CCER</th><th class="num">Perfect</th>
      </tr></thead><tbody>${cmpRows}</tbody></table>
    </div>
    <p class="sub" style="margin-top:10px">Showing the diff for <b>${esc(model.name || selectedModelForDiff)}</b> — click a row above to switch.</p>
    <div class="diff-block">
      <p class="diff-label">Reference — flagged errors (D = deleted, S = substituted)</p>
      <div class="tokens">${dp.refHtml}</div>
    </div>
    <div class="diff-block">
      <p class="diff-label">Model output — differences highlighted (S = substitution, I = insertion)</p>
      <div class="tokens">${dp.hypHtml}</div>
    </div>`;

  document.querySelectorAll('#rec-detail tr[data-run]').forEach(tr => tr.addEventListener('click', () => {
    selectedModelForDiff = tr.dataset.run; renderRecDetail();
  }));
}

/* ---------- by model ---------- */
function closeDD(except) {
  document.querySelectorAll('.dd.open').forEach(d => { if (d !== except) d.classList.remove('open'); });
}

function buildDD(id, options, value, onChange) {
  const root = document.getElementById(id);
  root.classList.add('dd');
  root.innerHTML = `<button type="button" class="dd-btn" aria-haspopup="listbox"><span class="dd-lbl"></span><span class="dd-caret">▾</span></button>
                    <div class="dd-menu" role="listbox"></div>`;
  const btn = root.querySelector('.dd-btn'), menu = root.querySelector('.dd-menu');
  const label = () => { const o = options.find(o => o.v === value); root.querySelector('.dd-lbl').textContent = o ? o.t : ''; };
  menu.innerHTML = options.map(o => `<button type="button" role="option" class="dd-opt ${o.v === value ? 'sel' : ''}" data-v="${esc(o.v)}">${esc(o.t)}</button>`).join('');
  label();
  btn.addEventListener('click', e => {
    e.stopPropagation();
    const willOpen = !root.classList.contains('open');
    closeDD(root);
    root.classList.toggle('open', willOpen);
  });
  menu.querySelectorAll('.dd-opt').forEach(b => b.addEventListener('click', e => {
    e.stopPropagation();
    value = b.dataset.v;
    menu.querySelectorAll('.dd-opt').forEach(x => x.classList.toggle('sel', x === b));
    label();
    root.classList.remove('open');
    onChange(value);
  }));
  return {
    set(v) { value = v; menu.querySelectorAll('.dd-opt').forEach(x => x.classList.toggle('sel', x.dataset.v === v)); label(); },
    get() { return value; },
  };
}

function initControls() {
  const sorted = [...runs].sort((a, b) => a.wer - b.wer);
  selectedRun = sorted[0].run_id;
  ddModel = buildDD('dd-model',
    sorted.map(r => ({ v: r.run_id, t: `${r.name} (WER ${fmt(r.wer)})` })), selectedRun,
    v => { selectedRun = v; renderModelTable(); });
  ddSort = buildDD('dd-sort', [
    { v: 'wer_desc', t: 'WER (worst first)' },
    { v: 'wer_asc', t: 'WER (best first)' },
    { v: 'rec', t: 'Recording id' },
  ], modelSort, v => { modelSort = v; renderModelTable(); });
}

let modelRowsCache = [];
function renderModelTable() {
  const ql = document.getElementById('model-search').value.trim().toLowerCase();
  const sort = modelSort;
  let rows = q('SELECT * FROM utterances WHERE run_id=?', [selectedRun]);
  if (ql) rows = rows.filter(r => r.recording_id.toLowerCase().includes(ql) || (r.ref_norm || '').includes(ql));
  if (sort === 'wer_asc') rows.sort((a, b) => a.wer - b.wer);
  else if (sort === 'rec') rows.sort((a, b) => a.recording_id.localeCompare(b.recording_id));
  else rows.sort((a, b) => b.wer - a.wer);
  modelRowsCache = rows;
  document.querySelector('#model-table tbody').innerHTML = rows.map(r => `
    <tr data-rec="${esc(r.recording_id)}">
      <td>${esc(r.recording_id)}</td>
      <td>${esc(r.category_code)}</td>
      <td>${esc(r.speaker_id)}</td>
      <td class="num">${fmt(r.wer)}</td>
      <td class="num">${r.S}</td><td class="num">${r.D}</td><td class="num">${r.I}</td>
      <td class="num">${fmt(ccerOf(r))}</td>
      <td class="num">${r.perfect ? '✓' : ''}</td>
    </tr>`).join('');
  document.querySelectorAll('#model-table tbody tr').forEach(tr => tr.addEventListener('click', () => showModelDiff(tr.dataset.rec)));
}

function showModelDiff(rec) {
  const row = modelRowsCache.find(r => r.recording_id === rec) || q('SELECT * FROM utterances WHERE run_id=? AND recording_id=?', [selectedRun, rec])[0];
  if (!row) return;
  const info = runById[selectedRun] || {};
  const dp = diffPair(row.ref_norm || '', row.hyp_norm || '');
  const kpi = (label, val) => `<div class="kpi"><b>${val}</b><span>${label}</span></div>`;
  document.getElementById('model-detail').innerHTML = `
    <div class="card" style="margin-top:18px">
      <h3 style="margin:0 0 4px">${esc(info.name || selectedRun)} · ${esc(rec)}</h3>
      ${audioHtml(rec)}
      <div class="kpis">
        ${kpi('WER', fmt(row.wer))}
        ${kpi('Substitutions', row.S)}
        ${kpi('Deletions', row.D)}
        ${kpi('Insertions', row.I)}
        ${kpi('Numbers err', row.num_n ? `${row.num_err}/${row.num_n}` : '–')}
        ${kpi('Negations err', row.neg_n ? `${row.neg_err}/${row.neg_n}` : '–')}
        ${kpi('Body-side err', row.side_n ? `${row.side_err}/${row.side_n}` : '–')}
        ${kpi('CCER', fmt(ccerOf(row)))}
      </div>
      <div class="diff-block">
        <p class="diff-label">Reference — flagged errors (D = deleted, S = substituted; numbers/negations/body side underlined)</p>
        <div class="tokens">${dp.refHtml}</div>
      </div>
      <div class="diff-block">
        <p class="diff-label">Model output — differences highlighted (S = substitution, I = insertion)</p>
        <div class="tokens">${dp.hypHtml}</div>
      </div>
      <button class="btn" id="compare-all">Compare this recording across all models →</button>
    </div>`;
  document.getElementById('compare-all').addEventListener('click', () => {
    switchTab('rec');
    selectedModelForDiff = selectedRun;
    document.getElementById('rec-search').value = '';
    renderRecList('');
    selectRecording(rec);
    document.querySelector('#rec-detail').scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
}

function showModel(runId) {
  selectedRun = runId;
  if (ddModel) ddModel.set(runId);
  switchTab('model');
  renderModelTable();
  document.getElementById('pane-model').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

/* ---------- diff ---------- */
function catClass(t) {
  if (/\d/.test(t)) return 'catnum';
  if (NEGATIONS.has(t)) return 'catneg';
  if (/^(praw|lew)/.test(t)) return 'catside';
  return '';
}

function align(refT, hypT) {
  const n = refT.length, m = hypT.length;
  const dp = Array.from({ length: n + 1 }, () => new Array(m + 1).fill(0));
  for (let i = 0; i <= n; i++) dp[i][0] = i;
  for (let j = 0; j <= m; j++) dp[0][j] = j;
  for (let i = 1; i <= n; i++) for (let j = 1; j <= m; j++) {
    const c = refT[i - 1] === hypT[j - 1] ? 0 : 1;
    dp[i][j] = Math.min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + c);
  }
  const refTags = new Array(n).fill('ok'), hypTags = new Array(m).fill('ok');
  let i = n, j = m;
  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && dp[i][j] === dp[i - 1][j - 1] + (refT[i - 1] === hypT[j - 1] ? 0 : 1)) {
      if (refT[i - 1] !== hypT[j - 1]) { refTags[i - 1] = 'S'; hypTags[j - 1] = 'S'; }
      i--; j--;
    } else if (i > 0 && dp[i][j] === dp[i - 1][j] + 1) { refTags[i - 1] = 'D'; i--; }
    else { hypTags[j - 1] = 'I'; j--; }
  }
  return { refTags, hypTags };
}

function diffPair(ref, hyp) {  const refT = ref ? ref.split(/\s+/) : [];
  const hypT = hyp ? hyp.split(/\s+/) : [];
  const { refTags, hypTags } = align(refT, hypT);
  const refHtml = refT.map((t, i) => `<span class="tok ${refTags[i]} ${catClass(t)}">${esc(t)}</span>`).join(' ') || '<span class="muted">(empty)</span>';
  const hypHtml = hypT.length
    ? hypT.map((t, i) => `<span class="tok ${hypTags[i]}">${esc(t)}</span>`).join(' ')
    : '<span class="muted">(empty hypothesis)</span>';
  return { refHtml, hypHtml };
}

init();
