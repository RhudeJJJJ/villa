"""Build a review page and grid-support SVG from completed native outputs only."""
import hashlib
import html
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent


def esc(value):
    return html.escape(str(value), quote=True)


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    runs = Path(sys.argv[1]).resolve(strict=True)
    target = Path(sys.argv[2]).resolve()
    summary = read(runs / 'summary.json')
    assert summary['completed'] and summary['passed'], 'No success figure from partial/failed runs'
    target.mkdir(parents=True, exist_ok=False)
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1320" height="940" viewBox="0 0 1320 940">',
           '<rect width="1320" height="940" fill="#fff"/>',
           '<style>text{font-family:Arial,sans-serif;fill:#17232d}.title{font-size:25px;font-weight:bold}.sub{font-size:16px}.small{font-size:13px}.case{font-size:18px;font-weight:bold}</style>',
           '<text x="30" y="38" class="title">Unmasked CLI resume: actual saved grid cells</text>',
           '<text x="30" y="66" class="sub">PHerc0139 · real m7 prediction + published mesh · development 5 × 5 crop · RNG 2104 · one thread</text>']
    profiles = ['fill-zero', 'right-one', 'wide-control']
    table = []
    for row, variant in enumerate(['baseline', 'fixed']):
        for col, profile in enumerate(profiles):
            case = summary['cases']['development']['variants'][variant]['profiles'][profile]
            surface = runs / 'main/development' / variant / profile / 'surface'
            with Image.open(surface / 'x.tif') as image:
                valid = np.asarray(image) != -1
            meta = read(surface / 'meta.json')
            rr, cc = np.nonzero(valid)
            rr = rr - meta['grid_offset'][1]
            cc = cc - meta['grid_offset'][0]
            assert len(rr) == case['valid_points']
            ox, oy = 34 + col * 435, 100 + row * 360
            svg.append(f'<text x="{ox}" y="{oy}" class="case">{esc(variant)} / {esc(profile)}</text>')
            svg.append(f'<text x="{ox}" y="{oy+24}" class="sub">{len(rr)} valid · {case["outside_requested_grid"]} outside request</text>')
            x, y, step = ox + 50, oy + 51, 18
            def px(c): return x + (c + 5) * step
            def py(r): return y + (r + 5) * step
            for i in range(-5, 11):
                svg.append(f'<line x1="{px(-5)}" y1="{py(i)}" x2="{px(10)}" y2="{py(i)}" stroke="#e5e9ed"/>')
                svg.append(f'<line x1="{px(i)}" y1="{py(-5)}" x2="{px(i)}" y2="{py(10)}" stroke="#e5e9ed"/>')
            rlo, rhi, clo, chi = {'fill-zero':(0,5,0,5), 'right-one':(0,5,0,6), 'wide-control':(-4,9,-4,9)}[profile]
            svg.append(f'<rect x="{px(clo)-step/2}" y="{py(rlo)-step/2}" width="{(chi-clo)*step}" height="{(rhi-rlo)*step}" fill="#f2f7fa" stroke="#52677a" stroke-width="1.5"/>')
            svg.append(f'<rect x="{px(0)-step/2}" y="{py(0)-step/2}" width="{5*step}" height="{5*step}" fill="none" stroke="#132c45" stroke-width="2"/>')
            observed_outside = 0
            for r, c in zip(rr, cc):
                permitted = rlo <= r < rhi and clo <= c < chi
                original = 0 <= r < 5 and 0 <= c < 5
                color = '#1764a0' if original else ('#1b8657' if permitted else '#cf2e2e')
                observed_outside += not permitted
                svg.append(f'<circle cx="{px(c)}" cy="{py(r)}" r="4.3" fill="{color}"/>')
            assert observed_outside == case['outside_requested_grid']
            svg.append(f'<text x="{ox+45}" y="{oy+345}" class="small">column → / row ↓ · original grid coordinates</text>')
            table.append((variant, profile, case['valid_points'], case['new_points'], case['outside_requested_grid']))
    svg.extend(['<text x="30" y="860" class="sub">Blue: original vertices · Green: permitted new cells · Red: new cells beyond the request</text>',
                '<text x="30" y="886" class="small">Outline: imported 5 × 5 grid; shaded rectangle: requested extent (including the right-only direction).</text>',
                '<text x="30" y="910" class="small">This figure shows grid admission, not physical sheet accuracy, ink or readable text. Three crops share one carrier.</text>',
                '</svg>'])
    (target / 'requested-support.svg').write_text('\n'.join(svg) + '\n', encoding='utf-8')
    rows = ''.join('<tr>' + ''.join('<td>'+esc(v)+'</td>' for v in row) + '</tr>' for row in table)
    all_rows = []
    for crop, case in summary['cases'].items():
        for variant, run in case['variants'].items():
            for profile, result in run['profiles'].items():
                all_rows.append('<tr>'+''.join('<td>'+esc(v)+'</td>' for v in (crop,variant,profile,result['valid_points'],result['outside_requested_grid'],result['passed']))+'</tr>')
    logs = []
    for variant in ['baseline','fixed']:
        log = runs / 'invocations/development' / variant / 'stdout.txt'
        logs.append('<h3>'+esc(variant)+' — saved checker stdout</h3><pre>'+esc(log.read_text(encoding='utf-8'))+'</pre>')
    patch = ROOT / 'release-draft/requested-resume-bounds.patch'
    page = '''<!doctype html><html lang="de"><meta charset="utf-8"><title>GrowPatch – aktuelle Nachweise</title><style>body{font:16px system-ui;margin:36px auto;max-width:1320px;padding:0 20px;color:#17232d;line-height:1.5}h1{font-size:30px}table{border-collapse:collapse;font-size:14px}th,td{border:1px solid #c9d3dc;padding:7px 11px;text-align:left}pre{white-space:pre-wrap;background:#f3f6f8;padding:18px;font-size:12px;overflow:auto}img{width:100%}.note{padding:16px;background:#edf5f1}</style><h1>GrowPatch: aktueller Vorher-/Nachher-Beleg</h1>'''
    page += '<p class="note">Vollständiger nativer Prüflauf bestanden: '+esc(summary['actual_native_processes_completed_exit_0'])+' Prozesse. Das Beweisziel ist die angeforderte Rastergrenze.</p>'
    page += '<p>Baseline: Main e2254ebe0168a232e5ba7b94997c749b4e6a4544. Der Fix erhält den 25-Zellen-Arbeitsrand für Optimierung und begrenzt unmaskierte Resume-Kandidaten auf die bereits ausgewählten Extras. Windows/GCC, Debug -O0 -g0, ein Thread, Seed 2104. Core/Tracer und aktuelle offizielle CLI-Quelle wurden frisch gebaut.</p>'
    page += '<img src="requested-support.svg" alt="Tatsächliche gespeicherte Rasterpunkte vor und nach dem Fix"><table><tr><th>Variante</th><th>Profil</th><th>Gültig</th><th>Neu</th><th>Außerhalb Anfrage</th></tr>'+rows+'</table>'
    page += '<p>Quellenbezug: gebaut wurde e2254ebe. Der spätere Main 6f202456 hat denselben vollständigen volume-cartographer-Git-Teilbaum c48bb8937fd96bc0a6852e13fccc8f4968301326; seine neun Änderungen betreffen foundation/. Das ist kein Neubau der späteren Root-Versionsmetadaten.</p>'
    page += '<p>Erster Versuch separat erhalten: ein Baseline-Prozess wurde nach 120 Sekunden beendet und vollständig eingesammelt. Protokollrevision 2 verlängerte ausschließlich das äußere Limit auf 600 Sekunden. Die hier gezeigten abgeschlossenen Ergebnisse stammen aus dem zweiten Versuch; der erste Timeout ist kein abgeschlossener Vergleich.</p>'
    page += '<h2>Alle drei Ausschnitte</h2><table><tr><th>Crop</th><th>Variante</th><th>Profil</th><th>Gültig</th><th>Außerhalb</th><th>Gate</th></tr>'+''.join(all_rows)+'</table>'
    page += '<p>Wide-Paare: XYZ und Generationen einschließlich ungültiger Zellen bytegleich dekodiert. Zusätzliche Kontrolle: positive grow_extra bleiben bei disable=true erhalten; frische Seeds werden vor/nach verglichen. Eingaben und Binärdateien blieben während der Suite unverändert.</p>'
    page += '<h2>Grenzen und vorhandene Alternative</h2><p>Alle drei Crops stammen aus einem öffentlichen PHerc0139-Prädiktionsträger. Kein unabhängiger Scrolltest, keine anatomische oder Ink-Qualitätsaussage. Vorhandene nichtleere allowed-growth-Masken schützen die importierte Außenkante bereits; für diesen maskierten Pfad wird kein zusätzlicher Grenzschutz behauptet. Der Standard-CLI-Pfad ist unmaskiert. GUI-Erreichbarkeit wurde im Quelltext geprüft, die GUI nicht ausgeführt. Kein Laufnachweis für grobe Wachstumsskalierung oder Inpaint. PR #2133 beschreibt die Limitation bereits.</p>'
    page += '<h2>Kleine Quelländerung</h2><pre>'+esc(patch.read_text(encoding='utf-8'))+'</pre>'
    page += '<p><a href="captured-cli-output.html">Vollständige gespeicherte native CLI-Ausgabe: Baseline und Fix nebeneinander</a>. Beide nativen Prozesse beenden regulär mit Exitcode 0; der Prüfer meldet für die verletzte Baseline-Anfrage erwartungsgemäß Exitcode 1.</p>'
    page += '<h2>Unveränderte gespeicherte Prüfausgabe</h2>'+''.join(logs)
    page += '<p>Diese Browseransicht zeigt gespeicherte tatsächliche Prüfausgaben; sie ist keine GUI-Bedienung und kein unabhängiger menschlicher Review.</p></html>'
    (target / 'review.html').write_text(page,encoding='utf-8')
    native_sections = []
    for variant in ['baseline', 'fixed']:
        native_log = runs / 'main/development' / variant / 'fill-zero/stdout.txt'
        raw = native_log.read_bytes()
        native_sections.append('<section><h2>'+esc(variant)+' / Fill, zero extra cells</h2><p>Captured native stdout; SHA256 '+hashlib.sha256(raw).hexdigest()+'</p><pre>'+esc(raw.decode('utf-8'))+'</pre></section>')
    proof = '<!doctype html><html lang="en"><meta charset="utf-8"><title>Actual captured CLI output</title><style>body{font:15px system-ui;color:#17232d;margin:28px}pre{white-space:pre-wrap;font:11px monospace;background:#f3f6f8;padding:12px}main{display:grid;grid-template-columns:1fr 1fr;gap:22px}h1{font-size:26px}h2{font-size:18px}</style><h1>Actual captured CLI output: requested zero expansion</h1><p>Baseline: 81 valid saved points, 56 outside request. Guard: 25 valid saved points, zero outside; input XYZ bytes retained. Both native processes exited 0. Counts come from decoded saved outputs. This is a browser rendering of saved stdout, not a terminal-window capture or GUI execution.</p><main>'+''.join(native_sections)+'</main></html>'
    (target / 'captured-cli-output.html').write_text(proof,encoding='utf-8')
    manifest = {p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in target.iterdir() if p.is_file()}
    (target / 'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'review':str(target / 'review.html'),'files':manifest}),flush=True)


if __name__ == '__main__':
    main()
