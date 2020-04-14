#!/usr/bin/env python3

import openpyxl
import datetime
import json

from os.path import expanduser
from argparse import ArgumentParser
from numbers import Number
from collections import defaultdict, Counter
from itertools import groupby
from more_itertools import chunked
from time import sleep

from asnake.logging import setup_logging, get_logger
from asnake.aspace import ASpace
from asnake.jsonmodel import JM

ap = ArgumentParser(description='Import ASpace container data from spreadsheets')
ap.add_argument('excel',
                type=lambda filename: openpyxl.load_workbook(expanduser(filename)),
                help='Excel file of container info')
ap.add_argument('--repo_id',
                type=int,
                default=2,
                help="ID of the repository to create containers in")
ap.add_argument('--logfile',
                default='import_container_data.log',
                help='Filename for log output')
ap.add_argument('--skip_via_log',
                default=False,
                help='Filename of partial import logfile')

enforce_integer = {'Object Record ID', 'Location', 'Container Profile'}
enforce_string = {'Barcode', 'Container Indicator', 'Child Container Indicator'} # unused currently while testing openpyxl
def cell_value(cell, header):
    if isinstance(cell.value, datetime.datetime):
        return cell.value.date().isoformat()
    elif header in enforce_integer:
        return int(cell.value) if cell.value else ''
    elif cell.value == None:
        return ''
    else:
        return str(cell.value).strip()

def dictify_sheet(sheet):
    rows = iter(sheet)
    rowmap = [cell.value.strip() for cell in next(rows) if cell.value]

    for row in rows:
        out = {}
        for idx, header in enumerate(rowmap):
            out[header] = cell_value(row[idx], header)
        if any(out.values()): # skip blank rows
            yield out

unique_field_counters = defaultdict(Counter)
def _check_unique_field(field, c_row, error_dict):
    if c_row[field]:
        unique_field_counters[field][c_row[field]] += 1
        if unique_field_counters[field][c_row[field]] > 1:
            error_dict['temp_id'] = c_row['TempContainerRecord']
            error_dict['duplicate_fields'].append(field)

def validate_container_row(c_row):
    '''Checks if rows required for container creation are empty'''
    required = ['TempContainerRecord', 'Container Type', 'Container Indicator']
    unique = ['TempContainerRecord', 'Barcode']

    error_dict = defaultdict(list)
    for field in required:
        if not c_row[field]:
            error_dict['temp_id'] = c_row['TempContainerRecord']
            error_dict['empty_fields'].append(field)

    for field in unique:
        _check_unique_field(field, c_row, error_dict)

    if len(error_dict):
        log.error('FAILED validate_container_row', **error_dict)
        return False
    else:
        return True

def container_row_to_container(c_row):
    """Takes a container record and processes it into JSON ready to post.

Expected fields are:
    TempContainerRecord
    Container Profile
    Container Type
    Container Indicator
    Barcode
    Location
    Location Start Date"""


    tc = JM.top_container(
        indicator=str(c_row['Container Indicator']),
        type=c_row['Container Type'],
    )
    if c_row['Barcode']:
        tc['barcode'] = c_row['Barcode']
    if c_row['Container Profile']:
        tc['container_profile'] = JM.container_profile(
            ref=f'/container_profiles/{c_row["Container Profile"]}' if c_row["Container Profile"] else None)
    if c_row['Location']:
        locations = [JM.container_location(
            status="current",
            ref=f'/locations/{c_row["Location"]}',
            start_date=c_row['Location Start Date'])]
        tc['container_locations'] = locations
    return tc

def validate_sub_container_row(sc_row):
    '''Checks if rows required for instance and sub_container creation are empty'''
    required = ['TempContainerRecord', 'Object Record ID', 'Instance Type']
    error_dict = defaultdict(list)
    for field in required:
        if not sc_row[field]:
            error_dict['temp_id'] = sc_row['TempContainerRecord']
            error_dict['ao_id'] = sc_row['Object Record ID']
            error_dict['empty_fields'].append(field)
    if sc_row['TempContainerRecord'] in failures:
        error_dict['temp_id'] = sc_row['TempContainerRecord']
        error_dict['ao_id'] = sc_row['Object Record ID']
        log.error('OMITTED validate_sub_container_row', **error_dict)

    elif len(error_dict):
        log.error('FAILED validate_sub_container_row', **error_dict)
        return False
    else:
        return True

