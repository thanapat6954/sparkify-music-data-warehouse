"""Set up a local Metabase dashboard against the built PostgreSQL warehouse.

Uses Metabase v0.56 API. Saves local credentials only in ignored .env.
Reruns update the named project questions and dashboard instead of duplicating them.
"""
import json
import os
from pathlib import Path
import re
import secrets
import sys
import urllib.parse
import urllib.request
import urllib.error
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.local_config import load_local_env, save_local_setting
from scripts.pipeline import connect

# Dashboard filters. Each maps to a native-query variable inside an optional [[...]] clause,
# so an empty filter removes the clause and the question shows the whole dataset.
FILTERS = {
    'start_date': ('Start date (UTC)', 'date', 'date/single', None, 'f.event_date >= {{start_date}}'),
    'end_date': ('End date (UTC)', 'date', 'date/single', None, 'f.event_date <= {{end_date}}'),
    'daypart': ('Time of day (UTC)', 'text', 'string/=', ['night', 'morning', 'afternoon', 'evening'], 't.daypart_utc = {{daypart}}'),
    'membership': ('Free / Paid', 'text', 'string/=', ['free', 'paid'], 'f.subscription_key = {{membership}}'),
}
ALL_FILTERS = list(FILTERS)
FACT = 'from analytics.fact_user_events f join analytics.dim_time t on f.time_key = t.time_key'
WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
# Questions replaced by filtered versions; archived so the collection holds no stale copies.
RETIRED = ['Monthly active listeners', 'Songplays by hour (UTC)']


def where(filters, songplays=True):
    clauses = ['f.is_songplay = 1'] if songplays else ['1 = 1']
    return 'where ' + clauses[0] + ''.join(f' [[and {FILTERS[name][4]}]]' for name in filters)


def heatmap_sql():
    hours = ', '.join(f'sum(case when t.hour_utc = {h} then 1 else 0 end) as "{h:02d}"' for h in range(24))
    label = ' '.join(f"when {i} then '{i} {d}'" for i, d in enumerate(WEEKDAYS, 1))
    return (f'select case t.iso_weekday {label} end as weekday, {hours} {FACT} {where(ALL_FILTERS)} '
            'group by t.iso_weekday order by t.iso_weekday')


def dashboard_specs():
    """(name, sql, display, visualization settings, filters, row, col, size_x, size_y)."""
    hours = [f'{h:02d}' for h in range(24)]
    heat = {'table.column_formatting': [{'columns': hours, 'type': 'range', 'colors': ['#FFFFFF', '#D86B4B'],
        'min_type': None, 'max_type': None, 'operator': '=', 'value': '', 'color': '#D86B4B', 'highlight_row': False}]}
    return [
        ('Active listeners', f"select count(distinct case when f.user_key <> 'unknown' then f.user_key end) as active_listeners {FACT} {where(ALL_FILTERS)}", 'scalar', {}, ALL_FILTERS, 0, 0, 8, 4),
        ('Songplays', f'select count(*) as songplays {FACT} {where(ALL_FILTERS)}', 'scalar', {}, ALL_FILTERS, 0, 8, 8, 4),
        ('Played track hours', f'select round(cast(sum(f.played_track_duration_seconds) / 3600.0 as numeric), 2) as track_hours {FACT} {where(ALL_FILTERS)}', 'scalar', {}, ALL_FILTERS, 0, 16, 8, 4),
        ('Daily active listeners (UTC)', f"select f.event_date, count(distinct case when f.user_key <> 'unknown' then f.user_key end) as dau {FACT} {where(ALL_FILTERS)} group by f.event_date order by f.event_date", 'line', {'graph.dimensions': ['event_date'], 'graph.metrics': ['dau'], 'graph.colors': ['#D86B4B']}, ALL_FILTERS, 4, 0, 16, 8),
        ('Free vs Paid track hours', f'select f.subscription_key, round(cast(sum(f.played_track_duration_seconds) / 3600.0 as numeric), 2) as track_hours {FACT} {where(ALL_FILTERS)} group by f.subscription_key order by f.subscription_key', 'bar', {'graph.dimensions': ['subscription_key'], 'graph.metrics': ['track_hours'], 'graph.colors': ['#265B59']}, ALL_FILTERS, 4, 16, 8, 8),
        ('Songplays heatmap: weekday x hour (UTC)', heatmap_sql(), 'table', heat, ALL_FILTERS, 12, 0, 24, 7),
        ('Top songs', f"select s.song_title || ' - ' || s.artist_name as song, count(*) as songplays {FACT} join analytics.dim_song s on f.song_key = s.song_key {where(ALL_FILTERS)} group by s.song_title, s.artist_name order by songplays desc, s.artist_name, s.song_title limit 10", 'row', {'graph.dimensions': ['song'], 'graph.metrics': ['songplays'], 'graph.show_values': True, 'graph.colors': ['#265B59']}, ALL_FILTERS, 19, 0, 12, 8),
        ('Top artists', f'select a.artist_name, count(*) as songplays {FACT} join analytics.dim_artist a on f.artist_key = a.artist_key {where(ALL_FILTERS)} group by a.artist_name order by songplays desc, a.artist_name limit 10', 'row', {'graph.dimensions': ['artist_name'], 'graph.metrics': ['songplays'], 'graph.show_values': True, 'graph.colors': ['#D86B4B']}, ALL_FILTERS, 19, 12, 12, 8),
        # Watchlist is a snapshot at the dataset's last day, so dashboard filters do not apply.
        ('Engagement screening (not churn)', 'select watchlist_reason,count(*) as accounts from analytics.rpt_engagement_watchlist group by watchlist_reason order by accounts desc', 'table', {}, [], 27, 0, 12, 6),
        ('Observed subscription submissions', f'select sum(f.is_upgrade_submission) as upgrade_submissions, sum(f.is_downgrade_submission) as downgrade_submissions {FACT} {where(ALL_FILTERS, songplays=False)}', 'table', {}, ALL_FILTERS, 27, 12, 12, 6),
    ]


