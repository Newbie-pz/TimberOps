import request from './request'
import type { Customer, CustomerCreate, CustomerUpdate } from '@/types'

export async function listCustomers(): Promise<Customer[]> {
  const { data } = await request.get<Customer[]>('/customers')
  return data
}

export async function getCustomer(id: string): Promise<Customer> {
  const { data } = await request.get<Customer>(`/customers/${id}`)
  return data
}

export async function createCustomer(payload: CustomerCreate): Promise<Customer> {
  const { data } = await request.post<Customer>('/customers', payload)
  return data
}

export async function updateCustomer(
  id: string,
  payload: CustomerUpdate,
): Promise<Customer> {
  const { data } = await request.patch<Customer>(`/customers/${id}`, payload)
  return data
}

export async function deleteCustomer(id: string, reason: string): Promise<void> {
  await request.delete(`/customers/${id}`, { data: { reason } })
}
