import request from './request'
import type { ManagedUser, Role } from '@/types'

export async function listUsers(): Promise<ManagedUser[]> {
  const { data } = await request.get<ManagedUser[]>('/users')
  return data
}

export async function listRoles(): Promise<Role[]> {
  const { data } = await request.get<Role[]>('/users/roles')
  return data
}

export async function assignUserRole(
  userId: string,
  roleId: string,
): Promise<void> {
  await request.post(`/users/${userId}/roles`, { role_id: roleId })
}

export async function removeUserRole(
  userId: string,
  roleId: string,
): Promise<void> {
  await request.delete(`/users/${userId}/roles/${roleId}`)
}
