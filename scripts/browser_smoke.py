#!/usr/bin/env python3
"""Headless-Chrome smoke test for the vendored Decap CMS at /admin/.

This gate exists because /admin/ was once a blank page. Two faults caused it:

  1. ``admin/admin-init.js`` set ``window.CMS_MANUAL_INIT``, so the vendored
     bundle logged "skipping automatic initialization" and never started.
     ``admin/admin-boot.js`` then called ``window.yaml.load`` — js-yaml 4.1.0
     exports ``window.jsyaml``, so no parser existed under that name and the
     load handler threw. (Phase B below re-proves that global-name mismatch
     with the repository's own vendored parser.)
  2. ``admin/config.yml`` gave its first collection a singular top-level
     ``file:`` key, which Decap does not accept (it needs ``files:`` or
     ``folder:``), and the hand-rolled parse produced a duplicate collection.

So this script drives a real browser over the real vendored bundle and fails
unless the page self-initializes, renders a non-empty UI, loads config.yml
through Decap's own loader, and the shipped config parses into valid,
non-duplicated collections. It also checks invite/recovery hash routing.

Standard library only. No packages are installed, no third-party host is
contacted: an ephemeral ``127.0.0.1`` server serves the repository itself and
Chrome talks to it plus its own DevTools endpoint.

Usage::

    python scripts/browser_smoke.py
    python scripts/browser_smoke.py --out C:/tmp/browser-smoke --json

Exit code 0 = PASSED. Writes ``report.json`` and ``admin.png`` under --out.
"""

import argparse
import base64
import hashlib
import json
import os
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]

CHROME_CANDIDATES = (
    "chrome.exe",
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
    "/c/Program Files/Google/Chrome/Application/chrome.exe",
    "/c/Program Files (x86)/Google/Chrome/Application/chrome.exe",
    "C:/Program Files/Google/Chrome/Application/chrome.exe",
    "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
)

# Rendered by Decap when its own config load or validation fails. English is
# Decap's default locale.
CONFIG_ERROR_MARKERS = ("Config Errors", "Check your config.yml file.")
# Any console line mentioning this is a config/collection complaint, which the
# blank-/admin/ regression must never produce.
CONFIG_CONSOLE_MARKER = "collection"
# Logged by the vendored bundle when window.CMS_MANUAL_INIT is truthy.
MANUAL_INIT_MARKER = "skipping automatic initialization"
# Logged by the vendored bundle when it actually starts.
BUNDLE_STARTED_MARKER = "decap-cms-app"

EXPECTED_SCRIPT_SOURCES = ["vendor/decap-cms.js"]
EXPECTED_CONFIG_FILES = ["content/site.json", "content/policies.json"]
TOKEN_HASHES = {
    "invite": "/#invite_token=SMOKE-INVITE",
    "recovery_from_subpage": "/policies/privacy.html#recovery_token=SMOKE-RECOVERY",
    "confirmation_from_subpage": "/services.html#confirmation_token=SMOKE-CONFIRM",
    "recovery_on_admin": "/admin/#recovery_token=SMOKE-RECOVERY",
    "email_change_on_admin": "/admin/#email_change_token=SMOKE-EMAILCHANGE",
}


class SmokeFailure(AssertionError):
    pass


# --------------------------------------------------------------------------
# Local file server (Netlify-faithful content types, loopback only)
# --------------------------------------------------------------------------
class _Handler(SimpleHTTPRequestHandler):
    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".yml": "text/yaml",
        ".yaml": "text/yaml",
        ".js": "text/javascript",
        ".wasm": "application/wasm",
        ".woff2": "font/woff2",
    }

    def __init__(self, *args, directory=None, **kwargs):
        super().__init__(*args, directory=str(directory), **kwargs)

    def log_message(self, *args):  # keep the smoke output readable
        pass

    def log_error(self, *args):
        pass


def start_server(root):
    server = ThreadingHTTPServer(("127.0.0.1", 0), lambda *a, **k: _Handler(*a, directory=root, **k))
    server.daemon_threads = True
    # A browser that abandons a response (page navigation) is normal here; it
    # must not spray tracebacks over the evidence.
    server.handle_error = lambda *args, **kwargs: None
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, "http://127.0.0.1:%d" % server.server_address[1]


