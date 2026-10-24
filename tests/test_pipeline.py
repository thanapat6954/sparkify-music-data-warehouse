"""Behavioral regression checks using a clearly synthetic, temporary dataset."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile
from scripts.pipeline import canonical_event, load_raw, connect, run_dbt, query, ua_families


def write_zip(path, records):
    with ZipFile(path, 'w') as z:
        z.writestr('fixture.json', '\n'.join(json.dumps(r) for r in records))


class PipelineTests(unittest.TestCase):
    def test_identity_and_device(self):
        self.assertEqual(canonical_event({'a': 1, 'b': 2}), canonical_event({'b': 2, 'a': 1}))
        self.assertEqual(ua_families('Mozilla Windows Chrome/123'), ('desktop', 'Chrome'))

    def test_replay_late_arrival_and_membership_history(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            db = path / 'fixture.duckdb'
            target = os.getenv('SPARKIFY_TEST_TARGET', 'duckdb')
            def event(ts, level, item):
                return dict(ts=ts, userId='1', level=level, page='NextSong', song='Fixture song', artist='Fixture artist', length=120.0, sessionId=1, itemInSession=item)
            # A Free -> Paid -> Free sequence, intentionally arriving out of order.
            rows = [event(1541030400000, 'free', 1), event(1541203200000, 'free', 3)]
            write_zip(path / 'log_data.zip', rows + rows[:1])
            write_zip(path / 'song_data.zip', [dict(song_id='fixture', title='Fixture song', artist_name='Fixture artist', duration=120, year=2018)])
            self.assertEqual(load_raw(target, db, path)['inserted_events'], 2)
            self.assertEqual(load_raw(target, db, path)['inserted_events'], 0)
            run_dbt(target, 'build', db)
            con = connect(target, db)
            try:
                # A missing calendar day must exist as a zero-activity snapshot.
                gap = query(con, "select songplays from analytics.fact_user_day where event_date=date '2018-11-02'")
                self.assertEqual(gap, [{'songplays': 0}])
            finally:
                con.close()
            rows.append(event(1541116800000, 'paid', 2))
            write_zip(path / 'log_data.zip', rows)
            self.assertEqual(load_raw(target, db, path)['inserted_events'], 1)
            run_dbt(target, 'build', db)
            con = connect(target, db)
            try:
                history = query(con, "select membership_level from analytics.dim_user_subscription where user_id='1' order by valid_from")
                self.assertEqual([r['membership_level'] for r in history], ['free', 'paid', 'free'])
                result = query(con, 'select count(*) as n, sum(played_track_duration_seconds) as seconds from analytics.fact_user_events')[0]
                self.assertEqual(result, {'n': 3, 'seconds': 360.0})
                wrong = query(con, 'select f.event_id from analytics.fact_user_events f join analytics.dim_user_subscription h on f.subscription_history_key=h.subscription_history_key where f.subscription_key<>h.membership_level')
                self.assertEqual(wrong, [])
            finally:
                con.close()


if __name__ == '__main__':
    unittest.main()
