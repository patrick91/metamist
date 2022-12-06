"""
Quick script to back-populate a CSV file of ext seq ids into metamist.
"""
import logging
import csv
import click

from google.cloud import storage

from sample_metadata.apis import SequenceApi
from sample_metadata.models import SequenceUpdateModel
from sample_metadata.apis import SampleApi


logger = logging.getLogger(__file__)
logging.basicConfig(format='%(levelname)s (%(name)s %(lineno)s): %(message)s')
logger.setLevel(logging.INFO)


@click.command()
@click.option(
    '--project',
    required=True,
    help='The sample-metadata project ($DATASET)',
)
@click.option('--bucket-name', required=True)
@click.option('--sample-sequence-map', required=True)
def main(project: str, bucket_name: str, sample_sequence_map: str):
    """Back populate external_ids for existing sequences"""
    sapi = SampleApi()
    seqapi = SequenceApi()
    client = storage.Client()

    bucket = client.get_bucket(bucket_name)
    blob = bucket.blob(sample_sequence_map)
    dest_file = f'/tmp/{sample_sequence_map}.csv'
    blob.download_to_filename(dest_file)

    with open(dest_file) as fh:
        rd = csv.DictReader(fh, delimiter=',')
        for row in rd:
            external_id = row['sample_id']
            external_sequence_id = row['sequence_id']
            sample_map = sapi.get_sample_id_map_by_external(
                project, request_body=[external_id]
            )
            sequence = seqapi.get_sequences_by_sample_ids([sample_map[external_id]])
            if len(sequence) > 1:
                logging.warning(f'Skipping {external_id}, multiple sequences found.')
                continue

            internal_sequence_id = sequence[0]['id']
            seqapi.update_sequence(
                internal_sequence_id,
                SequenceUpdateModel(external_ids={'kccg_id': external_sequence_id}),
            )


if __name__ == '__main__':
    # pylint: disable=no-value-for-parameter
    main()
