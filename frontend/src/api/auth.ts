import request from './request'
import type { LoginResponse, Permission, Role, User } from '@/types'

export interface RegisterPayload {
  username: string
  password: string
  real_name: string
}

export interface LoginPayload {
  username: string
  password: string
}

export async function register(payload: RegisterPayload): Promise<User> {
  const { data } = await request.post<User>('/auth/register', payload)
  return data
}

export async function login(payload: LoginPayload): Promise<LoginResponse> {
  const { data } = await request.post<LoginResponse>('/auth/login', payload)
  return data
}

export async function getCurrentUser(accessToken: string): Promise<User> {
  const { data } = await request.get<User>('/auth/me', {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
  return data
}

export async function getCurrentUserRoles(accessToken: string): Promise<Role[]> {
  const { data } = await request.get<Role[]>('/auth/roles', {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
  return data
}

export async function getCurrentUserPermissions(
  accessToken: string,
): Promise<Permission[]> {
  const { data } = await request.get<Permission[]>('/auth/permissions', {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
  return data
}
