/* ============================================================================
   The Reading Bridge — admin bootstrap, part 1 of 2

   Runs BEFORE vendor/decap-cms.js and tells Decap not to start itself, so that
   admin-boot.js can hand it the config read from config.yml.

   This is an external file on purpose. The /admin/* Content-Security-Policy is
   script-src 'self' with no 'unsafe-inline', so an inline <script> here would
   simply not run in production. Keep every admin script external.
   ============================================================================ */

window.CMS_MANUAL_INIT = true;
