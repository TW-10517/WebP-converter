# WebP Converter

A local desktop app for converting images **to and from** WebP. It reads PNG,
JPEG, WebP, GIF, BMP and TIFF, and writes WebP, PNG or JPEG. English and
Japanese UI, light and dark themes.

Images come in by dropping them on the drop zone — files or a whole folder — or
by clicking it to browse. `Ctrl+O` adds files, `Ctrl+Shift+O` adds a folder,
`Ctrl+Enter` converts, `Esc` stops.

Quality applies to WebP and JPEG; PNG is always lossless, so its quality
controls are disabled. Lossless applies to WebP only.

The bulb button in the top right explains every control. It has its own
English / 日本語 switch, so the explanations can be read in either language
without changing the app's language.

## Running

```
pip install -r requirements.txt
python -m webpconv
```

Or double-click `WebP Converter.pyw` (starts with no console window).

## Offline by design

The app never touches the network. There is no update check, no telemetry and no
remote service — every conversion happens in this process using Pillow. This is
enforced rather than assumed: `webpconv/security.py` patches `socket.connect`,
`socket.connect_ex` and `socket.create_connection` to raise at startup, so any
outbound connection attempt fails loudly. `tests/test_core.py` asserts this.

## Other hardening

- **Decompression bombs** — decoded pixels are capped (`MAX_IMAGE_PIXELS`), so a
  crafted image cannot exhaust memory.
- **Path traversal** — output paths are resolved and verified to sit inside the
  chosen output folder before anything is written.
- **No silent overwrites** — an existing `name.webp` is left alone and the output
  becomes `name (2).webp`, unless "Overwrite existing files" is ticked. A
  conversion whose output path would land on its own source is always renamed,
  even with overwrite on, so the input is never destroyed mid-read.
- **Shell launches are whitelisted** — the row "Open" action only calls
  `os.startfile` for paths with a supported image extension.
- **Folder scans are bounded** — symlinked directories are skipped and the walk
  stops at `MAX_SCAN_FILES`, so a deep or looping tree cannot hang the UI.
- **Settings are untrusted input** — `settings.json` is range- and type-checked
  on load, falling back to defaults.

## Where things live

| Path | Purpose |
| --- | --- |
| `webpconv/core.py` | Conversion and scanning, no UI |
| `webpconv/security.py` | DPI awareness, taskbar identity, offline guard, path safety |
| `webpconv/config.py` | Validated settings in `%APPDATA%\WebPConverter` |
| `webpconv/app.py` | Main window |
| `webpconv/help.py` | The bulb button's explanation window |
| `webpconv/widgets.py` | Custom Tk widgets |
| `webpconv/theme.py` | Palettes, DPI scaling, fonts |
| `tools/make_logo.py` | Regenerates `assets/logo.png` and `icon.ico` |

Settings and `app.log` are written to `%APPDATA%\WebPConverter`.

## Tests

```
python -m unittest discover -s tests -t .
```

## Building a standalone .exe

```
pip install pyinstaller
pyinstaller WebPConverter.spec
```

## Note on file sizes

A PNG with large flat-colour areas can come out *larger* as lossy WebP; the app
flags this with an amber ▲ badge. Ticking **Lossless** usually fixes that case.
