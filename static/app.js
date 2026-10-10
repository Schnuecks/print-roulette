'use strict';

const $ = id => document.getElementById(id);
const card = $('card');
const wheel = $('wheel');
const spinBtn = $('spin');
const buttons = $('buttons');
const fFree = $('f-free');
const fSafe = $('f-safe');
const historyBox = $('history-box');
const historyList = $('history');
const root = document.documentElement;

const SVG = 'http://www.w3.org/2000/svg';
const COLOR_RE = /^#[0-9a-f]{6}$/i;
const HISTORY_KEY = 'pr-history';
const FILTER_KEY = 'pr-filters';
const HISTORY_MAX = 12;
const SPIN_MS = 3200;
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

let sources = [];   // alle Quellen vom Server
let segments = [];  // nur aktive Quellen, in Rad-Reihenfolge
let rotation = 0;   // aktuelle Drehung des Rads in Grad
let busy = false;
let lastMode = null; // 'wheel' oder Schlüssel einer Quelle

/* ---------- Hilfen ---------- */

function el(tag, text, attrs) {
  const n = document.createElement(tag);
  if (text != null) n.textContent = text;
  for (const k in attrs || {}) n.setAttribute(k, attrs[k]);
  return n;
}

function safeColor(c) {
  return COLOR_RE.test(c || '') ? c : '#71717a';
}

function safeUrl(u) {
  try {
    const p = new URL(u);
    return p.protocol === 'https:' ? p.href : null;
  } catch (e) {
    return null;
  }
}

function store(key, value) {
  try { localStorage.setItem(key, JSON.stringify(value)); } catch (e) { /* privat oder voll: egal */ }
}

function load(key, fallback) {
  try {
    const v = JSON.parse(localStorage.getItem(key));
    return v == null ? fallback : v;
  } catch (e) {
    return fallback;
  }
}

function setAccent(color) {
  root.style.setProperty('--accent', safeColor(color));
}

function setBusy(state) {
  busy = state;
  spinBtn.disabled = state;
  buttons.querySelectorAll('button').forEach(b => { b.disabled = state || b.dataset.off === '1'; });
}

/* ---------- Rad ---------- */

function polar(angle, r) {
  const rad = (angle - 90) * Math.PI / 180;
  return [150 + r * Math.cos(rad), 150 + r * Math.sin(rad)];
}

function buildWheel() {
  wheel.replaceChildren();
  const n = segments.length;
  if (!n) return;
  const step = 360 / n;
  segments.forEach((src, i) => {
    const a0 = i * step;
    const a1 = a0 + step;
    let shape;
    if (n === 1) {
      shape = document.createElementNS(SVG, 'circle');
      shape.setAttribute('cx', 150); shape.setAttribute('cy', 150); shape.setAttribute('r', 140);
    } else {
      const [x0, y0] = polar(a0, 140);
      const [x1, y1] = polar(a1, 140);
      shape = document.createElementNS(SVG, 'path');
      shape.setAttribute('d', `M150 150 L${x0} ${y0} A140 140 0 ${step > 180 ? 1 : 0} 1 ${x1} ${y1} Z`);
    }
    shape.setAttribute('fill', safeColor(src.color));
    shape.addEventListener('click', () => roll(src.key));
    const title = document.createElementNS(SVG, 'title');
    title.textContent = src.name;
    shape.appendChild(title);
    wheel.appendChild(shape);

    const mid = a0 + step / 2;
    const [tx, ty] = polar(mid, 95);
    const label = document.createElementNS(SVG, 'text');
    label.setAttribute('x', tx);
    label.setAttribute('y', ty);
    label.setAttribute('text-anchor', 'middle');
    label.setAttribute('dominant-baseline', 'middle');
    // Oberkante zeigt nach außen: das Segment unter dem Zeiger steht nach dem Drehen aufrecht
    label.setAttribute('transform', `rotate(${mid} ${tx} ${ty})`);
    label.textContent = src.name;
    wheel.appendChild(label);
  });
}

// Dreht das Rad so, dass das Segment der Quelle unter dem Zeiger oben landet.
function spinTo(key) {
  const i = segments.findIndex(s => s.key === key);
  if (i < 0) return Promise.resolve();
  const step = 360 / segments.length;
  const jitter = (Math.random() - 0.5) * step * 0.6;
  const target = (360 - (i * step + step / 2 + jitter)) % 360;
  const current = ((rotation % 360) + 360) % 360;
  const delta = ((target - current) + 360) % 360;
  rotation += (reducedMotion.matches ? 0 : 360 * 4) + delta;
  wheel.style.transform = `rotate(${rotation}deg)`;
  if (reducedMotion.matches) return Promise.resolve();
  return new Promise(res => setTimeout(res, SPIN_MS));
}

/* ---------- Würfeln ---------- */

async function fetchModel(src) {
  const q = new URLSearchParams({ source: src.key });
  if (fFree.checked) q.set('free', '1');
  if (!fSafe.checked) q.set('nsfw', '1');
  const r = await fetch('/api/random?' + q.toString());
  const m = await r.json();
  if (!r.ok) throw new Error(m.error || r.statusText);
  return m;
}

async function roll(mode) {
  if (busy || !segments.length) return;
  const src = mode === 'wheel'
    ? segments[Math.floor(Math.random() * segments.length)]
    : segments.find(s => s.key === mode);
  if (!src) return;
  lastMode = mode;
  setBusy(true);
  setAccent(src.color);
  card.classList.remove('hit');
  card.replaceChildren(el('small', mode === 'wheel' ? 'Das Rad dreht sich…' : 'Würfle auf ' + src.name + '…'));
  try {
    const [m] = await Promise.all([fetchModel(src), spinTo(src.key)]);
    show(m, src);
    remember(m);
  } catch (e) {
    card.replaceChildren(el('small', e.message, { class: 'error' }));
  } finally {
    setBusy(false);
  }
}

