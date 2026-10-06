#!/usr/bin/env python3
"""The Reading Bridge — static page generator.

PURPOSE
    Turn the content files under site/content/ plus the templates under
    site/build/templates/ into the 13 published HTML pages, IN PLACE, inside
    site/ (netlify.toml keeps publish = ".").

    This is a BUILD-TIME generator. Its output is plain static HTML that can be
    diffed and reviewed before deploy. It is deliberately NOT the runtime
    renderer that once broke this site: nothing here runs in a visitor's
    browser, and the pages it writes are complete and correct with JavaScript
    disabled.

STANDARD LIBRARY ONLY
    No third-party imports, so it runs on Netlify's build image with the stock
    `python3`. See netlify.toml for the build command.

USAGE
    python3 build/generate.py            # write the 13 pages in place
    python3 build/generate.py --check    # render to a temp dir and diff every
                                         # page against the live file; exit 1 if
                                         # any page differs (the acceptance test)

TEMPLATE LANGUAGE (deliberately tiny — 5 constructs)
    {{ path.to.value }}          substitute a value from the content files
    {{ value | html }}           substitute, escaped for HTML text/attribute use
    {% if x %}...{% elif y %}...{% else %}...{% endif %}
    {% for item in list %}...{% endfor %}
    (expressions are a dotted path, optionally compared to a quoted literal:
     {% if blk.type == 'ul' %} — no arithmetic, no function calls)

    Every value in the content files is already the literal string that must
    appear in the HTML (including entities such as &amp;), so substitution is a
    plain string insert. Only values that are *raw human text* (the policy
    labels, which contain a bare "&") are passed through `| html`.

LINE ENDINGS
    The published HTML uses LF (no CR). Every file is written as UTF-8 bytes so
    the host platform can never re-introduce CRLF.
"""

import argparse
import difflib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))          # site/build
SITE = os.path.dirname(HERE)                                # site
CONTENT_DIR = os.path.join(SITE, "content")
TEMPLATE_DIR = os.path.join(HERE, "templates")

# ---------------------------------------------------------------------------
# The page registry. Structure only — every word a visitor reads comes from the
# content files. `depth` selects the two link prefixes ("" at the site root,
# "../" under policies/); `template` is the <main> body for that page.
# ---------------------------------------------------------------------------
PAGES = [
    {"id": "index.html", "template": "pages/index.html", "depth": "root", "meta": "index"},
    {"id": "services.html", "template": "pages/services.html", "depth": "root", "meta": "services"},
    {"id": "owner.html", "template": "pages/owner.html", "depth": "root", "meta": "owner"},
    {"id": "assessment.html", "template": "pages/assessment.html", "depth": "root", "meta": "assessment"},
    {"id": "pricing.html", "template": "pages/pricing.html", "depth": "root", "meta": "pricing"},
    {"id": "faq.html", "template": "pages/faq.html", "depth": "root", "meta": "faq"},
    {"id": "area.html", "template": "pages/area.html", "depth": "root", "meta": "area"},
    {"id": "book.html", "template": "pages/book.html", "depth": "root", "meta": "book"},
    {"id": "contact.html", "template": "pages/contact.html", "depth": "root", "meta": "contact"},
    {"id": "privacy.html", "template": "pages/policies/policy.html", "depth": "policies",
     "policy": "privacy", "out": "policies/privacy.html"},
    {"id": "safeguarding.html", "template": "pages/policies/policy.html", "depth": "policies",
     "policy": "safeguarding", "out": "policies/safeguarding.html"},
    {"id": "cancellations.html", "template": "pages/policies/policy.html", "depth": "policies",
     "policy": "cancellations", "out": "policies/cancellations.html"},
    {"id": "payment.html", "template": "pages/policies/policy.html", "depth": "policies",
     "policy": "payment", "out": "policies/payment.html"},
]

PREFIX = {"root": "", "policies": "../"}


# ---------------------------------------------------------------------------
# Content
# ---------------------------------------------------------------------------
def load_content():
    with open(os.path.join(CONTENT_DIR, "site.json"), encoding="utf-8") as f:
        site = json.load(f)
    with open(os.path.join(CONTENT_DIR, "policies.json"), encoding="utf-8") as f:
        policies = json.load(f)
    return site, policies


# ---------------------------------------------------------------------------
# Template engine
# ---------------------------------------------------------------------------
TOKEN_RE = re.compile(r"\{\{(?P<var>.*?)\}\}|\{%(?P<tag>.*?)%\}", re.S)

TEXT, VAR, TAG = "text", "var", "tag"


def tokenize(text):
    pos = 0
    for m in TOKEN_RE.finditer(text):
        if m.start() > pos:
            yield TEXT, text[pos:m.start()]
        if m.group("var") is not None:
            yield VAR, m.group("var").strip()
        else:
            yield TAG, m.group("tag").strip()
        pos = m.end()
    if pos < len(text):
        yield TEXT, text[pos:]


class Node:
    pass


