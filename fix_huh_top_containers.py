#!/usr/bin/env python3

import openpyxl
import datetime
from os.path import expanduser
from argparse import ArgumentParser
from itertools import chain, groupby
from more_itertools import one, chunked
from functools import partial
from asnake.logging import setup_logging, get_logger
from asnake.aspace import ASpace


ap = ArgumentParser(description="Repoint Botany AOs to correct top containers")
ap.add_argument('excel',
                type=lambda filename: openpyxl.load_workbook(expanduser(filename)),
                help='Excel file with fields: instance_id, ao_id, old_tc, new_tc')
ap.add_argument('--repo_id',
                    type=int,
                    default=17,
                    help='ID of the repository to fix containers in')
ap.add_argument('--logfile',
                default='fix_top_containers.log',
                help='Filename for log output')

enforce_integer = {"Archival Object", "Current Container Record ID", "New Container Record ID", "Repo ID"}
def cell_value(cell, header):
    if isinstance(cell.value, datetime.datetime):
        return cell.value.date().isoformat()
    elif header in enforce_integer:
        return int(cell.value) if cell.value else ''
    elif cell.value == None:
        return ''
    else:
        return str(cell.value)

def dictify_sheet(sheet):
    rows = iter(sheet)
    rowmap = [cell.value.strip() for cell in next(rows) if cell.value]

    for row in rows:
        out = {}
        for idx, header in enumerate(rowmap):
            out[header] = cell_value(row[idx], header)
        yield out

if __name__ == '__main__':
    args = ap.parse_args()

    setup_logging(filename=args.logfile)
    log = get_logger('import_container_data')
    log.info('start_ingest')

    aspace = ASpace()

    def get_jsons(repo_id, id_set):
        '''Get chunk of Archival Object JSONModelObjects'''
        return aspace.client.get(f'repositories/{repo_id}/archival_objects', params={'id_set': ",".join(map(str, id_set))}).json()

    repo_id_key_fn = lambda x: x['Repo ID']

    rows = list(dictify_sheet(one(args.excel)))
    ao_ids_by_repo_id = groupby(sorted(rows, key=repo_id_key_fn), key=repo_id_key_fn)

    def get_id_num(uri):
        return int(uri[uri.rindex('/')+1:])

    def get_uri_prefix(uri):
        return uri[:uri.rindex('/')+1]

    ao_jsons_by_id = {}
    for repo_id, aos in ao_ids_by_repo_id:
        for chunk in chunked((el['Archival Object'] for el in aos), 250):
            ao_jsons_by_id.update({get_id_num(ao['uri']):ao for ao in get_jsons(repo_id, chunk)})

    for row in rows:
        ao = ao_jsons_by_id[row['Archival Object']]
        del ao['position']
        for instance in ao['instances']:
            if 'sub_container' in instance:
                extant_tc_ref = instance['sub_container']['top_container']['ref']
                if get_id_num(extant_tc_ref) == row['Current Container Record ID']:
                    instance['sub_container']['top_container']['ref'] = get_uri_prefix(extant_tc_ref) + str(row['New Container Record ID'])
                    break
        res = aspace.client.post(ao['uri'], json=ao)
        if res.status_code == 200:
            log.info('update_container', **row)
        else:
            log.error('FAILED update_container', result=res.json(), **row)

    log.info('end_ingest')