def template_tags(sql):
    tags = {}
    for name in sorted(set(re.findall(r'\{\{(\w+)\}\}', sql))):
        label, kind, *_ = FILTERS[name]
        tags[name] = {'id': str(uuid.uuid5(uuid.NAMESPACE_URL, 'sparkify/' + name)), 'name': name,
                      'display-name': label, 'type': kind}
    return tags


def dashboard_parameters():
    params = []
    for name, (label, _, kind, values, _) in FILTERS.items():
        param = {'id': name, 'name': label, 'slug': name, 'type': kind,
                 'sectionId': 'date' if kind.startswith('date') else 'string'}
        if values:
            param.update(values_source_type='static-list', values_source_config={'values': values})
        params.append(param)
    return params


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
    specs = dashboard_specs()
    for name in RETIRED:
        old = mb.find(name, 'card')
        if old:
            mb.call('PUT', f"/api/card/{old['id']}", {'archived': True})
    cards = []
    for name, sql, display, settings, filters, row, col, sx, sy in specs:
        existing = mb.find(name, 'card')
        payload = {'name': name, 'collection_id': collection['id'], 'display': display,
            'description': 'Source: supplied Sparkify ZIP sample, November 2018 UTC. Track hours sum song lengths; engagement rules have no validated churn labels.',
            'dataset_query': {'database': db['id'], 'type': 'native', 'native': {'query': sql, 'template-tags': template_tags(sql)}},
            'visualization_settings': settings}
        card = mb.call('PUT' if existing else 'POST', '/api/card/' + str(existing['id']) if existing else '/api/card', payload)
        # Execute each saved question, not merely create its metadata.
        result = mb.call('POST', f"/api/card/{card['id']}/query", {})
        if result.get('status') != 'completed':
            raise RuntimeError(f'Question execution failed: {name}')
        cards.append((card, filters, row, col, sx, sy))
    name = 'Sparkify Music Streaming Analytics'
    dashboard = mb.find(name, 'dashboard')
    if dashboard:
        dashboard = mb.call('GET', f"/api/dashboard/{dashboard['id']}")
    else:
        dashboard = mb.call('POST', '/api/dashboard', {'name': name, 'collection_id': collection['id'],
            'description': 'November 2018 UTC. Played track hours are sums of track lengths. Engagement screening is an unvalidated rule, not churn prediction.'})
    prior = {c['card_id']: c['id'] for c in dashboard.get('dashcards', [])}
    dashcards = [{'id': prior.get(card['id'], -(i + 1)), 'card_id': card['id'],
        'row': row, 'col': col, 'size_x': sx, 'size_y': sy, 'series': [],
        'parameter_mappings': [{'parameter_id': f, 'card_id': card['id'], 'target': ['variable', ['template-tag', f]]} for f in filters],
        'visualization_settings': {}}
        for i, (card, filters, row, col, sx, sy) in enumerate(cards)]
    note = ('Filters use UTC event dates and hours. Time of day: night 00-05, morning 06-11, afternoon 12-17, evening 18-23. '
            'Free / Paid is the level at the time of each event. Engagement screening is a last-day snapshot and ignores filters.')
    dashcards.append({'id': -(len(cards) + 1), 'card_id': None, 'row': 33, 'col': 0, 'size_x': 24, 'size_y': 2,
        'series': [], 'parameter_mappings': [],
        'visualization_settings': {'virtual_card': {'name': None, 'display': 'text', 'visualization_settings': {}, 'dataset_query': {}, 'archived': False}, 'text': note}})
    mb.call('PUT', f"/api/dashboard/{dashboard['id']}", {'dashcards': dashcards, 'parameters': dashboard_parameters(), 'width': 'full'})
    verified = mb.call('GET', f"/api/dashboard/{dashboard['id']}")
    assert len(verified['dashcards']) == len(dashcards)
    assert {p['id'] for p in verified['parameters']} == set(FILTERS)
    # A filter must change the answer: Free + Paid songplays must add up to the unfiltered total.
    songplays = next(card for card, *_ in cards if card['name'] == 'Songplays')
    def songplays_for(level):
        params = [{'type': 'string/=', 'target': ['variable', ['template-tag', 'membership']], 'value': [level]}] if level else []
        return mb.call('POST', f"/api/card/{songplays['id']}/query", {'parameters': params})['data']['rows'][0][0]
    split = {level: songplays_for(level) for level in ('free', 'paid')}
    if split['free'] + split['paid'] != songplays_for(None):
        raise RuntimeError(f'Free/Paid filter does not reconcile: {split}')
    evidence = {'url': f"{base}/dashboard/{dashboard['id']}", 'dashboard_id': dashboard['id'],
        'database_id': db['id'], 'questions': [{'id': card['id'], 'name': card['name'], 'query_status': 'completed'} for card, *_ in cards],
        'filters': [label for label, *_ in FILTERS.values()], 'filter_check': {'songplays_' + k: v for k, v in split.items()},
        'database_role': 'sparkify_bi (analytics SELECT only)', 'credentials': 'Stored locally in ignored .env; never committed'}
    report = ROOT / 'reports' / 'metabase_dashboard.json'
    report.write_text(json.dumps(evidence, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    main()