def free_port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def find_chrome():
    override = os.environ.get("CHROME_PATH")
    if override and Path(override).exists():
        return override
    for candidate in CHROME_CANDIDATES:
        if candidate.startswith(("C:", "/c/", "/Applications")):
            if Path(candidate).exists():
                return candidate
            continue
        found = shutil.which(candidate)
        if found:
            return found
    return None


# --------------------------------------------------------------------------
# Minimal CDP client over a hand-rolled WebSocket (stdlib only)
# --------------------------------------------------------------------------
class _Reader:
    def __init__(self, sock, initial=b""):
        self.sock = sock
        self.buf = bytearray(initial)

    def read(self, count):
        while len(self.buf) < count:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise SmokeFailure("DevTools websocket closed unexpectedly")
            self.buf += chunk
        out = bytes(self.buf[:count])
        del self.buf[:count]
        return out


def _frame(payload, opcode=0x1):
    mask = os.urandom(4)
    length = len(payload)
    header = bytearray([0x80 | opcode])
    if length < 126:
        header.append(0x80 | length)
    elif length < 65536:
        header.append(0x80 | 126)
        header += struct.pack(">H", length)
    else:
        header.append(0x80 | 127)
        header += struct.pack(">Q", length)
    header += mask
    return bytes(header) + bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))


class DevTools:
    """Just enough CDP for a deterministic smoke test."""

    def __init__(self, websocket_url, timeout=60):
        parts = urlsplit(websocket_url)
        self.sock = socket.create_connection((parts.hostname, parts.port or 80), timeout=timeout)
        self.sock.settimeout(timeout)
        key = base64.b64encode(os.urandom(16)).decode()
        request = (
            "GET %s HTTP/1.1\r\nHost: %s:%d\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
            "Sec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n\r\n"
            % (parts.path + (("?" + parts.query) if parts.query else ""), parts.hostname, parts.port or 80, key)
        )
        self.sock.sendall(request.encode())
        raw = b""
        while b"\r\n\r\n" not in raw:
            raw += self.sock.recv(4096)
        head, _, rest = raw.partition(b"\r\n\r\n")
        if b" 101 " not in head.split(b"\r\n")[0]:
            raise SmokeFailure("DevTools websocket upgrade refused: %r" % head[:120])
        self.reader = _Reader(self.sock, rest)
        self._next_id = 0
        self.events = []

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass

    def _receive(self):
        while True:
            first, second = self.reader.read(2)
            opcode = first & 0x0F
            masked = bool(second & 0x80)
            length = second & 0x7F
            if length == 126:
                length = struct.unpack(">H", self.reader.read(2))[0]
            elif length == 127:
                length = struct.unpack(">Q", self.reader.read(8))[0]
            mask = self.reader.read(4) if masked else None
            payload = self.reader.read(length) if length else b""
            if mask:
                payload = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
            if opcode == 0x9:
                self.sock.sendall(_frame(payload, opcode=0xA))
                continue
            if opcode == 0x8:
                raise SmokeFailure("DevTools websocket closed by the browser")
            if opcode in (0x1, 0x2):
                return payload.decode("utf-8", "replace")

    def call(self, method, params=None, timeout=60):
        self._next_id += 1
        message_id = self._next_id
        self.sock.sendall(_frame(json.dumps({"id": message_id, "method": method, "params": params or {}}).encode()))
        deadline = time.time() + timeout
        while time.time() < deadline:
            message = json.loads(self._receive())
            if message.get("id") == message_id:
                if "error" in message:
                    raise SmokeFailure("CDP %s failed: %s" % (method, message["error"]))
                return message.get("result", {})
            if "method" in message:
                self.events.append(message)
        raise SmokeFailure("CDP %s timed out" % method)

    def drain(self, quiet=0.35):
        self.sock.settimeout(quiet)
        try:
            while True:
                message = json.loads(self._receive())
                if "method" in message:
                    self.events.append(message)
        except (socket.timeout, TimeoutError, OSError):
            pass
        finally:
            self.sock.settimeout(60)

    def evaluate(self, expression, await_promise=False):
        result = self.call(
            "Runtime.evaluate",
            {
                "expression": expression,
                "returnByValue": True,
                "awaitPromise": await_promise,
                "userGesture": True,
            },
        )
        if result.get("exceptionDetails"):
            raise SmokeFailure("page script raised: %s" % json.dumps(result["exceptionDetails"])[:400])
        return result.get("result", {}).get("value")


