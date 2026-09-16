import type { CargoType, WeighingStatus, WeightResult, WeightType } from '@/types'

export const cargoTypeLabel: Record<CargoType, string> = {
  ORE: '矿石',
  COAL: '煤炭',
  TIMBER: '木材',
  OTHER: '其他',
}

export const statusLabel: Record<WeighingStatus, string> = {
  WAIT_TARE: '等待空车称重',
  TARE_COMPLETED: '空车称重完成',
  WAIT_GROSS: '等待重车称重',
  GROSS_COMPLETED: '重车称重完成',
  COMPLETED: '已完成',
  CANCELLED: '已取消',
}

export const weightResultLabel: Record<WeightResult, string> = {
  PENDING: '待判定',
  NORMAL: '正常',
  OVERWEIGHT: '超重',
}

export const weightTypeLabel: Record<WeightType, string> = {
  TARE: '空车皮重',
  GROSS: '首次毛重',
  REWEIGH: '复磅毛重',
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return '—'
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(new Date(value))
}

export function isValidTons(value: string): boolean {
  return /^(?:0|[1-9]\d{0,6})(?:\.\d{1,3})?$/.test(value) && /[1-9]/.test(value)
}

function tonsToMilliTons(value: string): bigint | null {
  const match = value.match(/^(\d+)(?:\.(\d{1,3}))?$/)
  if (!match) return null
  return BigInt(match[1]) * 1000n + BigInt((match[2] || '').padEnd(3, '0'))
}

function formatMilliTons(value: bigint): string {
  const sign = value < 0n ? '-' : ''
  const absolute = value < 0n ? -value : value
  return `${sign}${absolute / 1000n}.${String(absolute % 1000n).padStart(3, '0')}`
}

export function subtractTons(left: string, right: string): string | null {
  const leftValue = tonsToMilliTons(left)
  const rightValue = tonsToMilliTons(right)
  if (leftValue === null || rightValue === null) return null
  return formatMilliTons(leftValue - rightValue)
}

export function positiveDifference(left: string, right: string): string | null {
  const difference = subtractTons(left, right)
  if (difference === null) return null
  return difference.startsWith('-') ? '0.000' : difference
}
