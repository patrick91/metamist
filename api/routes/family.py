# pylint: disable=invalid-name
import codecs
import csv
from typing import List, Optional
import io
from datetime import date

from fastapi import APIRouter, UploadFile, File, Query
from pydantic import BaseModel
from starlette.responses import StreamingResponse

from api.utils import get_projectless_db_connection
from api.utils.db import (
    get_project_readonly_connection,
    get_project_write_connection,
    Connection,
)
from db.python.layers.family import FamilyLayer
from models.models.family import Family

router = APIRouter(prefix='/family', tags=['family'])


class FamilyUpdateModel(BaseModel):
    """Model for updating a family"""

    id: int
    external_id: Optional[str] = None
    description: Optional[str] = None
    coded_phenotype: Optional[str] = None


@router.post('/{project}/pedigree', operation_id='importPedigree')
async def import_pedigree(
    file: UploadFile = File(...),
    has_header: bool = False,
    create_missing_participants: bool = False,
    connection: Connection = get_project_write_connection,
):
    """Get sample by external ID"""
    family_layer = FamilyLayer(connection)
    reader = csv.reader(codecs.iterdecode(file.file, 'utf-8-sig'), delimiter='\t')
    headers = None
    if has_header:
        headers = next(reader)

    rows = [r for r in reader if not r[0].startswith('#')]
    if len(rows[0]) == 1:
        raise ValueError(
            'Only one column was detected in the pedigree, ensure the file is TAB separated (\\t)'
        )

    return {
        'success': await family_layer.import_pedigree(
            headers, rows, create_missing_participants=create_missing_participants
        )
    }


@router.get(
    '/{project}/pedigree', operation_id='getPedigree', response_class=StreamingResponse
)
async def get_pedigree(
    internal_family_ids: List[int] = Query(None),
    replace_with_participant_external_ids: bool = False,
    replace_with_family_external_ids: bool = False,
    empty_participant_value: Optional[str] = '',
    include_header: bool = True,
    connection: Connection = get_project_readonly_connection,
):
    """
    Generate tab-separated Pedigree file for ALL families
    unless internal_family_ids is specified.

    Allow replacement of internal participant and family IDs
    with their external counterparts.
    """
    family_layer = FamilyLayer(connection)
    pedigree_rows = await family_layer.get_pedigree(
        project=connection.project,
        family_ids=internal_family_ids,
        replace_with_participant_external_ids=replace_with_participant_external_ids,
        replace_with_family_external_ids=replace_with_family_external_ids,
        empty_participant_value=empty_participant_value,
        include_header=include_header,
    )

    output = io.StringIO()
    writer = csv.writer(output, delimiter='\t')
    writer.writerows(pedigree_rows)

    basefn = f'{connection.project}-{date.today().isoformat()}'

    if internal_family_ids:
        basefn += '-'.join(str(fm) for fm in internal_family_ids)

    return StreamingResponse(
        iter(output.getvalue()),
        media_type='text/csv',
        headers={'Content-Disposition': f'filename={basefn}.ped'},
    )


@router.get('/{project}/', operation_id='getFamilies')
async def get_families(
    connection: Connection = get_project_readonly_connection,
) -> List[Family]:
    """Get families for some project"""
    family_layer = FamilyLayer(connection)
    return await family_layer.get_families()


@router.post('/', operation_id='updateFamily')
async def update_family(
    family: FamilyUpdateModel, connection: Connection = get_projectless_db_connection
):
    """Update information for a single family"""
    family_layer = FamilyLayer(connection)
    return {
        'success': await family_layer.update_family(
            id_=family.id,
            external_id=family.external_id,
            description=family.description,
            coded_phenotype=family.coded_phenotype,
        )
    }


@router.post('/{project}/family-template', operation_id='importFamilies')
async def import_families(
    file: UploadFile = File(...),
    has_header: bool = True,
    delimiter='\t',
    connection: Connection = get_project_write_connection,
):
    """Get sample by external ID"""
    delimiter = delimiter.replace('\\t', '\t')

    family_layer = FamilyLayer(connection)
    reader = csv.reader(codecs.iterdecode(file.file, 'utf-8-sig'), delimiter=delimiter)
    headers = None
    if has_header:
        headers = next(reader)

    rows = [r for r in reader if not r[0].startswith('#')]
    if len(rows[0]) == 1:
        raise ValueError(
            'Only one column was detected in the pedigree, ensure the file is TAB separated (\\t)'
        )
    success = await family_layer.import_families(headers, rows)
    return {'success': success}
