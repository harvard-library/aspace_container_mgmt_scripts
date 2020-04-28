#!/usr/bin/env python3

import json
from argparse import ArgumentParser, FileType
from os.path import expanduser
from collections import Counter

ap = ArgumentParser(description="Report on success/failure of import process")
ap.add_argument('logfile',
                type=FileType('r', encoding="utf8"),
                help="log file to process")


if __name__ == '__main__':
    args = ap.parse_args()
    with args.logfile as f:
        events = [json.loads(x) for x in f]

        counts = Counter()
        for e in events:
            counts[e['event']] += 1

        print(f"Containers Created: {counts['create_container']}")
        print(f"Recordss successfully updated: {counts['update_record']}")
        print("\n\n")

        print(f"Containers that failed validation: {counts['FAILED validate_container_row']}")
        for e in events:
            if e['event'] == 'FAILED validate_container_row':
                field_issues = ", and ".join((f"{k.replace('_', ' ')}: {v}" for k,v in e.items() if k.endswith('fields')))
                print(f"\ttemp_id={e['temp_id']} had {field_issues}")
        print("\n\n")

        print(f"Containers passed validation but couldn't be created: {counts['FAILED create_container']}")
        for e in events:
            if e['event'] == 'FAILED create_container':
                print(f"\ttemp_id={e['temp_id']} failed with the following error: {e['result']}")
        print("\n\n")

        print(f"Instances that failed validation: {counts['FAILED validate_sub_container_row']}")
        for e in events:
            if e['event'] == 'FAILED validate_sub_container_row':
                print(f"\ttemp_id={e['temp_id']} and record={e['record_uri']} had empty fields: {e['empty_fields']}")
        print("\n\n")

        print(f"Instances that were omitted because of failed container creation: {counts['OMITTED validate_sub_container_row']}")
        for e in events:
            if e['event'] == 'OMITTED validate_sub_container_row':
                print(f"\trecord_uri={e['record_uri']} temp_id={e['temp_id']} omitted")

        print(f"Instances that failed to update for some other reason: {counts['FAILED update_record']}")
        for e in events:
            if e['event'] == 'FAILED update_record':
                print(f"\trecord_uri={e['record_uri']} result={e['result']}")
