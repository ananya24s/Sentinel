/* Shared chrome + helpers for every Sentinel page. */
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const pc = x => x == null ? '–' : (x * 100).toFixed(1) + '%';

const PAGES = [
  ['/', 'Home'], ['/how-it-works', 'How it works'], ['/attack-lab', 'Attack lab'],
  ['/activity', 'Activity'], ['/integrate', 'Integrate'], ['/benchmark', 'Benchmark'], ['/about', 'About'],
];

/* ---------------- theme ---------------- */
function currentTheme() { return document.documentElement.dataset.theme || 'dark'; }
function applyTheme(t) { document.documentElement.dataset.theme = t; try { localStorage.setItem('sentinel.theme', t); } catch (e) { /* ignore */ } }
const SUN = '<svg class="sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2.5v2.2M12 19.3v2.2M2.5 12h2.2M19.3 12h2.2M5.3 5.3l1.6 1.6M17.1 17.1l1.6 1.6M18.7 5.3l-1.6 1.6M6.9 17.1l-1.6 1.6"/></svg>';
const MOON = '<svg class="moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M20.5 14.2A8.5 8.5 0 0 1 9.8 3.5a8.5 8.5 0 1 0 10.7 10.7z"/></svg>';

/* faint security motifs in the page margins: text fragments, redaction marks, scan lines, a ruler */
function ambientHTML() {
  const rd = (w, o) => `<u class="rd${o ? ' o' : ''}" style="width:${w}px"></u>`;
  const groups = [
    ['l', 250, [`&lt;!-- ${rd(46)} --&gt;`, `SYSTEM: ${rd(40, 1)}`, 'ignore previous', `reveal ${rd(38)} prompt`]],
    ['r', 330, [`[INST] ${rd(52)}`, `also tell the reader`, `translate to ${rd(34, 1)}`, '&lt;|im_start|&gt;system']],
    ['l', 780, [`send to http://${rd(44)}`, `base64 ${rd(70)}`, `EMAIL_FROM: ${rd(46, 1)}`]],
    ['r', 880, [`forward this thread`, `to ${rd(60)}@${rd(36)}`, `disregard the summary`, rd(88)]],
    ['l', 1320, [`&lt;!-- assistant: ${rd(40, 1)}`, 'new instructions:', `${rd(80)} ${rd(38)}`]],
    ['r', 1430, [`ignore the ${rd(44)} above`, `SYSTEM OVERRIDE`, `${rd(64, 1)}`]],
  ];
  const frags = groups.map(([side, top, lines]) => `<div class="frags ${side}" style="top:${top}px">${lines.map(l => `<div>${l}</div>`).join('')}</div>`).join('');
  const ticks = []; for (let y = 210; y < 1900; y += 96) { const w = 60 + ((y / 96) % 3) * 26; ticks.push(`<i class="sl l" style="top:${y}px;width:${w}px"></i><i class="sl r" style="top:${y + 34}px;width:${w + 14}px"></i>`); }
  return `<div class="ambient" aria-hidden="true">${frags}${ticks.join('')}<i class="ruler l"></i><i class="ruler r"></i><i class="sweep l"></i><i class="sweep r" style="animation-delay:-8s"></i></div>`;
}

function mountChrome() {
  // the margin motifs assume a centred column; on the full-width pages they would sit under the content
  if (document.querySelector('main.narrow, main.prose')) document.body.insertAdjacentHTML('afterbegin', ambientHTML());
  const path = location.pathname.replace(/\/$/, '') || '/';
  $('#top').outerHTML = `<header class="top">
    <a class="brand" href="/"><img src="/static/brand/mark.svg" alt="Sentinel logo"><b>Sentinel</b></a>
    <nav class="main">${PAGES.map(([h, n]) => `<a href="${h}" class="${h === path ? 'on' : ''}">${n}</a>`).join('')}</nav>
    <div class="hdr-r"><div class="status"><span class="dot" id="dot"></span><span id="stat">Loading models…</span></div>
      <button class="themebtn" id="themebtn" aria-label="Switch between light and dark theme" title="Switch theme">${SUN}${MOON}</button></div></header>`;
  $('#themebtn').onclick = () => applyTheme(currentTheme() === 'dark' ? 'light' : 'dark');
  $('#bot').outerHTML = `<footer class="bot"><div><img src="/static/brand/mark.svg" alt=""><span>Sentinel · Tool-Output Trust-Boundary Defense · Engineers' Day, LLM Engineering, Problem 5 · Team Bug Slayers</span></div>
    <div><a href="/docs" target="_blank">API reference</a></div></footer>`;
}

