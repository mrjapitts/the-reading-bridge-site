# Repository gates and QA promotion handoff

Run every command below from the repository root. The tools use only the Python
standard library and local Git/filesystem state. They do not install packages,
open ports, call live services, invoke Netlify/deployment tooling, contact the
production domain or Koalendar, or call GitHub APIs. Deployment-related
environment variables are removed from all gate subprocesses.

## Repository gate

```sh
python scripts/repo_gate.py
```

The gate fails unless the current branch is in its designated worktree, the
pre-state is clean, and the target is neither `main` nor the protected checkout
at `E:/2_nichola/site`. It then:

1. compiles every tracked Python file in memory (no bytecode/cache writes),
2. parses both content JSON files and `netlify.toml`,
3. checks the 13 generated pages are tracked and validates local links,
   fragments, and duplicate HTML IDs,
4. runs the documented `build/generate.py --check` acceptance test and requires
   all 13 pages to be byte-identical, and
5. proves the worktree remains clean after the gate.

Run unit tests separately:

```sh
python -m unittest discover -s tests -v
```

There is no package manifest, npm project, type-checker configuration, server
runtime, database migration system, or application API in this static-site
repository; those gates are intentionally not invented.

## Admin CMS gate (blank-/admin/ regression)

```sh
python scripts/browser_smoke.py
```

`/admin/` once served a blank page: `admin/index.html` set
`window.CMS_MANUAL_INIT` (so the vendored Decap bundle logged "skipping
automatic initialization" and never started) and then called
`window.yaml.load`, while the vendored js-yaml exports `window.jsyaml`.
`admin/config.yml` also gave a collection an invalid singular top-level
`file:` key. The fix is Decap's standard automatic initialization: one script
element, no manual bootstrap, `files:`-shaped collections.

This gate drives a real local Chrome over the repository's own vendored bundle
(it is also part of `python -m unittest discover -s tests`). An ephemeral
loopback server serves the repository; nothing is installed, no third-party
host is contacted and no deploy tooling is invoked. It fails unless:

1. the admin page loads only `vendor/decap-cms.js` and never sets
   `window.CMS_MANUAL_INIT`;
2. the vendored bundle starts, fetches `admin/config.yml` itself and renders a
   non-empty UI (no config-error screen, no uncaught JS exception, no
   config/collection console complaint);
3. the shipped config parses, through the repository's vendored js-yaml, into
   two collections with unique names and labels, each declaring exactly one of
   `files:` or `folder:`, targeting `content/site.json` and
   `content/policies.json`;
4. `identity-redirect.js` still routes `#invite_token`, `#confirmation_token`,
   `#recovery_token` and `#email_change_token` hashes to `/admin/` with the
   token key and value intact, while ordinary visits and hashes are untouched.

Evidence (report plus a screenshot of the rendered admin page) is written to
`--out` (a temporary directory by default). Residual gap: Netlify Identity's
actual consumption of an invite/recovery token needs the live Netlify service,
so only the routing and preservation of the token are exercised here.

## Exact-integration-SHA QA approval

Approval is a JSON operational artifact outside tracked history. It is a
**policy attestation, not a digital signature**: the checker enforces the
recorded issuer name and exact SHA but cannot cryptographically establish who
ran the creation command.

Schema `nichola.qa-approval/v1` requires:

```json
{
  "schema": "nichola.qa-approval/v1",
  "integration_sha": "40 lowercase hexadecimal characters",
  "issuer_profile": "minerva_qa",
  "decision": "approved",
  "evidence": ["one or more concrete test results or evidence references"],
  "issued_at_utc": "RFC 3339 UTC timestamp",
  "identity_assurance": "policy-attestation-only"
}
```

Only Minerva's mapped worktree/branch can create an artifact, and its `HEAD`
must equal the SHA being approved. Use an external handoff directory (preferred)
or `.nichola-state/`, which is ignored:

```sh
# Run by Minerva from E:/2_nichola-worktrees/minerva_qa after validating SHA.
python scripts/qa_approval.py create \
  --sha <INTEGRATION_SHA> \
  --output E:/2_nichola-handoff/qa-approvals/<INTEGRATION_SHA>.json \
  --evidence "python scripts/repo_gate.py: PASS" \
  --evidence "python -m unittest discover -s tests -v: PASS"
```

Atlas must copy/read that explicit handoff artifact, check out the unchanged
integration SHA, and run:

```sh
python scripts/repo_gate.py \
  --promotion-approval E:/2_nichola-handoff/qa-approvals/<INTEGRATION_SHA>.json
```

A missing file, malformed record, non-Minerva issuer, non-approved decision, or
SHA mismatch fails. Any new integration commit changes `HEAD`, so the old
approval fails and Minerva must validate and approve the new exact SHA. The
artifact authorizes no push, deployment, production change, or edit to another
Hermes profile's state.
