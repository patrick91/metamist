# pylint: disable=too-many-locals
import json
import asyncio
import dataclasses
from datetime import date
from collections import defaultdict
from itertools import groupby
from typing import Dict, List, Optional, Set

from pydantic import BaseModel

from db.python.connect import DbBase
from db.python.layers.base import BaseLayer
from db.python.layers.sample import SampleLayer
from db.python.tables.analysis import AnalysisTable
from db.python.tables.sequence import SampleSequencingTable
from models.enums import SampleType, SequenceType, SequenceStatus


class NestedSequence(BaseModel):
    """Sequence model"""

    id: int
    type: SequenceType
    status: SequenceStatus
    meta: Dict


class NestedSample(BaseModel):
    """Sample with nested sequences"""

    id: str
    external_id: str
    type: SampleType
    meta: Dict
    sequences: List[NestedSequence]
    created_date: Optional[str]


class NestedFamily(BaseModel):
    """Simplified family model"""

    id: int
    external_id: str


class NestedParticipant(BaseModel):
    """Participant with nested family and sampels"""

    id: Optional[int]
    external_id: Optional[str]
    meta: Optional[Dict]
    families: List[NestedFamily]
    samples: List[NestedSample]
    reported_sex: Optional[int]
    reported_gender: Optional[str]
    karyotype: Optional[str]


@dataclasses.dataclass
class ProjectSummary:
    """Return class for the project summary endpoint"""

    # stats
    total_samples: int
    total_participants: int
    sequence_stats: dict[str, dict[str, str]]

    # grid
    participants: List[NestedParticipant]
    participant_keys: list[tuple[str, str]]
    sample_keys: list[tuple[str, str]]
    sequence_keys: list[tuple[str, str]]


class WebLayer(BaseLayer):
    """Web layer"""

    async def get_project_summary(
        self, token: Optional[str], limit: int = 50
    ) -> ProjectSummary:
        """
        Get a summary of a project, allowing some "after" token,
        and limit to the number of results.
        """
        webdb = WebDb(self.connection)
        return await webdb.get_project_summary(token=token, limit=limit)


