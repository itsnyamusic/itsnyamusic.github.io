# itsnyamusic.com

The whole of itsnyamusic.com, in one repo. Static HTML on GitHub Pages, no build
step for the site itself, no framework, no dependencies.

Custom domain via `CNAME`. HTTPS is enforced. There is nothing to install.

## Layout

| Path | What it is |
|---|---|
| `index.html` | the homepage and link hub, the canonical artist page |
| `releases/` | full discography, **generated, see below** |
| `releases/nyaverse/` | NYAVERSE album page |
| `releases/nyaverse/lyrics/` | full lyrics, all 13 tracks |
| `releases/cyber-rap/` | Cyber-Rap single page, prod. Shvde, announced before release |
| `releases/leider-remix/` | Leider (Remix) single page, feat. Exces Grace, a remix of Leider from NYAVERSE |
| `releases/digitalgods-cypher/` | DIGITALGODS CYPHER single page, feat. MTeTu, lylyth, Jessil, Naeyiwu |
| `releases/houseflip/` | Houseflip single page |
| `releases/olympia-remix/` | Olympia (Remix) single page, feat. FEBO |
| `nyaverse/` | redirect to `releases/nyaverse/`, kept because the album's old address is all over the web |
| `digitalgodsshow/` | DIGITALGODS SHOW (10.10.2026): recap, running order, Nya's setlist; holds the show's `MusicEvent` (`/#digitalgods-show`) |
| `tickets/` | redirect to the homepage; it was the short link printed on the show flyer, so keep it |
| `press/` | press coverage, **generated, see below** |
| `press-kit/` | press kit, deliberately `noindex, nofollow` |
| `datenschutz/` | privacy policy |
| `impressum/` | legal notice (§ 5 DDG) |
| `links/` | redirect to the homepage, kept because a lot of external records still point at it |
| `assets/` | shared images, icons, fonts, `fonts.css`, `site.css` |

## Rules worth knowing before editing

**The artist identity lives at one id.** Every page's structured data refers to
the artist as `https://itsnyamusic.com/#artist`, defined on the homepage. If you
add a page, reference that id, do not define a second artist entity. Two rival
entities is the thing this site is specifically built to avoid.

**The homepage `dateModified` needs a full datetime.** The homepage is a
`ProfilePage`, and Search Console flags a date with no time as invalid there.
Write `2026-10-30T23:08:50+01:00`, never `2026-10-30`.

**Every page loads `assets/site.css` right after `fonts.css`.** A page's own
`<style>` holds its layout; `site.css` holds everything that has to be the
same on every page, in one place so it cannot drift: the body font, the four
greys, the type sizes, how a link in text looks, row heights, square "pixel"
dots, the torn fringe on covers, the glitch on a row title on hover, the
torn background bloom, the grain and the spinning wireframe.
Its selectors start with `html` so they win over a page's own `<style>`.
A new page copied from an existing one brings the link along;
`build-releases.py` refuses a release page without it.

When a page needs a colour or a size, use what `site.css` already defines
rather than a new value: `--ink`, `--text`, `--dim`, `--faint` and `--rule`
for greys, `--fs-label`, `--fs-small`, `1rem` and `--fs-lead` for text. No
text is smaller than `--fs-label` and small labels carry no letter-spacing.
Everything coloured uses `var(--accent)` or `rgba(var(--accent-rgb), a)`,
which is the page's own colour (purple if the page sets none), so it works on
any release page.

The bloom's shape is the mask `assets/glitch-bloom.svg`. Its colour is the
page's exact `--accent-rgb` at two opacities, nothing else.

**Depth comes from tearing, not from glow.** Nothing on the site has a
blurred shadow. A cover or flyer gets a torn fringe instead: `site.css`
gives the picture a transparent border, fills it with scanlines in the
page's colour, and `assets/glitch-halo.svg` cuts that into bands sticking out
of the picture's edge. `assets/glitch-field.svg` does the same one size up,
bands reaching in from the edges of the screen. The small covers on rows get
a few small tears from `assets/glitch-halo-small.svg`, three variants that
the rows take in turn. Titles print twice, and a row's title jumps and
splits on hover. All of it is the page's accent, so a new release page gets
it in its own colour without any work.

