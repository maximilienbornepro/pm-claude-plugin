"""svg2pptx - convertit le SVG du schéma d'architecture (vocabulaire golden.py) en formes PowerPoint natives.

Vocabulaire couvert, celui du rendu de référence : rect (cartes `.bg`, boîtes `.box`, zones en pointillés,
plaques de logo), path / line (flux `.flow`, `.arr`, `.auth`, `.api`, avec flèches), text (`.t`, `.tm`,
`.s`, `.lbl`, `.lsai`, `.lkc`), image (logos en data-URI), circle. Les icônes interactives (loupes `.zoom`)
sont omises. Les couleurs `var(--x)` sont résolues avec la palette passée en paramètre (skin du dossier).

Chaque élément devient une forme éditable : on peut retoucher le schéma dans PowerPoint.
"""
from __future__ import annotations

import base64
import io
import re
import xml.etree.ElementTree as ET

CLASS = {
    # class: (fill, stroke, stroke_width, dash)
    "bg": ("surface", "line", 1.0, False),
    "box": ("surface", "line", 1.0, False),
    "zone": ("s2", "line", 1.2, True),
    "arr": (None, "muted", 1.6, False),
    "flow": (None, "sai", 2.0, True),
    "api": (None, "sai", 3.0, False),
    "auth": (None, "kc", 2.2, True),
}
TEXT = {
    # class: (size px, colour, weight)
    "t": (15, "ink", 400), "tm": (13.5, "ink", 400), "s": (12, "muted", 300),
    "lbl": (11, "muted", 300), "lsai": (11, "sai", 400), "lkc": (11, "kc", 400),
}


def _strip_ns(tag):
    return tag.split("}")[-1]


def _style(el):
    out = {}
    for part in (el.get("style") or "").split(";"):
        if ":" in part:
            k, v = part.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def _color(v, pal):
    if not v or v in ("none", "transparent", "context-stroke"):
        return None
    m = re.match(r"var\(--([\w-]+)\)", v)
    if m:
        v = pal.get(m.group(1), "#888888")
    v = v.strip().lstrip("#")
    if len(v) == 3:
        v = "".join(c * 2 for c in v)
    return v.upper() if re.fullmatch(r"[0-9a-fA-F]{6}", v) else None


def _path_points(d):
    """M/L/H/V (absolute or relative) -> list of subpaths (list of points). Curves are flattened to end points."""
    toks = re.findall(r"[MLHVZCQmlhvzcq]|-?\d*\.?\d+(?:e-?\d+)?", d)
    subs, cur, x, y, cmd, i = [], [], 0.0, 0.0, None, 0
    while i < len(toks):
        t = toks[i]
        if re.fullmatch(r"[A-Za-z]", t):
            cmd = t; i += 1
            if cmd in "Zz" and cur:
                cur.append(cur[0])
            continue
        def num():
            nonlocal i
            v = float(toks[i]); i += 1
            return v
        if cmd in ("M", "m"):
            nx, ny = num(), num()
            if cmd == "m":
                nx, ny = x + nx, y + ny
            if cur:
                subs.append(cur)
            cur = [(nx, ny)]; x, y = nx, ny
            cmd = "L" if cmd == "M" else "l"
        elif cmd in ("L", "l"):
            nx, ny = num(), num()
            if cmd == "l":
                nx, ny = x + nx, y + ny
            cur.append((nx, ny)); x, y = nx, ny
        elif cmd in ("H", "h"):
            nx = num(); x = x + nx if cmd == "h" else nx; cur.append((x, y))
        elif cmd in ("V", "v"):
            ny = num(); y = y + ny if cmd == "v" else ny; cur.append((x, y))
        elif cmd in ("C", "c"):
            vals = [num() for _ in range(6)]
            nx, ny = vals[4], vals[5]
            if cmd == "c":
                nx, ny = x + nx, y + ny
            cur.append((nx, ny)); x, y = nx, ny
        elif cmd in ("Q", "q"):
            vals = [num() for _ in range(4)]
            nx, ny = vals[2], vals[3]
            if cmd == "q":
                nx, ny = x + nx, y + ny
            cur.append((nx, ny)); x, y = nx, ny
        else:
            i += 1
    if cur:
        subs.append(cur)
    return subs


def _image_file(href, tmpdir):
    """data-URI -> PNG path usable by python-pptx (webp converted; svg via Quick Look when available)."""
    m = re.match(r"data:([\w/+.-]+);base64,(.*)", href or "", re.S)
    if not m:
        return None
    mime, raw = m.group(1), base64.b64decode(m.group(2))
    import hashlib
    from pathlib import Path
    h = hashlib.md5(raw).hexdigest()[:12]
    out = Path(tmpdir) / f"logo-{h}.png"
    if out.exists():
        return out
    try:
        if "svg" in mime:
            import subprocess
            import tempfile
            src = Path(tempfile.mkdtemp()) / f"{h}.svg"
            src.write_bytes(raw)
            subprocess.run(["qlmanage", "-t", "-s", "256", "-o", str(src.parent), str(src)], capture_output=True, timeout=20)
            png = src.parent / f"{h}.svg.png"
            if not png.exists():
                return None
            from PIL import Image
            im = Image.open(png).convert("RGBA")
            bbox = Image.eval(im.convert("L"), lambda v: 255 - v).getbbox()  # crop Quick Look white margins
            (im.crop(bbox) if bbox else im).save(out)
        else:
            from PIL import Image
            Image.open(io.BytesIO(raw)).convert("RGBA").save(out)
        return out
    except Exception:
        return None


