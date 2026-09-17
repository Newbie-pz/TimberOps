<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { Lock, UserFilled } from '@element-plus/icons-vue'

import { useAuthStore } from '@/stores/auth'
import { getRegistrationStatus } from '@/api/auth'

interface LoginForm {
  username: string
  password: string
}

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const formRef = ref<FormInstance>()
const submitting = ref(false)
const registrationEnabled = ref(false)
const form = reactive<LoginForm>({ username: '', password: '' })
const rules: FormRules<LoginForm> = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function submit(): Promise<void> {
  if (!(await formRef.value?.validate())) return
  submitting.value = true
  try {
    await authStore.login(form)
    if (!authStore.roles.length) {
      ElMessage.warning('当前账号尚未分配角色，请联系管理员。')
      await router.replace('/pending-access')
      return
    }
    const redirect =
      typeof route.query.redirect === 'string' && route.query.redirect.startsWith('/')
        ? route.query.redirect
        : '/'
    await router.replace(redirect)
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  try {
    registrationEnabled.value = (await getRegistrationStatus()).enabled
  } catch {
    registrationEnabled.value = false
  }
})
</script>

<template>
  <main class="login-page">
    <section class="login-brand-panel">
      <div class="login-brand-mark">T</div>
      <p>TIMBEROPS / WEIGHBRIDGE</p>
      <h1>木材加工企业智能运营与车辆称重管理平台</h1>
      <span>企业内部系统 · 请使用已分配账号登录</span>
    </section>

    <section class="login-form-panel">
      <el-card shadow="never" class="login-card">
        <div class="login-heading">
          <h2>账号登录</h2>
          <p>登录后进入磅房运营工作台</p>
        </div>
        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-position="top"
          @keyup.enter="submit"
        >
          <el-form-item label="用户名" prop="username">
            <el-input
              v-model="form.username"
              :prefix-icon="UserFilled"
              autocomplete="username"
              placeholder="请输入用户名"
              size="large"
            />
          </el-form-item>
          <el-form-item label="密码" prop="password">
            <el-input
              v-model="form.password"
              :prefix-icon="Lock"
              autocomplete="current-password"
              placeholder="请输入密码"
              show-password
              type="password"
              size="large"
            />
          </el-form-item>
          <el-button
            class="login-submit"
            type="primary"
            size="large"
            :loading="submitting"
            @click="submit"
          >
            登录
          </el-button>
          <p v-if="registrationEnabled" class="auth-switch">
            还没有账号？<RouterLink to="/register">注册账号</RouterLink>
          </p>
        </el-form>
      </el-card>
    </section>
  </main>
</template>