**The site scales itself up on a big screen.** Every size is in rem, and
`site.css` sets the root size from the window: 100% up to 1280px wide,
growing to 150% on a 2560x1440 screen. So write sizes in rem, never px, or
that element stays small while the rest grows. A cover's `sizes` attribute
has to say the same thing, or the browser fetches the 640px file for an
810px slot: copy it from an existing release page,
`(max-width: 620px) 100vw, clamp(540px, calc(270px + 21.1vw), 810px)`.

**The spinning wireframe is `assets/spin.webp`,** one turn of the object as
72 frames in a 12 by 6 sheet. Like the bloom it is only a mask over the
page's accent, so it takes each page's colour by itself. It is drawn by
`.wrap::after`, so any page with a `.wrap` has it: in the bottom right corner
on a wide screen, at the end of the page under the footer on a phone, and
standing still for visitors who ask for reduced motion. A page that ends in
a list of links (the homepage) has it beside the last links on a phone
instead, drawn by `.links::after`. To swap the object,
render a new turntable as `spin_0000.png` onwards and run:

```
python build-spin.py <frames folder> --start 12
```

It prints the frame's `aspect-ratio`; if that changed, put it into the
`.wrap::after` rule in `site.css`. It needs Pillow.

**No external requests, on any page, ever.** Loading any page must not contact
a third party. Fonts are self-hosted and declared once in `assets/fonts.css`.
Do not add a CDN, a Google Font, an analytics snippet or a tracker, and do not
add `preconnect`/`dns-prefetch` to a third party either, since those open a
connection on their own.

There is no third-party content on any page. If a video is ever added, make it
click-to-load: ship a placeholder button and only insert the iframe (from
`youtube-nocookie.com`) once the visitor presses it, never a bare `<iframe>`,
and add a matching "Videos" section to `datenschutz/` naming Google Ireland
Limited as the recipient. `datenschutz/` currently promises no third-party
connections at all.

To check, search the built pages for anything the browser fetches by itself
(`iframe`/`img`/`script`/`link rel=preconnect|stylesheet`/`url()`) pointing at
a host that is not `itsnyamusic.com`. There should be none.

**`press/` is generated.** Do not hand-edit the markup between the
`PRESS-LD` and `PRESS-LIST` markers, it gets overwritten. Edit `press.json`,
then run the generator and commit both:

```
python build-press.py            # rebuild
python build-press.py --check    # verify without writing, exits 1 if stale
```

**`releases/` is generated too**, the same way. The rows and the structured
data both come from `releases.json`, so they cannot drift apart. Edit the JSON,
then run the generator and commit both:

```
python build-releases.py            # rebuild
python build-releases.py --check    # verify without writing, exits 1 if stale
```

The list is everything on Nya's own Spotify discography, which is the source
for it, plus the few releases that only exist on SoundCloud. A song where she
is only a guest goes on `credits/` instead; a joint release where she is a main
artist, like Bad Dreams with Kairox, goes here with a `with` field.

Each row links to the release's own page on this site if it has one (`page`,
which is how NYAVERSE works), otherwise to Spotify, otherwise to SoundCloud
(`soundcloud`, for releases that are not on Spotify), otherwise to YouTube
(`youtube`, for releases that only exist as a music video). The dot shows which. A
new release page belongs under `releases/<name>/`.

**Release pages take their colour from their cover, automatically.** The
same `build-releases.py` run reads each release page's `og:image`, picks the
cover's most vivid colour (pushed to neon, kept at 6:1 contrast or better on
the black background) and writes it into the page: between the
`/* ACCENT:START */` and `/* ACCENT:END */` comments at the top of its
`<style>`, as `--accent` and `--accent-rgb`, and into its `theme-color` meta.
The page's CSS only ever uses `var(--accent)` and `rgba(var(--accent-rgb), a)`.
To make a new release page, copy an existing one: the block comes with it,
and the build fills in the new colour. The build stops if a page has no
block or still has the old purple (`#b967ff`) hard-coded, so a page cannot
quietly miss out. The NYAVERSE link dots keep the NYAVERSE purple on purpose.
The same run also puts every release's cover as a small thumbnail on the
left of its `/releases/` row, and sets an upcoming release's date in its colour. A
release with a page uses its page's cover. For the others, the site makes no
requests to other servers, so the build fetches the cover once from
Spotify's oEmbed (SoundCloud's for SoundCloud-only releases), shrinks it to
112px and saves it as `assets/release-covers/<title>.jpg`; commit those with
the page. To replace one, delete the file and run the build again.
`--check` fails if a cover file is missing. It needs Pillow
(`pip install pillow`).