def sub_container_row_to_instance(sc_row):
    """Takes a sub_container record and processes it into JSON ready to add to archival_object.

Expected fields are:
    Object Record ID
    Instance Type
    TempContainerRecord
    Child Container Type
    Child Container Indicator"""
    container_id = temp_id2id[sc_row['TempContainerRecord']]
    sub_container = JM.sub_container(
        top_container=JM.top_container(
            ref=f'/repositories/{args.repo_id}/top_containers/{container_id}'
        ))

    if sc_row['Child Container Type']:
        sub_container['type_2'] = sc_row['Child Container Type']
    if sc_row['Child Container Indicator']:
        sub_container['indicator_2'] = str(sc_row['Child Container Indicator'])

    instance = JM.instance(
        instance_type=sc_row['Instance Type'],
        sub_container=sub_container
    )

    return instance

def populate_skiplists(log_entries):
    for entry in log_entries:
        if entry['event'] in {'create_container', 'skip_container'}:
            temp_id2id[entry['temp_id']] = entry['id']
        if entry['event'] in {'update_ao', 'skip_ao'}:
            ao_processed.add(entry.get('ao_id', entry.get('id', None))) # id was used in in early versions of script

if __name__ == '__main__':
    args = ap.parse_args()
    setup_logging(filename=args.logfile)
    log = get_logger('import_container_data')
    log.info('start_ingest')
    aspace = ASpace()

    # Global variables referenced from local functions
    temp_id2id = {}
    ao_processed = set()
    failures = set()

    if args.skip_via_log:
        with open(expanduser(args.skip_via_log)) as f:
            populate_skiplists(map(json.loads, f))

    ao_sheet, container_sheet = args.excel
    # containers
    for c_row in dictify_sheet(container_sheet):
        temp_id = c_row['TempContainerRecord']
        if temp_id in temp_id2id:
            log.warning('skip_container', temp_id=temp_id, id=temp_id2id[temp_id])
            continue

        if validate_container_row(c_row):
            res = aspace.client.post(f'repositories/{args.repo_id}/top_containers',
                                     json=container_row_to_container(c_row))

            if res.status_code == 200:
                temp_id2id[temp_id] = res.json()["id"]
                log.info('create_container', id=res.json()["id"], temp_id=temp_id)
            else:
                log.error("FAILED create_container", result=res.json(), temp_id=temp_id)
                failures.add(temp_id)
        else:
            if temp_id:
                # validate_container_row handles logging error
                failures.add(temp_id)

    # sub_containers
    sorting_fn=lambda x: x['Object Record ID']

    if ao_processed:
        for ao_id in ao_processed:
            log.warning('skip_ao', ao_id=ao_id)

    rows = filter(lambda row: row['Object Record ID'] not in ao_processed, dictify_sheet(ao_sheet))

    groups_by_ao = {ao_id:list(group)
                    for ao_id, group in groupby(sorted(rows, key=sorting_fn), key=sorting_fn)}

    for group in chunked(groups_by_ao.items(), 100):
        ao_ids = [item[0] for item in group]

        res = aspace.client.get(f"repositories/{args.repo_id}/archival_objects",
                                params={"id_set":ao_ids})
        if res.status_code != 200:
            raise RuntimeError(f"Something went wrong with batch of IDs: {ao_ids}")

        ao_jsons = {int(ao['uri'].split('/')[-1]):ao for ao in res.json()}

        for ao_id, ao_group in group:
            instances_added = []
            ao_json = ao_jsons.get(ao_id, None)
            if not ao_json:
                log.error('FAILED missing_ao', result=None, ao_id=ao_id, ao_json=None)
                continue
            del ao_json['position']
            initial_instance_count = len(ao_json.get('instances', []))
            for sc_row in ao_group:
                temp_id = sc_row['TempContainerRecord']
                if not temp_id in temp_id2id:
                    log.error('FAILED update_ao', result=f"'{temp_id}' not present in temp_id2id", ao=ao_json, ao_id=ao_id)
                    continue
                if validate_sub_container_row(sc_row):
                    if not 'instances' in ao_json:
                        ao_json['instances'] = []
                    ao_json['instances'].append(sub_container_row_to_instance(sc_row))
                    instances_added.append({'temp_id': temp_id, 'container_id': temp_id2id[temp_id]})


            if len(ao_json.get('instances', [])) > initial_instance_count:
                res = aspace.client.post(ao_json['uri'], json=ao_json)
            if res.status_code == 200:
                log.info('update_ao', ao_id=ao_id, instances_added=instances_added)
            else:
                log.error('FAILED update_ao', result=res.json(), ao=ao_json, ao_id=ao_id)

    log.info('end_ingest')
