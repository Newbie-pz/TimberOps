import axios, { AxiosError } from 'axios'
import { ElMessage } from 'element-plus'

interface ApiErrorEnvelope {
  error?: {
    code?: string
    message?: string
  }
  detail?: string | Array<{ msg?: string }>
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly code: string,
    public readonly status?: number,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 15_000,
  headers: { 'Content-Type': 'application/json' },
})

request.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ApiErrorEnvelope>) => {
    const body = error.response?.data
    const errorCode = body?.error?.code || 'REQUEST_FAILED'
    const validationDetail = Array.isArray(body?.detail)
      ? body.detail.map((item) => item.msg).filter(Boolean).join('；')
      : body?.detail
    const message =
      (errorCode === 'AI_SERVICE_UNAVAILABLE'
        ? 'AI 服务当前未启用或模型配置不可用'
        : body?.error?.message) ||
      validationDetail ||
      (error.code === 'ECONNABORTED' ? '请求超时，请稍后重试' : '服务暂时不可用')
    const apiError = new ApiError(
      message || '请求失败',
      errorCode,
      error.response?.status,
    )
    ElMessage.error(apiError.message)
    return Promise.reject(apiError)
  },
)

export default request
