# How the site is built

The 13 published HTML pages are **generated** from the content files. Editing
content never means editing HTML.

```
content/site.json        every word, price and label on the site
content/policies.json    the four policy page bodies
        |
        v
build/generate.py   +    build/templates/   (layout, header, footer, page bodies)
        |
        v
index.html, services.html, ... , policies/privacy.html, ...   (13 files, written in place)
```

Netlify runs `python3 build/generate.py` on every deploy (`netlify.toml`) and
then publishes this folder as-is.

## Running it

```sh
python3 build/generate.py            # regenerate the 13 pages in place
python3 build/generate.py --check    # render to a temp dir and diff against
                                     # the live files; exit 1 if anything differs
```

`--check` is the acceptance test. It must print `BYTE-IDENTITY: PASSED — all 13
generated pages are byte-identical to the live files`. There is no Python
package to install: the generator is standard library only, so it runs on
Netlify's build image.

The generator is **idempotent**. If the content has not changed it rewrites the
pages with exactly the same bytes, so a content-only edit produces a
content-only diff and nothing else.

## Why this is not the thing that broke before

An earlier version of this site re-rendered `<main>` **in the browser** from
`content/site.json`. That produced duplicated sections, literal `undefined`
text, and eventually replaced whole pages with an error notice.

This generator runs at **build time** and its output is plain static HTML that
can be diffed before it is deployed. The pages it writes are complete with
JavaScript disabled. The browser-side `main.js` still only rebuilds the header
chrome and refreshes the copyright year — it does not touch `<main>`.

## Template language

`build/generate.py` contains a small template engine. Five constructs:

| syntax | meaning |
| --- | --- |
| `{{ site.hero.headline }}` | insert a value from a content file |
| `{{ value \| html }}` | insert a value, escaping `& < > "` |
| `{% if x %}...{% elif y %}...{% else %}...{% endif %}` | conditionals |
| `{% for item in list %}...{% endfor %}` | loops |
| dotted paths and `== 'literal'` | all the expression syntax there is |

No arithmetic, no function calls, no plugins.

### The two rules that keep the output byte-identical

1. **A content value is inserted verbatim** unless a template explicitly adds
   the `| html` filter. Most values in `content/policies.json` already contain
   HTML entities (`&amp;`, `&middot;`) because they were extracted from the
   verified HTML character for character — escaping them again would corrupt
   them.
2. **`| html` is used only for values that are plain human text and may contain
   a bare `&`.** Today that is the service titles, the FAQ answers, and the four
   policy labels in the footer.

## Templates

| file | what it is |
| --- | --- |
| `templates/layout.html` | `<html>`, `<head>`, skip link, and the assembly points |
| `templates/partials/header.html` | the shared header chrome |
| `templates/partials/footer.html` | the shared footer |
| `templates/pages/*.html` | the `<main>` body of each root page |
| `templates/pages/policies/policy.html` | one body used by all four policy pages |

The header and footer are pre-rendered into every page rather than built in the
browser; that is what makes the site work with JavaScript disabled.

## Adding content

1. Add the value to `content/site.json` (or `content/policies.json`).
2. Reference it from a template and, if needed, add a rule in the page registry
   at the top of `build/generate.py`.
3. Add a matching field to `admin/config.yml` — **Decap drops any key it has no
   field for when it saves the file.**
4. Run `python3 build/generate.py --check`, then review the diff.
