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
                default=14,
                help="ID of the repository to update containers in")
ap.add_argument('--logfile',
                default='update_containers.log',
                help='Filename for log output')
ap.add_argument('--skip_via_log',
                default=False,
                help='Filename of partial import logfile')

enforce_integer = {'Container Record ID', 'Location'}
enforce_string = {'Barcode'} # unused currently while testing openpyxl
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
        yield out

if __name__ == '__main__':
    args = ap.parse_args()
    setup_logging(filename=args.logfile)
    log = get_logger('update_containers')

    aspace = ASpace()

    log.info('start_ingest')

    for row in dictify_sheet(next(iter(args.excel))):
        try:
            container = aspace.repositories(args.repo_id).top_containers(row['Container Record ID']).json()
            container['barcode'] = row['Barcode']
        except (AttributeError, RuntimeError) as e:
            log.error('FAILED update_container', response=container, data=row, exc_info=e)
            continue

        if row['Location']:
            container['container_locations'].append(
                JM.container_location(
                    status='current',
                    start_date=row['Location Start Date'],
                    ref=f'/locations/{row["Location"]}'))

        res = aspace.client.post(container['uri'], json = container)
        if res.status_code == 200:
            log.info('update_container', data=row)
        else:
            log.error('FAILED update_container', status=res.status_code, data=row, response=res.json())

    log.info('end_ingest')