def render(D, s, svg, x, y, w, h, pal, tmpdir, fonts=None):
    """Draw the SVG into the box (x, y, w, h) in cq on slide s. Returns the drawn box (x, y, w, h)."""
    from slides import F_LIGHT, F_REG
    root = ET.fromstring(svg)
    vb = [float(v) for v in root.get("viewBox").split()]
    k = min(w / vb[2], h / vb[3])
    ox = x + (w - vb[2] * k) / 2
    oy = y
    P = lambda a, b: (ox + (a - vb[0]) * k, oy + (b - vb[1]) * k)  # noqa: E731

    def walk(el, cls_ctx=()):
        tag = _strip_ns(el.tag)
        cls = tuple((el.get("class") or "").split()) or ()
        if tag in ("defs", "marker", "title", "desc"):
            return
        if "zoom" in cls:
            return
        st = _style(el)
        if tag == "rect":
            base = next((CLASS[c] for c in cls if c in CLASS), None)
            fill = _color(st.get("fill") or el.get("fill") or (base and base[0] and f"var(--{base[0]})"), pal)
            stroke = _color(st.get("stroke") or el.get("stroke") or (base and base[1] and f"var(--{base[1]})"), pal)
            sw = float(st.get("stroke-width") or el.get("stroke-width") or (base[2] if base else 1))
            dash = bool(el.get("stroke-dasharray") or st.get("stroke-dasharray") or (base and base[3]))
            rx = float(el.get("rx") or 0)
            X, Y = P(float(el.get("x", 0)), float(el.get("y", 0)))
            W, H = float(el.get("width")) * k, float(el.get("height")) * k
            from pptx.enum.shapes import MSO_SHAPE
            sh = D.rect(s, X, Y, W, H, fill, stroke, lw=sw * k * 9.6, dash=dash,
                        shape=MSO_SHAPE.ROUNDED_RECTANGLE if rx else MSO_SHAPE.RECTANGLE)
            if rx:
                sh.adjustments[0] = min(.5, rx / max(1e-6, min(float(el.get("width")), float(el.get("height")))))
        elif tag in ("path", "line", "polyline"):
            base = next((CLASS[c] for c in cls if c in CLASS), (None, "muted", 1.4, False))
            stroke = _color(st.get("stroke") or el.get("stroke") or f"var(--{base[1]})", pal)
            if not stroke:
                return
            sw = float(st.get("stroke-width") or el.get("stroke-width") or base[2])
            dash = bool(el.get("stroke-dasharray") or st.get("stroke-dasharray") or base[3])
            if tag == "line":
                subs = [[(float(el.get("x1")), float(el.get("y1"))), (float(el.get("x2")), float(el.get("y2")))]]
            elif tag == "polyline":
                nums = [float(v) for v in re.findall(r"-?\d*\.?\d+", el.get("points", ""))]
                subs = [list(zip(nums[::2], nums[1::2]))]
            else:
                subs = _path_points(el.get("d", ""))
            end = bool(el.get("marker-end")); start = bool(el.get("marker-start"))
            for sp in subs:
                if len(sp) >= 2:
                    D.poly(s, [P(a, b) for a, b in sp], color=stroke, w=max(.6, sw * k * 9.6), dash=dash, start=start, end=end)
        elif tag == "circle":
            fill = _color(st.get("fill") or el.get("fill"), pal)
            if fill:
                X, Y = P(float(el.get("cx")), float(el.get("cy")))
                D.oval(s, X, Y, float(el.get("r")) * k, fill)
        elif tag == "image":
            href = el.get("href") or el.get("{http://www.w3.org/1999/xlink}href")
            f = _image_file(href, tmpdir)
            if f:
                from PIL import Image
                iw, ih = Image.open(f).size
                bx, by = P(float(el.get("x", 0)), float(el.get("y", 0)))
                bw, bh = float(el.get("width")) * k, float(el.get("height")) * k
                sc = min(bw / iw, bh / ih)
                D.picture(s, f, bx + (bw - iw * sc) / 2, by + (bh - ih * sc) / 2, h=ih * sc)
        elif tag == "text":
            txt = "".join(el.itertext()).strip()
            if not txt:
                return
            spec = next((TEXT[c] for c in cls if c in TEXT), (12, "ink", 400))
            size_px = float(st.get("font-size", "").rstrip("px") or spec[0])
            color = _color(st.get("fill") or el.get("fill"), pal) or _color(f"var(--{spec[1]})", pal)
            weight = spec[2]
            anchor = el.get("text-anchor") or st.get("text-anchor") or "start"
            X, Y = P(float(el.get("x", 0)), float(el.get("y", 0)))
            size = size_px * k
            bw = max(len(txt) * size * .62 + 2, 4)
            bx = X if anchor == "start" else (X - bw / 2 if anchor == "middle" else X - bw)
            al = {"start": "l", "middle": "c", "end": "r"}[anchor]
            tb = D.text(s, bx, Y - size * 0.95, bw, size * 1.3, txt, size=size, color=color,
                        font=F_REG if weight >= 400 else F_LIGHT, align=al, spacing=.3 if "lbl" in cls else 0)
            tb.text_frame.word_wrap = False
        for ch in list(el):
            walk(ch, cls_ctx + cls)

    for ch in list(root):
        walk(ch)
    return ox, oy, vb[2] * k, vb[3] * k
