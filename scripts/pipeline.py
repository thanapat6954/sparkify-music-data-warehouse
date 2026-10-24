"""Load local Sparkify archives, build dbt models, test and export evidence.

No ZIP extraction, credentials in files, or external API keys are required.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.local_config import load_local_env

EVENT_COLUMNS = {
    'event_id': 'varchar primary key', 'event_ts': 'timestamp not null',
    'user_id': 'varchar', 'gender': 'varchar', 'membership_level': 'varchar not null',
    'location': 'varchar', 'session_id': 'bigint', 'item_in_session': 'integer',
    'song': 'varchar', 'artist': 'varchar', 'length_seconds': 'double precision',
    'page': 'varchar not null', 'auth': 'varchar', 'status': 'integer',
    'user_agent': 'varchar', 'device_family': 'varchar', 'browser_family': 'varchar',
    'source_file': 'varchar not null',
}
SONG_COLUMNS = {
    'song_id': 'varchar primary key', 'artist_id': 'varchar',
    'title': 'varchar', 'artist_name': 'varchar', 'duration': 'double precision',
    'year': 'integer', 'artist_location': 'varchar',
}


def read_archive(path):
    with ZipFile(path) as archive:
        for name in sorted(archive.namelist()):
            if not name.endswith('.json') or '__MACOSX' in name or Path(name).name.startswith('._'):
                continue
            with archive.open(name) as source:
                for number, line in enumerate(source, 1):
                    if line.strip():
                        yield name, number, json.loads(line)


def ua_families(ua):
    ua = ua or ''
    device = next((name for token, name in [
        ('iPad', 'tablet'), ('iPhone', 'mobile'), ('Android', 'mobile'),
        ('Windows', 'desktop'), ('Macintosh', 'desktop'), ('X11', 'desktop')
        ] if token in ua), 'unknown')
    browser = next((name for token, name in [
        ('Edg/', 'Edge'), ('OPR/', 'Opera'), ('Chrome/', 'Chrome'),
        ('Firefox/', 'Firefox'), ('Safari/', 'Safari'), ('Trident/', 'Internet Explorer')
        ] if token in ua), 'unknown')
    return device, browser


def canonical_event(record):
    encoded = json.dumps(record, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(encoded.encode()).hexdigest()


def connect(target, db_path):
    if target == 'duckdb':
        import duckdb
        db_path.parent.mkdir(parents=True, exist_ok=True)
        con = duckdb.connect(str(db_path))
        con.execute("set timezone='UTC'")
        return con
    import psycopg
    con = psycopg.connect(
        host=os.getenv('PGHOST', 'localhost'), port=os.getenv('PGPORT', '25432'),
        dbname=os.getenv('PGDATABASE', 'sparkify'), user=os.getenv('PGUSER', 'sparkify'),
        password=os.environ['PGPASSWORD'], options='-c timezone=UTC', connect_timeout=10)
    return con


def load_raw(target, db_path, data_dir):
    """Append new content keys transactionally; unchanged replays are idempotent.

    Source corrections with changed content produce new events because the source
    has no authoritative event ID. See docs/modeling.md for this limitation.
    """
    con = connect(target, db_path)
    cur = con.cursor()
    try:
        print('Reading and deduplicating source archives...', flush=True)
        if target == 'duckdb':
            cur.execute('begin transaction')
        cur.execute('create schema if not exists raw')
        for table, columns in [('events', EVENT_COLUMNS), ('songs', SONG_COLUMNS)]:
            definitions = ', '.join(f'{k} {v}' for k, v in columns.items())
            cur.execute(f'create table if not exists raw.{table} ({definitions})')
        seen_events = {r[0] for r in cur.execute('select event_id from raw.events').fetchall()} if target == 'duckdb' else None
        if seen_events is None:
            cur.execute('select event_id from raw.events')
            seen_events = {r[0] for r in cur.fetchall()}
        cur.execute('select song_id from raw.songs')
        seen_songs = {r[0] for r in cur.fetchall()}
        events, songs = [], []
        for name, number, r in read_archive(data_dir / 'log_data.zip'):
            event_id = canonical_event(r)
            if event_id in seen_events:
                continue
            user_id = str(r.get('userId') or '').strip() or None
            if r.get('ts') is None or not r.get('page'):
                raise ValueError(f'Missing timestamp or page at {name}:{number}')
            duration = r.get('length')
            if duration is not None and duration < 0:
                raise ValueError(f'Negative duration at {name}:{number}')
            device, browser = ua_families(r.get('userAgent'))
            events.append((event_id, datetime.fromtimestamp(r['ts'] / 1000, timezone.utc).replace(tzinfo=None),
                user_id, r.get('gender'), r.get('level') or 'unknown', r.get('location'),
                r.get('sessionId'), r.get('itemInSession'), r.get('song'), r.get('artist'), duration,
                r['page'], r.get('auth'), r.get('status'), r.get('userAgent'), device, browser,
                f'{name}:{number}'))
            seen_events.add(event_id)
        for name, number, r in read_archive(data_dir / 'song_data.zip'):
            if r['song_id'] not in seen_songs:
                songs.append(tuple(r.get(k) for k in SONG_COLUMNS))
                seen_songs.add(r['song_id'])
        placeholder = '?' if target == 'duckdb' else '%s'
        for table, columns, rows in [('events', EVENT_COLUMNS, events), ('songs', SONG_COLUMNS, songs)]:
            if rows:
                print(f'Loading {len(rows):,} rows into raw.{table}...', flush=True)
                values = '(' + ','.join([placeholder] * len(columns)) + ')'
                if target == 'duckdb':
                    import pandas as pd
                    # Vectorized ingestion avoids per-value adapter type detection.
                    cur.register('incoming_batch', pd.DataFrame.from_records(rows, columns=list(columns)))
                    try:
                        cur.execute(f"insert into raw.{table} ({','.join(columns)}) select * from incoming_batch")
                    finally:
                        cur.unregister('incoming_batch')
                else:
                    cur.executemany(f"insert into raw.{table} ({','.join(columns)}) values {values}", rows)
        # Commit the cursor's transaction: DuckDB cursors use separate connections.
        if target == 'duckdb':
            cur.execute('commit')
        else:
            con.commit()
        return {'inserted_events': len(events), 'inserted_songs': len(songs)}
    except Exception:
        if target == 'duckdb':
            cur.execute('rollback')
        else:
            con.rollback()
        raise
    finally:
        cur.close()
        con.close()


def run_dbt(target, command, db_path, full_refresh=False):
    env = os.environ.copy()
    env['SPARKIFY_DUCKDB_PATH'] = str(db_path)
    env['DBT_SEND_ANONYMOUS_USAGE_STATS'] = 'false'
    args = [sys.executable, '-c', 'from dbt.cli.main import cli; cli()', command,
            '--project-dir', str(ROOT / 'dbt'), '--profiles-dir', str(ROOT / 'dbt'), '--target', target,
            '--target-path', str(db_path.parent / (db_path.stem + '_dbt_target'))]
    if full_refresh:
        args.append('--full-refresh')
    subprocess.run(args, check=True, cwd=ROOT, env=env)


def query(con, sql):
    cur = con.cursor()
    cur.execute(sql)
    names = [d[0] for d in cur.description]
    result = [dict(zip(names, row)) for row in cur.fetchall()]
    cur.close()
    return result


def export_results(target, db_path, output_dir):
    con = connect(target, db_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        reports = ['daily_kpis', 'monthly_kpis', 'listening_by_membership', 'listening_heatmap', 'top_artists', 'top_songs', 'engagement_watchlist']
        for report in reports:
            sql = f'select * from analytics.rpt_{report}'
            if report == 'engagement_watchlist':
                # No account identifiers in the committed report.
                sql = "select md5(user_key) as user_pseudonym, as_of_date, observed_days, current_7d_songplays, prior_7d_songplays, days_since_last_songplay, songplay_decline_fraction, watchlist_reason, interpretation from analytics.rpt_engagement_watchlist"
            rows = query(con, sql)
            if rows:
                with (output_dir / f'{report}.csv').open('w', encoding='utf-8', newline='') as handle:
                    writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                    writer.writeheader()
                    writer.writerows(rows)
        summary = {
            'source': query(con, 'select count(*) as events, min(event_ts) as first_event_utc, max(event_ts) as last_event_utc, count(distinct user_id) as identified_users from raw.events')[0],
            'catalog_rows': query(con, 'select count(*) as n from raw.songs')[0]['n'],
            'pages': query(con, 'select page, count(*) as events from raw.events group by page order by events desc'),
            'monthly': query(con, 'select * from analytics.rpt_monthly_kpis order by month'),
            'catalog_coverage': query(con, "select s.catalog_match_status, count(*) as songplays from analytics.fact_user_events f join analytics.dim_song s on f.song_key = s.song_key where f.is_songplay = 1 group by s.catalog_match_status"),
            'membership': query(con, 'select subscription_key, sum(songplays) as songplays, sum(played_track_hours) as played_track_hours from analytics.rpt_listening_by_membership group by subscription_key'),
            'watchlist': query(con, 'select watchlist_reason, count(*) as users from analytics.rpt_engagement_watchlist group by watchlist_reason'),
            'semantics': {'timezone': 'UTC; user local time is unavailable', 'duration': 'Sum of track lengths attached to NextSong, not verified listening time', 'churn': 'Unavailable: no cancellation labels in supplied data', 'watchlist': 'Heuristic engagement screening, not churn probability'},
        }
        (output_dir / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str) + '\n', encoding='utf-8')
        return summary
    finally:
        con.close()


def main():
    load_local_env(ROOT)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', choices=['duckdb', 'postgres'], default='duckdb')
    parser.add_argument('--data-dir', type=Path, default=ROOT / 'dataset' / 'dataset')
    parser.add_argument('--db-path', type=Path, default=ROOT / 'warehouse' / 'sparkify.duckdb')
    parser.add_argument('--output-dir', type=Path, default=None)
    parser.add_argument('--full-refresh', action='store_true')
    parser.add_argument('--load-only', action='store_true')
    args = parser.parse_args()
    if args.output_dir is None:
        args.output_dir = ROOT / 'reports' if args.target == 'duckdb' else ROOT / 'reports' / 'postgres'
    args.output_dir.mkdir(parents=True, exist_ok=True)
    loaded = load_raw(args.target, args.db_path.resolve(), args.data_dir.resolve())
    print(json.dumps(loaded), flush=True)
    if args.load_only:
        return
    run_dbt(args.target, 'build', args.db_path.resolve(), args.full_refresh)
    summary = export_results(args.target, args.db_path.resolve(), args.output_dir)
    artifact = args.db_path.resolve().parent / (args.db_path.stem + '_dbt_target') / 'run_results.json'
    if artifact.exists():
        results = json.loads(artifact.read_text(encoding='utf-8'))
        evidence = {'target': args.target, 'dbt_version': results['metadata']['dbt_version'],
                    'generated_at_utc': results['metadata']['generated_at'],
                    'raw_load': loaded,
                    'results': [{'unique_id': r['unique_id'], 'status': r['status']} for r in results['results']]}
        (args.output_dir / 'dbt_build_evidence.json').write_text(json.dumps(evidence, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary, indent=2, default=str), flush=True)


if __name__ == '__main__':
    main()
