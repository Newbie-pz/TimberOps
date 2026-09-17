import request from '@/api/request'
import type { CargoType, WeighingStatus } from '@/types'

export interface StatusDistributionItem {
  status: WeighingStatus
  count: number
}

export interface CargoWeightRankingItem {
  cargo_type: CargoType
  completed_task_count: number
  total_net_weight_tons: string
}

export interface VehicleTransportRankingItem {
  vehicle_id: string
  plate_number: string
  completed_task_count: number
  total_net_weight_tons: string
}

export interface DashboardOverview {
  business_date: string
  timezone: 'UTC+08:00'
  currency: 'CNY'
  today_task_count: number
  today_completed_task_count: number
  pending_task_count: number
  today_completed_net_weight_tons: string
  today_income: string
  status_distribution: StatusDistributionItem[]
  cargo_weight_ranking: CargoWeightRankingItem[]
  vehicle_transport_ranking: VehicleTransportRankingItem[]
}

export async function getDashboardOverview(): Promise<DashboardOverview> {
  const { data } = await request.get<DashboardOverview>('/dashboard/overview')
  return data
}
