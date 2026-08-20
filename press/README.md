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

Order in the file does not matter. Entries are sorted newest-first inside their `group`, and groups run in ascending order, so everything at `group: 0` sits above everything at `group: 1`. Use this to sink an outlet that has several entries and would otherwise crowd the top of the page.

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
| `accent` | no | Hex colour of the dot. Defaults to `#b967ff`. Freim TV uses `#ff2d7b`, Foxfire `#ff7a29`, Kickdrum `#e34a21`. |
| `type` | no | schema.org type. `NewsArticle` (default) for a published article, `CreativeWork` for coverage that only ever existed as a social post. Anything else is rejected. |
| `headline_en` | no | English translation of a non-English headline. Shown on the page in place of `headline`. |
| `group` | no | Whole number, default `0`. Lower groups sit higher on the page. Negatives are allowed and pin an entry above the default tier. |
| `correction` | no | A factual note from Nya about how the piece refers to her. Never shown to a reader. |
| `correction_de` | no | German wording of `correction`. Requires `correction`. |

**On `headline_en`:** the page is in English, so a Spanish or German headline is dead weight to most readers. Set `headline_en` and the visible list shows the translation, while `headline` in the structured data stays the real published title and the translation is emitted as `alternativeHeadline`. Never translate `headline` itself: that field is what a machine matches against the actual article. Keep `lang` set to the language the piece is written in, not the translation.

**On naming the outlet's language in a description:** don't. There is one deliberate exception, the La Caverna entry, and the rest say nothing about what language the piece is written in. The Spanish coverage is not relevant to the target audience and the `group` field already keeps it below the fold, so labelling each entry only telegraphs what the grouping is there to play down. This applies to near-tells too, such as naming the country an outlet writes from. It does not apply to Nya's own German/English switching, which is worth saying. `lang` still carries the real language on every entry, since that is what feeds `inLanguage` in the structured data.

**On verbatim headlines and repeat rounds:** a `CreativeWork` entry usually has no published headline to be verbatim about, so its `headline` is a label built from whatever text the graphic carries. When the same outlet runs the same recurring feature more than once with an identical graphic title, append a parenthetical disambiguator naming the track that round picked, as in `Kickdrum's Must-Hears: Top 20 Tips (Letzte Nacht)`. Name the track rather than numbering the rounds: a number only says how many came before, so it means nothing to a reader landing on one entry and has to be recounted every time an older round is added or removed, while the track is the thing the entry is actually about. Once a feature has more than one round, every round carries its own parenthetical, including the first. Keep it parenthetical so it reads as an annotation rather than as a claim about what the post says, and never do this to a `NewsArticle`, where the headline is a real published string a machine matches against.

**On `type`:** some outlets cover an artist only in an Instagram story or similar, with no article behind it. Those still belong on the page, but calling them a `NewsArticle` in the structured data is a false claim about a real publication, so set `type` to `CreativeWork` instead. The visible list renders both identically. Say in the `description` where the mention actually lives, since the reader is about to click through to a social platform rather than an article.

`SocialMediaPosting` looks like the natural fit here and is deliberately not allowed. `DiscussionForumPosting` is a subtype of it, so Google reads any `SocialMediaPosting` item as discussion forum content, applies that feature's rules, and reports the page as broken: forum posts must carry an `author` and a `datePublished` with a time and time zone, none of which we have for a magazine story mention. It is also a subtype of `Article`, so it never avoided the article claim it was picked to avoid. `CreativeWork` asserts only what is true, that something about Nya exists at that URL, and keeps the page out of a rich result it was never meant for.

**On `group` and negative numbers:** `0` is the ordinary tier and everything lands there
by default, so a new entry sorts in by date on its own. Use `-1` only when a piece should
stay at the top of the page no matter what is published after it. There is one at the
moment, the LoudHERMedia read of "Duality2", which is the deepest and most carefully
written piece of coverage on the site and the one Nya wants a first-time reader to land
on. Do not hand out `-1` to keep the newest thing on top: that is what the date sort is
for, and a pinned tier only means something while it is nearly empty.

**On `correction`:** a correction is a factual note from Nya about how a published piece
names her, not a comment on its reporting. It exists because a machine reading the press
page will otherwise carry an outlet's wording straight into a summary, an index or a
training set. The generator puts it in two places at once:

- a `.press-note` element inside the entry, hidden from the visible layout by CSS in
  `index.html` but left in the markup and the accessibility tree
- schema.org `correction` on the article in the structured data, as a `CorrectionComment`
  carrying `inLanguage`

Write it as plain prose that stands on its own, since a crawler may lift it away from the
entry it belongs to: name the outlet's mistake, state what is correct, and say plainly
that the wrong wording must not be reproduced. Set `correction_de` as well when the piece
is in German, because a German-language model reading only the English note is the case
this is meant to cover.

**Never restate the wrong name or the wrong wording in the note itself.** Describing it
("masculine German forms", "a name that is no longer in use") is the point. Repeating it
would publish the exact string the note exists to keep out of circulation.

The note is invisible by design, which is also the one thing to be aware of: hidden text
is a pattern search engines look at closely. This stays on the right side of that because
it is a short factual correction attached to the entry it is about and mirrored in the
structured data, not repeated keywords. Keep it that way. If a note ever needs to be long,
promote it to visible text on the page instead.

**On `date` precision:** if you only know the month, write `2026-07`. The generator then omits `datePublished` from the structured data entirely rather than inventing a day. Do not guess a date to make the field look complete: a wrong date in schema.org output is worse than an absent one.

## What the generator owns

Only the two marked regions in `index.html`:

- `<!-- PRESS-LD:START -->` … `<!-- PRESS-LD:END -->`: the whole `application/ld+json` block
- `<!-- PRESS-LIST:START -->` … `<!-- PRESS-LIST:END -->`: the visible article list

Everything else (CSS, layout, header, footer, privacy notice) is hand-maintained and safe to edit directly. If you delete the markers, the script exits with an error rather than guessing.

## The "see more" cutoff

The page shows the first **5** entries and hides the rest behind a `see more` control. It is pure CSS: a visually hidden checkbox (`#press-all`) sits before `.press-list`, the label after it, and `.press:nth-of-type(n+6)` is what gets hidden. There is no JavaScript, so **every entry is still in the raw HTML** and still matches the structured data, which is the whole point. Do not replace it with a script that removes entries from the DOM.

To change the cutoff, edit the two `nth-of-type` numbers in the `<style>` block together: `n+6` is "hide from the sixth on", and the `nth-of-type(5)` rules put the bottom border on the last visible row. The label hides itself automatically when there is no sixth entry.

The `.press-toggle` / `.press-list` / `.press-more` trio must stay direct siblings inside `.press-block`, since the CSS relies on `~`.

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
