# pinea design

The **tvOS app** (`pinea.player`, separate repo) is the master for design and UI. The web UI follows it,
translated for mouse, keyboard and smaller screens. Read this file before any UI work.

- **From tvOS** sections describe what the app does today (read from its SwiftUI code).
- **Web** sections are the rules for this repo. Items marked **(proposal)** are not confirmed yet.
- Screenshots: `design/reference/` (gitignored, never commit them: they show artwork). Take them
  from the tvOS app connected to the **Pinea Sandbox** server (`npm run dev:sandbox`), not from real media.

---

## 1. Brand

### Logo
- File: [`design/logo.svg`](logo.svg) (copy of the tvOS asset `Logo.imageset/pinea-pink.svg`).
- 16:9 (480 × 270) rounded rectangle, corner radius 15 (≈ 3 % of the width).
- Fill: linear gradient **`#800031` (left) → `#E60058` (right)**, slightly diagonal.
- Wordmark "PINEA" in condensed capitals, letter-spaced, color **`#121212`** (near black, not white).
- tvOS: top left of the library header. It is also the button that opens the library / settings menu.
  Focused, it gets a black and an accent-colored glow.

### Colors (tvOS asset catalog)

| tvOS asset | Value | Used for |
|---|---|---|
| `AccentColor` | **`#E60058`** | Focus fill of controls, prominent buttons, placeholder icons (at 40 %) |
| `AccentSecondaryColor` | `#800031` | Dark end of the logo gradient |
| `BackgroundTop` | `#404040` | App background gradient, top right |
| `BackgroundBottom` | `#131313` | App background gradient, bottom left |
| `Placeholder` | `#2A2225` | Image placeholder (warm dark grey) |
| `primaryNegative` | `#010000` in dark mode | Text/icons **on** accent fills: black, not white |
| system `.primary` / `.secondary` | white / grey | Text levels |

The app is dark only. Background = `LinearGradient(BackgroundTop → BackgroundBottom)` from top-trailing
to bottom-leading over the whole screen.

---

## 2. Foundations (from tvOS)

### Typography
System font (SF). Levels used:

| Role | tvOS style | Example |
|---|---|---|
| Item title in a detail header | `.headline` | Movie title, person name |
| Section title | `.title3` | "Cast", "Extras" |
| Header subtitle | `.caption`, `.secondary` | File location, "3 Seasons" |
| Card labels | 14 pt regular, one line | Title (primary) + duration (secondary) |

### Shapes and aspect ratios

| Element | Ratio | Corner radius |
|---|---|---|
| Movie / collection / person poster | portrait **0.6748 : 1** (≈ 2:3) | 20 (continuous) |
| Video and extra thumbnails, VIDEOS libraries | **16:9** | 20 |
| Person in the cast row | **1:1** | **circle** at rest, 20 when focused |
| Header poster | portrait, 500 pt high | 20 |
| Navigation tabs | capsule | — |
| Icon buttons (Play, Shuffle, Search) | circle | — |

### Images
- **At rest:** saturation 0.8 and a 20 % black overlay, so images look slightly dimmed.
- **Focused:** full color, no overlay.
- **Missing image:** `Placeholder` fill with an SF Symbol (`film`, `person`, …), thin weight, in accent at 40 %.
  Collections without a poster also show their name on the placeholder (always visible, not only on hover).

### Materials, depth, motion
- Cards and controls sit on **Liquid Glass** (`glassEffect(.regular)`; header bar `.clear`).
- Card shadow: black 33 %, radius 12.
- Focus: the card scales to **1.35**, the glass container grows (radius 20 → 32, padding 15) and the
  label row appears **below the image, only while focused**.
- All focus changes: `easeOut`, **0.15 s**.

### Spacing (tvOS points, 1920 × 1080)

| Where | Value |
|---|---|
| Between sections of a detail page | 120 |
| Header poster ↔ text column | 60 |
| Library header ↔ grid | 80 |
| Shelf title ↔ shelf | 30 |
| Items in a shelf | 60 (cast: 50) |
| Grid MOVIES / SERIES | 6 columns, gaps 46 h / 70 v |
| Grid VIDEOS | 5 columns, gaps 55 h / 55 v |

---

