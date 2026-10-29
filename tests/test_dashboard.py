"""Dashboard questions run against a synthetic warehouse, with filters rendered as Metabase would."""
import json
import os
from pathlib import Path
import re
import tempfile
import unittest
from zipfile import ZipFile
from scripts.bootstrap_metabase import FILTERS, dashboard_specs, template_tags
from scripts.pipeline import load_raw, connect, run_dbt, query


def render(sql, values):
    """Keep an optional [[...]] clause only when its variable has a value, like Metabase."""
    def clause(match):
        name = re.search(r'\{\{(\w+)\}\}', match.group(1)).group(1)
        return match.group(1).replace('{{%s}}' % name, f"'{values[name]}'") if name in values else ''
    return re.sub(r'\[\[(.*?)\]\]', clause, sql)


class DashboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        path = Path(cls.temp.name)
        db = path / 'fixture.duckdb'
        target = os.getenv('SPARKIFY_TEST_TARGET', 'duckdb')
        def play(ts, user, level, song, item):
            return dict(ts=ts, userId=user, level=level, page='NextSong', song=song, artist='Fixture artist',
                        length=60.0, sessionId=int(user), itemInSession=item)
        # 2018-11-01 03:00 UTC (Thu night) and 2018-11-05 14:00 UTC (Mon afternoon).
        night, afternoon = 1541041200000, 1541426400000
        rows = [play(night, '1', 'free', 'Song A', 1), play(night + 1000, '1', 'free', 'Song A', 2),
                play(afternoon, '2', 'paid', 'Song B', 1)]
        with ZipFile(path / 'log_data.zip', 'w') as z:
            z.writestr('fixture.json', '\n'.join(json.dumps(r) for r in rows))
        with ZipFile(path / 'song_data.zip', 'w') as z:
            z.writestr('fixture.json', json.dumps(dict(song_id='a', title='Song A', artist_name='Fixture artist', duration=60, year=2018)))
        load_raw(target, db, path)
        run_dbt(target, 'build', db)
        cls.con = connect(target, db)
        cls.specs = {s[0]: s for s in dashboard_specs()}

    @classmethod
    def tearDownClass(cls):
        cls.con.close()
        cls.temp.cleanup()

    def run_card(self, name, **values):
        return query(self.con, render(self.specs[name][1], values))

    def test_every_question_runs_with_and_without_filters(self):
        for name, sql, *_ in self.specs.values():
            self.assertTrue(set(template_tags(sql)) <= set(FILTERS))
            self.run_card(name)
            self.run_card(name, start_date='2018-11-01', end_date='2018-11-30', daypart='night', membership='free')

    def test_filters_change_answers(self):
        self.assertEqual(self.run_card('Songplays'), [{'songplays': 3}])
        self.assertEqual(self.run_card('Songplays', membership='free'), [{'songplays': 2}])
        self.assertEqual(self.run_card('Songplays', daypart='afternoon'), [{'songplays': 1}])
        self.assertEqual(self.run_card('Songplays', start_date='2018-11-02'), [{'songplays': 1}])
        self.assertEqual(self.run_card('Active listeners', end_date='2018-11-01'), [{'active_listeners': 1}])

    def test_heatmap_and_top_songs(self):
        heat = {r['weekday']: r for r in self.run_card('Songplays heatmap: weekday x hour (UTC)')}
        self.assertEqual(heat['4 Thu']['03'], 2)
        self.assertEqual(heat['1 Mon']['14'], 1)
        self.assertEqual(len(heat['1 Mon']), 25)
        top = self.run_card('Top songs')
        self.assertEqual(top[0], {'song': 'Song A - Fixture artist', 'songplays': 2})
        self.assertEqual(self.run_card('Top songs', membership='paid'), [{'song': 'Song B - Fixture artist', 'songplays': 1}])


if __name__ == '__main__':
    unittest.main()
