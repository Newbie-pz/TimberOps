import request from '@/api/request'
import type { CargoType } from '@/types'

export type ReportType = 'daily' | 'monthly'

export interface ReportCargoRankingItem {
  cargo_type: CargoType
  completed_task_count: number
  total_net_weight_tons: string
}

export interface ReportVehicleRankingItem {
  vehicle_id: string
  plate_number: string
  completed_task_count: number
  total_net_weight_tons: string
}

export interface BusinessReport {
  report_type: ReportType
  period_start: string
  period_end: string
  timezone: 'UTC+08:00'
  currency: 'CNY'
  task_count: number
  completed_task_count: number
  completed_net_weight_tons: string
  income: string
  cargo_ranking: ReportCargoRankingItem[]
  vehicle_ranking: ReportVehicleRankingItem[]
}

export interface ReportSelection {
  report_type: ReportType
  report_date?: string
  year?: number
  month?: number
}

export interface ReportExportFile {
  blob: Blob
  filename: string
}

export async function getDailyReport(reportDate: string): Promise<BusinessReport> {
  const { data } = await request.get<BusinessReport>('/reports/daily', {
    params: { report_date: reportDate },
  })
  return data
}

export async function getMonthlyReport(year: number, month: number): Promise<BusinessReport> {
  const { data } = await request.get<BusinessReport>('/reports/monthly', {
    params: { year, month },
  })
  return data
}

export async function exportReport(selection: ReportSelection): Promise<ReportExportFile> {
  const response = await request.get<Blob>('/reports/export', {
    params: selection,
    responseType: 'blob',
  })
  const disposition = response.headers['content-disposition'] as string | undefined
  const filename = disposition?.match(/filename="?([^";]+)"?/i)?.[1] || 'timberops-report.xlsx'
  return { blob: response.data, filename }
}