# --------------------------------------------------------------------------
# Chrome process
# --------------------------------------------------------------------------
# Records what the page's own scripts do with fetch. Installed before any page
# script runs, so it captures Decap's own config.yml request.
PROBE_SCRIPT = """
window.__smoke = { configFetches: [], cmsManualInitAtBoot: String(window.CMS_MANUAL_INIT) };
(() => {
  const original = window.fetch;
  window.fetch = function (input, init) {
    const url = (typeof input === 'string') ? input : (input && input.url);
    const record = { url: String(url), status: null, contentType: null, error: null };
    window.__smoke.configFetches.push(record);
    return original.apply(this, arguments).then(function (response) {
      record.status = response.status;
      record.contentType = response.headers.get('Content-Type');
      return response;
    }, function (error) {
      record.error = String(error);
      throw error;
    });
  };
})();
"""


def launch_chrome(chrome, port, user_data_dir, url="about:blank"):
    command = [
        chrome,
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-background-networking",
        "--disable-component-update",
        "--disable-extensions",
        "--disable-sync",
        "--disable-client-side-phishing-detection",
        "--no-proxy-server",
        "--window-size=1280,900",
        "--user-data-dir=%s" % user_data_dir,
        "--remote-debugging-port=%d" % port,
        url,
    ]
    return subprocess.Popen(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def wait_for_devtools(port, process, timeout=45):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if process.poll() is not None:
            raise SmokeFailure("Chrome exited early with code %s" % process.returncode)
        try:
            with urlopen("http://127.0.0.1:%d/json/version" % port, timeout=2) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception:
            time.sleep(0.25)
    raise SmokeFailure("Chrome DevTools endpoint never became ready on port %d" % port)


def start_browser(chrome, out_dir, attempts=3):
    """Launch headless Chrome and wait for its DevTools endpoint.

    Retried because a profile directory that was just torn down can still be
    locked for a moment on Windows, which makes Chrome exit before it ever
    listens; without the retry the smoke result is flaky instead of decidable.
    """
    last = None
    for attempt in range(attempts):
        port = free_port()
        profile = out_dir / ("chrome-profile-%d" % attempt)
        shutil.rmtree(profile, ignore_errors=True)
        process = launch_chrome(chrome, port, profile)
        try:
            return process, port, wait_for_devtools(port, process, timeout=45)
        except SmokeFailure as error:
            last = error
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
            time.sleep(1.5)
    raise last


def page_target(port):
    with urlopen("http://127.0.0.1:%d/json/list" % port, timeout=5) as response:
        targets = json.loads(response.read().decode("utf-8"))
    for target in targets:
        if target.get("type") == "page" and target.get("webSocketDebuggerUrl"):
            return target
    raise SmokeFailure("no page target available in the headless browser")


def navigate(devtools, url, settle=12.0, ready_expression="true"):
    devtools.call("Page.navigate", {"url": url})
    deadline = time.time() + settle
    while time.time() < deadline:
        try:
            if devtools.evaluate("document.readyState") == "complete":
                break
        except SmokeFailure:
            pass
        time.sleep(0.25)
    while time.time() < deadline:
        try:
            if devtools.evaluate(ready_expression):
                return True
        except SmokeFailure:
            pass
        time.sleep(0.25)
    return False


# --------------------------------------------------------------------------
# In-page evidence
# --------------------------------------------------------------------------
PAGE_EVIDENCE = """
(() => {
  const text = (document.body.innerText || '').replace(/\\s+/g, ' ').trim();
  const root = document.getElementById('nc-root');
  const scripts = Array.from(document.querySelectorAll('script[src]')).map(function (s) {
    return s.getAttribute('src');
  });
  const mountText = root ? (root.innerText || '').replace(/\\s+/g, ' ').trim() : '';
  return JSON.stringify({
    cmsManualInitType: typeof window.CMS_MANUAL_INIT,
    cmsManualInitBoot: String(window.__smoke && window.__smoke.cmsManualInitAtBoot),
    cmsGlobalType: typeof window.CMS,
    jsyamlGlobalType: typeof window.jsyaml,
    yamlGlobalType: typeof window.yaml,
    fetchCount: (window.__smoke && window.__smoke.configFetches.length) || 0,
    configFetches: (window.__smoke && window.__smoke.configFetches) || [],
    pathname: window.location.pathname,
    hash: window.location.hash,
    elementCount: document.querySelectorAll('*').length,
    mountFound: !!root,
    mountDescendants: root ? root.querySelectorAll('*').length : -1,
    mountControls: root ? root.querySelectorAll('input,select,textarea,button,a[href]').length : -1,
    mountText: mountText.slice(0, 240),
    bodyTextLength: text.length,
    bodyTextSample: text.slice(0, 220),
    scriptSources: scripts,
    configErrorVisible: /Config Errors|Check your config\\.yml file\\./.test(text),
    loadingVisible: /Loading configuration|Waiting for backend/.test(text)
  });
})()
"""

# Phase B runs with the repository's own vendored js-yaml injected by the test
# harness (never by admin/index.html), so the shipped config can be validated
# by the real parser while the page itself stays free of obsolete helpers.
CONFIG_EVIDENCE = """
(async () => {
  const response = await fetch('%(config_url)s', { cache: 'no-store' });
  const text = await response.text();
  const report = {
    url: '%(config_url)s',
    status: response.status,
    contentType: response.headers.get('Content-Type'),
    jsyamlGlobalType: typeof window.jsyaml,
    yamlGlobalType: typeof window.yaml,
    parseError: null,
    collections: []
  };
  let config;
  try {
    config = window.jsyaml.load(text);
  } catch (error) {
    report.parseError = String(error);
    return JSON.stringify(report);
  }
  report.collectionCount = config.collections.length;
  report.backend = config.backend && config.backend.name;
  config.collections.forEach(function (collection) {
    const files = Array.isArray(collection.files) ? collection.files : null;
    report.collections.push({
      name: collection.name,
      label: collection.label,
      hasFiles: !!files,
      hasFolder: typeof collection.folder === 'string',
      singularFile: Object.prototype.hasOwnProperty.call(collection, 'file'),
      fieldCount: Array.isArray(collection.fields) ? collection.fields.length : 0,
      filePaths: files ? files.map(function (entry) { return entry.file; }) : [],
      fileNames: files ? files.map(function (entry) { return entry.name; }) : [],
      fileLabels: files ? files.map(function (entry) { return entry.label; }) : [],
      filesWithFields: files ? files.filter(function (entry) {
        return Array.isArray(entry.fields) && entry.fields.length > 0;
      }).length : 0
    });
  });
  return JSON.stringify(report);
})()
"""


def collect_messages(events):
    console, exceptions = [], []
    for event in events:
        method = event.get("method")
        params = event.get("params", {})
        if method == "Runtime.exceptionThrown":
            details = params.get("exceptionDetails", {})
            description = (
                details.get("exception", {}).get("description")
                or details.get("text")
                or json.dumps(details)[:300]
            )
            exceptions.append(description)
        elif method == "Runtime.consoleAPICalled":
            kind = params.get("type", "log")
            parts = []
            for argument in params.get("args", []):
                parts.append(str(argument.get("value", argument.get("description", ""))))
            console.append({"type": kind, "text": " ".join(parts)})
        elif method == "Log.entryAdded":
            entry = params.get("entry", {})
            console.append({"type": entry.get("level", "log"), "text": entry.get("text", "")})
    return console, exceptions


def config_faults(config, faults):
    entries = config.get("collections", [])
    if config.get("parseError"):
        faults.append("the vendored js-yaml could not parse config.yml: %s" % config["parseError"])
        return
    names = [entry["name"] for entry in entries]
    if config.get("collectionCount") != 2:
        faults.append("config declares %s collections, expected 2" % config.get("collectionCount"))
    if len(names) != len(set(names)):
        faults.append("config has duplicate collection names: %s" % names)
    labels = [entry["label"] for entry in entries]
    if len(labels) != len(set(labels)):
        faults.append("config has duplicate collection labels: %s" % labels)
    for entry in entries:
        if entry["singularFile"]:
            faults.append(
                "collection %r uses the invalid singular top-level 'file:'; Decap needs 'files:' or 'folder:'"
                % entry["name"]
            )
        if entry["hasFiles"] == entry["hasFolder"]:
            faults.append("collection %r must declare exactly one of 'files:' or 'folder:'" % entry["name"])
        if entry["hasFiles"]:
            if not entry["filePaths"]:
                faults.append("collection %r has an empty files list" % entry["name"])
            if entry["filesWithFields"] != len(entry["filePaths"]):
                faults.append(
                    "collection %r has a file entry without fields (%s of %s)"
                    % (entry["name"], entry["filesWithFields"], len(entry["filePaths"]))
                )
            if len(entry["fileNames"]) != len(set(entry["fileNames"])):
                faults.append("collection %r reuses a file entry name: %s" % (entry["name"], entry["fileNames"]))
            if len(entry["fileLabels"]) != len(set(entry["fileLabels"])):
                faults.append("collection %r reuses a file entry label: %s" % (entry["name"], entry["fileLabels"]))
        elif entry["fieldCount"] == 0:
            faults.append("collection %r exposes no fields" % entry["name"])
    found_paths = sorted(path for entry in entries for path in entry["filePaths"])
    if found_paths != sorted(EXPECTED_CONFIG_FILES):
        faults.append("config file collection targets are %s, expected %s" % (found_paths, EXPECTED_CONFIG_FILES))
    if config.get("backend") != "git-gateway":
        faults.append("backend is %r, expected 'git-gateway'" % config.get("backend"))


def routing_faults(routing, faults):
    """Token hashes must reach /admin/ intact; ordinary visits must not move."""
    for label, path_and_hash in TOKEN_HASHES.items():
        target = routing.get(label)
        expected_hash = path_and_hash.split("#", 1)[1]
        token_key, token_value = expected_hash.split("=", 1)
        if not target:
            faults.append("routing %r did not complete" % label)
            continue
        if not target.startswith("/admin/"):
            faults.append("routing %r landed on %r, expected /admin/" % (label, target))
        # Decap's own hash router normalises '#x' to '#/x'; the token key and
        # value must survive whatever prefix the router adds.
        if token_key not in target:
            faults.append("routing %r lost the %s key: %r" % (label, token_key, target))
        if token_value not in target:
            faults.append("routing %r lost the token value: %r" % (label, target))
    if routing.get("ordinary_hash_untouched") != "/#main":
        faults.append("an ordinary hash was redirected away from home: %r" % routing.get("ordinary_hash_untouched"))
    if routing.get("ordinary_page_untouched") != "/services.html":
        faults.append("an ordinary page visit was redirected: %r" % routing.get("ordinary_page_untouched"))


def _follow(devtools, url, base_url, settle=8.0):
    """Navigate to a fresh document, let a token redirect settle, report path#hash.

    ``about:blank`` is visited first on purpose: navigating between two URLs that
    differ only by fragment/hash is same-document navigation, so the page's own
    identity-redirect script would not re-run and the probe would measure the
    previous document instead of a real load.
    """
    navigate(devtools, "about:blank", settle=4.0, ready_expression="document.readyState === 'complete'")
    navigate(devtools, url, settle=settle, ready_expression="true")
    time.sleep(0.4)
    return devtools.evaluate("window.location.pathname + window.location.hash")


def run_smoke(root=REPO_ROOT, out_dir=None, chrome=None, settle=15.0):
    """Run the browser smoke test. Returns (report, failures)."""
    root = Path(root).resolve()
    out_dir = Path(out_dir) if out_dir else Path(tempfile.mkdtemp(prefix="nichola-browser-smoke-"))
    out_dir.mkdir(parents=True, exist_ok=True)
    chrome = chrome or find_chrome()
    report = {"chrome": chrome, "root": str(root), "out": str(out_dir)}
    failures = []
    if not chrome:
        return report, ["no Chrome/Chromium binary found (set CHROME_PATH)"]

    jsyaml_path = root / "admin" / "vendor" / "js-yaml.min.js"
    if not jsyaml_path.is_file():
        report["failures"] = ["vendored js-yaml is missing: %s" % jsyaml_path]
        report["passed"] = False
        (out_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report, report["failures"]
    jsyaml_source = jsyaml_path.read_text(encoding="utf-8")
    report["jsyamlSha256"] = hashlib.sha256(jsyaml_path.read_bytes()).hexdigest()

    server, base_url = start_server(root)
    process, port, version = start_browser(chrome, out_dir)
    devtools = None
    try:
        report["browser"] = version.get("Browser")
        target = page_target(port)
        devtools = DevTools(target["webSocketDebuggerUrl"])
        devtools.call("Runtime.enable")
        devtools.call("Log.enable")
        devtools.call("Page.enable")

        # --- Phase A: the admin page exactly as shipped -------------------
        devtools.call("Page.addScriptToEvaluateOnNewDocument", {"source": PROBE_SCRIPT})
        admin_url = base_url + "/admin/"
        report["adminLoaded"] = navigate(
            devtools,
            admin_url,
            settle=settle,
            ready_expression=(
                "(() => { const r = document.getElementById('nc-root');"
                " return !!(r && r.querySelectorAll('*').length > 5)"
                " || /Config Errors|Check your config/.test(document.body.innerText); })()"
            ),
        )
        devtools.drain()
        time.sleep(1.0)
        devtools.drain()

        evidence = json.loads(devtools.evaluate(PAGE_EVIDENCE))
        report["page"] = evidence
        console, exceptions = collect_messages(devtools.events)
        report["console"] = console
        report["exceptions"] = exceptions

        screenshot = devtools.call("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": False})
        image = out_dir / "admin.png"
        image.write_bytes(base64.b64decode(screenshot["data"]))
        report["screenshot"] = str(image)

        # --- Phase B: validate the shipped config with the vendored parser -
        devtools.events.clear()
        devtools.call("Page.addScriptToEvaluateOnNewDocument", {"source": jsyaml_source})
        navigate(devtools, base_url + "/", settle=10.0)
        config = json.loads(
            devtools.evaluate(
                CONFIG_EVIDENCE % {"config_url": admin_url + "config.yml"},
                await_promise=True,
            )
        )
        report["config"] = config
        config_console, config_exceptions = collect_messages(devtools.events)
        report["configPhaseConsole"] = config_console
        report["configPhaseExceptions"] = config_exceptions

        # --- Phase C: invite / recovery hash routing ----------------------
        routing = {}
        routing["invite"] = _follow(devtools, base_url + TOKEN_HASHES["invite"], base_url)
        routing["recovery_from_subpage"] = _follow(devtools, base_url + TOKEN_HASHES["recovery_from_subpage"], base_url)
        routing["confirmation_from_subpage"] = _follow(devtools, base_url + TOKEN_HASHES["confirmation_from_subpage"], base_url)
        routing["recovery_on_admin"] = _follow(devtools, base_url + TOKEN_HASHES["recovery_on_admin"], base_url)
        routing["email_change_on_admin"] = _follow(devtools, base_url + TOKEN_HASHES["email_change_on_admin"], base_url)
        routing["ordinary_hash_untouched"] = _follow(devtools, base_url + "/#main", base_url, settle=6.0)
        routing["ordinary_page_untouched"] = _follow(devtools, base_url + "/services.html", base_url, settle=6.0)
        report["routing"] = routing

        # --- Verdict ------------------------------------------------------
        if evidence["cmsManualInitType"] != "undefined" or evidence["cmsManualInitBoot"] != "undefined":
            failures.append("CMS_MANUAL_INIT is set; Decap must self-initialize")
        if evidence["scriptSources"] != EXPECTED_SCRIPT_SOURCES:
            failures.append(
                "admin page loads %s, expected only %s" % (evidence["scriptSources"], EXPECTED_SCRIPT_SOURCES)
            )
        if evidence["yamlGlobalType"] != "undefined":
            failures.append("the obsolete window.yaml helper is loaded on the admin page")
        if any(MANUAL_INIT_MARKER in entry["text"] for entry in console):
            failures.append("the vendored bundle skipped automatic initialization")
        if not any(BUNDLE_STARTED_MARKER in entry["text"] for entry in console):
            failures.append("the vendored Decap bundle never announced itself — it did not start")
        if evidence["configErrorVisible"]:
            failures.append("Decap rendered its config-error screen: %r" % evidence["bodyTextSample"])
        if not evidence["mountFound"] or evidence["mountDescendants"] < 5:
            failures.append(
                "the Decap mount is empty (%s descendants) — /admin/ is blank" % evidence.get("mountDescendants")
            )
        if evidence["bodyTextLength"] < 1 or not evidence["mountText"]:
            failures.append("the admin UI rendered no visible text")
        if evidence["mountControls"] < 1:
            failures.append("the admin UI rendered no interactive controls")
        config_request = next((entry for entry in evidence["configFetches"] if "config.yml" in entry["url"]), None)
        if config_request is None:
            failures.append("Decap never fetched config.yml by itself")
        elif config_request.get("status") != 200:
            failures.append("Decap's config.yml fetch returned %s" % config_request.get("status"))
        elif "yaml" not in (config_request.get("contentType") or ""):
            failures.append("config.yml was served as %r, not a YAML type" % config_request.get("contentType"))
        if config["jsyamlGlobalType"] != "object":
            failures.append("the vendored js-yaml did not expose window.jsyaml when loaded")
        if config["yamlGlobalType"] != "undefined":
            failures.append(
                "the vendored js-yaml exposes window.jsyaml, never window.yaml — "
                "admin-boot.js's window.yaml.load could never work"
            )
        config_faults(config, failures)
        if exceptions:
            failures.append("uncaught JS exceptions on /admin/: %s" % exceptions[:3])
        if config_exceptions:
            failures.append("uncaught JS exceptions while validating the config: %s" % config_exceptions[:3])
        for entry in console + config_console:
            if entry["type"] in ("error", "warning") and (
                any(marker in entry["text"] for marker in CONFIG_ERROR_MARKERS)
                or CONFIG_CONSOLE_MARKER in entry["text"].lower()
            ):
                failures.append("console %s about the configuration: %s" % (entry["type"], entry["text"]))
        routing_faults(routing, failures)
    finally:
        if devtools is not None:
            devtools.close()
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
        server.shutdown()
        server.server_close()

    report["failures"] = failures
    report["passed"] = not failures
    (out_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report, failures


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    parser.add_argument("--out", type=Path, help="directory for report.json and admin.png")
    parser.add_argument("--chrome", help="explicit Chrome/Chromium binary")
    parser.add_argument("--json", action="store_true", help="print the full report as JSON")
    args = parser.parse_args(argv)

    report, failures = run_smoke(root=args.root, out_dir=args.out, chrome=args.chrome)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        page = report.get("page", {})
        config = report.get("config", {})
        print("BROWSER-SMOKE: browser=%s" % report.get("browser"))
        print("BROWSER-SMOKE: chrome=%s" % report.get("chrome"))
        print(
            "BROWSER-SMOKE: mount descendants=%s controls=%s text=%r"
            % (page.get("mountDescendants"), page.get("mountControls"), page.get("mountText"))
        )
        print(
            "BROWSER-SMOKE: globals decap=%s jsyaml=%s manual-init=%s"
            % (page.get("cmsGlobalType"), page.get("jsyamlGlobalType"), page.get("cmsManualInitBoot"))
        )
        print(
            "BROWSER-SMOKE: config.yml status=%s type=%s parse=%s collections=%s backend=%s"
            % (
                config.get("status"),
                config.get("contentType"),
                config.get("parseError") or "ok",
                config.get("collectionCount"),
                config.get("backend"),
            )
        )
        print("BROWSER-SMOKE: routing=%s" % json.dumps(report.get("routing"), sort_keys=True))
        print("BROWSER-SMOKE: report=%s" % (Path(report["out"]) / "report.json"))
    if failures:
        for failure in failures:
            print("BROWSER-SMOKE: FAILED — %s" % failure, file=sys.stderr)
    print("BROWSER-SMOKE: %s" % ("PASSED" if not failures else "FAILED"))
    return 0 if not failures else 1


class BrowserSmokeTests(unittest.TestCase):
    """The real headless-Chrome check, runnable through unittest as well."""

    @classmethod
    def setUpClass(cls):
        if not find_chrome():
            raise unittest.SkipTest("no local Chrome/Chromium binary available")

    def test_admin_cms_initializes_in_a_real_browser(self):
        report, failures = run_smoke()
        self.assertEqual(
            failures,
            [],
            "browser smoke failed: %s\nreport: %s" % (failures, Path(report["out"]) / "report.json"),
        )
        self.assertGreaterEqual(report["page"]["mountDescendants"], 5)
        self.assertEqual(report["config"]["collectionCount"], 2)


if __name__ == "__main__":
    sys.exit(main())
