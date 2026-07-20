# Adding press coverage

**Do not edit the article list in `index.html` by hand.** It is generated.

## Three steps

1. Add an entry to **`/press.json`** (repo root), in the `articles` array:

   ```json
   {
     "outlet": "Publication Name",
     "url": "https://...",
     "headline": "The article's real headline, verbatim",
     "description": "One or two sentences on what the piece actually says.",
     "date": "2026-08-14",
     "author": "Byline Name",
     "lang": "en",
     "accent": "#ff7a29"
   }
   ```

2. Run the generator from the repo root:

   ```
   python build-press.py
   ```

3. Commit **both** `press.json` and the rebuilt `press/index.html`.

Order does not matter, entries are sorted newest-first automatically.

## Fields

| Field | Required | Notes |
|---|---|---|
| `outlet` | yes | Publication name. Becomes `publisher` in the structured data. |
| `url` | yes | Direct link to the article. |
| `headline` | yes | The real headline, verbatim. Do not paraphrase, since it is published as `headline` in schema.org data. |
| `description` | yes | 1–2 sentences. Human-facing only. |
| `date` | yes | `YYYY-MM-DD` if the exact day is known, `YYYY-MM` if only the month is. |
| `author` | no | Byline. Omit or `null` if unknown. |
| `lang` | no | BCP47 code, defaults to `en`. Use `es` for Spanish pieces, `de` for German. |
| `accent` | no | Hex colour of the dot. Defaults to `#b967ff`. Freim TV uses `#ff2d7b`, Foxfire `#ff7a29`. |

**On `date` precision:** if you only know the month, write `2026-07`. The generator then omits `datePublished` from the structured data entirely rather than inventing a day. Do not guess a date to make the field look complete: a wrong date in schema.org output is worse than an absent one.

## What the generator owns

Only the two marked regions in `index.html`:

- `<!-- PRESS-LD:START -->` … `<!-- PRESS-LD:END -->`: the whole `application/ld+json` block
- `<!-- PRESS-LIST:START -->` … `<!-- PRESS-LIST:END -->`: the visible article list

Everything else (CSS, layout, header, footer, privacy notice) is hand-maintained and safe to edit directly. If you delete the markers, the script exits with an error rather than guessing.

Both regions come from the same source, so the visible page and the structured data cannot drift apart. That matters here: this site's whole SEO/GEO strategy depends on machines reading the page correctly.

## Checking without changing anything

```
python build-press.py --check
```

Exits `1` and prints `STALE` if `press.json` has been edited without rebuilding. Exits `0` when up to date. Safe to wire into a pre-commit hook.

## Notes

- Output is fully static HTML. Do not convert this to client-side rendering: AI crawlers cannot be relied on to execute JavaScript, and the structured data must be present in the raw HTML.
- Fonts are self-hosted in `/assets/fonts/`. Do not reintroduce Google Fonts: remote font loading transmits visitor IPs to Google, which is a documented GDPR problem in Germany (LG München, Jan 2022).
- Verify every URL is live before adding it. A press page that 404s is worse than a shorter one.