class WebDb(DbBase):
    """Db layer for web related routes,"""

    def _project_summary_sample_query(self, limit, after):
        """
        Get query for getting list of samples
        """
        wheres = ['project = :project']
        values = {'limit': limit, 'project': self.project, 'after': after}
        # if after:
        #     values['after'] = after
        #     # wheres.append('id > :after')
        #     wheres.append('offset :after')

        where_str = ''
        if wheres:
            where_str = 'WHERE ' + ' AND '.join(wheres)
        sample_query = f'SELECT id, external_id, type, meta, participant_id FROM sample {where_str} ORDER BY id LIMIT :limit OFFSET :after'

        return sample_query, values

    @staticmethod
    def _project_summary_process_sequence_rows_by_sample_id(
        sequence_rows,
    ) -> Dict[int, List[NestedSequence]]:
        """
        Get sequences for samples for project summary
        """

        seq_id_to_sample_id_map = {seq['id']: seq['sample_id'] for seq in sequence_rows}
        seq_models = [
            NestedSequence(
                id=seq['id'],
                status=SequenceStatus(seq['status']),
                type=SequenceType(seq['type']),
                meta=json.loads(seq['meta']),
            )
            for seq in sequence_rows
        ]
        seq_models_by_sample_id = {
            k: list(v)
            for k, v in (
                groupby(seq_models, key=lambda s: seq_id_to_sample_id_map[s.id])
            )
        }

        return seq_models_by_sample_id

    @staticmethod
    def _project_summary_process_sample_rows(
        sample_rows, seq_models_by_sample_id, sample_id_start_times: Dict[int, date]
    ) -> List[NestedSample]:
        """
        Process the returned sample rows into nested samples + sequences
        """

        smodels = [
            NestedSample(
                id=s['id'],
                external_id=s['external_id'],
                type=s['type'],
                meta=json.loads(s['meta']) or {},
                created_date=str(sample_id_start_times.get(s['id'], '')),
                sequences=seq_models_by_sample_id.get(s['id'], []) or [],
            )
            for s in sample_rows
        ]
        return smodels

    async def get_total_number_of_samples(self):
        """Get total number of active samples within a project"""
        _query = 'SELECT COUNT(*) FROM sample WHERE project = :project AND active'
        return await self.connection.fetch_val(_query, {'project': self.project})

    async def get_total_number_of_participants(self):
        """Get total number of participants within a project"""
        _query = 'SELECT COUNT(*) FROM participant WHERE project = :project'
        return await self.connection.fetch_val(_query, {'project': self.project})

    @staticmethod
    def _project_summary_process_family_rows_by_pid(
        family_rows,
    ) -> Dict[int, List[NestedFamily]]:
        """
        Process the family rows into NestedFamily objects
        """
        pid_to_fids = defaultdict(list)
        for frow in family_rows:
            pid_to_fids[frow['participant_id']].append(frow['family_id'])

        res_families = {}
        for f in family_rows:
            if f['family_id'] in family_rows:
                continue
            res_families[f['family_id']] = NestedFamily(
                id=f['family_id'], external_id=f['external_family_id']
            )
        pid_to_families = {
            pid: [res_families[fid] for fid in fids]
            for pid, fids in pid_to_fids.items()
        }
        return pid_to_families

    async def get_project_summary(
        self, token: Optional[str], limit: int
    ) -> ProjectSummary:
        """
        Get project summary

        :param token: for PAGING
        :param limit: Number of SAMPLEs to return, not including nested sequences
        """
        # do initial query to get sample info
        sampl = SampleLayer(self._connection)
        sample_query, values = self._project_summary_sample_query(
            limit, int(token or 0)
        )
        sample_rows = list(await self.connection.fetch_all(sample_query, values))

        if len(sample_rows) == 0:
            return ProjectSummary(
                participants=[],
                participant_keys=[],
                sample_keys=[],
                sequence_keys=[],
                # stats
                total_samples=0,
                total_participants=0,
                sequence_stats={},
            )

        pids = list(set(s['participant_id'] for s in sample_rows))
        sids = list(s['id'] for s in sample_rows)

        # sequences

        seq_query = 'SELECT id, sample_id, meta, type, status FROM sample_sequencing WHERE sample_id IN :sids'
        sequence_promise = self.connection.fetch_all(seq_query, {'sids': sids})

        # participant
        p_query = 'SELECT id, external_id, meta, reported_sex, reported_gender, karyotype FROM participant WHERE id in :pids'
        participant_promise = self.connection.fetch_all(p_query, {'pids': pids})

        # family
        f_query = """
SELECT f.id as family_id, f.external_id as external_family_id, fp.participant_id
FROM family_participant fp
INNER JOIN family f ON f.id = fp.family_id
WHERE fp.participant_id in :pids
        """
        family_promise = self.connection.fetch_all(f_query, {'pids': pids})

        atable = AnalysisTable(self._connection)
        seqtable = SampleSequencingTable(self._connection)

        [
            sequence_rows,
            participant_rows,
            family_rows,
            sample_id_start_times,
            total_samples,
            total_participants,
            cram_number_by_seq_type,
            seq_number_by_seq_type,
            seqr_stats_by_seq_type,
        ] = await asyncio.gather(
            sequence_promise,
            participant_promise,
            family_promise,
            sampl.get_samples_create_date(sids),
            self.get_total_number_of_samples(),
            self.get_total_number_of_participants(),
            atable.get_number_of_crams_by_sequence_type(project=self.project),
            seqtable.get_sequence_type_numbers_for_project(project=self.project),
            atable.get_seqr_stats_by_sequence_type(project=self.project),
        )

        # post-processing
        seq_models_by_sample_id = (
            self._project_summary_process_sequence_rows_by_sample_id(sequence_rows)
        )
        smodels = self._project_summary_process_sample_rows(
            sample_rows, seq_models_by_sample_id, sample_id_start_times
        )
        # the pydantic model is casting to the id to a str, as that makes sense on the front end
        # but cast back here to do the lookup
        sid_to_pid = {s['id']: s['participant_id'] for s in sample_rows}
        smodels_by_pid = {
            k: list(v)
            for k, v in (groupby(smodels, key=lambda s: sid_to_pid[int(s.id)]))
        }

        pid_to_families = self._project_summary_process_family_rows_by_pid(family_rows)
        participant_map = {p['id']: p for p in participant_rows}

        # we need to specifically handle the empty participant case,
        # we'll accomplish this using an hash set

        pid_seen = set()
        pmodels = []

        for s, srow in zip(smodels, sample_rows):
            pid = srow['participant_id']
            if pid is None:
                pmodels.append(
                    NestedParticipant(
                        id=None,
                        external_id=None,
                        meta=None,
                        families=[],
                        samples=[s],
                        reported_sex=None,
                        reported_gender=None,
                        karyotype=None,
                    )
                )
            elif pid not in pid_seen:
                pid_seen.add(pid)
                p = participant_map[pid]
                pmodels.append(
                    NestedParticipant(
                        id=p['id'],
                        external_id=p['external_id'],
                        meta=json.loads(p['meta']),
                        families=pid_to_families.get(p['id'], []),
                        samples=list(smodels_by_pid.get(p['id'])),
                        reported_sex=p['reported_sex'],
                        reported_gender=p['reported_gender'],
                        karyotype=p['karyotype'],
                    )
                )

        ignore_participant_keys: Set[str] = set()
        ignore_sample_meta_keys = {'reads', 'vcfs', 'gvcf'}
        ignore_sequence_meta_keys = {'reads', 'vcfs', 'gvcf'}

        participant_meta_keys = set(
            pk
            for p in pmodels
            if p and p.meta
            for pk in p.meta.keys()
            if pk not in ignore_participant_keys
        )
        sample_meta_keys = set(
            sk
            for p in pmodels
            for s in p.samples
            for sk in s.meta.keys()
            if (sk not in ignore_sample_meta_keys)
        )
        sequence_meta_keys = set(
            sk
            for p in pmodels
            for s in p.samples
            for seq in s.sequences
            for sk in seq.meta
            if (sk not in ignore_sequence_meta_keys)
        )

        has_reported_sex = any(p.reported_sex for p in pmodels)
        has_reported_gender = any(p.reported_gender for p in pmodels)
        has_karyotype = any(p.karyotype for p in pmodels)

        participant_keys = [('external_id', 'Participant ID')]

        if has_reported_sex:
            participant_keys.append(('reported_sex', 'Reported sex'))
        if has_reported_gender:
            participant_keys.append(('reported_gender', 'Reported gender'))
        if has_karyotype:
            participant_keys.append(('karyotype', 'Karyotype'))

        participant_keys.extend(('meta.' + k, k) for k in participant_meta_keys)
        sample_keys: list[tuple[str, str]] = [
            ('id', 'Sample ID'),
            ('external_id', 'External Sample ID'),
            ('created_date', 'Created date'),
        ] + [('meta.' + k, k) for k in sample_meta_keys]
        sequence_keys = [('type', 'type')] + [
            ('meta.' + k, k) for k in sequence_meta_keys
        ]

        seen_seq_types = set(cram_number_by_seq_type.keys()).union(
            set(seq_number_by_seq_type.keys())
        )
        sequence_stats = {}
        for seq in seen_seq_types:
            sequence_stats[seq] = {
                'Sequences': str(seq_number_by_seq_type.get(seq, 0)),
                'Crams': str(cram_number_by_seq_type.get(seq, 0)),
                'Seqr': str(seqr_stats_by_seq_type.get(seq, 0)),
            }

        return ProjectSummary(
            participants=pmodels,
            participant_keys=participant_keys,
            sample_keys=sample_keys,
            sequence_keys=sequence_keys,
            total_samples=total_samples,
            total_participants=total_participants,
            sequence_stats=sequence_stats,
        )
