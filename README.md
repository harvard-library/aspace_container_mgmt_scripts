# ASpace Container Management Scripts

## Summary

Scripts written to support the ASpace container management project at Harvard.

## Dependencies

- Python 3.6 or higher
- [ArchivesSnake](https://github.com/archivesspace-labs/ArchivesSnake)
- [Jupyter](https://jupyter.org/) (optional if you just want to run the script)
- [more_itertools](https://github.com/erikrose/more-itertools)
- [openpyxl](https://openpyxl.readthedocs.io/en/stable/)

If you're using pipenv, you can install all of these by running

``` sh
pipenv install
```

in the project's root directory.

## Scripts

### import_container_data.py

Takes a spreadsheet with container data and ingests that data to the ASpace API.

### Usage

``` text
usage: import_container_data.py [-h] [--repo_id REPO_ID] [--logfile LOGFILE] [--skip_via_log SKIP_VIA_LOG] excel

Import ASpace container data from spreadsheets

positional arguments:
  excel                          Excel file of container info

optional arguments:
  -h, --help                     show this help message and exit
  --repo_id REPO_ID              ID of the repository to create containers in
  --logfile LOGFILE              Filename for log output
  --skip_via_log SKIP_VIA_LOG    Filename of partial import logfile
```

### Example

``` shellsession
$ import_container_data.py houghton/1951-3100-ready-for-ingest-rev-3.xlsx --repo_id=24 --logfile=houghton_import_1951-3100_2.log
```

### Usage notes

Because imports can take a long time, it's often a good idea to run this script backgrounded via e.g. nohup or screen.
Progress can be tracked by `tail -f` of the logfile.

If the import fails partway, the log should indicate where - if you correct the issue, you can resume from where you left off
by running the importer with a new logfile, and providing the old logfile via the `--skip_via_log` argument to the CLI.


#### Spreadsheet structure

This script expects a spreadsheet with two sheets, the first consisting of subcontainer info, the second of top container info.

Columns for sheet 1 (names must match exactly):

| **Name**                  | **Contents**                                 | **Required?** |
|---------------------------|----------------------------------------------|---------------|
| Object Record ID          | database id for Archival Object              | Y             |
| Instance Type             | database id for instance type                | Y             |
| TempContainerRecord       | temporary top container record (see sheet 2) | Y             |
| Child Container Type      | database id for container type               | N             |
| Child Container Indicator | indicator for child container                | N             |

Columns for sheet 2 (names must match exactly):

| **Name**            | **Contents**                         | **Required?** |
|---------------------|--------------------------------------|---------------|
| TempContainerRecord | temporary id (see sheet 1)           | Y             |
| Container Profile   | database id for container profile    | N             |
| Container Type      | database id for container type       | Y             |
| Container Indicator | indicator for top container          | Y             |
| Barcode             | barcode                              | N             |
| Location            | database id for location             | Y             |
| Location Start Date | start date for location (YYYY-MM-DD) | Y             |

## report_container_data.py

Processes log from import_container_data.py into a report, emitted on STDOUT

### Usage

``` text
usage: report_container_data.py [-h] logfile

Report on success/failure of import process

positional arguments:
  logfile     log file to process

optional arguments:
  -h, --help  show this help message and exit
```

### Example

``` shellsession
$ report_container_data.py houghton_import_1951-3100_2.log > hou_load_report-2020_03_28.txt
```

## Contributors

* Dave Mayo: http://github.com/pobocks **(Primary Contact)**

## License and Copyright

2019 President and Fellows of Harvard College
