#!/usr/bin/env python3
from asnake.logging import setup_logging, get_logger
from asnake.aspace import ASpace
from argparse import ArgumentParser
from itertools import chain

ap = ArgumentParser(description='Delete jobs of type "fetch_urn_job" from all repositories')
ap.add_argument('--logfile',
                default='remove_urn_fetcher_jobs.log',
                help='Filename for log output')

if __name__ == '__main__':
    args = ap.parse_args()
    setup_logging(filename=args.logfile)
    log = get_logger('remove_urn_fetcher_jobs')

    aspace = ASpace()
    for job in chain(repo.jobs for repo in repositories):
        if job.job_type == "fetch_urn_job":
            log.info(f"deleting {job.uri}")
            resp = aspace.client.delete(job.uri)
            if resp.status_code in (200, 204,):
                log.info(f"deleted {job.uri}")
            else:
                log.info(f"failed to delete {job.uri}")
