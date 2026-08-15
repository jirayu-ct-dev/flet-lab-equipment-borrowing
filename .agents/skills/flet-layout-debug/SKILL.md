---
name: flet-layout-debug
description: Fix and debug Flet layout bugs — content pushed right, giant gray placeholder blocks, rows/columns exploding into full-height side panels, or responsive layouts breaking after window resize. Covers the flet 0.86 expand=False flex corruption bug, the expand=None vs expand=False distinction, and a headless-browser pixel-measurement workflow for pinpointing layout root causes in Flutter-canvas Flet apps that cannot be inspected via DOM.
---

# Flet Layout Debug

Flet (0.86+) renders to a Flutter canvas — no DOM to inspect. Layout bugs must
be diagnosed by code reading plus rendered-output measurement. This skill
bundles the one known renderer-level bug in this repo plus the general
debugging workflow that found it.

## Known bug: `expand = False` corrupts flex layout

### Symptom (exact signature)

A `Row`/`ResponsiveRow`/`Column` that should lay children out inline instead
renders as **two side-by-side full-height panels**:

- Large empty/white area on the left (~the first child's col fraction, e.g. 5/12)
- A giant uniform **gray block `(196,196,196)`** on the right (~remaining
  fraction, e.g. 7/12) that looks like a broken placeholder/loading area
- Content appears "pushed right" / starting mid-screen
- No console errors, no exceptions — the app otherwise works

Trigger: any control inside a `Row`/`ResponsiveRow` (or any parent that passes
flex constraints) has `expand` set to `False`. Typical source is view code that
"unsets" flex when toggling mobile/desktop layouts:

```python
self.search_field.expand = False   # BUG: corrupts the whole enclosing Row
```

### Fix

Use `expand = None` (not `False`) to remove a control from flex distribution:

```python
self.search_field.expand = None    # correct: control is not a flex child
```

In flet 0.86 `None` and `False` are NOT interchangeable for `expand`:

- `None` = no flex participation (control keeps its own `width`, ignored by
  the parent's flex algorithm) — the safe "unset"
- `False` = sent to the layout protocol as an explicit non-truthy flex value
  that breaks the parent's flex/col layout computation for the whole run

Rules:

1. Never write `.expand = False` anywhere in flet 0.86+ code. Grep for it when
   a layout explodes: `rg "\.expand\s*=\s*False" app/`
2. When a view is rebuilt on breakpoint change and previously set
   `expand = True`, always reset with `.expand = None` (plus reset `width`
   if the layout switched between fixed-width and `float("inf")`).

### Detection shortcut

If the user reports "content pushed right / big gray box / layout split into
two columns", check for `expand = False` FIRST before anything else. It has
been the root cause every time in this repo (inventory + loans filter bars).

## Also check (other layout-killers found in this codebase)

- `width=float("inf")` inside a `Row` on a **non-flex** child: the child claims
  the row's full max width and overlaps siblings (text overlaps the next
  button). Inside a `Row`, make the expanding child `expand = True` +
  `width = None` instead. `float("inf")` width is only safe for children of a
  `Column` (cross-axis stretch).
- Tests asserting `expand is False` must be updated to `expand is None` when
  the fix is applied — `is False` passes on the buggy code.

## Debugging workflow (when the cause is NOT the known bug)

Flet pages are a Flutter canvas: `page.locator(...)`/accessibility DOM yields
nothing useful. Measure rendered pixels instead.

1. **Run the real app headless**
   - Serve: `flet run --web --port 8700 main.py` (note: `python -m flet` does
     NOT work in flet 0.86 — there is no `flet.__main__`)
   - Drive with Playwright chromium. Sidebar nav clicks need real coordinates
     (`page.mouse.click(x, y)`); the semantics placeholder is outside the
     viewport and cannot be clicked.
   - Screenshots are ground truth; read them with PIL and classify pixels.

2. **Pixel analysis helpers** (see "scripts" below)
   - Column runs at a given y for a color predicate → tells you where each
     control/card/block sits horizontally
   - Detect the bug's signature color `(196,196,196)`; count pixels — 0 after
     a successful fix
   - ASCII downscale map of the whole page for eyeballing structure

3. **Bisect by rebuilding the view in a standalone probe entrypoint**
   - Create a temporary `probe.py` at repo root (imports of `app.*` fail if
     the file sits under `.flet/` because `flet run` changes CWD) with a
     `PROBE_CASE` env var switching between cases A, B, C...
   - Start with: (A) trivial layout known-good, (B) the broken view as-is
   - Then swap ONE thing at a time: replace the suspicious bar with a
     hand-built one, replace one control at a time, strip children, strip
     event handlers, strip mutations
   - Serve each case on its own port (`flet run --web --port <p> probe.py`,
     ~9 s startup), screenshot, measure. The case where the signature
     disappears isolates the culprit.
   - Kill leftover `python` listeners between runs (`Get-NetTCPConnection`)
     or a stale server keeps serving OLD code and poisons results.

4. **Verify the fix end-to-end**
   - Real app (not probe), seeded data if tables should render
     (`APP_SEED_DEMO=1`, idempotent via `app_seed_runs`)
   - Multiple viewports (1600 / 1280 / 1024 / 430) + resize stress across the
     breakpoint (e.g. 1600→900→1600, and 5 successive resizes), then assert:
     signature color count == 0, content spans the full content area,
     table card present at mid-page
   - `python -m pytest` — view tests may assert the old (buggy) values

5. **Clean up**: delete probe files and kill all flet servers before finishing.

## Scripts

Pixel measurement (paste into a python file or `-c`):

```python
from PIL import Image

def xrr(path, y, pred):
    im = Image.open(path).convert("RGB"); w, h = im.size; px = im.load()
    rs = []; s = None
    for x in range(w):
        if pred(px[x, y]):
            if s is None: s = x
        else:
            if s is not None: rs.append((s, x - 1)); s = None
    if s is not None: rs.append((s, w - 1))
    return [r for r in rs if r[1] - r[0] > 40]

gray = lambda c: c == (196, 196, 196)   # bug signature color
# xrr(shot, 400, gray) -> [] means fixed; [(510, 1181)] means bug present
```

Probe skeleton (`probe.py`, run with `PROBE_CASE=B flet run --web --port 8590 probe.py`):

```python
import os
import flet as ft

case = os.environ.get("PROBE_CASE", "A")

def main(page: ft.Page) -> None:
    page.padding = 0
    if case == "A":
        content = ft.Column(controls=[ft.Text("baseline")], expand=True)
    elif case == "B":
        content = <the broken composition, verbatim>
    page.add(ft.Container(expand=True, content=content))

if __name__ == "__main__":
    ft.run(main)
```

## References from the original incident (2026-08)

- Bug introduced while toggling mobile/desktop filter layouts: commit history
  around "Improve inventory search, filters, and responsive layouts"
- Affected then: `app/views/inventory.py` (4 sites), `app/views/loans.py`
  (1 site); fixed by switching all to `expand = None`
- Rendering truth: bisect cases V1 (bug reproduces on clean bar by adding
  `expand = False`) and V2/V3 (bug disappears by resetting to `None` in the
  real view)
