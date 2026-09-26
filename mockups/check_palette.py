#!/usr/bin/env python3
"""Team-color pair checker: OKLab deltaE (x100) under normal + CVD vision, WCAG contrast vs surface."""
import sys

def hex2rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) / 255 for i in (0, 2, 4))

def lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def to_linear(rgb):
    return tuple(lin(c) for c in rgb)

MACHADO = {
    'protan': [[0.152286, 1.052583, -0.204868],
               [0.114503, 0.786281, 0.099216],
               [-0.003882, -0.048116, 1.051998]],
    'deutan': [[0.367322, 0.860646, -0.227968],
               [0.280085, 0.672501, 0.047413],
               [-0.011820, 0.042940, 0.968881]],
    'tritan': [[1.255528, -0.076749, -0.178779],
               [-0.078411, 0.930809, 0.147602],
               [0.004733, 0.691367, 0.303900]],
}

def mat3(m, v):
    return tuple(sum(m[i][j] * v[j] for j in range(3)) for i in range(3))

def oklab(linrgb):
    r, g, b = (max(0.0, min(1.0, c)) for c in linrgb)
    l = 0.4122214708*r + 0.5363325363*g + 0.0514459929*b
    m = 0.2119034982*r + 0.6806995451*g + 0.1073969566*b
    s = 0.0883024619*r + 0.2817188376*g + 0.6299787005*b
    l_, m_, s_ = l ** (1/3), m ** (1/3), s ** (1/3)
    return (0.2104542553*l_ + 0.7936177850*m_ - 0.0040720468*s_,
            1.9779984951*l_ - 2.4285922050*m_ + 0.4505937099*s_,
            0.0259040371*l_ + 0.7827717662*m_ - 0.8086757660*s_)

def dE(a, b):
    return 100 * sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5

def rel_lum(linrgb):
    r, g, b = linrgb
    return 0.2126*r + 0.7152*g + 0.0722*b

def contrast(l1, l2):
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)

designs = [
    ("D1 broadcast", "#131A2A", "#F5A623", "#4FC3F7"),
    ("D2 atlas",     "#F0E9D8", "#B3402E", "#2C5F8A"),
    ("D3 wayfind",   "#F7F5F0", "#C42847", "#1D6FB8"),
    ("D4 arcade",    "#10122B", "#FF5CA8", "#43E97B"),
    ("D5 fog",       "#ECF0F3", "#D96248", "#2F7E85"),
]

for name, surf, ca, cb in designs:
    la, lb = to_linear(hex2rgb(ca)), to_linear(hex2rgb(cb))
    ls = to_linear(hex2rgb(surf))
    normal = dE(oklab(la), oklab(lb))
    rows = [f"normal dE={normal:5.1f} {'PASS' if normal >= 15 else 'FAIL'}"]
    worst = 999
    for kind, m in MACHADO.items():
        d = dE(oklab(mat3(m, la)), oklab(mat3(m, lb)))
        worst = min(worst, d)
        rows.append(f"{kind} dE={d:5.1f} {'PASS' if d >= 8 else ('WARN' if d >= 6 else 'FAIL')}")
    csa = contrast(rel_lum(la), rel_lum(ls))
    csb = contrast(rel_lum(lb), rel_lum(ls))
    rows.append(f"surf contrast A={csa:.2f} B={csb:.2f} {'PASS' if min(csa, csb) >= 3 else 'WARN'}")
    print(f"{name} [{ca} vs {cb} on {surf}]")
    for r in rows:
        print("   ", r)
