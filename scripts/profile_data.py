"""Reproduce the source profile and SHA-256 manifest without extracting ZIPs."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from pipeline import ROOT, read_archive


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-dir', type=Path, default=ROOT / 'dataset' / 'dataset')
    parser.add_argument('--output', type=Path, default=ROOT / 'reports' / 'data_profile.json')
    args = parser.parse_args()
    profile = {'origin': 'Archives supplied locally by the project owner; upstream download URL and redistribution license have not been independently established.', 'files': {}}
    for name in ['log_data.zip', 'song_data.zip']:
        path = args.data_dir / name
        fields, pages, levels = Counter(), Counter(), Counter()
        missing_users = rows = 0
        examples = []
        for member, number, record in read_archive(path):
            rows += 1
            fields.update(record.keys())
            if name == 'log_data.zip':
                pages[record.get('page')] += 1
                levels[record.get('level')] += 1
                missing_users += not bool(record.get('userId'))
                if len(examples) < 3 and record.get('page') == 'NextSong':
                    examples.append({k: record.get(k) for k in ['page', 'song', 'artist', 'length', 'level', 'ts']})
        profile['files'][name] = {'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'rows': rows, 'fields': dict(fields), 'page_counts': dict(pages), 'membership_event_counts': dict(levels), 'anonymous_events': missing_users, 'examples_without_personal_fields': examples}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(args.output)


if __name__ == '__main__':
    main()
