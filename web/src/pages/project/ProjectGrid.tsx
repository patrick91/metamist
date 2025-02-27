import * as React from 'react'
import _, { capitalize } from 'lodash'
import { Table as SUITable, Form, Popup } from 'semantic-ui-react'

import FilterAltIcon from '@mui/icons-material/FilterAlt'
import FilterAltOutlinedIcon from '@mui/icons-material/FilterAltOutlined'
import CloseIcon from '@mui/icons-material/Close'
import { IconButton } from '@mui/material'
import Table from '../../shared/components/Table'
import SampleLink from '../../shared/components/links/SampleLink'
import FamilyLink from '../../shared/components/links/FamilyLink'
import sanitiseValue from '../../shared/utilities/sanitiseValue'
import { ProjectSummary, MetaSearchEntityPrefix } from '../../sm-api/api'
import SequencingGroupLink from '../../shared/components/links/SequencingGroupLink'

interface ProjectGridProps {
    summary: ProjectSummary
    projectName: string
    filterValues: Record<
        string,
        { value: string; category: MetaSearchEntityPrefix; title: string; field: string }
    >
    updateFilters: (e: {
        [k: string]: {
            value: string
            category: MetaSearchEntityPrefix
            title: string
            field: string
        }
    }) => void
}

const formatExternalIds = (ids: Record<string, string>) => {
    return Object.entries(ids)
        .map(([k, v]) => (k.length === 0 ? sanitiseValue(v) : `${k}: ${v}`))
        .join(', ')
}

