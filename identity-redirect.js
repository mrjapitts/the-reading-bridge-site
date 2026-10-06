/*
 * Netlify Identity sends invitation, confirmation and recovery links to the
 * site's root by default. The Netlify Identity widget that consumes those
 * tokens lives inside Decap CMS at /admin/, not on the public pages.
 *
 * Redirect only Identity-token hashes. Ordinary visitors and ordinary hashes
 * are untouched. This file is self-hosted, so the public CSP remains strict.
 */
(() => {
  'use strict';

  const tokenHash = /^#(?:invite_token|confirmation_token|recovery_token|email_change_token)=/;
  if (tokenHash.test(window.location.hash) && !window.location.pathname.startsWith('/admin/')) {
    window.location.replace('/admin/' + window.location.hash);
  }
})();
