import request from './request'
import type { AIChatRequest, AIChatResponse } from '@/types'

const configuredTimeout = Number(import.meta.env.VITE_AI_TIMEOUT_MS || 35_000)
const AI_CHAT_TIMEOUT_MS =
  Number.isFinite(configuredTimeout) && configuredTimeout > 0
    ? configuredTimeout
    : 35_000

export async function chatWithAI(payload: AIChatRequest): Promise<AIChatResponse> {
  const { data } = await request.post<AIChatResponse>('/ai/chat', payload, {
    timeout: AI_CHAT_TIMEOUT_MS,
  })
  return data
}