## 3. Screens (from tvOS)

### Library
- **Header bar** (75 pt high):
  - left: the logo, which is the library menu
  - center: capsule tabs **Movies / Collections / Recommendations** with icons, on clear glass.
    The selected tab has a 10 % white fill; the focused tab has an accent fill and black text.
    SERIES libraries show the series grid instead.
  - right: circular icon buttons **Play**, **Shuffle**, **Search**.
- **Grid** of cards, using the columns per library type above. Title and duration show only on focus.
- Selecting a card opens the **detail page**; it does not start playback.

### Movie detail
From top to bottom, vertical spacing 120:
1. **Background:** the movie's poster, full screen, blur 200, blend mode `color`, opacity fades
   0 → 0.6 over 5 s after a 1 s delay. This tints the page with the poster's colors.
   **Web: not used** (decision, see section 6): neutral gray background, the poster itself is lit instead.
2. **Header:** portrait poster (500 high, radius 20) on the left. On the right a column, aligned to the
   poster's bottom edge: title (`headline`), subtitle (`caption`, secondary; today the file location),
   flexible space, then actions. Main action: **Play** (`glassProminent`, accent filled).
3. **Cast** shelf: title "Cast", horizontal scroll, circular 220 × 220 person cards in API order.
   Name only on focus. Selecting a person opens the person page.
4. **Extras** shelf: 16:9 cards, 520 wide. Label: the extra type (Trailer, Behind the scenes, …) plus the duration.
   Selecting one plays it directly.

### Person
Same header as the movie detail: the person's portrait, name, actions **Play All** / **Play Shuffle**.
Below it, a grid of their movies.

### Series
tvOS and web: same header with the serie poster, subtitle "N seasons · M episodes" (web also: years), then
**all seasons on one page**. Each season: a header (season poster, "Season N" / "Specials" / "Other episodes",
"N episodes · years · runtime"), then a horizontal row of **16:9 episode cards** (the episode still, else the poster
cropped; label "Episode 3: Title"). An episode opens the movie detail view (with cast).

- **Season poster:** the poster of an episode that also has a still (scrapers store the season poster on every
  matched episode), else a poster several episodes share, else the serie's poster (frame grabs are one per episode).
- **Order:** seasons numeric, episodes by number. Web: Specials (season 0) and episodes without a season come last.

Web (three levels, each its own URL and history entry):
1. **Library** (SERIES type): only the series as a poster grid ("N seasons" on hover). Files the scraper couldn't
   assign to a serie are listed below under "Not assigned to a series", so nothing disappears.
2. **Serie** (`?serie=`): as above. Play = first episode of the first regular season.
3. **Episode** (`?movie=`): the movie detail page with cast. Above the title: serie · season · episode.

---

## 4. Web translation rules

| tvOS | Web |
|---|---|
| Focus engine | `:hover` for pointer, `:focus-visible` for keyboard. Both use the same "focused" look |
| Scale 1.35 on focus | Small lift: scale ≈ 1.04 or translateY(-3px). 1.35 is for 10-foot viewing only |
| Labels only on focus | **Same: artwork first.** Grids show only artwork; title and meta appear on hover/focus in a glass label under the card. Exception: cast cards always show name and character (the role is the information) |
| Liquid Glass | Translucent surface + `backdrop-filter: blur()` + `--border` hairline, **only on single elements** (top bar, dialogs). Repeated elements (card labels) use an almost opaque surface instead |
| Image dim at rest → full color on focus | 20 % black overlay (`--art-dim`), faded out on hover/focus. No saturation filter: CSS filters on every image are too slow |
| tvOS points | Roughly ÷ 2 for spacing and sizes (e.g. section gap 120 → 56–64 px, poster height 500 → 280–320 px) **(proposal)** |
| Liquid Glass prominent button | `.btn-primary`: accent fill, **black** text (`primaryNegative`) |
| Opening a card | Opens the detail page (as on tvOS). Play is a button there and a small play button on the card's hover state. Maintenance actions (refresh metadata, find match) live on the detail page, not on cards |

### Tokens
The CSS variables in `frontend/src/styles.css` are the web copy of the tvOS assets. Change colors there,
never hard-code them in components.

