import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import {
  getCurrentUser,
  getCurrentUserPermissions,
  getCurrentUserRoles,
  login as requestLogin,
  type LoginPayload,
} from '@/api/auth'
import {
  accessToken,
  clearAccessToken,
  getAccessToken,
  setAccessToken,
} from '@/auth/session'
import type { Permission, PermissionCode, Role, User } from '@/types'

export const useAuthStore = defineStore('auth', () => {
  const currentUser = ref<User | null>(null)
  const roles = ref<Role[]>([])
  const permissions = ref<Permission[]>([])
  const restoring = ref(false)
  let restorePromise: Promise<boolean> | null = null

  const isAuthenticated = computed(
    () => Boolean(accessToken.value && currentUser.value),
  )
  const permissionCodes = computed(
    () => new Set(permissions.value.map((item) => item.code)),
  )

  function resetIdentity(): void {
    currentUser.value = null
    roles.value = []
    permissions.value = []
  }

  async function loadIdentity(): Promise<void> {
    const [user, userRoles, userPermissions] = await Promise.all([
      getCurrentUser(),
      getCurrentUserRoles(),
      getCurrentUserPermissions(),
    ])
    currentUser.value = user
    roles.value = userRoles
    permissions.value = userPermissions
  }

  async function login(payload: LoginPayload): Promise<void> {
    const response = await requestLogin(payload)
    setAccessToken(response.access_token)
    try {
      await loadIdentity()
    } catch (error) {
      clearAccessToken()
      resetIdentity()
      throw error
    }
  }

  function logout(): void {
    clearAccessToken()
    resetIdentity()
  }

  async function restoreSession(): Promise<boolean> {
    if (!getAccessToken()) {
      resetIdentity()
      return false
    }
    if (isAuthenticated.value) return true
    if (restorePromise) return restorePromise

    restoring.value = true
    restorePromise = loadIdentity()
      .then(() => true)
      .catch(() => {
        clearAccessToken()
        resetIdentity()
        return false
      })
      .finally(() => {
        restoring.value = false
        restorePromise = null
      })
    return restorePromise
  }

  function hasPermission(code: PermissionCode | string): boolean {
    return permissionCodes.value.has(code as PermissionCode)
  }

  return {
    currentUser,
    roles,
    permissions,
    isAuthenticated,
    restoring,
    login,
    logout,
    restoreSession,
    hasPermission,
  }
})
