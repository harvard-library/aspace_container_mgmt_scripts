#!/usr/bin/env python3

import json
from argparse import ArgumentParser, FileType
from os.path import expanduser
from collections import Counter
from datetime import datetime

ap = ArgumentParser(description="Report on success/failure of import process")
ap.add_argument('logfile',
                type=FileType('r', encoding="utf8"),
                help="log file to process")


if __name__ == '__main__':
    args = ap.parse_args()
    with args.logfile as f:
        events = [json.loads(x) for x in f]
        
        end_event = events[-1]
        if end_event['event'] != 'end_ingest':
            exit("Partial logfile, last event is not 'end_ingest'")
        end_time = datetime.fromisoformat(end_event['timestamp'][:19])
        start_time = None
        for e in reversed(events):
            if e['event'] == 'start_ingest':
                start_time = datetime.fromisoformat(e['timestamp'][:19])
                break
        if not start_time:
            exit("Partial logfile, missing 'start_ingest'")

        print(f"Processing begun at: {start_time}, completed at {end_time}, total duration {end_time - start_time}\n")
 
        counts = Counter()
        for e in events:
            counts[e['event']] += 1

        print(f"Containers Created: {counts['create_container']}")
        print(f"AOs successfully updated: {counts['update_ao']}")
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
                print(f"\ttemp_id={e['temp_id']} and archival_object_id={e['ao_id']} had empty fields: {e['empty_fields']}")
        print("\n\n")

        print(f"Instances that were omitted because of failed container creation: {counts['OMITTED validate_sub_container_row']}")
        for e in events:
            if e['event'] == 'OMITTED validate_sub_container_row':
                print(f"\tao_id={e['ao_id']} temp_id={e['temp_id']} omitted")

        print(f"Instances that failed to update for some other reason: {counts['FAILED update_ao']}")
        for e in events:
            if e['event'] == 'FAILED update_ao':
                print(f"\tao_id={e['ao_id']} result={e['result']}")
