import request from '@/api/request'
import type { BillingListItem, BillingRecord, BillingRecordFilters } from '@/types'

export async function listBillingRecords(
  filters: BillingRecordFilters = {},
): Promise<BillingListItem[]> {
  const { data } = await request.get<BillingListItem[]>('/billing/records', {
    params: filters,
  })
  return data
}

export async function payBillingRecord(id: string): Promise<BillingRecord> {
  const { data } = await request.patch<BillingRecord>(`/billing/records/${id}/pay`)
  return data
}

export async function waiveBillingRecord(id: string): Promise<BillingRecord> {
  const { data } = await request.patch<BillingRecord>(`/billing/records/${id}/waive`)
  return data
}
