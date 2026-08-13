# Brand assets

Drop the official CPDSE artwork here. The app looks for these two names and uses whatever
it finds — **no code changes needed**, just overwrite the files.

| File | Where it appears | Notes |
| --- | --- | --- |
| `cpdse-mark.svg` | App header (≈30 px), HTML report footer | The mark **without** the tagline — at header size the text is illegible |
| `cpdse-logo.svg` | Sign-in page (≈150 px) | The full lock-up **with** "People, Data, & Drugs" |

## Accepted formats

SVG is preferred (sharp at every size, tiny). If you only have raster artwork, the loader
also accepts the same basename with `.png`, `.webp`, `.jpg` or `.jpeg` — e.g.
`cpdse-mark.png`. SVG wins if both exist. For raster, supply at least 2× the display size
(≥ 64 px for the mark, ≥ 300 px for the lock-up) so it stays crisp on retina screens.

Optionally add `favicon.png` (square, ≥ 64 px) for the browser tab icon; without it the app
falls back to an emoji.

## If a file is missing

The app degrades quietly: no image, no error, layout unchanged. Nothing breaks, so it is safe
to run before the official artwork arrives.

## Placeholders currently in this folder

The SVGs here are **rough recreations** drawn from a screenshot, not the official vector
artwork — the geometry and the caduceus are approximate. **Replace them** with the files from
the CPDSE logo package before the app is shown to students.

Keep colours to the CPDSE palette (Forest Green `#3C5E3E`, Antique Gold `#D6C17C`). This
directory and `core/theme.py` are the only places in the app where hex values may appear.
