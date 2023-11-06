from collections import defaultdict, namedtuple
import asyncio
from datetime import datetime
import pandas as pd
from typing import Dict, Any
from metamist.audit.non_async_auditor import GenericAuditor
from metamist.audit.audithelper import AuditHelper
import logging
from typing import Any


class TobWgsAuditor(GenericAuditor):
    def __init__(
        self,
        dataset: str,
        sequencing_types: str,
        file_types: str,
        default_analysis_type='cram',
        default_analysis_status='completed',
    ):
        super().__init__(
            dataset=dataset,
            sequencing_types=sequencing_types,
            file_types=file_types,
            default_analysis_type=default_analysis_type,
            default_analysis_status=default_analysis_status,
        )

    def get_assay_map_from_participants(
        self, participants: list[dict]
    ) -> tuple[dict[str, str], dict[int, str], dict[Any, list[tuple[Any, Any]]]]:
        """
        Input the list of Metamist participant dictionaries from the 'QUERY_PARTICIPANTS_SAMPLES_SGS_ASSAYS' query

        Returns the mappings:
        1. { sg_id       : sample_id }
        2. { assay_id    : sg_id }
        3. { assay_id    : (read_filepath, read_filesize,) }
        """

        sg_sample_id_map = {}
        assay_sg_id_map = {}
        assay_filepaths_filesizes = defaultdict(list)

        sample_sgs = {
            sample['id']: sample['sequencingGroups']
            for participant in participants
            for sample in participant['samples']
        }

        # md5_check_list = []

        for sample_id, sgs in sample_sgs.items():
            for sg in sgs:
                if sg['type'].lower() not in self.sequencing_types:
                    continue

                sg_sample_id_map[sg['id']] = sample_id
                for assay in sg['assays']:
                    reads = assay['meta'].get('reads')
                    if not reads:
                        logging.warning(
                            f'{self.dataset} :: SG {sg["id"]} assay {assay["id"]} has no reads field'
                        )
                        continue

                    if assay_sg_id_map.get(assay['id']):
                        raise ValueError(
                            f'{self.dataset} :: Assay {assay["id"]} has multiple SGs: {assay_sg_id_map[assay["id"]]} and {sg["id"]}'
                        )
                    assay_sg_id_map[assay['id']] = sg['id']

                    if isinstance(reads, dict):
                        assay_filepaths_filesizes[assay['id']].append(
                            (
                                reads.get('location'),
                                reads.get('size'),
                            )
                        )
                        continue

                    if not isinstance(reads, list):
                        logging.error(
                            f'{self.dataset} :: Got {type(reads)} reads for SG {sg["id"]}, expected list type. Reads may have been deleted after analysis'
                        )
                        continue
                    for read in reads:
                        if not isinstance(read, dict):
                            logging.error(
                                f'{self.dataset} :: Got {type(read)} read for SG {sg["id"]}, expected dict: {read}'
                            )
                            continue

                        assay_filepaths_filesizes[assay['id']].append(
                            (
                                read.get('location'),
                                read.get('size'),
                            )
                        )

                        # here implement md5 hash check
                        location = read.get('location')
                        checksum = read.get('checksum').split(' ')[0].split(':')[1]
                        # md5_check_list.append(self.check_md5_hash(location, checksum))

        return (
            sg_sample_id_map,
            assay_sg_id_map,
            assay_filepaths_filesizes,
            # md5_check_list,
        )

    def get_crams_from_participants(self, participants: list[dict]):
        # if i peruse the cpg-tob-wgs-main bucket for crams can i assume these are 1:1 matches with CPG ID's in metamist?
        pass

    def map_bone_marrow_sgid_to_assay(
        self, participants: list[dict], sg_cram_paths: dict
    ):
        # get the bone marrow samples from the participant list
        bone_marrow_sg_assay: Dict = {}
        for participant in participants:
            for sample in participant['samples']:
                sgs = sample['sequencingGroups']
                for sg in sgs:
                    if sg['id'] not in sg_cram_paths.keys():
                        continue
                    if sg['id'] in sg_cram_paths.keys():
                        for assay in sg['assays']:
                            meta = assay.get('meta')
                            if not meta:
                                logging.warning(
                                    f'{self.dataset} :: Assay {assay["id"]} has no meta field'
                                )
                                continue
                            if meta.get('Primary study') == 'Pilot/bone marrow':
                                bone_marrow_sg_assay[sg['id']] = assay['id']
        return bone_marrow_sg_assay

    @staticmethod
    def get_most_recent_analyses_by_sg(
        dataset: str, analyses_list: list[dict[str, Any]]
    ) -> dict[str, dict[str, Any]]:
        """
        Takes a list of completed analyses for a number of sequencing groups and returns the latest
        completed analysis for each sequencing group, creating a 1:1 mapping of SG to analysis.
        """
        most_recent_analysis_by_sg = {}
        most_recent_long_read_analysis_by_sg = {}
        sg_ids_with_no_analyses = []
        for sg_analyses in analyses_list:
            sg_id = sg_analyses['id']
            analyses = sg_analyses['analyses']
            # Filter analyses to consider only those with a .cram extension in the output field
            cram_analyses = [
                analysis
                for analysis in analyses
                if analysis['output'].endswith('.cram')
            ]

            long_read_analyses = [
                analysis
                for analysis in analyses
                if 'ont' in analysis['meta'].get('sequence_type')
            ]

            if not cram_analyses:
                sg_ids_with_no_analyses.append(sg_id)
                logging.warning(f'{dataset} :: SG {sg_id} has no completed analyses')
                continue

            if len(cram_analyses) == 1:
                most_recent_analysis_by_sg[sg_id] = cram_analyses[0]
                continue

            sorted_cram_analyses = sorted(
                cram_analyses,
                key=lambda x: datetime.strptime(
                    x['timestampCompleted'], '%Y-%m-%dT%H:%M:%S'
                ),
            )

            sorted_long_read_analyses = sorted(
                long_read_analyses,
                key=lambda x: datetime.strptime(
                    x['timestampCompleted'], '%Y-%m-%dT%H:%M:%S'
                ),
            )
            most_recent_analysis_by_sg[sg_id] = sorted_cram_analyses[-1]
            if sorted_long_read_analyses:
                most_recent_long_read_analysis_by_sg[sg_id] = sorted_long_read_analyses[
                    -1
                ]
            # log long read analyses
            if len(most_recent_long_read_analysis_by_sg) > 0:
                logging.warning(
                    f'{dataset} :: SG {sg_id} has multiple long read analyses: {most_recent_long_read_analysis_by_sg}'
                )

        return (
            most_recent_analysis_by_sg,
            most_recent_long_read_analysis_by_sg,
            sg_ids_with_no_analyses,
        )


