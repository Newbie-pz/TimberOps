import request from '@/api/request'
import type { AuditLog, AuditLogFilters } from '@/types'

export async function listAuditLogs(
  filters: AuditLogFilters = {},
): Promise<AuditLog[]> {
  const { data } = await request.get<AuditLog[]>('/audit/logs', {
    params: filters,
  })
  return data
}
