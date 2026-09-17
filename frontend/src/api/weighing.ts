import request from './request'
import type {
  CargoCatalog,
  ReweighInput,
  TaskDetailResponse,
  WeighingRecord,
  WeighingTask,
  WeighingTaskCreate,
  WeighingTaskFilters,
  WeighingExportFile,
  WeighingExportFilters,
  WeightInput,
} from '@/types'

export async function getCargoCatalog(): Promise<CargoCatalog> {
  const { data } = await request.get<CargoCatalog>('/weighing/cargo-catalog')
  return data
}

export async function createWeighingTask(
  payload: WeighingTaskCreate,
): Promise<WeighingTask> {
  const { data } = await request.post<WeighingTask>('/weighing/tasks', payload)
  return data
}

export async function listWeighingTasks(
  filters: WeighingTaskFilters = {},
): Promise<WeighingTask[]> {
  const { data } = await request.get<WeighingTask[]>('/weighing/tasks', {
    params: filters,
  })
  return data
}

export async function getWeighingTask(id: string): Promise<TaskDetailResponse> {
  const { data } = await request.get<TaskDetailResponse>(`/weighing/tasks/${id}`)
  return data
}

export async function listWeighingRecords(id: string): Promise<WeighingRecord[]> {
  const { data } = await request.get<WeighingRecord[]>(
    `/weighing/tasks/${id}/records`,
  )
  return data
}

export async function recordTare(
  id: string,
  payload: WeightInput,
): Promise<WeighingTask> {
  const { data } = await request.post<WeighingTask>(
    `/weighing/tasks/${id}/tare`,
    payload,
  )
  return data
}

export async function finishLoading(id: string): Promise<WeighingTask> {
  const { data } = await request.post<WeighingTask>(
    `/weighing/tasks/${id}/wait-gross`,
  )
  return data
}

export async function recordGross(
  id: string,
  payload: WeightInput,
): Promise<WeighingTask> {
  const { data } = await request.post<WeighingTask>(
    `/weighing/tasks/${id}/gross`,
    payload,
  )
  return data
}

export async function recordReweigh(
  id: string,
  payload: ReweighInput,
): Promise<WeighingTask> {
  const { data } = await request.post<WeighingTask>(
    `/weighing/tasks/${id}/reweigh`,
    payload,
  )
  return data
}

export async function completeWeighingTask(id: string): Promise<WeighingTask> {
  const { data } = await request.post<WeighingTask>(
    `/weighing/tasks/${id}/complete`,
  )
  return data
}

export async function deleteWeighingTask(
  id: string,
  reason: string,
): Promise<void> {
  await request.delete(`/weighing/tasks/${id}`, { data: { reason } })
}

export async function exportWeighingHistory(
  filters: WeighingExportFilters,
): Promise<WeighingExportFile> {
  const response = await request.get<Blob>('/export/weighing', {
    params: filters,
    responseType: 'blob',
  })
  const disposition = response.headers['content-disposition'] || ''
  const matchedFilename = disposition.match(/filename="?([^";]+)"?/i)?.[1]
  return {
    blob: response.data,
    filename: matchedFilename || 'timberops-weighing.xlsx',
  }
}
