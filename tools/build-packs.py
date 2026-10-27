#!/usr/bin/env python3
"""
產生寶可夢資料包（site/data/packs/genN.json）。

資料來源（都在 GitHub 上，PokeAPI 專案）：
  - 編號、繁體中文名稱、屬性、是否傳說、捕獲率：PokeAPI/pokeapi 的 data/v2/csv
  - 代表色：PokeAPI/sprites 的官方插圖，自動抓出主色和配色

用法：
  pip install pillow
  python3 tools/build-packs.py            # 產生第 1～3 代
  python3 tools/build-packs.py 1 2 3 4    # 指定要哪幾代

下載的檔案會快取在 tools/.cache/（不進 git）。
"""
import csv, io, json, math, os, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "tools", ".cache")
OUT = os.path.join(ROOT, "site", "data", "packs")
CSV_URL = "https://raw.githubusercontent.com/PokeAPI/pokeapi/master/data/v2/csv/{}.csv"
ART_URL = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/{}.png"
ZH_HANT = "4"          # PokeAPI 的語言編號：繁體中文
GEN_NAMES = {1: "第一代（關都）", 2: "第二代（城都）", 3: "第三代（豐緣）", 4: "第四代（神奧）"}
TYPE_IDS = {1: "normal", 2: "fighting", 3: "flying", 4: "poison", 5: "ground", 6: "rock", 7: "bug", 8: "ghost", 9: "steel",
            10: "fire", 11: "water", 12: "grass", 13: "electric", 14: "psychic", 15: "ice", 16: "dragon", 17: "dark", 18: "fairy"}


def fetch(url, path):
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with urllib.request.urlopen(url, timeout=60) as r, open(path, "wb") as f:
            f.write(r.read())
    return path


def table(name):
    return list(csv.DictReader(open(fetch(CSV_URL.format(name), os.path.join(CACHE, "csv", name + ".csv")), encoding="utf-8")))


# ---------- 顏色：sRGB → CIELAB ----------
def lin(c):
    c /= 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


LIN = [lin(i) for i in range(256)]


def lab(r, g, b):
    R, G, B = LIN[r], LIN[g], LIN[b]
    x = (R * .4124 + G * .3576 + B * .1805) / .95047
    y = R * .2126 + G * .7152 + B * .0722
    z = (R * .0193 + G * .1192 + B * .9505) / 1.08883
    f = lambda t: t ** (1 / 3) if t > .008856 else 7.787 * t + 16 / 116
    fy = f(y)
    return (116 * fy - 16, 500 * (f(x) - fy), 200 * (fy - f(z)))


def de(p, q):
    return math.dist(p, q)


def lab_to_rgb(L, a, b):
    fy = (L + 16) / 116; fx = fy + a / 500; fz = fy - b / 200
    inv = lambda t: t ** 3 if t ** 3 > .008856 else (t - 16 / 116) / 7.787
    x, y, z = inv(fx) * .95047, inv(fy), inv(fz) * 1.08883
    R = x * 3.2406 + y * -1.5372 + z * -.4986
    G = x * -.9689 + y * 1.8758 + z * .0415
    B = x * .0557 + y * -.2040 + z * 1.0570
    g = lambda c: 12.92 * c if c <= .0031308 else 1.055 * c ** (1 / 2.4) - .055
    return tuple(max(0, min(255, round(g(c) * 255))) for c in (R, G, B))


VIVID = 1.4      # 官方插圖是偏淡的水彩風，提高彩度讓顏色接近大家印象中的寶可夢顏色


def vivid(rgb):
    L, a, b = lab(*[round(v) for v in rgb])
    c = math.hypot(a, b)
    if c < 8:                                        # 灰、白、黑維持原樣
        return rgb
    k = VIVID
    for _ in range(12):                              # 超出色域就慢慢降低
        out = lab_to_rgb(L - (k - 1) * 6, a * k, b * k)
        if 0 < min(out) and max(out) < 255 or k <= 1:
            return out
        k -= 0.05
    return lab_to_rgb(L, a, b)