class TextNode(Node):
    def __init__(self, text):
        self.text = text


class VarNode(Node):
    def __init__(self, expr):
        parts = [p.strip() for p in expr.split("|")]
        self.expr = parts[0]
        self.filters = parts[1:]


class IfNode(Node):
    def __init__(self, branches):
        # branches: list of (condition_or_None, [nodes]); the last may be
        # (None, [...]) for the {% else %} arm.
        self.branches = branches


class ForNode(Node):
    def __init__(self, var, expr, body):
        self.var = var
        self.expr = expr
        self.body = body


class TemplateError(Exception):
    pass


def parse(text):
    toks = list(tokenize(text))
    nodes, idx = _parse_block(toks, 0, stop=())
    if idx != len(toks):
        raise TemplateError("unexpected trailing content at token %d" % idx)
    return nodes


def _parse_block(toks, i, stop):
    nodes = []
    while i < len(toks):
        kind, val = toks[i]
        if kind == TAG:
            word = val.split(None, 1)[0] if val else ""
            if word in stop:
                return nodes, i
            if word == "if":
                node, i = _parse_if(toks, i, val[2:].strip())
                nodes.append(node)
                continue
            if word == "for":
                node, i = _parse_for(toks, i, val)
                nodes.append(node)
                continue
            raise TemplateError("unexpected tag {%% %s %%}" % val)
        if kind == VAR:
            nodes.append(VarNode(val))
        else:
            nodes.append(TextNode(val))
        i += 1
    if stop:
        raise TemplateError("missing {%% %s %%}" % stop[0])
    return nodes, i


def _parse_if(toks, i, first_cond):
    branches = []
    cond = first_cond
    i += 1  # consume the {% if %}
    while True:
        body, i = _parse_block(toks, i, stop=("elif", "else", "endif"))
        branches.append((cond, body))
        kind, val = toks[i]
        word = val.split(None, 1)[0] if val else ""
        if word == "elif":
            cond = val[4:].strip()
            i += 1
            continue
        if word == "else":
            body, i = _parse_block(toks, i + 1, stop=("endif",))
            branches.append((None, body))
            return IfNode(branches), i + 1  # consume {% endif %}
        return IfNode(branches), i + 1  # consume {% endif %}


def _parse_for(toks, i, tag):
    m = re.match(r"for\s+([A-Za-z_][\w.]*)\s+in\s+(.+)$", tag)
    if not m:
        raise TemplateError("bad for tag: %s" % tag)
    var, expr = m.group(1), m.group(2).strip()
    body, i = _parse_block(toks, i + 1, stop=("endfor",))
    return ForNode(var, expr, body), i + 1  # consume {% endfor %}


def resolve(path, scopes):
    parts = path.split(".")
    if parts[0] in ("true", "false"):
        return parts[0] == "true"
    if not parts[0]:
        return None
    value = None
    found = False
    for scope in scopes:
        if parts[0] in scope:
            value = scope[parts[0]]
            found = True
            break
    if not found:
        raise TemplateError("unknown name %r" % parts[0])
    for part in parts[1:]:
        if isinstance(value, dict):
            if part not in value:
                raise TemplateError("unknown key %r in %r" % (part, path))
            value = value[part]
        elif isinstance(value, list):
            value = value[int(part)]
        else:
            raise TemplateError("cannot descend into %r for %r" % (value, path))
    return value


def eval_cond(expr, scopes):
    parts = expr.split("==")
    try:
        if len(parts) == 2:
            left = resolve(parts[0].strip(), scopes)
            right = parts[1].strip()
            if len(right) >= 2 and right[0] in "'\"" and right[-1] == right[0]:
                right = right[1:-1]          # quoted literal
            else:
                right = resolve(right, scopes)  # another path, e.g. page.id
            return str(left) == str(right)
        return bool(resolve(expr.strip(), scopes))
    except TemplateError:
        # An optional key that is simply absent (e.g. services[0].ages) is
        # falsy, not an error. Required keys are resolved through {{ ... }},
        # where an unknown name still raises.
        return False


