"""Set up a local Metabase dashboard against the built PostgreSQL warehouse.

Uses Metabase v0.56 API. Saves local credentials only in ignored .env.
Reruns update the named project questions and dashboard instead of duplicating them.
"""
import json
import os
from pathlib import Path
import secrets
import sys
import urllib.parse
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.local_config import load_local_env, save_local_setting
from scripts.pipeline import connect


class Metabase:
    def __init__(self, base):
        self.base = base.rstrip('/')
        self.session = None

    def call(self, method, path, payload=None):
        headers = {'Content-Type': 'application/json'}
        if self.session:
            headers['X-Metabase-Session'] = self.session
        data = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(self.base + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                body = response.read()
                return json.loads(body) if body else {}
        except urllib.error.HTTPError as error:
            # Avoid dumping request payloads, which may contain local credentials.
            message = error.read().decode()[:500]
            raise RuntimeError(f'{method} {path}: HTTP {error.code}: {message}') from None

    def find(self, name, model):
        response = self.call('GET', '/api/search?q=' + urllib.parse.quote(name))
        return next((r for r in response.get('data', []) if r.get('name') == name and r.get('model') == model), None)


def main():
    load_local_env(ROOT)
    base = os.getenv('METABASE_URL', 'http://localhost:23000')
    if urllib.parse.urlparse(base).hostname not in ('localhost', '127.0.0.1'):
        raise ValueError('This bootstrap script is scoped to local Metabase only.')
    mb = Metabase(base)
    props = mb.call('GET', '/api/session/properties')
    email = os.getenv('METABASE_ADMIN_EMAIL', 'sparkify.admin@example.com')
    # v0.56 may retain setup-token after initialization; has-user-setup is authoritative.
    if not props.get('has-user-setup', False):
        if not props.get('setup-token'):
            raise RuntimeError('Metabase is not ready for initial setup.')
        password = 'Dw!9' + secrets.token_urlsafe(24)
        setup = mb.call('POST', '/api/setup', {
            'token': props['setup-token'],
            'user': {'email': email, 'first_name': 'Sparkify', 'last_name': 'Local Admin', 'password': password},
            'prefs': {'site_name': 'Sparkify Music Analytics', 'site_locale': 'en'}})
        save_local_setting(ROOT, 'METABASE_ADMIN_EMAIL', email)
        save_local_setting(ROOT, 'METABASE_ADMIN_PASSWORD', password)
        mb.session = setup['id']
    else:
        if not os.getenv('METABASE_ADMIN_PASSWORD'):
            raise RuntimeError('Existing Metabase: set local admin credentials in .env before bootstrapping.')
        mb.session = mb.call('POST', '/api/session', {'username': email, 'password': os.environ['METABASE_ADMIN_PASSWORD']})['id']

    # Give BI access to analytics only, not raw names or source logs.
    bi_password = os.getenv('METABASE_PG_PASSWORD') or secrets.token_urlsafe(32)
    save_local_setting(ROOT, 'METABASE_PG_PASSWORD', bi_password)
    import psycopg.sql
    con = connect('postgres', ROOT / 'warehouse' / 'sparkify.duckdb')
    with con:
        with con.cursor() as cur:
            cur.execute("select 1 from pg_roles where rolname='sparkify_bi'")
            if not cur.fetchone():
                cur.execute(psycopg.sql.SQL('create role sparkify_bi login password {}').format(psycopg.sql.Literal(bi_password)))
            cur.execute('grant usage on schema analytics to sparkify_bi')
            cur.execute('grant select on all tables in schema analytics to sparkify_bi')
            cur.execute('alter default privileges in schema analytics grant select on tables to sparkify_bi')

    databases = mb.call('GET', '/api/database')['data']
    db = next((d for d in databases if d['name'] == 'Sparkify PostgreSQL'), None)
    if db is None:
        db = mb.call('POST', '/api/database', {'name': 'Sparkify PostgreSQL', 'engine': 'postgres',
            'details': {'host': 'postgres', 'port': 5432, 'dbname': os.getenv('PGDATABASE', 'sparkify'),
                        'user': 'sparkify_bi', 'password': bi_password, 'ssl': False,
                        'schema-filters-type': 'inclusion', 'schema-filters-patterns': 'analytics'},
            'is_full_sync': True, 'auto_run_queries': True})

    collection = mb.find('Sparkify Warehouse', 'collection')
    if not collection:
        collection = mb.call('POST', '/api/collection', {'name': 'Sparkify Warehouse', 'color': '#D86B4B',
            'description': 'Verified November 2018 Sparkify sample. All event times are UTC.'})
    specs = [
        ('Monthly active listeners', 'select mau from analytics.rpt_monthly_kpis', 'scalar', {}, 0, 0, 8, 4),
        ('Songplays', 'select sum(songplays) as songplays from analytics.rpt_daily_kpis', 'scalar', {}, 0, 8, 8, 4),
        ('Played track hours', 'select round(sum(played_track_hours)::numeric,2) as track_hours from analytics.rpt_daily_kpis', 'scalar', {}, 0, 16, 8, 4),
        ('Daily active listeners (UTC)', 'select event_date,dau from analytics.rpt_daily_kpis order by event_date', 'line', {'graph.dimensions': ['event_date'], 'graph.metrics': ['dau'], 'graph.colors': ['#D86B4B']}, 4, 0, 16, 8),
        ('Free vs Paid track hours', 'select subscription_key, sum(played_track_hours) as track_hours from analytics.rpt_listening_by_membership group by subscription_key order by subscription_key', 'bar', {'graph.dimensions': ['subscription_key'], 'graph.metrics': ['track_hours'], 'graph.colors': ['#265B59']}, 4, 16, 8, 8),
        ('Songplays by hour (UTC)', 'select hour_utc, sum(songplays) as songplays from analytics.rpt_listening_heatmap group by hour_utc order by hour_utc', 'bar', {'graph.dimensions': ['hour_utc'], 'graph.metrics': ['songplays'], 'graph.colors': ['#265B59']}, 12, 0, 12, 8),
        ('Top artists', "select a.artist_name,count(*) as songplays from analytics.fact_user_events f join analytics.dim_artist a on f.artist_key=a.artist_key where f.is_songplay=1 group by a.artist_name order by songplays desc,a.artist_name limit 10", 'bar', {'graph.dimensions': ['artist_name'], 'graph.metrics': ['songplays'], 'graph.show_values': True, 'graph.x_axis.labels_enabled': True, 'graph.colors': ['#D86B4B']}, 12, 12, 12, 8),
        ('Engagement screening (not churn)', 'select watchlist_reason,count(*) as accounts from analytics.rpt_engagement_watchlist group by watchlist_reason order by accounts desc', 'table', {}, 20, 0, 12, 6),
        ('Observed subscription submissions', 'select sum(upgrade_submissions) as upgrade_submissions,sum(downgrade_submissions) as downgrade_submissions from analytics.rpt_daily_kpis', 'table', {}, 20, 12, 12, 6),
    ]
    cards = []
    for name, sql, display, settings, row, col, sx, sy in specs:
        existing = mb.find(name, 'card')
        payload = {'name': name, 'collection_id': collection['id'], 'display': display,
            'description': 'Source: supplied Sparkify ZIP sample, November 2018 UTC. Track hours sum song lengths; engagement rules have no validated churn labels.',
            'dataset_query': {'database': db['id'], 'type': 'native', 'native': {'query': sql, 'template-tags': {}}},
            'visualization_settings': settings}
        card = mb.call('PUT' if existing else 'POST', '/api/card/' + str(existing['id']) if existing else '/api/card', payload)
        # Execute each saved question, not merely create its metadata.
        result = mb.call('POST', f"/api/card/{card['id']}/query", {})
        if result.get('status') != 'completed':
            raise RuntimeError(f'Question execution failed: {name}')
        cards.append((card, row, col, sx, sy))
    name = 'Sparkify Music Streaming Analytics'
    dashboard = mb.find(name, 'dashboard')
    if dashboard:
        dashboard = mb.call('GET', f"/api/dashboard/{dashboard['id']}")
    else:
        dashboard = mb.call('POST', '/api/dashboard', {'name': name, 'collection_id': collection['id'],
            'description': 'November 2018 UTC. Played track hours are sums of track lengths. Engagement screening is an unvalidated rule, not churn prediction.'})
    prior = {c['card_id']: c['id'] for c in dashboard.get('dashcards', [])}
    dashcards = [{'id': prior.get(card['id'], -(i + 1)), 'card_id': card['id'],
        'row': row, 'col': col, 'size_x': sx, 'size_y': sy,
        'series': [], 'parameter_mappings': [], 'visualization_settings': {}}
        for i, (card, row, col, sx, sy) in enumerate(cards)]
    mb.call('PUT', f"/api/dashboard/{dashboard['id']}", {'dashcards': dashcards, 'width': 'full'})
    verified = mb.call('GET', f"/api/dashboard/{dashboard['id']}")
    assert len(verified['dashcards']) == len(specs)
    evidence = {'url': f"{base}/dashboard/{dashboard['id']}", 'dashboard_id': dashboard['id'],
        'database_id': db['id'], 'questions': [{'id': card['id'], 'name': card['name'], 'query_status': 'completed'} for card, *_ in cards],
        'database_role': 'sparkify_bi (analytics SELECT only)', 'credentials': 'Stored locally in ignored .env; never committed'}
    report = ROOT / 'reports' / 'metabase_dashboard.json'
    report.write_text(json.dumps(evidence, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    main()
