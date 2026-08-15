"""Scenario matrix to find the deterministic post-refresh break."""

from PIL import Image
from playwright.sync_api import sync_playwright

SHOTS = r"C:\Users\user\AppData\Local\Temp\opencode"


def metrics(path):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    px = im.load()
    # card extent at y=500 (or 400)
    card = None
    for y in (500, 420, 350):
        s = None
        runs = []
        for x in range(290, w - 20):
            c = px[x, y]
            if c == (248, 249, 255):
                if s is None:
                    s = x
            else:
                if s is not None:
                    runs.append((s, x - 1))
                    s = None
        runs = [r for r in runs if r[1] - r[0] > 300]
        if runs:
            card = runs[-1]
            break
    if not card:
        return None
    # table line right edge
    best = 0
    for y in range(300, h - 40):
        for x in range(card[1] - 2, card[0] + 2, -1):
            c = px[x, y]
            if abs(c[0] - 238) <= 6 and abs(c[1] - 238) <= 6 and abs(c[2] - 238) <= 6:
                best = max(best, x)
                break
    return {"card": card, "line_right": best, "interior_w": card[1] - card[0] - 24}


def report(tag, shot):
    m = metrics(shot)
    if not m:
        print(f"{tag}: no card")
        return
    table_w = m["line_right"] - m["card"][0] - 12 if m["line_right"] else None
    print(f"{tag}: card w={m['card'][1]-m['card'][0]} table_w~{table_w} gap={m['card'][1]-12-m['line_right'] if m['line_right'] else '?'}")


REFRESH = {"loans": (1300, 190), "inventory": (1430, 200)}


def run(page, tile_y, name, tag, waits=(2500, 800)):
    page.mouse.click(140, tile_y)
    page.wait_for_timeout(waits[0])
    shot = f"{SHOTS}\\s_{tag}_before.png"
    page.screenshot(path=shot)
    report(f"{name} {tag} before", shot)
    cx, cy = REFRESH[name]
    page.mouse.click(cx, cy)
    page.wait_for_timeout(waits[1])
    shot = f"{SHOTS}\\s_{tag}_after.png"
    page.screenshot(path=shot)
    report(f"{name} {tag} AFTER ", shot)


with sync_playwright() as p:
    b = p.chromium.launch()

    # A: cold-ish start, short waits, loans
    page = b.new_page(viewport={"width": 1600, "height": 900})
    page.goto("http://localhost:8700")
    page.wait_for_timeout(5000)
    run(page, 130 + 56 * 4, "loans", "A_quick")
    run(page, 130 + 56 * 1, "inventory", "A_quick")
    b.close()

with sync_playwright() as p:
    b = p.chromium.launch()
    # B: 1920 viewport
    page = b.new_page(viewport={"width": 1920, "height": 1000})
    page.goto("http://localhost:8700")
    page.wait_for_timeout(6000)
    run(page, 130 + 56 * 4, "loans", "B_1920")
    b.close()

with sync_playwright() as p:
    b = p.chromium.launch()
    # C: shrink then refresh; D: grow then refresh; E: nav away/back; F: flip mobile/desktop
    page = b.new_page(viewport={"width": 1600, "height": 900})
    page.goto("http://localhost:8700")
    page.wait_for_timeout(6000)
    page.mouse.click(140, 130 + 56 * 4)
    page.wait_for_timeout(2500)

    page.set_viewport_size({"width": 1280, "height": 900})
    page.wait_for_timeout(1500)
    run(page, 130 + 56 * 4, "loans", "C_shrink", waits=(1500, 1500))

    page.set_viewport_size({"width": 1920, "height": 900})
    page.wait_for_timeout(1500)
    run(page, 130 + 56 * 4, "loans", "D_grow", waits=(1500, 1500))

    page.set_viewport_size({"width": 700, "height": 900})
    page.wait_for_timeout(2000)
    page.set_viewport_size({"width": 1920, "height": 900})
    page.wait_for_timeout(2000)
    run(page, 130 + 56 * 4, "loans", "F_flip", waits=(2000, 1500))
    b.close()
