import { readonly, ref } from 'vue'

export const ACCESS_TOKEN_STORAGE_KEY = 'timberops_access_token'

const storedToken = ref<string | null>(
  localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY),
)
let unauthorizedHandler: (() => void | Promise<void>) | null = null

export const accessToken = readonly(storedToken)

export function getAccessToken(): string | null {
  return storedToken.value
}

export function setAccessToken(token: string): void {
  localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, token)
  storedToken.value = token
}

export function clearAccessToken(): void {
  localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY)
  storedToken.value = null
}

export function registerUnauthorizedHandler(
  handler: () => void | Promise<void>,
): void {
  unauthorizedHandler = handler
}

export async function handleUnauthorized(): Promise<void> {
  await unauthorizedHandler?.()
}