def html_escape(value):
    return (str(value).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def render(nodes, scopes, out):
    for node in nodes:
        if isinstance(node, TextNode):
            out.append(node.text)
        elif isinstance(node, VarNode):
            value = resolve(node.expr, scopes)
            for f in node.filters:
                if f == "html":
                    value = html_escape(value)
                else:
                    raise TemplateError("unknown filter %r" % f)
            out.append("" if value is None else str(value))
        elif isinstance(node, IfNode):
            for cond, body in node.branches:
                if cond is None or eval_cond(cond, scopes):
                    render(body, scopes, out)
                    break
        elif isinstance(node, ForNode):
            try:
                items = resolve(node.expr, scopes)
            except TemplateError:
                items = []          # an optional list that is absent: iterate nothing
            if items is None:
                items = []
            for item in items:
                render(node.body, [dict({node.var: item}), *scopes], out)
        else:  # pragma: no cover
            raise TemplateError("bad node %r" % node)
    return out


def render_string(text, ctx):
    return "".join(render(parse(text), [ctx], []))


def read_template(rel):
    with open(os.path.join(TEMPLATE_DIR, rel.replace("/", os.sep)),
              encoding="utf-8", newline="") as f:
        return f.read()


def render_template(rel, ctx, strip_final_newline=True):
    """Render a template file. Partials and page bodies end with a single
    trailing newline which the assembler supplies itself, so it is stripped
    exactly once; the layout keeps its final newline."""
    text = render_string(read_template(rel), ctx)
    if strip_final_newline and text.endswith("\n"):
        text = text[:-1]
    return text


# ---------------------------------------------------------------------------
# Page assembly
# ---------------------------------------------------------------------------
def normalise_policy(policy):
    """Bullet lists are stored as an array of strings. Decap's list widget can,
    depending on configuration, write an array of single-key objects instead, so
    accept either shape rather than letting a CMS save break the build."""
    for section in policy.get("sections", []):
        for block in section.get("blocks", []):
            items = block.get("items")
            if isinstance(items, list):
                block["items"] = [
                    next(iter(i.values())) if isinstance(i, dict) and i else i
                    for i in items
                ]
    return policy


def build_page(page, site, policies):
    prefix = PREFIX[page["depth"]]
    if "policy" in page:
        policy = normalise_policy(policies[page["policy"]])
        title = policy["page_title"]
        description = policy["meta_description"]
    else:
        meta = site["pages"][page["meta"]]
        title = meta["title"]
        description = meta["description"]

    ctx = {
        "site": site,
        "page": {
            "id": page["id"],
            "depth": page["depth"],
            "prefix": prefix,
            "title": title,
            "description": description,
        },
    }
    if "policy" in page:
        ctx["policy"] = policies[page["policy"]]
    if page.get("meta") == "index":
        # The home page shows the first three services only; services.html shows
        # all of them.
        ctx["page_services"] = site["services"][:3]

    ctx["header"] = render_template("partials/header.html", ctx)
    ctx["main"] = render_template(page["template"], ctx)
    ctx["footer"] = render_template("partials/footer.html", ctx)
    return render_template("layout.html", ctx, strip_final_newline=False)


def output_rel(page):
    return page.get("out", page["id"])


def generate_all():
    site, policies = load_content()
    return [(output_rel(p), build_page(p, site, policies)) for p in PAGES]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def write_in_place():
    for rel, html in generate_all():
        if "\r" in html:
            raise SystemExit("refusing to write %s: contains CR" % rel)
        path = os.path.join(SITE, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(html.encode("utf-8"))
        print("wrote %s (%d bytes)" % (rel, len(html.encode("utf-8"))))


def check():
    """Render into a temporary directory and diff every page against the live
    file. Exit non-zero if anything differs."""
    import tempfile
    failures = []
    print("generator byte-identity check — all 13 pages")
    print("%-32s %-10s %-10s %s" % ("page", "generated", "live", "result"))
    print("-" * 72)
    tmp = tempfile.mkdtemp(prefix="trb-generate-check-")
    for rel, html in generate_all():
        gen = html.encode("utf-8")
        tmp_path = os.path.join(tmp, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(tmp_path), exist_ok=True)
        with open(tmp_path, "wb") as f:
            f.write(gen)
        live_path = os.path.join(SITE, rel.replace("/", os.sep))
        if not os.path.isfile(live_path):
            failures.append(rel)
            print("%-32s %-10d %-10s %s" % (rel, len(gen), "MISSING", "*** FAIL ***"))
            continue
        with open(live_path, "rb") as f:
            live = f.read()
        same = gen == live
        if not same:
            failures.append(rel)
        print("%-32s %-10d %-10d %s" % (rel, len(gen), len(live),
                                        "IDENTICAL" if same else "*** DIFFERENT ***"))
        if not same:
            g = gen.decode("utf-8", "replace").splitlines(keepends=True)
            lv = live.decode("utf-8", "replace").splitlines(keepends=True)
            for line in list(difflib.unified_diff(
                    lv, g, fromfile="live/" + rel, tofile="generated/" + rel, n=1))[:40]:
                print("    " + line.rstrip("\n"))
    print()
    if failures:
        print("BYTE-IDENTITY: *** FAILED *** — %d file(s) differ: %s"
              % (len(failures), ", ".join(failures)))
        print("(generated copies left in %s for inspection)" % tmp)
        return 1
    print("BYTE-IDENTITY: PASSED — all 13 generated pages are byte-identical to the "
          "live files (LF endings, no BOM, no CR).")
    print("scratch: %s" % tmp)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build The Reading Bridge static pages.")
    ap.add_argument("--check", action="store_true",
                    help="render to a temp dir and diff against the live files")
    args = ap.parse_args(argv)
    if args.check:
        return check()
    write_in_place()
    return 0


if __name__ == "__main__":
    sys.exit(main())
