/* ============================================================================
   The Reading Bridge — main.js (v1)

   PROGRESSIVE ENHANCEMENT ONLY. Every page ships a complete, pre-rendered seed
   inside <main id="main">; that seed is the single source of truth for page
   content and this file NEVER touches <main>. The shared header chrome and the
   full footer are also pre-rendered in the HTML seeds, so every page renders
   fully with JavaScript disabled; main.js only rebuilds the header chrome from
   content/site.json, refreshes the footer's copyright year, and wires the nav
   toggle.

   DO NOT reintroduce content rendering here. An earlier version re-rendered
   <main> from content/site.json and it produced duplicated sections, literal
   "undefined" text and "This page could not load its content" on 5 pages, and
   wiped the four policies/*.html pages (whose bodies exist ONLY in the HTML).
   The render* functions were deleted outright so they cannot be re-dispatched.

   Privacy-first: no analytics, no cookies, no third-party scripts or fonts.
   ============================================================================ */

'use strict';

/* The pages live at two depths (site root and policies/). main.js itself always
   sits at the site root, so resolve a prefix back to it and use that for every
   data/asset/nav reference instead of assuming the page is at the root.
   (Before this, policies/*.html fetched 'content/site.json' relative to
   /policies/, which 404s and threw.) */
function sitePrefix() {
  const s = document.currentScript || document.querySelector('script[src$="main.js"]');
  if (!s || !s.src) return '';
  let root;
  try { root = new URL('.', s.src).pathname; } catch (e) { root = '/'; }
  if (!root) root = '/';
  if (!root.endsWith('/')) root += '/';
  const doc = location.pathname.replace(/[^/]*$/, '') || '/';
  if (doc === root) return '';
  if (doc.startsWith(root)) {
    return doc.slice(root.length).split('/').filter(Boolean).map(() => '../').join('');
  }
  return '';
}
const ROOT = sitePrefix();

const SITE_JSON = ROOT + 'content/site.json';
const LOGO = ROOT + 'assets/logo-lockup.png';

const navItems = [
  { label: 'Home', href: 'index.html', activeClass: (p) => p === 'index.html' },
  { label: 'Services', href: 'services.html', activeClass: (p) => p === 'services.html' },
  { label: 'Owner', href: 'owner.html', activeClass: (p) => p === 'owner.html' },
  { label: 'Assessment', href: 'assessment.html', activeClass: (p) => p === 'assessment.html' },
  { label: 'Pricing', href: 'pricing.html', activeClass: (p) => p === 'pricing.html' },
  { label: 'FAQ', href: 'faq.html', activeClass: (p) => p === 'faq.html' },
  { label: 'Area', href: 'area.html', activeClass: (p) => p === 'area.html' },
  { label: 'Book', href: 'book.html', activeClass: (p) => p === 'book.html' },
  { label: 'Contact', href: 'contact.html', activeClass: (p) => p === 'contact.html' }
];

/* ---------- tiny helpers ---------- */
function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'class') node.className = v;
    else if (k === 'html') node.innerHTML = v;
    else if (k === 'text') node.textContent = v;
    else if (k.startsWith('data-')) node.setAttribute(k, v);
    else node.setAttribute(k, v);
  }
  for (const c of [].concat(children)) {
    if (c == null) continue;
    node.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
  }
  return node;
}

