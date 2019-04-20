#!/usr/bin/env python3

import xlrd
from os.path import expanduser
from argparse import ArgumentParser
from numbers import Number

from asnake.logging import setup_logging, get_logger
from asnake.aspace import ASpace
from asnake.jsonmodel import JM

ap = ArgumentParser(description='Import ASpace container data from spreadsheets')
ap.add_argument('excel', type=lambda filename: xlrd.open_workbook(expanduser(filename)), help='Excel file of container info')
ap.add_argument('--repo_id', type=int, help="ID of the repository to create containers in", default=2)
ap.add_argument('--logfile', help='Filename for log output')

def cell_value(cell):
    if str(cell).startswith('xldate'):
        return xlrd.xldate.xldate_as_datetime(cell.value, args.excel.datemode).date().isoformat()
    else:
        return int(cell.value) if isinstance(cell.value, Number) else cell.value

def dictify_sheet(sheet):
    rows = sheet.get_rows()
    rowmap = [cell.value for cell in next(rows)]
    for row in rows:
        yield dict(zip(rowmap, map(cell_value, row)))

def container_row_to_container(c_row):
    global c_types
    """Takes a container record and processes it into JSON ready to post.

Expected fields are:
    TempContainerRecord
    Container Profile
    Container Type
    Container Indicator
    Barcode
    Location
    Location Start Date"""

    locations = [JM.container_location(
        status="current",
        ref=f'/locations/{c_row["Location"]}',
        start_date=c_row['Location Start Date'])]

    tc = JM.top_container(
        indicator=str(c_row['Container Indicator']),
        container_locations=locations,
        type=c_types[c_row['Container Type']],
    )
    if c_row['Barcode']:
        tc['barcode'] = c_row['Barcode']
    if c_row['Container Profile']:
        tc['container_profile'] = JM.container_profile(
            ref=f'/container_profiles/{c_row["Container Profile"]}' if c_row["Container Profile"] else None)

    return tc


if __name__ == '__main__':
    args = ap.parse_args()
    setup_logging(filename=args.logfile or 'import_container_data.log')
    log = get_logger('import_container_data')

    aspace = ASpace()
    c_types = {entry['id']:entry['value']
               for entry
               in aspace.config.enumerations.names("container_type").json()['enumeration_values']}
    temp_id2id = {}
    for c_row in dictify_sheet(args.excel.sheet_by_index(1)):
        res = aspace.client.post(f'repositories/{args.repo_id}/top_containers',
                                 json=container_row_to_container(c_row))
        if res.status_code == 200:
            temp_id2id[c_row['TempContainerRecord']] = res.json()["id"]
            log.info('create_container', id=res.json()["id"])
        else:
            log.error("FAILED create_container", result=res.json())