def colors_of(path):
    """從官方插圖抓出主色和配色：Lab 空間加權 k-means，忽略透明背景和黑色描邊，
    每一群用中位數代表（避免陰影、高光把顏色平均成灰色）"""
    im = Image.open(path).convert("RGBA").resize((120, 120), Image.NEAREST)   # 不混色縮圖
    px = [p for p in getattr(im, "get_flattened_data", im.getdata)() if p[3] > 250]
    pts = [(lab(r, g, b), (r, g, b)) for r, g, b, _ in px]
    dark = sum(1 for l, _ in pts if l[0] < 18)
    if dark < len(pts) * 0.25:                      # 黑色不多 → 是描邊，排除
        pts = [p for p in pts if p[0][0] >= 18]
    K = 8
    mean = tuple(sum(p[0][k] for p in pts) / len(pts) for k in range(3))
    C = [mean]
    step = max(1, len(pts) // 1500)
    sample = pts[::step]
    while len(C) < K:
        C.append(max(sample, key=lambda p: min(de(c, p[0]) for c in C))[0])
    for _ in range(10):
        G = [[] for _ in C]
        for p in pts:
            G[min(range(len(C)), key=lambda j: de(C[j], p[0]))].append(p)
        G = [g for g in G if g]
        C = [tuple(sum(p[0][k] for p in g) / len(g) for k in range(3)) for g in G]
    def median(g, k, idx):
        v = sorted(p[idx][k] for p in g); return v[len(v) // 2]
    groups = sorted(([len(g), [median(g, k, 0) for k in range(3)], [median(g, k, 1) for k in range(3)]] for g in G), key=lambda g: -g[0])
    merged = []
    for g in groups:                                 # 很像的群合併（保留較大群的顏色）
        m = next((o for o in merged if de(o[1], g[1]) < 10), None)
        if m: m[0] += g[0]
        else: merged.append(g)
    merged.sort(key=lambda g: -g[0])
    total = sum(g[0] for g in merged)
    main = merged[0]
    accent = next((g for g in merged[1:] if de(g[1], main[1]) > 18 and g[0] / total >= 0.06), merged[1] if len(merged) > 1 else main)
    hexc = lambda rgb: "#%02X%02X%02X" % tuple(round(v) for v in rgb)
    return [hexc(vivid(main[2])), hexc(vivid(accent[2]))]


def rarity(sp, is_final):
    """1 常見、2 少見、3 稀有：傳說／幻之、捕獲率很低的最終形態算稀有"""
    cap = int(sp["capture_rate"])
    if sp["is_legendary"] == "1" or sp["is_mythical"] == "1":
        return 3
    if sp["is_baby"] == "1":
        return 1
    if is_final and cap <= 45:                       # 噴火龍、暴鯉龍、快龍、卡比獸……
        return 3
    if sp["evolves_from_species_id"] or cap <= 100:  # 進化過的、或本來就不好抓的（御三家）
        return 2
    return 1


def main():
    gens = [int(a) for a in sys.argv[1:]] or [1, 2, 3]
    species = {int(s["id"]): s for s in table("pokemon_species")}
    names = {int(r["pokemon_species_id"]): r["name"] for r in table("pokemon_species_names") if r["local_language_id"] == ZH_HANT}
    types = {}
    for r in table("pokemon_types"):
        pid = int(r["pokemon_id"])
        if pid < 10000:
            types.setdefault(pid, {})[int(r["slot"])] = TYPE_IDS.get(int(r["type_id"]))
    ids = sorted(i for i, s in species.items() if int(s["generation_id"]) in gens)
    has_child = {int(s["evolves_from_species_id"]) for s in species.values() if s["evolves_from_species_id"]}
    with ThreadPoolExecutor(8) as ex:
        list(ex.map(lambda i: fetch(ART_URL.format(i), os.path.join(CACHE, "art", f"{i}.png")), ids))
    with ThreadPoolExecutor(os.cpu_count() or 4) as ex:
        cols = dict(zip(ids, ex.map(lambda i: colors_of(os.path.join(CACHE, "art", f"{i}.png")), ids)))
    os.makedirs(OUT, exist_ok=True)
    for gen in gens:
        mons = []
        for i in ids:
            sp = species[i]
            if int(sp["generation_id"]) != gen:
                continue
            t = types[i]
            typ = "flying" if t.get(1) == "normal" and t.get(2) == "flying" else t[1]   # 一般＋飛行的鳥歸到飛行
            mons.append({"id": i, "name": names[i], "type": typ, "rarity": rarity(sp, i not in has_child), "colors": cols[i]})
        path = os.path.join(OUT, f"gen{gen}.json")
        with open(path, "w", encoding="utf-8") as f:
            f.write('{\n  "name": "%s",\n  "pokemon": [\n' % GEN_NAMES.get(gen, f"第{gen}代"))
            f.write(",\n".join("    " + json.dumps(m, ensure_ascii=False, separators=(",", ":")) for m in mons))
            f.write("\n  ]\n}\n")
        r = [m["rarity"] for m in mons]
        print(f"{path}: {len(mons)} 隻（常見 {r.count(1)}、少見 {r.count(2)}、稀有 {r.count(3)}）")


if __name__ == "__main__":
    main()
