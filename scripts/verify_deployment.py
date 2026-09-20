"""Read-only deployment checks; --write-smoke adds one event and cancels it afterward."""
import argparse
import json
from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4

import httpx


def verify(base_url, write_smoke=False):
    checks = []
    with httpx.Client(base_url=base_url.rstrip('/'), timeout=60, follow_redirects=True) as client:
        def get(path, **kwargs):
            r = client.get(path, **kwargs)
            r.raise_for_status()
            return r.json()

        meta = get('/api/meta')
        assert meta['mode'] == 'api' and meta['persistent'] is True
        if '.vercel.app' in base_url:
            assert meta['storage'] == 'postgres', meta
        checks.append('Live API and persistent storage')
        for path, marker in [('/', 'schedule-workspace'), ('/guide.html', 'Rules and assumptions'), ('/app.js', 'checkVesselChange'), ('/audit.js', 'filterRows')]:
            r = client.get(path)
            r.raise_for_status()
            assert marker in r.text, (path, marker)
        checks.append('New interface, guide and measurement controls served')
        vessels = get('/api/vessels', params={'q': 'Clear Tern'})
        vessel = next(v for v in vessels if v['name'] == 'R/V Clear Tern')
        berths = get('/api/berths')
        face = next(b for b in berths if b['name'] == 'North Pier Face')
        body = {'vessel_id': vessel['id'], 'berth_id': face['id'], 'start': '2035-07-01', 'end': '2035-07-02'}
        r = client.post('/api/check', json=body)
        r.raise_for_status()
        assert r.json()['blocking'] and any(f['code'] == 'fit' for f in r.json()['findings']), r.text
        checks.append('Oversized vessel is refused by the read-only check')
        r = client.post('/api/check', json={**body, 'start': '2035-07-03'})
        assert r.status_code == 422, r.text
        checks.append('Reversed dates rejected')
        before = get('/api/vessels', params={'q': 'R/V Clear Tern'})
        preview = client.post(f"/api/vessels/{vessel['id']}/check-change", json={'length_ft': 130})
        preview.raise_for_status()
        assert 'token' in preview.json()['impact']
        assert before == get('/api/vessels', params={'q': 'R/V Clear Tern'})
        assert isinstance(get(f"/api/vessels/{vessel['id']}/changes"), list)
        checks.append('Measurement preview is read-only and review storage is available')
        assert isinstance(get('/api/annotations', params={'start': '2017-01-01', 'end': '2017-12-31'}), list)
        assert get('/api/audit')['totals']['reservations'] == 1982
        checks.append('Operational notes and fixed historical audit available')
        audit = get('/data/audit.json')
        rows = audit['findings']
        assert sum(r['category'] == 'fit' for r in rows) == 9
        assert sum(r['category'] == 'unverifiable' for r in rows) == 12
        closure = [r for r in rows if r['category'] == 'closure']
        assert len(closure) == 1 and closure[0]['start'] == '2017-07-11' and closure[0]['end'] == '2017-07-15'
        checks.append('Filterable audit evidence reconciles: nine fit findings, twelve shared unknown days, one closure overlap')

        if write_smoke:
            day = date.today() + timedelta(days=5000)
            dates = {'start': day.isoformat(), 'end': day.isoformat()}
            occupied = {r['berth_id'] for r in get('/api/reservations', params=dates)}
            berth = next(b for b in berths if b['id'] not in occupied and b['length_ft']
                         and (not b['active_from'] or b['active_from'] <= dates['start'])
                         and (not b['active_to'] or b['active_to'] >= dates['end']))
            event = {**dates, 'berth_id': berth['id'], 'kind': 'event', 'title': f'Deployment QA {uuid4().hex[:8]}'}
            saved_id = None
            try:
                created = client.post('/api/reservations', json=event)
                assert created.status_code == 201, created.text
                saved_id = created.json()['reservation']['id']
                assert get(f'/api/reservations/{saved_id}')['title'] == event['title']
                refused = client.post('/api/reservations', json={**event, 'title': 'QA competing event (must not save)'})
                assert refused.status_code == 409, refused.text
                update = client.patch(f'/api/reservations/{saved_id}', json={'notes': 'Verification: edit saved and read back.'})
                update.raise_for_status()
                assert get(f'/api/reservations/{saved_id}')['notes'] == 'Verification: edit saved and read back.'
                checks.append(f'Create/read/conflicting-save refusal/edit/read passed for test event #{saved_id}')
            finally:
                if saved_id is not None:
                    cancelled = client.patch(f'/api/reservations/{saved_id}', json={'status': 'cancelled'})
                    cancelled.raise_for_status()
                    assert get(f'/api/reservations/{saved_id}')['status'] == 'cancelled'
                    checks.append(f'Test event #{saved_id} cancelled; its record remains as evidence')
        return {'base_url': base_url, 'storage': meta['storage'], 'write_smoke': write_smoke, 'passed': checks}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:8000')
    parser.add_argument('--write-smoke', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = verify(args.base_url, args.write_smoke)
    rendered = json.dumps(report, indent=2)
    if args.output:
        args.output.write_text(rendered + '\n')
    print(rendered)
