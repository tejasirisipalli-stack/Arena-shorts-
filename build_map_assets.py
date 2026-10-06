"""Builds assets/map/ap_outline.json (normalised Andhra Pradesh geometry) from the
open GeoJSON district dataset by ishawakankar/India_Districts.

The raw download is cached in build/ (not tracked). Re-run this script to refresh:

    python3 build_map_assets.py            # uses build/ap_districts.geojson
    python3 build_map_assets.py --download # fetches the dataset first

District boundaries are simplified with Ramer-Douglas-Peucker and projected with an
equirectangular projection corrected by cos(latitude), which is accurate enough for a
single-state map graphic. Coordinates are normalised so the state fits a box of
width 1.0 and height = 1/aspect.
"""
import json, math, os, sys, base64, subprocess

RAW = 'build/ap_districts.geojson'
OUT = 'assets/map/ap_outline.json'
REPO = 'ishawakankar/India_Districts'
PATH = 'Andra_Pradesh/andra_pradesh.geojson'


def download():
    os.makedirs('build', exist_ok=True)
    sha = json.loads(subprocess.run(
        ['curl', '-s', f'https://api.github.com/repos/{REPO}/contents/{PATH}'],
        capture_output=True, text=True, check=True).stdout)['sha']
    blob = json.loads(subprocess.run(
        ['curl', '-s', f'https://api.github.com/repos/{REPO}/git/blobs/{sha}'],
        capture_output=True, text=True, check=True).stdout)
    with open(RAW, 'wb') as fh:
        fh.write(base64.b64decode(blob['content']))
    print('downloaded', RAW)


def rings_of(geom):
    """Every ring in a Polygon/MultiPolygon, as flat [lon, lat] lists."""
    acc = []

    def walk(c):
        if isinstance(c[0][0], (int, float)):
            acc.append(c)
        else:
            for x in c:
                walk(x)
    walk(geom['coordinates'])
    return acc


def dp(pts, eps):
    """Douglas-Peucker. Rings arrive closed, so drop the duplicate end point first."""
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts = pts[:-1]
    n = len(pts)
    if n < 3:
        return pts
    keep = [False] * n
    keep[0] = keep[n - 1] = True
    stack = [(0, n - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        ax, ay = pts[i]
        bx, by = pts[j]
        dx, dy = bx - ax, by - ay
        norm = math.hypot(dx, dy)
        if norm == 0:
            continue
        dmax, idx = -1.0, -1
        for k in range(i + 1, j):
            px, py = pts[k]
            dist = abs(dy * px - dx * py + bx * ay - by * ax) / norm
            if dist > dmax:
                dmax, idx = dist, k
        if dmax > eps and idx > 0:
            keep[idx] = True
            stack.append((i, idx))
            stack.append((idx, j))
    return [p for p, k in zip(pts, keep) if k]


def main():
    if '--download' in sys.argv or not os.path.exists(RAW):
        download()
    data = json.load(open(RAW))

    districts = []
    for feat in data['features']:
        rr = rings_of(feat['geometry'])
        if not rr:
            continue
        districts.append((feat['properties']['NAME_2'], max(rr, key=len)))

    districts.sort(key=lambda d: d[0])
    simplified = [(name, dp(r, 0.0012)) for name, r in districts]
    print('district rings:', [(n, len(r)) for n, r in simplified])

    allp = [p for _, r in simplified for p in r]
    lat0 = (min(p[1] for p in allp) + max(p[1] for p in allp)) / 2
    kx = math.cos(math.radians(lat0))

    def project(lon, lat):
        return (lon * kx, -lat)

    proj = [project(*p) for p in allp]
    x0, x1 = min(p[0] for p in proj), max(p[0] for p in proj)
    y0, y1 = min(p[1] for p in proj), max(p[1] for p in proj)
    w, h = x1 - x0, y1 - y0
    scale = 1.0 / max(w, h)

    def norm(lon, lat):
        px, py = project(lon, lat)
        return [round((px - x0) * scale, 5), round((py - y0) * scale, 5)]

    out = {
        'source': f'https://github.com/{REPO} (district boundaries, simplified)',
        'note': 'Normalised Andhra Pradesh outline + district rings, y grows downward.',
        'aspect': round(w / h, 4),
        'name': 'ఆంధ్రప్రదేశ్',
        # Rings are stored in the same normalised space as `tenali` below, so the
        # renderer can project them straight onto the canvas.
        'districts': [{'name': n, 'rings': [norm(lon, lat) for lon, lat in r]}
                      for n, r in simplified],
        'tenali': norm(80.640, 16.243),
        'vijayawada': norm(80.648, 16.507),
        'guntur_city': norm(80.436, 16.306),
    }
    # District bounding boxes let later stages zoom on the right area.
    for d in out['districts']:
        pts = d['rings']          # a single outer ring: a flat list of [x, y] points
        d['bbox'] = [min(p[0] for p in pts), min(p[1] for p in pts),
                     max(p[0] for p in pts), max(p[1] for p in pts)]
    os.makedirs('assets/map', exist_ok=True)
    json.dump(out, open(OUT, 'w'), ensure_ascii=False)
    print('wrote', OUT, os.path.getsize(OUT), 'bytes; aspect', out['aspect'])
    print('guntur bbox', next(d['bbox'] for d in out['districts'] if d['name'] == 'Guntur'))
    print('tenali', out['tenali'])


if __name__ == '__main__':
    main()
