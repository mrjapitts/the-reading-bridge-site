/* ============================================================================
   The Reading Bridge — admin bootstrap, part 2 of 2

   Fetch config.yml, parse it with the vendored js-yaml, and start the editor.
   Runs after vendor/decap-cms.js and vendor/js-yaml.min.js.

   External file for the same reason as admin-init.js: the /admin/*
   Content-Security-Policy is script-src 'self' with no 'unsafe-inline'.
   ============================================================================ */

window.addEventListener('load', async () => {
  const response = await fetch('config.yml');
  const text = await response.text();
  const config = window.yaml.load(text);
  window.CMS.init({ config });
});
