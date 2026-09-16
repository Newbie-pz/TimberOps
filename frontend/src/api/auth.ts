import request from './request'
import type { LoginResponse, User } from '@/types'

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
