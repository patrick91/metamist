import * as React from 'react'
import { Table as SUITable, Popup, Checkbox } from 'semantic-ui-react'
import _ from 'lodash'
import Table from '../../../shared/components/Table'
import sanitiseValue from '../../../shared/utilities/sanitiseValue'
import '../../project/AnalysisRunnerView/AnalysisGrid.css'

interface Field {
    category: string
    title: string
    width?: string
    className?: string
    dataMap?: (data: any, value: string) => any
}

function setFieldValue(field: string, value: any, rec: any) {
    // set field value if not undefined
    if (value !== undefined) {
        rec[field] = value
    }
}

function prepareTotalRow(data: any[], key: string) {
    // aggregate data by key
    console.log(data)
    const aggData: any[] = []
    data.forEach((curr) => {
        const { cost, topic, usage_start_time, usage_end_time, creator } = curr
        const usageStartDate = new Date(usage_start_time)
        const usageEndDate = new Date(usage_end_time)
        const ar_guid = curr['ar-guid']
        const cromwell_id = curr['cromwell-workflow-id']
        const goog_pipelines_worker = curr['goog-pipelines-worker']
        const compute_category = curr['compute-category']
        // specific for datproc jobs
        const dataproc_autozone = curr['goog-dataproc-autozone']
        const dataproc_name = curr['goog-dataproc-cluster-name']
        const dataproc_uuid = curr['goog-dataproc-cluster-uuid']
        const dataproc_location = curr['goog-dataproc-location']

        const idx = aggData.findIndex((d) => d.key === curr[key])
        if (curr[key] !== undefined && cost >= 0) {
            // do not include credits, should be filter out at API?
            if (idx === -1) {
                const rec = {
                    type: key,
                    key: curr[key],
                    ar_guid,
                    compute_category,
                    topic,
                    cost,
                    start_time: usageStartDate,
                    end_time: usageEndDate,
                    wdl_task_name: key === 'wdl-task-name' ? curr[key] : undefined,
                    cromwell_sub: key === 'cromwell-sub-workflow-name' ? curr[key] : undefined,
                    seq_group_id: key === 'seq_group_id' ? curr[key] : undefined,
                }

                // append specific fields for dataproc jobs / cromwell jobs
                setFieldValue('goog_pipelines_worker', goog_pipelines_worker, rec)
                setFieldValue('cromwell_id', cromwell_id, rec)
                setFieldValue('creator', creator, rec)
                setFieldValue('dataproc_autozone', dataproc_autozone, rec)
                setFieldValue('dataproc_name', dataproc_name, rec)
                setFieldValue('dataproc_uuid', dataproc_uuid, rec)
                setFieldValue('dataproc_location', dataproc_location, rec)

                // append to aggData
                aggData.push(rec)
            } else {
                aggData[idx].cost += cost
                aggData[idx].start_time = new Date(
                    Math.min(usageStartDate.getTime(), aggData[idx].start_time.getTime())
                )
                aggData[idx].end_time = new Date(
                    Math.max(usageEndDate.getTime(), aggData[idx].end_time.getTime())
                )
            }
        }
    })

    return aggData
}

function prepareDetails(data: any[], key: string) {
    // aggregate data by key
    const aggData: any[] = []
    data.forEach((curr) => {
        const { cost, topic, sku } = curr
        const ar_guid = curr['ar-guid']
        const cromwell_id = curr['cromwell-workflow-id']
        const idx = aggData.findIndex(
            (d) => d.key === curr[key] && d.batch_resource === sku.description
        )
        if (curr[key] !== undefined && cost >= 0) {
            // do not include credits, should be filter out at API?
            if (idx === -1) {
                aggData.push({
                    type: key,
                    key: curr[key],
                    ar_guid,
                    cromwell_id,
                    topic,
                    cost,
                    wdl_task_name: key === 'wdl-task-name' ? curr[key] : undefined,
                    cromwell_sub: key === 'cromwell-sub-workflow-name' ? curr[key] : undefined,
                    seq_group_id: key === 'seq_group_id' ? curr[key] : undefined,
                    batch_resource: sku.description,
                })
            } else {
                aggData[idx].cost += cost
            }
        }
    })

    return aggData
}