function filterNote(src) {
  const missing = [];
  if (fFree.checked && !src.filters.free) missing.push('Preis');
  if (fSafe.checked && !src.filters.nsfw) missing.push('NSFW');
  return missing.length ? src.name + ' liefert keine Angaben zu ' + missing.join(' und ') + ', der Filter greift hier nicht.' : null;
}

function show(m, src) {
  const url = safeUrl(m.url);
  if (!url) {
    card.replaceChildren(el('small', 'Ungültiger Link', { class: 'error' }));
    return;
  }
  setAccent(m.color);
  const parts = [el('span', m.sourceName, { class: 'badge' })];
  const image = safeUrl(m.image);
  if (image) {
    const img = el('img', null, { src: image, alt: m.title, referrerpolicy: 'no-referrer' });
    let tries = 0;
    img.onerror = () => {
      // Cults und Thingiverse erzeugen Vorschaubilder erst beim ersten Abruf
      if (++tries > 3) { img.remove(); return; }
      setTimeout(() => { img.src = image + '#' + tries; }, 3000 * tries);
    };
    parts.push(img);
  }
  parts.push(el('a', m.title, { class: 'title', href: url, target: '_blank', rel: 'noopener noreferrer' }));
  parts.push(el('small', m.creator ? 'von ' + m.creator + ' · öffnet auf ' + m.sourceName : 'öffnet auf ' + m.sourceName));
  const note = src ? filterNote(src) : null;
  if (note) parts.push(el('span', note, { class: 'note' }));
  card.replaceChildren(...parts);
  card.classList.add('hit');
}

/* ---------- Verlauf ---------- */

function cleanEntry(m) {
  const url = safeUrl(m && m.url);
  if (!url) return null;
  return {
    url,
    title: String(m.title || '').slice(0, 200),
    creator: m.creator ? String(m.creator).slice(0, 80) : null,
    image: safeUrl(m.image),
    sourceName: String(m.sourceName || '').slice(0, 40),
    color: safeColor(m.color),
  };
}

function getHistory() {
  const list = load(HISTORY_KEY, []);
  return Array.isArray(list) ? list.map(cleanEntry).filter(Boolean).slice(0, HISTORY_MAX) : [];
}

function remember(m) {
  const entry = cleanEntry(m);
  if (!entry) return;
  const list = getHistory().filter(h => h.url !== entry.url);
  list.unshift(entry);
  store(HISTORY_KEY, list.slice(0, HISTORY_MAX));
  renderHistory();
}

function renderHistory() {
  const list = getHistory();
  historyBox.hidden = list.length === 0;
  historyList.replaceChildren(...list.map(h => {
    const b = el('button', null, { type: 'button', class: 'tile', title: h.title + ' (' + h.sourceName + ')' });
    b.style.setProperty('--c', h.color);
    if (h.image) {
      const img = el('img', null, { class: 'thumb', src: h.image, alt: '', loading: 'lazy', referrerpolicy: 'no-referrer' });
      img.onerror = () => img.replaceWith(el('div', (h.sourceName || '?').charAt(0), { class: 'thumb' }));
      b.appendChild(img);
    } else {
      b.appendChild(el('div', (h.sourceName || '?').charAt(0), { class: 'thumb' }));
    }
    b.appendChild(el('span', h.title));
    b.addEventListener('click', () => show(h, null));
    return b;
  }));
}

$('history-clear').addEventListener('click', () => {
  store(HISTORY_KEY, []);
  renderHistory();
});

/* ---------- Filter und Tastatur ---------- */

const savedFilters = load(FILTER_KEY, {});
if (typeof savedFilters.free === 'boolean') fFree.checked = savedFilters.free;
if (typeof savedFilters.safe === 'boolean') fSafe.checked = savedFilters.safe;
[fFree, fSafe].forEach(f => f.addEventListener('change', () => store(FILTER_KEY, { free: fFree.checked, safe: fSafe.checked })));

spinBtn.addEventListener('click', () => roll('wheel'));

document.addEventListener('keydown', e => {
  if (e.code !== 'Space' || e.repeat) return;
  const t = e.target;
  if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return;
  e.preventDefault();
  roll(lastMode || 'wheel');
});

/* ---------- Start ---------- */

fetch('/api/sources').then(r => r.json()).then(list => {
  sources = list.map(s => ({ ...s, color: safeColor(s.color), filters: s.filters || { free: false, nsfw: false } }));
  segments = sources.filter(s => s.enabled);
  buildWheel();
  for (const src of sources) {
    const b = el('button', src.name, { type: 'button' });
    b.style.setProperty('--btn', src.color);
    if (!src.enabled) {
      b.disabled = true;
      b.dataset.off = '1';
      b.title = src.reason || 'Nicht verfügbar';
    }
    b.addEventListener('click', () => roll(src.key));
    buttons.appendChild(b);
  }
  if (!segments.length) {
    spinBtn.disabled = true;
    card.replaceChildren(el('small', 'Keine Plattform verfügbar', { class: 'error' }));
  }
}).catch(e => {
  card.replaceChildren(el('small', 'Fehler: ' + e.message, { class: 'error' }));
});

renderHistory();