A release can go up before it is out: give it a `page` and no streaming
link, and its row reads "out <date>". Once the date has passed, the generator
refuses to build until the Spotify or SoundCloud link is added, so an
announcement cannot quietly go stale.

Guests go in a release's `features` (track number, title, guest names). They
are structured data only, the visible list stays titles and dates. Every name
used in `with` or `features` has to be in the `artists` list at the top of the
file with its Spotify profile, which is published as `sameAs` so a crawler can
tell that Naeyiwu or VAIN apart from anyone else with the same name. The
generator refuses to build if a name is missing from that list, which is what
catches typos.

Non-performing credits, like who mixed a track, go in `credits` (track
number, title, role, names). They are structured data only too, published as a
schema.org `Role` on the track's `contributor`, since schema.org has no
mixing-engineer property of its own. Names there need no Spotify profile.

`artist_links` adds further profiles to a name in `artists` (Wikidata item,
MusicBrainz artist, Genius artist). They go into `sameAs` after the Spotify
profile, which is how the producer of Cyber-Rap is tied to his own records.

**`credits/` is sorted newest first.** Every row in the list carries a
`data-date`, an ISO date at whatever precision the source actually gives:
a full date where the release has one, a bare year where the platform only
shows a year. Those sort against each other as plain strings, so nothing has
to be invented to fill a gap. Add a row wherever its date puts it, then:

```
python check-credits-order.py          # verify order and covers, exits 1 if off
python check-credits-order.py --fix    # reorder in place, add missing covers
```

`--fix` also gives each linked row its cover, like `/releases/`: fetched once from
the row's own link, shrunk to 112px and stored as
`assets/credit-covers/<artist-title>.jpg`. Commit those with the page. To replace
one, delete the file and run `--fix` again. It needs Pillow.

Rows with the same `data-date` keep the order they are written in, so where two
releases only resolve to the same year, whichever you put first stays first.
Unlike `press/`, this page is hand-edited; the script only ever moves whole
rows, it does not generate them.

A credit that is on MusicBrainz and Wikidata also gets a `MusicRecording` node
in the page's structured data, with `sameAs` pointing at those records and an
entry in the page's `mentions`. "Angel" is the first; copy its shape.

**`links/` must keep redirecting.** Wikidata, MusicBrainz, Discogs and several
artist-profile bios still point at `/links/`. The redirect carries that
authority to the homepage. It intentionally has no `noindex`, so the signals
consolidate instead of being dropped. Same for the images kept at
`links/assets/`, which older shared link previews still request.

**`nyaverse/` must keep redirecting,** and so must `nyaverse/lyrics/`. The
album page lived at `/nyaverse/` until 2026-09-21 and that address is in bios,
shared posts and on Wikidata. Like `links/`, both stubs have no
`noindex`, so their search history carries over to the new address. The lyrics
stub passes the `#track` anchor through, so links to a single song still land
on it.

**Keep the sitemap honest.** `sitemap.xml` lists only canonical, indexable
pages. `press-kit/`, `datenschutz/` and `impressum/` are excluded on purpose
because they are `noindex`, and `links/` and `nyaverse/` are excluded because
they are redirects.

**The legal pages are `noindex, follow`, never blocked in `robots.txt`.**
§ 5 DDG wants the Impressum "leicht erkennbar, unmittelbar erreichbar und
ständig verfügbar", and GDPR Art. 12 wants the same of the privacy policy.
Both are about reachability from the site itself, which the footer link on
every page satisfies, so keeping them out of search results is fine. What is
not fine is a `Disallow` in `robots.txt`: a blocked page can still be indexed
as a bare URL, because the crawler never gets to read the `noindex` it is
blocked from fetching. Keep `follow` so the footer links still carry weight,
and keep both pages returning 200 to everyone.

## History

The site used to be three repos: `links` served the hub at `/links/`, `promo`
served `/promo/`, and this repo held little more than a redirect. They were
merged here on 2026-07-28 and both old repos are archived with Pages disabled.
`/promo/` itself was removed on 2026-09-24 as redundant with the homepage,
/releases/ and /press-kit/; nothing links to it any more.
