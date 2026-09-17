<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  DataAnalysis,
  ChatDotRound,
  Fold,
  Goods,
  List,
  OfficeBuilding,
  Operation,
  SetUp,
  User,
} from '@element-plus/icons-vue'

import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const collapsed = ref(false)

const roleName = computed(() =>
  authStore.roles
    .map((role) => role.description || role.name)
    .join(' / ') || '未分配角色',
)

const activeMenu = computed(() => {
  if (route.path.startsWith('/weighing/workbench')) return '/weighing/history'
  return route.path
})

function navigate(path: string): void {
  void router.push(path)
}

async function logout(): Promise<void> {
  authStore.logout()
  await router.replace('/login')
}
</script>

<template>
  <div class="app-shell" :class="{ 'is-collapsed': collapsed }">
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-mark">T</div>
        <div v-if="!collapsed" class="brand-copy">
          <strong>TimberOps</strong>
          <span>磅房运营平台</span>
        </div>
      </div>

      <el-menu
        :default-active="activeMenu"
        :collapse="collapsed"
        background-color="transparent"
        text-color="#c8d3d0"
        active-text-color="#ffffff"
        @select="navigate"
      >
        <el-menu-item v-if="authStore.hasPermission('dashboard:view')" index="/">
          <el-icon><DataAnalysis /></el-icon>
          <template #title>首页</template>
        </el-menu-item>
        <el-menu-item v-if="authStore.hasPermission('vehicle:view')" index="/vehicles">
          <el-icon><SetUp /></el-icon>
          <template #title>车辆管理</template>
        </el-menu-item>
        <el-menu-item v-if="authStore.hasPermission('customer:view')" index="/customers">
          <el-icon><OfficeBuilding /></el-icon>
          <template #title>客户管理</template>
        </el-menu-item>
        <el-menu-item v-if="authStore.hasPermission('weighing:create')" index="/weighing/create">
          <el-icon><Goods /></el-icon>
          <template #title>称重任务</template>
        </el-menu-item>
        <el-menu-item v-if="authStore.hasPermission('weighing:view')" index="/weighing/history">
          <el-icon><List /></el-icon>
          <template #title>称重历史</template>
        </el-menu-item>
        <el-menu-item v-if="authStore.hasPermission('ai:query')" index="/ai">
          <el-icon><ChatDotRound /></el-icon>
          <template #title>智能助手</template>
        </el-menu-item>
        <el-menu-item v-if="authStore.hasPermission('user:manage')" index="/users">
          <el-icon><User /></el-icon>
          <template #title>用户管理</template>
        </el-menu-item>
      </el-menu>

      <div class="sidebar-foot" :title="collapsed ? '人工称重模式' : ''">
        <el-icon><Operation /></el-icon>
        <span v-if="!collapsed">人工称重模式</span>
      </div>
    </aside>

    <section class="main-column">
      <header class="topbar">
        <button class="collapse-button" type="button" @click="collapsed = !collapsed">
          <el-icon><Fold /></el-icon>
        </button>
        <div>
          <p class="topbar-eyebrow">TIMBEROPS / WEIGHBRIDGE</p>
          <h1>{{ route.meta.title }}</h1>
        </div>
        <div class="topbar-account">
          <div class="account-copy">
            <strong>{{ authStore.currentUser?.real_name }}</strong>
            <span>{{ authStore.currentUser?.username }} · {{ roleName }}</span>
          </div>
          <el-dropdown trigger="click" @command="logout">
            <el-button circle :icon="User" aria-label="用户菜单" />
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <main class="page-content">
        <RouterView />
      </main>
    </section>
  </div>
</template>
