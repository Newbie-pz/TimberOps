import request from './request'
import type { AIChatRequest, AIChatResponse } from '@/types'

export async function chatWithAI(payload: AIChatRequest): Promise<AIChatResponse> {
  const { data } = await request.post<AIChatResponse>('/ai/chat', payload)
  return data
}
