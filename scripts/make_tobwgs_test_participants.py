from metamist.apis import ParticipantApi
from metamist.models import (
    ParticipantUpsert,
    SampleUpsert,
    SequencingGroupUpsert,
    AssayUpsert,
)
import click

from metamist.graphql import gql, query
from cpg_utils import to_path


SAMPLE_QUERY = gql(
    """
    query ($project: String!, $sample_ids: [String!]) {
        sample(project: {eq: $project}, id: {in_: $sample_ids}) {
            id
            externalId
            sequencingGroups {
                id
                assays {
                    id
                    externalIds
                    meta
                }
                }
            }
            }
    """
)

papi_instance = ParticipantApi()


def create_participant(project_id: int, extID: str, sampleID: str, sg_id: str):
    participant_upsert = [
        ParticipantUpsert(
            id=None,
            external_id=extID,
            samples=[
                SampleUpsert(
                    id=sampleID,
                    external_id=extID,
                    project=project_id,
                    sequencing_groups=[
                        SequencingGroupUpsert(
                            id=sg_id,
                            sample_id=sampleID,
                        ),
                    ],
                    non_sequencing_assays=[
                        AssayUpsert(
                            id=None,
                            type='sequencing',
                            sample_id=sampleID,
                            meta={
                                'sequencing_type': 'genome',
                                'sequencing_platform': 'illumina',
                                'sequencing_technology': 'short-read',
                            },
                        ),
                    ],
                ),
            ],
        ),
    ]

    return participant_upsert


@click.command()
@click.option(
    '--project',
    required=True,
    help='The name of the project to add samples to.',
)
@click.option(
    '--project_id',
    required=True,
    type=int,
    help='The ID of the project to add samples to.',
)
@click.option(
    '--new_samples_path',
    required=True,
    help='Path to the CSV file with sample data.',
)
def main(project: id, project_id: int, new_samples_path: str):
    # Read in newly created samples
    with to_path(new_samples_path).open() as f:
        new_samples = f.read().splitlines()

    # Query for samples
    query_response = query(
        SAMPLE_QUERY, {"project": project, "sample_ids": new_samples}
    )

    # Create participant upserts
    participant_upserts = []
    for sample in query_response['sample']:
        extID = sample['externalId']
        sampleID = sample['id']
        for sg in sample['sequencingGroups']:
            sg_id = sg['id']
            participant_upserts.append(
                create_participant(project_id, extID, sampleID, sg_id)
            )

    # Upsert Participants
    for upsert in participant_upserts:
        api_response = papi_instance.upsert_participants(project, upsert)
        print(api_response)


if __name__ == '__main__':
    main()
