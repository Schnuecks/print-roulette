'use strict';

const card = document.getElementById('card');
const buttons = document.getElementById('buttons');
const root = document.documentElement;
const COLOR_RE = /^#[0-9a-f]{6}$/i;

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

function setAccent(color) {
  root.style.setProperty('--accent', safeColor(color));
}

function setBusy(busy, btn) {
  document.querySelectorAll('button').forEach(b => { b.disabled = busy || b.dataset.off === '1'; });
  if (btn) btn.classList.toggle('busy', busy);
}

async function draw(src, btn) {
  setBusy(true, btn);
  setAccent(src.color);
  card.classList.remove('hit');
  card.replaceChildren(el('small', 'Würfle auf ' + src.name + '…'));
  try {
    const r = await fetch('/api/random?source=' + encodeURIComponent(src.key));
    const m = await r.json();
    if (!r.ok) throw new Error(m.error || r.statusText);
    const url = safeUrl(m.url);
    if (!url) throw new Error('Ungültiger Link');
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
    const meta = m.creator ? 'von ' + m.creator + ' · öffnet auf ' + m.sourceName : 'öffnet auf ' + m.sourceName;
    parts.push(el('small', meta));
    card.replaceChildren(...parts);
    card.classList.add('hit');
  } catch (e) {
    card.replaceChildren(el('small', 'Fehler: ' + e.message, { class: 'error' }));
  } finally {
    setBusy(false, btn);
  }
}

fetch('/api/sources').then(r => r.json()).then(list => {
  for (const src of list) {
    const b = el('button', src.name);
    b.style.setProperty('--btn', safeColor(src.color));
    if (!src.enabled) {
      b.disabled = true;
      b.dataset.off = '1';
      b.title = src.reason || 'Nicht verfügbar';
    }
    b.addEventListener('click', () => draw(src, b));
    buttons.appendChild(b);
  }
}).catch(e => {
  card.replaceChildren(el('small', 'Fehler: ' + e.message, { class: 'error' }));
});