def audit_tob_wgs(
    dataset: str,
    sequencing_types: list[str],
    file_types: list[str],
    default_analysis_type: str,
    default_analysis_status: str,
):
    auditor = TobWgsAuditor(
        dataset=dataset,
        sequencing_types=sequencing_types,
        file_types=file_types,
        default_analysis_type=default_analysis_type,
        default_analysis_status=default_analysis_status,
    )

    participant_data = auditor.get_participant_data_for_dataset()
    sample_internal_external_id_map = auditor.map_internal_to_external_sample_ids(
        participant_data
    )

    (
        sg_sample_id_map,
        assay_sg_id_map,
        assay_filepaths_filesizes,
        # md5_check_list,
    ) = auditor.get_assay_map_from_participants(participant_data)

    (
        sg_cram_paths,
        long_read_analyses,
        sg_ids_with_no_analyses,
    ) = auditor.get_analysis_cram_paths_for_dataset_sgs(assay_sg_id_map)
    complete_incomplete_crams = auditor.get_complete_and_incomplete_sgs(
        assay_sg_id_map, sg_cram_paths
    )

    # map sg's with analyses (most recent analyses) to their primary study
    bone_marrow_sg_assay = auditor.map_bone_marrow_sgid_to_assay(
        participant_data, sg_cram_paths
    )
    return participant_data


audit_tob_wgs(
    dataset='tob-wgs',
    sequencing_types=['genome'],
    file_types=['cram'],
    default_analysis_type='cram',
    default_analysis_status='completed',
)
