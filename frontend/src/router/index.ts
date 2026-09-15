import { createRouter, createWebHistory } from 'vue-router'

import MainLayout from '@/layouts/MainLayout.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      component: MainLayout,
      children: [
        {
          path: '',
          name: 'dashboard',
          component: () => import('@/views/dashboard/Dashboard.vue'),
          meta: { title: '运营概览' },
        },
        {
          path: 'vehicles',
          name: 'vehicles',
          component: () => import('@/views/vehicle/VehicleList.vue'),
          meta: { title: '车辆管理' },
        },
        {
          path: 'customers',
          name: 'customers',
          component: () => import('@/views/customer/CustomerList.vue'),
          meta: { title: '客户管理' },
        },
        {
          path: 'weighing/create',
          name: 'weighing-create',
          component: () => import('@/views/weighing/Create.vue'),
          meta: { title: '创建称重任务' },
        },
        {
          path: 'weighing/workbench/:id',
          name: 'weighing-workbench',
          component: () => import('@/views/weighing/Workbench.vue'),
          meta: { title: '称重工作台' },
        },
        {
          path: 'weighing/history',
          name: 'weighing-history',
          component: () => import('@/views/weighing/History.vue'),
          meta: { title: '称重历史' },
        },
        {
          path: 'ai',
          name: 'ai-assistant',
          component: () => import('@/views/ai/Assistant.vue'),
          meta: { title: '智能助手' },
        },
      ],
    },
  ],
  scrollBehavior: () => ({ top: 0 }),
})

router.afterEach((to) => {
  document.title = `${String(to.meta.title || '磅房工作台')} · TimberOps`
})

export default router
