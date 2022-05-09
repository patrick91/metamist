# pylint: disable=too-many-instance-attributes,too-many-locals,unused-argument,no-self-use,wrong-import-order
"""
Parser for prophecy metadata.

parse_prophecy.py \
gs://cpg-prophecy-test-upload/R_220208_BINKAN1_PROPHECY_M001.csv \
gs://cpg-prophecy-test-upload/R_220208_BINKAN1_PROPHECY_M002.csv \
--search-location gs://cpg-prophecy-test-upload
"""

import logging
import csv
from typing import List
import click

from sample_metadata.parser.generic_metadata_parser import (
    GenericMetadataParser,
    SingleRow,
    run_as_sync,
)

logger = logging.getLogger(__file__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)

SEQUENCE_META_MAP = {
    'Application': 'platform',
    'External ID': 'external_id',
    'Sample Concentration (ng/ul)': 'concentration',
    'Volume (uL)': 'volume',
}

SAMPLE_META_MAP = {
    'Sex': 'sex',
}

PROJECT = 'prophecy-test'


class ProphecyParser(GenericMetadataParser):
    """Parser for Prophecy manifests"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _get_dict_reader(self, file_pointer, delimiter: str):
        # Skipping header metadata lines
        for line in file_pointer:
            if line.strip() == '""':
                break
        reader = csv.DictReader(file_pointer, delimiter=delimiter)
        return reader

    def fastq_file_name_to_sample_id(self, filename: str) -> str:
        """
        HG3FMDSX3_2_220208_FD02700641_Homo-sapiens_AACGAGGCCG-ATCCAGGTAT_R_220208_BINKAN1_PROPHECY_M002_R1.
        -> 220208_FD02700641
        """
        return '_'.join(filename.split('_')[2:4])

    async def get_read_filenames(self, sample_id: str, row: SingleRow) -> List[str]:
        """
        We don't have fastq urls in a manifest, so overriding this method to take
        urls from a bucket listing.
        """
        return [
            path
            for filename, path in self.filename_map.items()
            if self.fastq_file_name_to_sample_id(filename) == row['Sample/Name']
        ]


@click.command(help='GCS path to manifest file')
@click.option(
    '--sample-metadata-project',
    help='The sample-metadata project to import manifest into',
    default=PROJECT,
)
@click.option('--search-location', 'search_locations', multiple=True)
@click.option(
    '--confirm', is_flag=True, help='Confirm with user input before updating server'
)
@click.option('--dry-run', 'dry_run', is_flag=True)
@click.argument('manifests', nargs=-1)
@run_as_sync
async def main(
    manifests: List[str],
    sample_metadata_project: str,
    search_locations: List[str],
    confirm=True,
    dry_run=False,
):
    """Run script from CLI arguments"""
    parser = ProphecyParser(
        sample_metadata_project=sample_metadata_project,
        search_locations=search_locations,
        sample_name_column='External ID',
        participant_column='External ID',
        reported_gender_column='Sex',
        sample_meta_map=SAMPLE_META_MAP,
        qc_meta_map={},
        participant_meta_map={},
        sequence_meta_map=SEQUENCE_META_MAP,
    )

    for manifest_path in manifests:
        logger.info(f'Importing {manifest_path}')

        await parser.from_manifest_path(
            manifest=manifest_path,
            confirm=confirm,
            dry_run=dry_run,
        )


if __name__ == '__main__':
    # pylint: disable=no-value-for-parameter
    main()