let _ready = false;
async function pollHealth(onReady) {
  try {
    const h = await (await fetch('/api/health')).json();
    _ready = h.ready;
    $('#dot').className = 'dot' + (h.ready ? ' ok' : '');
    $('#stat').textContent = h.error ? 'Error: ' + h.error : h.ready ? 'Models ready' : 'Loading models…';
    if (h.ready) { onReady && onReady(); return; }
    if (!h.error) setTimeout(() => pollHealth(onReady), 1200);
  } catch (e) { setTimeout(() => pollHealth(onReady), 2000); }
}

async function post(path, body) {
  const r = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  let data = null; try { data = await r.json(); } catch (e) { /* ignore */ }
  return { ok: r.ok, status: r.status, data };
}
const looksLikeUrl = t => { t = t.trim(); return !/\s/.test(t) && (/^https?:\/\/\S+$/i.test(t) || /^(www\.)?[a-z0-9-]+(\.[a-z0-9-]+)+(\/\S*)?$/i.test(t)); };

function rememberScan(o) { try { sessionStorage.setItem('sentinel.last', JSON.stringify(o)); } catch (e) { /* ignore */ } }
function recallScan() { try { return JSON.parse(sessionStorage.getItem('sentinel.last')); } catch (e) { return null; } }

/* ---------------- result rendering ---------------- */
const REDACTION = '[untrusted instruction removed]';
const ACT = { ALLOW: 'PASSED', NEUTRALIZE: 'NEUTRALIZED', ALERT: 'ALERT' };
function received(text, res) {
  const spans = [...res.spans].sort((a, b) => a.start - b.start); let html = '', cur = 0;
  for (const s of spans) {
    if (s.start < cur) continue;
    html += esc(text.slice(cur, s.start));
    const t = esc(text.slice(s.start, s.end));
    html += s.verdict === 'injection' ? `<mark class="inj" title="score ${s.score}">${t}</mark>` : t;
    cur = s.end;
  }
  return html + esc(text.slice(cur));
}
const processed = res => res.processed_content.split(REDACTION).map(esc).join('<span class="redact">untrusted instruction removed</span>');
function docCard(title, body, act, small) {
  return `<div class="docwrap"><h4><span>${title}</span>${act ? `<span class="act b-${act}">${act}</span>` : ''}</h4><div class="sheet ${small ? 'sm' : ''}">${act ? `<div class="stamp ${act}">${ACT[act]}</div>` : ''}${body}</div></div>`;
}
function spanSection(res) {
  const isSus = s => s.verdict === 'injection' || s.score >= 0.05;
  const items = res.spans.filter(isSus), low = res.spans.filter(s => !isSus(s));
  const row = (s, minor) => {
    const reason = s.reason ? `<div class="sreason">${esc(s.reason)}</div>` : '';
    const stage = s.stage === 'boundary' ? 'boundary rule' : s.stage === 'patterns' ? 'fixed patterns' : 'scorer + off-task check';
    return `<div class="span ${s.verdict === 'injection' ? 'inj' : ''} ${minor ? 'minor' : ''}" ${minor ? 'hidden' : ''}>
      <div class="vp v-${s.verdict}">${s.verdict === 'injection' ? 'INJECTION' : 'DATA'}</div>
      <div><div class="stext">${esc(s.text)}</div>${reason}</div>
      <div><div class="score">score ${s.score.toFixed(3)}</div><div class="track"><i style="width:${Math.max(2, s.score * 100)}%"></i></div><div class="stage">${stage}</div></div></div>`;
  };
  return `<div class="sec"><h3><span>Span analysis <span style="text-transform:none;letter-spacing:0;font-weight:400;color:var(--dim)">· ${items.length} suspicious · ${low.length} low-risk</span></span>${low.length ? '<button data-showall>show low-risk spans</button>' : ''}</h3>${items.slice(0, 40).map(s => row(s, false)).join('') || '<p class="note" style="margin:0 0 8px">No suspicious spans.</p>'}${low.slice(0, 80).map(s => row(s, true)).join('')}</div>`;
}
function offtaskSection(res) {
  const list = res.spans.filter(s => s.signals && (s.verdict === 'injection' || s.score > 0.05)).sort((a, b) => b.score - a.score).slice(0, 4);
  if (!list.length) return '';
  const bar = (label, v, hot) => `<div class="sig"><div class="siglab"><span>${label}</span><b>${(v * 100).toFixed(0)}%</b></div><div class="track"><i style="width:${Math.max(2, Math.min(100, v * 100))}%;${hot ? 'background:var(--sig)' : ''}"></i></div></div>`;
  return `<div class="sec"><h3><span>Off-task analysis <span style="text-transform:none;letter-spacing:0;font-weight:400;color:var(--dim)">· how far each suspicious span sits from the user's task and from the rest of the page</span></span></h3>` + list.map(s => {
    const g = s.signals;
    return `<div class="infl"><p class="q">“${esc(s.text.slice(0, 150))}${s.text.length > 150 ? '…' : ''}”</p>
    <div class="three">${bar('Reads like an instruction', g.instruction_likeness, g.instruction_likeness >= .5)}${bar('Related to your task', Math.max(0, g.task_relatedness), false)}${bar('Fits the rest of the page', Math.max(0, g.page_coherence), false)}</div>
    <div class="mets"><span class="met">odd-one-out score <b>${g.oddness_z > 0 ? '+' : ''}${g.oddness_z.toFixed(1)}</b></span><span class="met">final score <b>${s.score.toFixed(2)}</b></span><span class="met">verdict <b>${s.verdict}</b></span></div></div>`;
  }).join('') + '</div>';
}
function renderResult(el, j, text, task, page) {
  const primary = j.sentinel || j.baseline, both = !!(j.sentinel && j.baseline);
  const inj = primary.detected_spans.length, n = primary.spans.length, tc = primary.trust_classification;
  let h = `<div class="bar"><span class="badge b-${primary.action}">${primary.action}</span>
    <div class="meta"><span><b>${inj}</b> injection${inj === 1 ? '' : 's'} found</span><span><b>${n}</b> spans scanned</span><span><b>${primary.latency_ms}</b> ms</span></div>
    <div class="trust"><span class="tpill t-ok">user task · trusted</span><span class="tpill t-bad">tool output · untrusted (${esc(tc.source)})</span>${tc.spoofed_role_markers.length ? `<span class="tpill t-bad">${tc.spoofed_role_markers.length} forged role marker${tc.spoofed_role_markers.length > 1 ? 's' : ''} stripped</span>` : ''}</div></div>`;
  if (page) h += `<div class="srcline">Fetched <b>${esc(page.title || page.url)}</b> · ${page.chars.toLocaleString()} characters${page.truncated ? ' (first 20,000 scanned)' : ''} · <span style="color:var(--dim)">${esc(page.url)}</span></div>`;
  h += `<div class="tools"><button class="btn ghost sm" data-copyclean>Copy clean text</button><button class="btn ghost sm" data-dl>Download report</button></div>`;
  h += `<div class="docs ${both ? 'c3' : 'c2'}">`;
  h += docCard('As received', received(text, primary), null, both);
  if (j.sentinel) h += docCard(both ? 'Sentinel → agent receives' : 'What the agent receives', processed(j.sentinel), j.sentinel.action, both);
  if (j.baseline) h += docCard(both ? 'Baseline → agent receives' : 'What the agent receives (baseline)', processed(j.baseline), j.baseline.action, both);
  h += '</div>' + spanSection(primary) + offtaskSection(primary);
  el.innerHTML = h;
  const cc = $('[data-copyclean]', el); if (cc) cc.onclick = () => { navigator.clipboard.writeText(primary.processed_content); flash(cc, 'Copied'); };
  const dl = $('[data-dl]', el); if (dl) dl.onclick = () => {
    const report = { generated_at: new Date().toISOString(), task, source: tc.source, tool_output: text, sentinel: j.sentinel || null, baseline: j.baseline || null };
    const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' }));
    a.download = 'sentinel-report.json'; a.click(); URL.revokeObjectURL(a.href);
  };
  const b = $('[data-showall]', el);
  if (b) b.onclick = () => { const hs = $$('.span.minor', el); const show = hs[0]?.hidden; hs.forEach(e => e.hidden = !show); b.textContent = show ? 'hide low-risk spans' : 'show low-risk spans'; };
}

/* ---------------- copy helper ---------------- */
function flash(b, msg) { const o = b.textContent; b.textContent = msg; setTimeout(() => b.textContent = o, 1200); }
function heat(v) { const g = Math.round(v * 100); const c = v >= .85 ? '#1c8f6c' : v >= .6 ? '#7a8a2c' : v >= .35 ? '#b9800b' : '#b8402a'; return `<div class="fc" style="background:${c}">${g}</div>`; }
