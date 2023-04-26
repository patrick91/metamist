"""
For batching of exome CNV calling it is important we know the capture type used.
VCGS kindly encodes this information in the fastq file name. This script parses all
sequences, identifies which are generated by VCGS (based on the fastq name pattern), then
updates the sequence.meta field with `facility` and `library_type` annotations.
"""
import logging
import re
import click

from metamist.apis import AssayApi
from metamist.models import AssayUpsert

logger = logging.getLogger(__file__)
logging.basicConfig(
    format='%(levelname)s (%(name)s %(lineno)s): %(message)s', level=logging.INFO
)
# logger.setLevel(logging.INFO)

# Facility specific regular expressions
# VCGS fastq
# This is the current name format
vcgs_fastq_regex = (
    r'(?P<run_date>\d{6})_(?P<g2>[A-Z\d]+)_(?P<g3>\d{4})_'
    r'(?P<g4>[A-Z]{2}\d+)_(?P<sample_id>[\w\d-]+)_(?P<library_id>[A-Z\d-]+)_'
    r'(?P<library_type>[\w\d]+)_(?P<lane>L\d+)_(?P<read>R[12])\.fastq\.gz'
)
# Pre mid 2018 the library id was not included:
vcgs_fastq_pre2018_regex = (
    r'(?P<run_date>\d{6})_(?P<g2>[A-Z\d]+)_(?P<g3>\d{4})_'
    r'(?P<g4>[A-Z]{2}\d+)_(?P<sample_id>[\w\d-]+)_'
    r'(?P<library_type>[\w\d]+)_(?P<lane>L\d+)_(?P<read>R[12])\.fastq\.gz'
)

# Garvan fastq
garvan_fastq_regex = (
    r'(?P<flowcell_id>[A-Z0-9]+_\d)_(?P<rundate>\d{6})_'
    r'(?P<sample_id>[A-Z]{2}\d{8})_(?P<species>[\w-]+)_'
    r'(?P<library_barcode>[ACGT]+-[ACGT]+)_(?P<batch_submission_id>R_\d{6}_[A-Z]{6})_'
    r'(?P<sample_type>DNA)_(?P<lane>[A-Z]\d{3})_(?P<read>R[12])\.fastq\.gz'
)


@click.command()
@click.option(
    '--project',
    required=True,
    help='The sample-metadata project ($DATASET)',
)
@click.option(
    '-d',
    '--dry-run',
    is_flag=True,
    default=False,
    help='Do not save changes to metamist',
)
def main(project: str, dry_run: bool):
    """Back populate facility and library_type meta fields for existing sequences"""
    asapi = AssayApi()
    # Pull all the sequences
    assays = asapi.get_assays_by_criteria(
        active=True,
        body_get_assays_by_criteria={
            'projects': [project],
        },
    )

    # For logs
    updated_assays: list[dict[str, dict]] = []

    for assay in assays:
        internal_sequence_id = assay.get('id')
        current_library_type = assay['meta'].get('library_type')

        # Quick validation
        if current_library_type:
            logging.info(
                f'{internal_sequence_id} already has current_library_type set: {current_library_type}. Skipping'
            )
            continue

        meta_fields_to_update = {}

        try:
            fastq_filename = assay.get('meta').get('reads')[0].get('basename')

        except (TypeError, KeyError):
            # Check if this is a bam ingested with a manifest that includes design_description
            if design_description := assay.get('meta', {}).get('design_description'):
                meta_fields_to_update['library_type'] = design_description
                fastq_filename = 'dummy-file-name'
            else:
                # Can't determine fastq_filename
                logging.warning(
                    f'Cant extract fastq_filename for {internal_sequence_id} skipping {assay}'
                )
                continue

        # Match VCGS standard fastq pattern
        if match := re.match(vcgs_fastq_regex, fastq_filename):
            meta_fields_to_update['facility'] = 'vcgs'
            meta_fields_to_update['library_type'] = match.group('library_type')

        # Match VCGS pre2018 fastq pattern
        elif match := re.match(vcgs_fastq_pre2018_regex, fastq_filename):
            meta_fields_to_update['facility'] = 'vcgs'
            meta_fields_to_update['library_type'] = match.group('library_type')

        # Match Garvan standard fastq pattern
        elif match := re.match(garvan_fastq_regex, fastq_filename):
            meta_fields_to_update['facility'] = 'garvan'

        # Check if this is a bam ingested with a manifest that includes design_description
        elif assay['meta'].get('design_description'):
            meta_fields_to_update['library_type'] = assay['meta'].get(
                'design_description'
            )

        else:
            logging.warning(
                f'No file name match found for {internal_sequence_id} skipping {fastq_filename}'
            )

        if meta_fields_to_update:
            if not dry_run:
                asapi.update_assay(
                    AssayUpsert(id=internal_sequence_id, meta=meta_fields_to_update),
                )
            updated_assays.append({internal_sequence_id: meta_fields_to_update})

    if dry_run:
        logging.info(
            f'Dummy run. Would have updated {len(updated_assays)} sequences. {updated_assays}'
        )
    else:
        logging.info(f'Updated {len(updated_assays)} sequences. {updated_assays}')


if __name__ == '__main__':
    # pylint: disable=no-value-for-parameter
    main()
