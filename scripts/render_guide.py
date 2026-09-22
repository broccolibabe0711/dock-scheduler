"""Render the report's limited Markdown vocabulary as self-contained HTML."""
from pathlib import Path
import html
import re
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parents[1]

def inline(text):
    text = html.escape(text)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\[([^\]]+)\]\(([^ )]+)\)', r'<a href="\2">\1</a>', text)
    return text

def slug(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')

def render(source):
    lines = source.splitlines()
    body, toc, i = [], [], 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        m = re.match(r'^(#{1,3}) (.+)$', line)
        if m:
            level, title = len(m[1]), m[2]
            anchor = slug(title)
            if level == 2:
                toc.append((anchor, title))
            body.append(f'<h{level} id="{anchor}">{inline(title)}</h{level}>')
            i += 1
        elif line.startswith('```'):
            code = []
            i += 1
            while i < len(lines) and not lines[i].startswith('```'):
                code.append(lines[i])
                i += 1
            i += 1
            body.append('<pre><code>' + html.escape('\n'.join(code)) + '</code></pre>')
        elif line.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].startswith('|'):
                cells = [cell.strip() for cell in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r':?-+:?', cell) for cell in cells):
                    rows.append(cells)
                i += 1
            head = '<thead><tr>' + ''.join(f'<th scope="col">{inline(c)}</th>' for c in rows[0]) + '</tr></thead>'
            data = []
            for row in rows[1:]:
                data.append('<tr>' + ''.join(f'<td data-label="{html.escape(rows[0][j], quote=True)}">{inline(c)}</td>' for j, c in enumerate(row)) + '</tr>')
            body.append('<div class="table-wrap"><table>' + head + '<tbody>' + ''.join(data) + '</tbody></table></div>')
        elif re.match(r'^(\d+\. |\- )', line):
            kind = 'ol' if line[0].isdigit() else 'ul'
            items = []
            pattern = r'^\d+\. ' if kind == 'ol' else r'^\- '
            while i < len(lines) and re.match(pattern, lines[i]):
                items.append('<li>' + inline(re.sub(pattern, '', lines[i])) + '</li>')
                i += 1
            body.append(f'<{kind}>' + ''.join(items) + f'</{kind}>')
        else:
            para = [line]
            i += 1
            while i < len(lines) and lines[i].strip() and not re.match(r'^(#|\||\d+\. |\- )', lines[i]):
                para.append(lines[i])
                i += 1
            body.append('<p>' + inline(' '.join(para)) + '</p>')
    return '\n'.join(body), toc