| tvOS | CSS variable | Target value | Today (to change) |
|---|---|---|---|
| `AccentColor` | `--accent` | `#E60058` | `#5eead4` (teal) |
| — (hover of accent) | `--accent-hover` | lighter accent, e.g. `#FF2A7A` **(proposal)** | `#99f6e4` |
| `AccentSecondaryColor` | `--accent-secondary` (new) | `#800031` | — |
| `primaryNegative` | `--accent-text` | `#010000` | `#0b2724` |
| `BackgroundTop` / `Bottom` | `--bg-top` / `--bg-bottom` (new), body gradient | **subtle**: `#262626` → `#131313` (decision: the background must never compete with artwork) | flat `#0f1114` |
| `Placeholder` | `--placeholder` (new) | `#2A2225` | `--surface-2` |
| Poster radius 20 pt | `--radius` | 10 px (≈ half) | 10 px ✓ |

---

## 5. Cast and people (role and order)

- The API (`GET /api/movie/{id}/people`) returns people **already sorted**: billing order first, then
  people without an order (directors, folder people) by name. Clients keep that order.
- Each person has `character` ("James Bond") and `sort_order` (0 = first billed).
- Cast card: circular photo, below it the **name** (primary) and **character** (secondary,
  one line, ellipsis), always visible. Directors are labelled "Director" instead of a character.
  tvOS doesn't show the character yet, so the web defines it first and tvOS follows.

---

## 6. Decisions
- **Performance rules for grids** (hundreds of posters): hover/focus only animates `transform` and `opacity`;
  no CSS `filter`, `backdrop-filter`, animated `box-shadow` or layout transitions on repeated elements;
  grids, rows and cast use thumbnails (`posterUrl(name, "thumb")`), full-size posters only in detail headers.
- **Artwork first.** Labels are hidden in grids and appear on hover/focus. Layouts should celebrate
  posters and stills: big images, little chrome.
  Exception: **VIDEOS libraries** (home videos have stills, not posters) show the title at all times as a quiet
  caption under the image (muted, 13 px, one line, no background). On hover the caption moves with the growing
  image, the title turns white and year · duration fade in next to it.
- **Background:** only a subtle **gray** gradient, everywhere, also on detail pages. **No color** in the background
  and no tint from the artwork (tvOS's blurred poster background is not used on the web). Allowed alternatives:
  plain dark gray or a fine noise texture.
- **Effects go on the artwork, not the page:** the detail poster is "lit": neutral light from the top left, a
  bright edge and a deep shadow. All white/black, never colored, and **not animated** (a light sweep was tried and removed).
- **Artwork keeps its own aspect ratio** (posters can be portrait or landscape) wherever the layout
  allows it: detail headers (fixed height 400 px, natural width), single-row shelves such as
  extras on a detail page (fixed height, natural width), and "Find match" results
  (whole poster inside a fixed slot).
- **Collections are always portrait** (0.6748 : 1, like movie posters), in every library type and on the
  detail page's collections shelf; their artwork is cropped to that ratio.
- **Library grids (final):** MOVIES and SERIES = portrait grid, fixed columns, posters cropped to 0.6748 : 1.
  VIDEOS (mixed portrait and landscape) = rows like an image search (`frontend/src/JustifiedGrid.tsx`): fixed card
  height, fixed gaps, the card widths flex. Every card starts as portrait (0.6748 : 1) or 16:9, whichever is closer
  to its image, then the cards of a row are stretched or squeezed a bit to fill the width exactly (the row ends where
  that needs the least change; images are cropped). The gap between rows is larger than between cards, so rows read
  as rows. The last row keeps the base widths, left-aligned.
- **No file names in the UI chrome.** The file location is debug information: it only appears in the
  technical details of a detail page, never as a title or subtitle. Detail header subtitle:
  year · duration · resolution.
- The tvOS app is still in development. When it and this file disagree, ask which one is right.

## 7. Open questions
- [ ] VIDEOS rows: store the poster format (portrait/landscape) on the server, so rows don't adjust while posters load?
- [ ] tvOS `Person` decodes `order`, the server sends `sort_order` → rename it in the tvOS model.
      (Nothing breaks meanwhile, because the field is optional and the list is already sorted.)
