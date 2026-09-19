import { createRouter, createWebHistory } from 'vue-router'

import { registerUnauthorizedHandler } from '@/auth/session'
import { pinia } from '@/stores'
import { useAuthStore } from '@/stores/auth'
import type { PermissionCode } from '@/types'

declare module 'vue-router' {
  interface RouteMeta {
    title?: string
    requiresAuth?: boolean
    permission?: PermissionCode
  }
}

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/auth/Login.vue'),
      meta: { title: '登录' },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('@/views/auth/Register.vue'),
      meta: { title: '注册账号' },
    },
    {
      path: '/',
      component: () => import('@/layouts/MainLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        {
          path: 'pending-access',
          name: 'pending-access',
          component: () => import('@/views/auth/PendingAccess.vue'),
          meta: { title: '等待权限分配' },
        },
        {
          path: '',
          name: 'dashboard',
          component: () => import('@/views/dashboard/Dashboard.vue'),
          meta: { title: '运营概览', permission: 'dashboard:view' },
        },
        {
          path: 'vehicles',
          name: 'vehicles',
          component: () => import('@/views/vehicle/VehicleList.vue'),
          meta: { title: '车辆管理', permission: 'vehicle:view' },
        },
        {
          path: 'customers',
          name: 'customers',
          component: () => import('@/views/customer/CustomerList.vue'),
          meta: { title: '客户管理', permission: 'customer:view' },
        },
        {
          path: 'weighing/create',
          name: 'weighing-create',
          component: () => import('@/views/weighing/Create.vue'),
          meta: { title: '创建称重任务', permission: 'weighing:create' },
        },
        {
          path: 'weighing/workbench/:id',
          name: 'weighing-workbench',
          component: () => import('@/views/weighing/Workbench.vue'),
          meta: { title: '称重工作台', permission: 'weighing:view' },
        },
        {
          path: 'weighing/history',
          name: 'weighing-history',
          component: () => import('@/views/weighing/History.vue'),
          meta: { title: '称重历史', permission: 'weighing:view' },
        },
        {
          path: 'billing',
          name: 'billing',
          component: () => import('@/views/billing/BillingList.vue'),
          meta: { title: '费用管理', permission: 'billing:view' },
        },
        {
          path: 'audit',
          name: 'audit',
          component: () => import('@/views/audit/AuditList.vue'),
          meta: { title: '审计日志', permission: 'audit:view' },
        },
        {
          path: 'reports',
          name: 'reports',
          component: () => import('@/views/report/Report.vue'),
          meta: { title: '业务报表', permission: 'report:view' },
        },
        {
          path: 'ai',
          name: 'ai-assistant',
          component: () => import('@/views/ai/Assistant.vue'),
          meta: { title: '智能助手', permission: 'ai:query' },
        },
        {
          path: 'users',
          name: 'users',
          component: () => import('@/views/user/UserManagement.vue'),
          meta: { title: '用户管理', permission: 'user:manage' },
        },
      ],
    },
  ],
  scrollBehavior: () => ({ top: 0 }),
})

registerUnauthorizedHandler(async () => {
  if (router.currentRoute.value.path !== '/login') {
    await router.replace({
      path: '/login',
      query: { redirect: router.currentRoute.value.fullPath },
    })
  }
})

router.beforeEach(async (to) => {
  const authStore = useAuthStore(pinia)
  const authenticated = await authStore.restoreSession()

  if (to.name === 'login' || to.name === 'register') {
    if (!authenticated) return true
    return authStore.roles.length ? { path: '/' } : { path: '/pending-access' }
  }
  if (to.matched.some((record) => record.meta.requiresAuth) && !authenticated) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (authenticated && !authStore.roles.length && to.name !== 'pending-access') {
    ElMessage.warning('当前账号尚未分配角色，请联系管理员。')
    return { path: '/pending-access' }
  }
  if (to.meta.permission && !authStore.hasPermission(to.meta.permission)) {
    ElMessage.warning('当前账号没有访问该页面的权限')
    return { path: '/' }
  }
  return true
})

router.afterEach((to) => {
  document.title = `${String(to.meta.title || '磅房工作台')} · TimberOps`
})

export default router