CSS = '''
:root{--ink:#182d39;--muted:#566772;--teal:#006b68;--line:#d4e0e4;--paper:#fff;--wash:#eef3f4;color-scheme:light}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:28px}
body{margin:0;background:var(--wash);color:var(--ink);font:16px/1.72 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
.top{background:#142e3c;color:#fff;padding:20px max(28px,calc((100vw - 1380px)/2));display:flex;align-items:center;justify-content:space-between;gap:16px}
.brand{font-size:16px;font-weight:700;letter-spacing:.03em}.brand span{display:block;font-size:11px;font-weight:500;letter-spacing:.17em;text-transform:uppercase;color:#9dcaca;margin-top:3px}
.top nav{display:flex;gap:18px;flex-wrap:wrap}.top a{color:#fff;font-size:14px;text-decoration:none}.top a[aria-current]{border-bottom:2px solid #73c6bf}
.layout{max-width:1380px;margin:auto;padding:38px 28px 72px;display:grid;grid-template-columns:220px minmax(0,1fr);gap:38px;align-items:start}
.toc{position:sticky;top:24px;font-size:13px;line-height:1.55}.toc h2{font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);margin:0 0 16px}.toc a{display:block;color:var(--muted);padding:7px 0;text-decoration:none}.toc a:hover{color:var(--teal)}
main{background:var(--paper);padding:46px 50px;border:1px solid var(--line);border-radius:14px;min-width:0;box-shadow:0 8px 30px #16384406}
.tools{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:32px;font-size:12px}.tools a,.tools button{font:inherit;color:var(--teal);border:1px solid #bdd4d1;background:#f5faf9;border-radius:6px;padding:8px 12px;text-decoration:none;cursor:pointer}
h1,h2,h3{line-height:1.2;letter-spacing:-.025em}h1{font-size:39px;margin:0 0 16px;max-width:760px;font-weight:750}h1+p{font-size:13px;color:var(--muted);margin:0 0 30px}
h2{font-size:26px;margin:54px 0 21px;padding-top:28px;border-top:1px solid var(--line)}h3{font-size:20px;margin:32px 0 12px}p{margin:14px 0 19px}h2+p,h3+p{margin-top:0}
a{color:var(--teal);text-decoration-thickness:1px;text-underline-offset:3px;overflow-wrap:anywhere}a:hover{color:#043f49}a:focus-visible,button:focus-visible{outline:3px solid #c8752b;outline-offset:4px}
pre{overflow:auto;padding:18px;background:#eef3f5;border-radius:8px;line-height:1.5}pre code{padding:0;white-space:pre}strong{font-weight:700}code{font-size:.86em;padding:2px 5px;border-radius:4px;background:#eef3f5;overflow-wrap:anywhere}li{padding:0 0 10px 5px}ul,ol{padding-left:24px}
.table-wrap{border:1px solid var(--line);border-radius:8px;overflow:hidden;margin:22px 0 26px}table{width:100%;border-collapse:collapse;table-layout:fixed;font-size:14px;line-height:1.65}th,td{padding:17px 19px;text-align:left;vertical-align:top;overflow-wrap:anywhere}th{background:#183c47;color:#fff;font-weight:650;font-size:13px}th:first-child,td:first-child{width:34%}td{border-top:1px solid var(--line)}tbody tr:nth-child(even){background:#f6f9f9}td:first-child{color:#244753;font-weight:550}
.footer{font-size:12px;color:var(--muted);border-top:1px solid var(--line);padding-top:20px;margin-top:44px}
@media(max-width:1100px){.layout{grid-template-columns:175px minmax(0,1fr);gap:24px}main{padding:36px 30px}h1{font-size:34px}.toc{font-size:12px}}
@media(max-width:800px){.layout{display:block;padding:20px 16px 48px}.toc{position:static;margin-bottom:22px}.toc h2{margin-bottom:8px}.toc a{display:inline-block;margin-right:16px;padding:4px 0}.top{padding:18px 20px}.top nav{gap:12px}main{padding:28px 24px}h1{font-size:30px}h2{font-size:23px;margin-top:38px}}
@media(max-width:550px){body{font-size:15px}.top{align-items:flex-start;flex-direction:column}main{padding:25px 18px}.table-wrap{border:0}table,tbody,tr,td{display:block;width:100%}thead{display:none}tr{border:1px solid var(--line);border-radius:8px;overflow:hidden;margin-bottom:14px}td:first-child{width:100%;background:#eaf2f2}td{border:0;padding:14px 16px}td+td{border-top:1px solid var(--line)}td::before{content:attr(data-label);display:block;font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin-bottom:7px}h1{font-size:28px}}
@media print{@page{size:A4;margin:17mm}body{background:white;font-size:10pt;line-height:1.5}.top,.toc,.tools{display:none}.layout{display:block;margin:0;padding:0;max-width:none}main{border:0;box-shadow:none;border-radius:0;padding:0}h1{font-size:25pt}h2{font-size:17pt;margin-top:24pt;padding-top:12pt}h3{font-size:13pt}h1,h2,h3{break-after:avoid}table{font-size:9pt;line-height:1.4}th,td{padding:8pt}tr{break-inside:avoid}th{background:#e8eff0;color:var(--ink)}.table-wrap{overflow:visible;border-radius:0}a{color:#164e5c}p,li{orphans:3;widows:3}.footer{font-size:8pt}}
'''

class Validator(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.links = []
        self.tables = 0
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if 'id' in a:
            assert a['id'] not in self.ids, a['id']
            self.ids.add(a['id'])
        if tag == 'a': self.links.append(a.get('href', ''))
        if tag == 'table': self.tables += 1

def build(source_name, stem, title):
    source = (ROOT / 'docs' / source_name).read_text()
    body, toc = render(source)
    nav = ''.join(f'<a href="#{anchor}">{html.escape(label)}</a>' for anchor, label in toc)
    page = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Dock Scheduler · {html.escape(title)}</title><style>{CSS}</style></head><body>
    <header class="top"><div class="brand">Dock Scheduler<span>{html.escape(title)}</span></div><nav><a href="index.html#harbor">Harbor</a><a href="guide.html">Guide</a><a href="acceptance.html">Acceptance tests</a></nav></header>
    <div class="layout"><aside class="toc"><h2>In this document</h2><nav aria-label="Contents">{nav}</nav></aside><main><div class="tools"><a href="{stem}.md" download>Download Markdown</a><button onclick="window.print()" type="button">Print / Save PDF</button></div>{body}</main></div></body></html>'''
    validator = Validator()
    validator.feed(page)
    for href in validator.links:
        if href.startswith('#'):
            assert href[1:] in validator.ids, href
    (ROOT / 'site' / f'{stem}.html').write_text(page)
    (ROOT / 'site' / f'{stem}.md').write_text(source)
    print(f'Built site/{stem}.html and site/{stem}.md')

if __name__ == '__main__':
    build('USER_GUIDE.md', 'guide', 'Guide and assumptions')
    build('ACCEPTANCE_TESTS.md', 'acceptance', 'Acceptance tests')
    build('SUBMISSION.md', 'submission', 'Submission guide')
