<script setup lang="ts">
import { useRouter } from 'vue-router'
import { WarningFilled } from '@element-plus/icons-vue'

import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

async function logout(): Promise<void> {
  authStore.logout()
  await router.replace('/login')
}
</script>

<template>
  <div class="pending-access-page">
    <el-card shadow="never" class="panel-card pending-access-card">
      <el-icon><WarningFilled /></el-icon>
      <h2>账号暂未开通</h2>
      <p>当前账号尚未分配角色，请联系管理员。</p>
      <el-button type="primary" @click="logout">退出登录</el-button>
    </el-card>
  </div>
</template>
