<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  DataAnalysis,
  Fold,
  Goods,
  List,
  OfficeBuilding,
  Operation,
  SetUp,
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const collapsed = ref(false)

const activeMenu = computed(() => {
  if (route.path.startsWith('/weighing/workbench')) return '/weighing/history'
  return route.path
})

function navigate(path: string): void {
  void router.push(path)
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
        <el-menu-item index="/">
          <el-icon><DataAnalysis /></el-icon>
          <template #title>首页</template>
        </el-menu-item>
        <el-menu-item index="/vehicles">
          <el-icon><SetUp /></el-icon>
          <template #title>车辆管理</template>
        </el-menu-item>
        <el-menu-item index="/customers">
          <el-icon><OfficeBuilding /></el-icon>
          <template #title>客户管理</template>
        </el-menu-item>
        <el-menu-item index="/weighing/create">
          <el-icon><Goods /></el-icon>
          <template #title>称重任务</template>
        </el-menu-item>
        <el-menu-item index="/weighing/history">
          <el-icon><List /></el-icon>
          <template #title>称重历史</template>
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
        <div class="system-state">
          <span class="state-dot" />
          系统运行正常
        </div>
      </header>

      <main class="page-content">
        <RouterView />
      </main>
    </section>
  </div>
</template>