/* ---------- Header ---------- */
function buildHeader(current) {
  const header = el('header', { class: 'site' });
  const row = el('div', { class: 'nav-row wrap' });

  const brandLink = el('a', { class: 'brand', href: ROOT + 'index.html', 'aria-label': 'The Reading Bridge home' });
  brandLink.appendChild(el('img', { src: LOGO, alt: 'The Reading Bridge logo', width: 52, height: 52 }));
  const brandText = el('div', { class: 'brand-text' });
  brandText.appendChild(el('span', { class: 'brand-name', text: SITE.name }));
  brandText.appendChild(el('span', { class: 'brand-desc', text: SITE.descriptor }));
  brandLink.appendChild(brandText);
  row.appendChild(brandLink);

  const toggle = el('button', { class: 'nav-toggle', 'aria-label': 'Toggle navigation', 'aria-expanded': 'false' });
  // Match the static seed's label exactly (&#9776; Menu) so the replaced header
  // is visually identical to the pre-rendered one.
  toggle.textContent = '\u2630 Menu';

  const links = el('nav', { class: 'nav-links', id: 'nav-links', 'aria-label': 'Primary' });
  for (const item of navItems) {
    const isActive = item.activeClass(current);
    const a = el('a', { href: ROOT + item.href, text: item.label });
    if (isActive) a.classList.add('active');
    links.appendChild(a);
  }
  // small booking CTA
  const book = el('a', { class: 'btn btn-primary', href: ROOT + 'book.html', text: 'Book a Free Session' });
  links.appendChild(book);

  toggle.addEventListener('click', () => {
    const open = links.classList.toggle('open');
    toggle.setAttribute('aria-expanded', String(open));
  });

  row.appendChild(toggle);
  row.appendChild(links);
  header.appendChild(row);
  return header;
}

/* ---------- Footer ----------
   There is deliberately NO runtime footer builder. Every page ships the full
   footer pre-rendered inside <footer id="footer">, so it is present with
   JavaScript disabled AND when content/site.json fails to load. A second
   (JS-built) footer would be a second source of truth for the same markup —
   exactly the class of mismatch that caused the original outage — and the
   date-bearing <ul> it used to build also carried an inline style the CSP
   drops in production. The seed is now the ONLY source; the one dynamic value,
   the copyright year, is refreshed in place by refreshCopyrightYear(). */

/* Refresh the © year without touching the pre-rendered footer structure. Safe
   to run even if site.json never loads. */
function refreshCopyrightYear() {
  const year = document.getElementById('copyright-year');
  if (year) year.textContent = String(new Date().getFullYear());
}

/* ============================================================================
   Boot
   ============================================================================ */
const SITE = {}; // populated below

async function init() {
  // The footer is pre-rendered in the HTML; only its year is dynamic, and that
  // must still update even if the fetch below fails.
  refreshCopyrightYear();
  try {
    const res = await fetch(SITE_JSON, { cache: 'no-store' });
    if (!res.ok) throw new Error('site.json ' + res.status);
    const data = await res.json();
    Object.assign(SITE, data);

    // --- Flat-key aliases (FAULT: content model mismatch) -------------------
    // main.js reads SITE.name / SITE.phone / SITE.email / SITE.area_served /
    // SITE.key_stages_served, but content/site.json nests those under
    // `business`. Without these aliases the footer rendered "undefined" and
    // init() threw on SITE.phone.replace(...) while building the contact block.
    const biz = data.business || {};
    SITE.name = biz.name || '';
    SITE.descriptor = biz.descriptor || '';
    SITE.phone = biz.phone || '';
    SITE.email = biz.email || '';
    SITE.area_served = biz.area_served || '';
    SITE.key_stages_served = biz.key_stages_served || '';

    const current = location.pathname.split('/').pop() || 'index.html';

    const header = buildHeader(current);
    const staticHeader = document.querySelector('header.site');
    if (staticHeader) staticHeader.replaceWith(header);
    else document.body.insertAdjacentElement('afterbegin', header);

    // --- <main> is deliberately NOT re-rendered ----------------------------
    // Every page ships a complete, pre-rendered seed inside <main id="main">
    // (and it is richer than site.json: the four policy bodies exist ONLY in
    // the HTML). Replacing <main> either duplicates content or, on the four
    // policies/*.html pages, wipes the page to nothing. The seed is the source
    // of truth. There is intentionally no renderer helper left in this file;
    // the ones that used to live here were deleted so they cannot be
    // re-dispatched and bring the outage back.

    // --- Footer: NOT re-rendered -------------------------------------------
    // Every page ships the complete footer pre-rendered in its HTML seed, so
    // it is present with JavaScript disabled and survives a failed site.json
    // fetch. main.js must never build a second footer (two sources of truth)
    // nor append into it; the copyright year was already refreshed above.
  } catch (err) {
    console.error('The Reading Bridge: init failed', err);
    // Never overwrite the pre-rendered seed on failure — doing so replaced
    // whole pages (contact.html, the policy pages) with an error notice.
  }
}

document.addEventListener('DOMContentLoaded', init);
