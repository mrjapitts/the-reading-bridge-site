# Nichola — Wildlife Safari Operator Site

A static website for **Nichola**, a wildlife safari operator based in
**Tarangire National Park, Tanzania**. It is published to
**Netlify** as a static site (the HTML is generated at build time from the
content files — see `build/README.md`; no server runtime), with
**Netlify CMS** for lightweight content editing and a hard security baseline
enforced through HTTP headers.

## Status

All core deliverables are in place and verified (see verification notes
below). This site is ready for review.

## Technology

- **Static HTML/CSS/JS** — no build toolchain.
- **Netlify** — hosting, plus Netlify Identity (email access login) and the
  CMS for editing content collections.
- **Netlify CMS** (`admin/index.html` + `admin/config.yml`) — content edited
  through the GitHub-backed editor. Content lives in `content/site.json`.

## Content model

All copy and structured data are sourced from a single file:

- `content/site.json` — the canonical content source (sections, pages,
  contact details, pricing). Every page is generated from it.

## Pages

| Route | Page | Content |
| --- | --- | --- |
| `/` | Home | Hero, intro, key selling points, call-to-action. |
| `/area` | The Area | Geography, wildlife, best time to visit. |
| `/services` | Services | Accommodation, guided safaris, logistics, custom trips. |
| `/assessment` | Impact & Assessment | Community, conservation, sustainability. |
| `/pricing` | Pricing | Day/rate structure. |
| `/book` | Book a Safari | Booking options and process. |
| `/faq` | FAQs | Common questions. |
| `/owner` | About the Owner | Founder narrative. |
| `/contact` | Contact | Contact details and channels. |
| `/policies/privacy` | Privacy Policy | Data handling. |
| `/policies/payment` | Payment & Cancellation | Terms, refunds. |
| `/policies/safeguarding` | Safeguarding Policy | Duty of care. |
| `/policies/cancellations` | Cancellation Policy | Cancellation tiers. |
| `/admin` | Admin (Netlify CMS) | Content editing portal (logged in). |

## Supporting files

- `netlify.toml` — build config and production redirects.
- `sitemap.xml` — lists all public pages for crawlers.
- `robots.txt` — allows all user-agent crawlers.
- `_headers` — production HTTP security headers (see hardening below).
- `assets/` — static assets.
- `styles.css`, `main.js` — global styles and client-side behaviour.

## Security hardening

`_headers` sets a strict production baseline:

- **CSP** — `default-src 'self'` with narrow `img-src`, `font-src`,
  `style-src`, `script-src`, `connect-src`, `object-src 'none'`,
  `base-uri 'self'`, and `form-action 'self' mailto:`.
- **Clickjacking** — `X-Frame-Options: DENY`.
- **MIME sniffing** — `X-Content-Type-Options: nosniff`.
- **Referrer** — `strict-origin-when-cross-origin`.
- **Sensor policy** — geolocation, microphone, camera, and interest-cohort
  disabled.

> **The content editor at `/admin/`:** Decap CMS is vendored under
> `admin/vendor/` (no CDN) and gets its own path-scoped CSP in `_headers`
> (`/admin/*`). The public pages keep the strict policy above, including
> `frame-src 'none'`; only `/admin/*` relaxes it. See `_headers` for the
> per-directive reasoning.
>
> **Note:** the rest of this README predates the current content model and is
> partly stale — for example the page table and the technology summary describe
> an earlier project. The authoritative description of how the site is built is
> in `build/README.md`.

## Deploy

Publish the site root (`/` here) to Netlify as a static site. `netlify.toml`
and `_headers` are picked up automatically; the redirects and security
headers apply in production.
