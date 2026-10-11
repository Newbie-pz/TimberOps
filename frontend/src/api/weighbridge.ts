import request from './request'
import type { WeighbridgeStatus, WeighbridgeWeightReading } from '@/types'

export async function getWeighbridgeStatus(): Promise<WeighbridgeStatus> {
  const { data } = await request.get<WeighbridgeStatus>('/weighbridge/status')
  return data
}

export async function getWeighbridgeWeight(): Promise<WeighbridgeWeightReading> {
  const { data } = await request.get<WeighbridgeWeightReading>('/weighbridge/weight')
  return data
}
