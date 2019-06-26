#!/usr/bin/env python3

import xlrd, openpyxl
from itertools import groupby
from numbers import Number
from os.path import expanduser
from argparse import ArgumentParser

from import_container_data import dictify_sheet, setup_logging, get_logger, ASpace, JM

def old_cell_value(cell):
    if str(cell).startswith('xldate'):
        return xlrd.xldate.xldate_as_datetime(cell.value, args.excel.datemode).date().isoformat()
    else:
        return int(cell.value) if isinstance(cell.value, Number) else cell.value

def old_dictify_sheet(sheet):
    rows = sheet.get_rows()
    rowmap = [cell.value.strip() for cell in next(rows)]
    for row in rows:
        yield dict(zip(rowmap, map(old_cell_value, row)))

def comp_sheets(filename):
    xl = xlrd.open_workbook(filename)
    op = openpyxl.load_workbook(filename, read_only=True)

    xl_rows = old_dictify_sheet(xl.sheets()[0])
    op_rows = dictify_sheet(next(iter(op)))

    cci_key = 'Child Container Indicator'
    yield from ((k, list(v),) for k,v in groupby(
        sorted(
            filter(
                lambda pair: str(pair[0][cci_key]) != pair[1][cci_key],
                zip(xl_rows,op_rows)
            ), key=lambda pair: pair[0]['Object Record ID']),
        key=lambda pair: pair[0]['Object Record ID'])
    )

ap = ArgumentParser(description='Fix incorrect indicators')
ap.add_argument('excel',
                type=comp_sheets,
                help='Excel file of container info')
ap.add_argument('--repo_id',
                type=int,
                default=9,
                help="ID of the repository to create containers in")
ap.add_argument('--logfile',
                default='fixup_indicators.log',
                help='Filename for log output')


if __name__ == '__main__':
    args = ap.parse_args()
    setup_logging(filename=args.logfile)
    log = get_logger('fixup_container_data')
    log.info('start_fixup')
    aspace = ASpace()

    cci_key = 'Child Container Indicator'

    for ao_id, group in args.excel:
        ao = aspace.repositories(args.repo_id).archival_objects(ao_id).json()
        log.info('group', ao_id=ao_id)
        del ao['position']
        for bad,good in group:
            for instance in ao['instances']:
                if 'sub_container' in instance:
                    if instance['sub_container']['indicator_2'] == str(bad[cci_key]):
                        log.info('register_change', bad=bad[cci_key], good=good[cci_key])
                        instance['sub_container']['indicator_2'] = good[cci_key]
        res = aspace.client.post(ao['uri'], json=ao)
        if res.status_code == 200:
            log.info('update_ao', ao_id=ao_id)
        else:
            log.error('FAILED update_ao')
    log.info('end_fixup')
