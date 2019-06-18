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

Processes log from import_container_data.py into a report

## Contributors

* Dave Mayo: http://github.com/pobocks **(Primary Contact)**

## License and Copyright

2019 President and Fellows of Harvard College