const ProjectGrid: React.FunctionComponent<ProjectGridProps> = ({
    summary,
    projectName,
    filterValues,
    updateFilters,
}) => {
    let headers = [
        {
            name: 'external_id',
            title: 'Family ID',
            category: MetaSearchEntityPrefix.F,
            first: true,
        },
        ...summary.participant_keys.map((field, i) => ({
            category: MetaSearchEntityPrefix.P,
            name: field[0],
            title: field[1],
            first: i === 0,
        })),
        ...summary.sample_keys.map((field, i) => ({
            category: MetaSearchEntityPrefix.S,
            name: field[0],
            title: field[1],
            first: i === 0,
        })),
        ...summary.sequencing_group_keys.map((field, i) => ({
            category: MetaSearchEntityPrefix.Sg,
            name: field[0],
            title: `${field[1]}`,
            first: i === 0,
        })),
        ...summary.assay_keys.map((field, i) => ({
            category: MetaSearchEntityPrefix.A,
            name: field[0],
            title: `${field[1]}`,
            first: i === 0,
        })),
    ]

    let headerGroups = [
        { title: 'Family', width: 1 },
        { title: 'Participant', width: summary.participant_keys.length },
        { title: 'Sample', width: summary.sample_keys.length },
        { title: 'Sequencing Group', width: summary.sequencing_group_keys.length },
        { title: 'Assay', width: summary.assay_keys.length },
    ]

    const [tempFilterValues, setTempFilterValues] =
        React.useState<
            Record<
                string,
                { value: string; category: MetaSearchEntityPrefix; title: string; field: string }
            >
        >(filterValues)

    const onFilterValueChange = (
        e: React.ChangeEvent<HTMLInputElement>,
        category: MetaSearchEntityPrefix,
        title: string
    ) => {
        const { name } = e.target
        const { value } = e.target
        setTempFilterValues({
            ...Object.keys(tempFilterValues)
                .filter((key) => `${category}.${name}` !== key)
                .reduce((res, key) => Object.assign(res, { [key]: tempFilterValues[key] }), {}),
            ...(value && { [`${category}.${name}`]: { value, category, title, field: name } }),
        })
    }

    const onClear = (column: string, category: MetaSearchEntityPrefix) => {
        updateFilters({
            ...Object.keys(tempFilterValues)
                .filter((key) => `${category}.${column}` !== key)
                .reduce((res, key) => Object.assign(res, { [key]: tempFilterValues[key] }), {}),
        })
    }

    const onSubmit = () => {
        updateFilters(tempFilterValues)
    }

    if (summary.participants.length === 0 && Object.keys(filterValues).length) {
        headers = Object.entries(filterValues).map(([, { field, category, title }]) => ({
            name: field,
            category,
            title,
            first: true,
        }))
        headerGroups = []
    }

    return (
        <Table
            className="projectSummaryGrid"
            celled
            style={{
                borderCollapse: 'collapse',
                borderTop: '2px solid var(--color-border-color)',
                borderRight: '2px solid var(--color-border-color)',
                borderBottom: '2px solid var(--color-border-color)',
            }}
        >
            <SUITable.Header>
                <SUITable.Row>
                    {headerGroups.map(({ title, width }) => (
                        <SUITable.HeaderCell
                            key={`${title}`}
                            colSpan={width}
                            style={{
                                textAlign: 'center',
                                borderLeft: '2px solid var(--color-border-color)',
                                borderBottom: '2px solid var(--color-border-default)',
                                backgroundColor: 'var(--color-table-header)',
                            }}
                        >
                            {title}
                        </SUITable.HeaderCell>
                    ))}
                </SUITable.Row>
            </SUITable.Header>
            <SUITable.Header>
                <SUITable.Row>
                    {headers.map(({ name, category, title, first }, i) => {
                        if (
                            title === 'Sample ID' ||
                            title === 'Created date' ||
                            title === 'Sequencing Group ID'
                        ) {
                            return (
                                <SUITable.HeaderCell
                                    key={`filter-${name}-${i}`}
                                    style={{
                                        borderBottom: 'none',
                                        borderLeft: first
                                            ? '2px solid var(--color-border-color)'
                                            : '1px solid var(--color-border-default)',
                                    }}
                                ></SUITable.HeaderCell>
                            )
                        }
                        return (
                            <SUITable.HeaderCell
                                key={`filter-${title}-${i}`}
                                style={{
                                    borderBottom: 'none',
                                    borderLeft: first
                                        ? '2px solid var(--color-border-color)'
                                        : '1px solid var(--color-border-default)',
                                }}
                            >
                                <div style={{ position: 'relative' }}>
                                    <div style={{ position: 'absolute', top: 0, right: 0 }}>
                                        <Popup
                                            position={
                                                summary.participants.length === 0
                                                    ? 'top right'
                                                    : 'top center'
                                            }
                                            trigger={
                                                `${category}.${name}` in filterValues ? (
                                                    <FilterAltIcon />
                                                ) : (
                                                    <FilterAltOutlinedIcon />
                                                )
                                            }
                                            hoverable
                                        >
                                            <Form onSubmit={onSubmit}>
                                                <Form.Group
                                                    inline
                                                    style={{ padding: 0, margin: 0 }}
                                                >
                                                    <Form.Field style={{ padding: 0, margin: 0 }}>
                                                        <Form.Input
                                                            action={{ icon: 'search' }}
                                                            placeholder="Filter..."
                                                            name={name}
                                                            value={
                                                                tempFilterValues[
                                                                    `${category}.${name}`
                                                                ]?.value || ''
                                                            }
                                                            onChange={(e) =>
                                                                onFilterValueChange(
                                                                    e,
                                                                    category,
                                                                    title
                                                                )
                                                            }
                                                        />
                                                    </Form.Field>
                                                    {`${category}.${name}` in filterValues && (
                                                        <Form.Field style={{ padding: 0 }}>
                                                            <IconButton
                                                                onClick={() =>
                                                                    onClear(name, category)
                                                                }
                                                                style={{ padding: 0 }}
                                                            >
                                                                <CloseIcon />
                                                            </IconButton>
                                                        </Form.Field>
                                                    )}
                                                </Form.Group>
                                            </Form>
                                        </Popup>
                                    </div>
                                </div>
                            </SUITable.HeaderCell>
                        )
                    })}
                </SUITable.Row>
            </SUITable.Header>
            <SUITable.Header>
                <SUITable.Row>
                    {headers.map(({ name, title, first }, i) => (
                        <SUITable.HeaderCell
                            key={`${name}-${i}`}
                            style={{
                                borderLeft: first
                                    ? '2px solid var(--color-border-color)'
                                    : '1px solid var(--color-border-default)',
                                borderBottom: '2px solid var(--color-border-default)',
                            }}
                        >
                            {title.includes(' ') ? title : capitalize(title)}
                        </SUITable.HeaderCell>
                    ))}
                </SUITable.Row>
            </SUITable.Header>
            <SUITable.Body>
                {summary.participants.map((p, pidx) =>
                    p.samples.map((s, sidx) => {
                        const backgroundColor =
                            pidx % 2 === 0 ? 'var(--color-bg)' : 'var(--color-bg-disabled)'
                        // const border = '1px solid #dee2e6'
                        const lengthOfParticipant = p.samples
                            .map((s_) =>
                                // do 1 here, because we want to show at least 1 row, even if there are
                                // no sequencing groups OR assays
                                Math.max(
                                    1,
                                    (s_.sequencing_groups ?? [])
                                        .map((a_) => (a_.assays ?? []).length)
                                        .reduce((a, b) => a + b, 0)
                                )
                            )
                            .reduce((a, b) => a + b, 0)

                        const lengthOfSamples = (s.sequencing_groups ?? [])
                            .map((a_) => (a_.assays ?? []).length)
                            .reduce((a, b) => a + b, 0)

                        const participantRowSpan =
                            lengthOfParticipant > 0 ? lengthOfParticipant : undefined
                        const samplesRowSpan = lengthOfSamples > 0 ? lengthOfSamples : undefined

                        let sgs = s.sequencing_groups || []
                        if (!sgs || sgs.length === 0) {
                            // @ts-ignore
                            sgs = [{}]
                        }
                        return sgs.map((sg, sgidx) =>
                            (sg.assays?.length > 0 ? sg.assays : [{}]).map((assay, assayidx) => {
                                const isFirstOfGroup = sidx === 0 && sgidx === 0 && assayidx === 0
                                const border = '1px solid #dee2e6'
                                // const border = '1px solid'
                                // debugger
                                return (
                                    <SUITable.Row key={`${p.id}-${s.id}-${sg.id}-${assay.id}`}>
                                        {isFirstOfGroup && (
                                            <SUITable.Cell
                                                style={{
                                                    backgroundColor,
                                                    borderRight: border,
                                                    borderBottom: border,
                                                    borderTop: border,
                                                    borderLeft:
                                                        '2px solid var(--color-border-color)',
                                                }}
                                                rowSpan={participantRowSpan}
                                            >
                                                {
                                                    <FamilyLink
                                                        id={p.families.map((f) => f.id).join(', ')}
                                                        projectName={projectName}
                                                    >
                                                        {p.families
                                                            .map((f) => f.external_id)
                                                            .join(', ')}
                                                    </FamilyLink>
                                                }
                                            </SUITable.Cell>
                                        )}
                                        {isFirstOfGroup &&
                                            summary.participant_keys.map(([k], i) => (
                                                <SUITable.Cell
                                                    style={{
                                                        backgroundColor,
                                                        borderRight: border,
                                                        borderBottom: border,
                                                        borderTop: border,
                                                        borderLeft:
                                                            i === 0
                                                                ? '2px solid var(--color-border-color)'
                                                                : '1px solid var(--color-border-default)',
                                                    }}
                                                    key={`${p.id}participant.${k}`}
                                                    rowSpan={participantRowSpan}
                                                >
                                                    {k === 'external_ids'
                                                        ? formatExternalIds(p.external_ids)
                                                        : sanitiseValue(_.get(p, k))}
                                                </SUITable.Cell>
                                            ))}
                                        {sgidx === 0 &&
                                            assayidx === 0 &&
                                            summary.sample_keys.map(([k], i) => (
                                                <SUITable.Cell
                                                    style={{
                                                        backgroundColor,
                                                        borderRight: border,
                                                        borderBottom: border,
                                                        borderTop: border,
                                                        borderLeft:
                                                            i === 0
                                                                ? '2px solid var(--color-border-color)'
                                                                : '1px solid var(--color-border-default)',
                                                        // border,
                                                    }}
                                                    key={`${s.id}sample.${k}`}
                                                    rowSpan={samplesRowSpan}
                                                >
                                                    {k === 'external_ids' || k === 'id' ? (
                                                        <SampleLink
                                                            id={s.id}
                                                            projectName={projectName}
                                                        >
                                                            {k === 'external_ids'
                                                                ? formatExternalIds(s.external_ids)
                                                                : sanitiseValue(s.id)}
                                                        </SampleLink>
                                                    ) : (
                                                        sanitiseValue(_.get(s, k))
                                                    )}
                                                </SUITable.Cell>
                                            ))}
                                        {assayidx === 0 &&
                                            summary.sequencing_group_keys.map(([k], i) => (
                                                <SUITable.Cell
                                                    style={{
                                                        borderRight: border,
                                                        borderBottom: border,
                                                        borderTop: border,
                                                        borderLeft:
                                                            i === 0
                                                                ? '2px solid var(--color-border-color)'
                                                                : '1px solid var(--color-border-default)',
                                                        backgroundColor,
                                                    }}
                                                    key={`${s.id}sequencing_group.${k}`}
                                                    rowSpan={
                                                        (sg.assays ?? []).length > 0
                                                            ? (sg.assays ?? []).length
                                                            : undefined
                                                    }
                                                >
                                                    {k === 'id' ? (
                                                        <SequencingGroupLink
                                                            projectName={projectName}
                                                            id={s.id}
                                                            sg_id={_.get(sg, 'id')?.toString()}
                                                        >
                                                            {sanitiseValue(_.get(sg, k))}
                                                        </SequencingGroupLink>
                                                    ) : (
                                                        sanitiseValue(_.get(sg, k))
                                                    )}
                                                </SUITable.Cell>
                                            ))}
                                        {summary.assay_keys.map(([k], i) => (
                                            <SUITable.Cell
                                                style={{
                                                    backgroundColor,
                                                    borderRight: border,
                                                    borderBottom: border,
                                                    borderTop: border,
                                                    borderLeft:
                                                        i === 0
                                                            ? '2px solid var(--color-border-color)'
                                                            : '1px solid var(--color-border-default)',
                                                    // border,
                                                }}
                                                key={`${s.id}assay.${k}`}
                                            >
                                                {sanitiseValue(_.get(assay, k))}
                                            </SUITable.Cell>
                                        ))}
                                    </SUITable.Row>
                                )
                            })
                        )
                    })
                )}
            </SUITable.Body>
        </Table>
    )
}

export default ProjectGrid
