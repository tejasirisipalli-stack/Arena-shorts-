"""Serves the finished JANASEVA NEWS Short for download and in-browser preview.

Run from the repository root:

    python3 serve_download.py            # http://0.0.0.0:8080

Implements HTTP Range requests so the inline player can seek, and sends
Content-Disposition on the download links so a click saves the file.
"""
import html, os, re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get('PORT', '8080'))
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')
VIDEO = 'ap_3lakh_houses_telugu_short.mp4'
FILES = {
    VIDEO: 'video/mp4',
    'ap_3lakh_houses_telugu_short.srt': 'text/plain; charset=utf-8',
    'ap_3lakh_houses_telugu_short.vtt': 'text/vtt; charset=utf-8',
    'thumbnail.jpg': 'image/jpeg',
    'youtube_metadata_te.md': 'text/markdown; charset=utf-8',
}
SIZE = os.path.getsize(os.path.join(ROOT, VIDEO)) / 1e6


def page():
    rows = []
    for name, mime in FILES.items():
        size = os.path.getsize(os.path.join(ROOT, name)) / 1024
        rows.append(
            f'<li><a href="/files/{name}?dl=1">{html.escape(name)}</a>'
            f'<span>{size:,.0f} KB</span></li>')
    return f"""<!doctype html>
<html lang="te"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>JANASEVA NEWS — ఏపీకి 3 లక్షల పక్కా ఇళ్లు | ₹3,600 కోట్లు</title>
<style>
  :root {{ color-scheme: dark; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; background:#050b16; color:#eaf4ff;
         font-family: system-ui, "Noto Sans Telugu", "Segoe UI", sans-serif; }}
  .wrap {{ max-width: 980px; margin: 0 auto; padding: 32px 20px 64px; }}
  header {{ border-bottom:1px solid #1d3b57; padding-bottom:18px; margin-bottom:28px; }}
  h1 {{ font-size: 26px; margin:0 0 6px; }}
  h2 {{ font-size: 15px; font-weight:500; color:#8fb4cc; margin:0; }}
  .badge {{ display:inline-block; background:#e2203a; color:#fff; font-size:12px;
            letter-spacing:.08em; padding:3px 10px; border-radius:4px; margin-bottom:12px; }}
  .cols {{ display:grid; grid-template-columns: minmax(280px,360px) 1fr; gap:32px; align-items:start; }}
  @media (max-width: 780px) {{ .cols {{ grid-template-columns: 1fr; }} }}
  video {{ width:100%; border-radius:14px; background:#000; border:1px solid #24506e;
           box-shadow:0 10px 40px rgba(0,0,0,.5); }}
  .btn {{ display:block; text-align:center; background:#e2203a; color:#fff; font-weight:700;
          text-decoration:none; padding:16px 22px; border-radius:12px; margin:18px 0 10px;
          font-size:17px; }}
  .btn:hover {{ background:#f03350; }}
  .meta {{ color:#9dbccd; font-size:14px; line-height:1.7; }}
  code {{ background:#0d1f33; padding:2px 6px; border-radius:5px; font-size:13px; }}
  ul {{ list-style:none; padding:0; margin:22px 0 0; }}
  li {{ display:flex; justify-content:space-between; gap:12px; padding:11px 0;
        border-bottom:1px solid #142739; font-size:14px; }}
  li a {{ color:#6fe0ff; text-decoration:none; }}
  li a:hover {{ text-decoration:underline; }}
  li span {{ color:#7c98ac; white-space:nowrap; }}
  footer {{ margin-top:34px; color:#7c98ac; font-size:13px; line-height:1.7; }}
</style></head>
<body><div class="wrap">
<header>
  <div class="badge">JANASEVA NEWS</div>
  <h1>ఏపీకి 3 లక్షల పక్కా ఇళ్లు | ₹3,600 కోట్లు</h1>
  <h2>60 సెకన్లు • 1080×1920 (9:16) • 30 fps • తెలుగు ఫేస్‌లెస్ న్యూస్ షార్ట్</h2>
</header>
<div class="cols">
  <div>
    <video controls preload="metadata" poster="/files/thumbnail.jpg">
      <source src="/files/{VIDEO}" type="video/mp4">
    </video>
    <a class="btn" href="/files/{VIDEO}?dl=1" download>⬇ డౌన్‌లోడ్ MP4 ({SIZE:.1f} MB)</a>
    <p class="meta">Bot కావాలంటే ఈ ఎరుపు బటన్ నొక్కండి. డౌన్‌లోడ్ లింక్:
      <code>/files/{VIDEO}?dl=1</code></p>
  </div>
  <div>
    <p class="meta">
      ప్రధానమంత్రి ఆవాస్ యోజన–గ్రామీణ్ (PMAY-G) కింద ఆంధ్రప్రదేశ్‌కు 3 లక్షల ఇళ్లు
      మంజూరు, సుమారు ₹3,600 కోట్ల నిధులు. గుంటూరు జిల్లా తెనాలి నియోజకవర్గంలోని
      బుర్రిపాలెంలో కార్యక్రమం. 3D కాంక్రీట్ ప్రింటింగ్‌తో 177 ఇళ్ల పైలట్ ప్రాజెక్ట్,
      అంచనా వ్యయం ₹14 కోట్లు.
    </p>
    <p class="meta"><strong>ముఖ్య గమనిక:</strong> ప్రస్తుతం మంజూరైన 3 లక్షల ఇళ్లు వేరు,
      భవిష్యత్ దశలో మంజూరు కావచ్చని చెప్పిన మరో 3 లక్షల ఇళ్లు వేరు. 6 నెలల గడువు
      ఒక లక్ష్యం మాత్రమే.</p>
    <ul>{''.join(rows)}</ul>
    <footer>
      ఈ ఫోల్డర్‌లోని అన్ని ఫైళ్లు డౌన్‌లోడ్ చేసుకోవచ్చు. సబ్‌టైటిల్స్ వీడియోలో బర్న్
      చేయబడ్డాయి; అదనంగా .srt ఫైల్ YouTube సబ్‌టైటిల్ ఎడిటర్‌లో వాడుకోవచ్చు.<br>
      This page serves the export folder. Use the red button, or open
      <code>/files/&lt;filename&gt;?dl=1</code> directly.
    </footer>
  </div>
</div>
</div></body></html>"""


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, *a):
        pass

    def _send(self, body, ctype, status=200, extra=None):
        self.send_response(status)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split('?', 1)[0]
        query = self.path.split('?', 1)[1] if '?' in self.path else ''
        if path in ('/', '/index.html'):
            return self._send(page().encode(), 'text/html; charset=utf-8')

        m = re.fullmatch(r'/files/([A-Za-z0-9._-]+)', path)
        if not m or m.group(1) not in FILES:
            return self._send(b'not found', 'text/plain', 404)
        name = m.group(1)
        full = os.path.join(ROOT, name)
        size = os.path.getsize(full)
        ctype = FILES[name]
        extra = {}
        if 'dl=1' in query:
            extra['Content-Disposition'] = f'attachment; filename="{name}"'

        # Range support: without it the inline player cannot seek.
        rng = self.headers.get('Range', '')
        start, end = 0, size - 1
        status = 200
        rm = re.fullmatch(r'bytes=(\d*)-(\d*)', rng.strip())
        if rm:
            if rm.group(1):
                start = int(rm.group(1))
                end = int(rm.group(2)) if rm.group(2) else size - 1
            else:                                   # suffix range: last N bytes
                start = max(0, size - int(rm.group(2) or 0))
            end = min(end, size - 1)
            if start > end:
                return self._send(b'', ctype, 416,
                                  {'Content-Range': f'bytes */{size}'})
            status = 206
            extra['Content-Range'] = f'bytes {start}-{end}/{size}'

        length = end - start + 1
        self.send_response(status)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(length))
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Cache-Control', 'no-store')
        for k, v in extra.items():
            self.send_header(k, v)
        self.end_headers()
        with open(full, 'rb') as fh:
            fh.seek(start)
            remaining = length
            while remaining > 0:
                chunk = fh.read(min(262144, remaining))
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    return
                remaining -= len(chunk)


if __name__ == '__main__':
    print(f'serving {ROOT} on http://0.0.0.0:{PORT}  ({SIZE:.1f} MB video)')
    ThreadingHTTPServer(('0.0.0.0', PORT), Handler).serve_forever()
