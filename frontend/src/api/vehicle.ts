import request from './request'
import type { Vehicle, VehicleCreate, VehicleUpdate } from '@/types'

export async function listVehicles(): Promise<Vehicle[]> {
  const { data } = await request.get<Vehicle[]>('/vehicles')
  return data
}

export async function getVehicle(id: string): Promise<Vehicle> {
  const { data } = await request.get<Vehicle>(`/vehicles/${id}`)
  return data
}

export async function createVehicle(payload: VehicleCreate): Promise<Vehicle> {
  const { data } = await request.post<Vehicle>('/vehicles', payload)
  return data
}

export async function updateVehicle(
  id: string,
  payload: VehicleUpdate,
): Promise<Vehicle> {
  const { data } = await request.patch<Vehicle>(`/vehicles/${id}`, payload)
  return data
}