const CromwellDataProcGrid: React.FunctionComponent<{
    data: any[]
}> = ({ data }) => {
    // prepare aggregated row by ar_guid, wdl, sub, seq
    const aggArGUIDData: any[] = prepareTotalRow(data, 'ar-guid')
    const aggSubData: any[] = prepareTotalRow(data, 'cromwell-sub-workflow-name')
    const aggWDLData: any[] = prepareTotalRow(data, 'wdl-task-name')
    const aggSGData: any[] = prepareTotalRow(data, 'seq_group_id')

    // prepare detailed cost per sku
    const aggArGUIDDetails: any[] = prepareDetails(data, 'ar-guid')
    const aggSubDetails: any[] = prepareDetails(data, 'cromwell-sub-workflow-name')
    const aggWDLDetails: any[] = prepareDetails(data, 'wdl-task-name')
    const aggSGDetails: any[] = prepareDetails(data, 'seq_group_id')

    const aggData = [...aggArGUIDData, ...aggWDLData, ...aggSubData, ...aggSGData]
    const aggResource = [...aggArGUIDDetails, ...aggSubDetails, ...aggWDLDetails, ...aggSGDetails]

    // combine data and resource for each ar_guid, wdl, sub, seq
    const combinedData = aggData.map((dataItem) => {
        const details = aggResource.filter(
            (resourceItem) =>
                resourceItem.key === dataItem.key && resourceItem.type === dataItem.type
        )
        return { ...dataItem, details }
    })

    const [openRows, setOpenRows] = React.useState<number[]>([])

    const handleToggle = (position: number) => {
        if (!openRows.includes(position)) {
            setOpenRows([...openRows, position])
        } else {
            setOpenRows(openRows.filter((i) => i !== position))
        }
    }

    const prepareBgColor = (log: any) => {
        if (
            log.wdl_task_name === undefined &&
            log.cromwell_sub === undefined &&
            log.seq_group_id === undefined
        ) {
            return 'var(--color-border-color)'
        }
        return 'var(--color-bg)'
    }

    const MAIN_FIELDS: Field[] = [
        {
            category: 'job_id',
            title: 'ID',
            dataMap: (dataItem: any, _value: string) => {
                if (dataItem.wdl_task_name !== undefined) {
                    return `WDL TASK: ${dataItem.wdl_task_name}`
                }
                if (dataItem.cromwell_sub !== undefined) {
                    return `CROMWELL SUB WORKFLOW : ${dataItem.cromwell_sub}`
                }
                if (dataItem.seq_group_id !== undefined) {
                    return `SEQ GROUP : ${dataItem.seq_group_id}`
                }
                return `AR GUID: ${dataItem.ar_guid}`
            },
        },
        {
            category: 'start_time',
            title: 'TIME STARTED',
            dataMap: (dataItem: any, value: string) => {
                const dateValue = new Date(value)
                return (
                    <span>
                        {Number.isNaN(dateValue.getTime()) ? '' : dateValue.toLocaleString()}
                    </span>
                )
            },
        },
        {
            category: 'end_time',
            title: 'TIME COMPLETED',
            dataMap: (dataItem: any, value: string) => {
                const dateValue = new Date(value)
                return (
                    <span>
                        {Number.isNaN(dateValue.getTime()) ? '' : dateValue.toLocaleString()}
                    </span>
                )
            },
        },
        {
            category: 'duration',
            title: 'DURATION',
            dataMap: (dataItem: any, _value: string) => {
                const duration = new Date(
                    dataItem.end_time.getTime() - dataItem.start_time.getTime()
                )
                const seconds = Math.floor((duration / 1000) % 60)
                const minutes = Math.floor((duration / (1000 * 60)) % 60)
                const hours = Math.floor((duration / (1000 * 60 * 60)) % 24)
                const formattedDuration = `${hours}h ${minutes}m ${seconds}s`
                return <span>{formattedDuration}</span>
            },
        },
        {
            category: 'cost',
            title: 'COST',
            dataMap: (dataItem: any, _value: string) => (
                <Popup
                    content={dataItem.cost}
                    trigger={<span>${dataItem.cost.toFixed(4)}</span>}
                    position="top center"
                />
            ),
        },
    ]

    const DETAIL_FIELDS: Field[] = [
        {
            category: 'compute_category',
            title: 'COMPUTE CATEGORY',
        },
        {
            category: 'creator',
            title: 'CREATOR',
        },
        {
            category: 'topic',
            title: 'TOPIC',
        },
        {
            category: 'cromwell_id',
            title: 'CROMWELL WORKFLOW ID',
        },
        {
            category: 'goog_pipelines_worker',
            title: 'GOOGLE PIPELINES WORKER',
        },
        {
            category: 'dataproc_autozone',
            title: 'DATAPROC AUTOZONE',
        },
        {
            category: 'dataproc_name',
            title: 'DATAPROC CLUSTER NAME',
        },
        {
            category: 'dataproc_uuid',
            title: 'DATAPROC CLUSTER UUID',
        },
        {
            category: 'dataproc_location',
            title: 'DATAPROC LOCATION',
        },
    ]

    const expandedRow = (log: any, idx: any) =>
        MAIN_FIELDS.map(({ category, dataMap, className }) => (
            <SUITable.Cell key={`${category}-${idx}`} className={className}>
                {dataMap ? dataMap(log, log[category]) : sanitiseValue(log[category])}
            </SUITable.Cell>
        ))

    return (
        <Table celled compact sortable>
            <SUITable.Header>
                <SUITable.Row>
                    <SUITable.HeaderCell style={{ borderBottom: 'none' }} />
                    {MAIN_FIELDS.map(({ category, title }, i) => (
                        <SUITable.HeaderCell
                            key={`${category}-${i}`}
                            style={{
                                borderBottom: 'none',
                                position: 'sticky',
                                resize: 'horizontal',
                                textAlign: 'center',
                            }}
                        >
                            {title}
                        </SUITable.HeaderCell>
                    ))}
                </SUITable.Row>
                <SUITable.Row>
                    <SUITable.Cell
                        style={{
                            borderTop: 'none',
                            backgroundColor: 'var(--color-table-header)',
                        }}
                    />
                    {MAIN_FIELDS.map(({ category }, i) => (
                        <SUITable.Cell
                            className="sizeRow"
                            key={`${category}-resize-${i}`}
                            style={{
                                borderTop: 'none',
                                backgroundColor: 'var(--color-table-header)',
                            }}
                        ></SUITable.Cell>
                    ))}
                </SUITable.Row>
            </SUITable.Header>
            <SUITable.Body>
                {combinedData
                    .sort((a, b) => {
                        // Sorts an array of objects on cost
                        if (a.cost < b.cost) {
                            return 1
                        }
                        if (a.cost > b.cost) {
                            return -1
                        }
                        return 0
                    })
                    .map((log, idx) => (
                        <React.Fragment key={log.key}>
                            <SUITable.Row
                                className={log.job_id === undefined ? 'bold-text' : ''}
                                style={{
                                    backgroundColor: prepareBgColor(log),
                                    textAlign: 'center',
                                }}
                            >
                                <SUITable.Cell collapsing>
                                    <Checkbox
                                        checked={openRows.includes(log.key)}
                                        toggle
                                        onChange={() => handleToggle(log.key)}
                                    />
                                </SUITable.Cell>
                                {expandedRow(log, idx)}
                            </SUITable.Row>
                            {Object.entries(log)
                                .filter(([c]) =>
                                    DETAIL_FIELDS.map(({ category }) => category).includes(c)
                                )
                                .map(([k, v]) => {
                                    const detailField = DETAIL_FIELDS.find(
                                        ({ category }) => category === k
                                    )
                                    const title = detailField ? detailField.title : k
                                    return (
                                        <SUITable.Row
                                            style={{
                                                display: openRows.includes(log.key)
                                                    ? 'table-row'
                                                    : 'none',
                                                backgroundColor: 'var(--color-bg)',
                                            }}
                                            key={`${log.key}-detail-${k}`}
                                        >
                                            <SUITable.Cell style={{ border: 'none' }} />
                                            <SUITable.Cell>
                                                <b>{title}</b>
                                            </SUITable.Cell>
                                            <SUITable.Cell colSpan="4">{v}</SUITable.Cell>
                                        </SUITable.Row>
                                    )
                                })}
                            <SUITable.Row
                                style={{
                                    display: openRows.includes(log.key) ? 'table-row' : 'none',
                                    backgroundColor: 'var(--color-bg)',
                                }}
                                key={`${log.key}-lbl`}
                            >
                                <SUITable.Cell style={{ border: 'none' }} />
                                <SUITable.Cell colSpan="5">
                                    <b>COST BREAKDOWN</b>
                                </SUITable.Cell>
                            </SUITable.Row>
                            {typeof log === 'object' &&
                                'details' in log &&
                                _.orderBy(log?.details, ['cost'], ['desc']).map((dk) => (
                                    <SUITable.Row
                                        style={{
                                            display: openRows.includes(log.key)
                                                ? 'table-row'
                                                : 'none',
                                            backgroundColor: 'var(--color-bg)',
                                        }}
                                        key={`${log.key}-${dk.batch_resource}`}
                                    >
                                        <SUITable.Cell style={{ border: 'none' }} />
                                        <SUITable.Cell colSpan="4">
                                            {dk.batch_resource}
                                        </SUITable.Cell>
                                        <SUITable.Cell>${dk.cost.toFixed(4)}</SUITable.Cell>
                                    </SUITable.Row>
                                ))}
                        </React.Fragment>
                    ))}
            </SUITable.Body>
        </Table>
    )
}

export default CromwellDataProcGrid
