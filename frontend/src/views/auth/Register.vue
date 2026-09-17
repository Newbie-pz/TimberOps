<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  ElMessage,
  type FormInstance,
  type FormItemRule,
  type FormRules,
} from 'element-plus'
import { Lock, User, UserFilled } from '@element-plus/icons-vue'

import { getRegistrationStatus, register } from '@/api/auth'

interface RegisterForm {
  username: string
  real_name: string
  password: string
  confirm_password: string
}

const router = useRouter()
const formRef = ref<FormInstance>()
const submitting = ref(false)
const form = reactive<RegisterForm>({
  username: '',
  real_name: '',
  password: '',
  confirm_password: '',
})

const confirmPasswordValidator: FormItemRule['validator'] = (_rule, value, callback) => {
  if (!value) callback(new Error('请再次输入密码'))
  else if (value !== form.password) callback(new Error('两次输入的密码不一致'))
  else callback()
}

const rules: FormRules<RegisterForm> = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 64, message: '用户名长度为 3 至 64 个字符', trigger: 'blur' },
  ],
  real_name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, max: 72, message: '密码长度为 8 至 72 个字符', trigger: 'blur' },
  ],
  confirm_password: [{ validator: confirmPasswordValidator, trigger: ['blur', 'change'] }],
}

async function submit(): Promise<void> {
  if (!(await formRef.value?.validate())) return
  submitting.value = true
  try {
    await register({
      username: form.username,
      real_name: form.real_name,
      password: form.password,
    })
    form.password = ''
    form.confirm_password = ''
    ElMessage.success('账号注册成功，请联系管理员分配角色。')
    await router.replace('/login')
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  try {
    const status = await getRegistrationStatus()
    if (!status.enabled) {
      ElMessage.info('当前未开放账号注册')
      await router.replace('/login')
    }
  } catch {
    await router.replace('/login')
  }
})
</script>

<template>
  <main class="login-page">
    <section class="login-brand-panel">
      <div class="login-brand-mark">T</div>
      <p>TIMBEROPS / ACCOUNT</p>
      <h1>创建 TimberOps 企业内部账号</h1>
      <span>注册成功后，请联系系统管理员开通业务访问权限</span>
    </section>

    <section class="login-form-panel">
      <el-card shadow="never" class="login-card register-card">
        <div class="login-heading">
          <h2>注册账号</h2>
          <p>请填写个人账号信息</p>
        </div>
        <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @keyup.enter="submit">
          <el-form-item label="用户名" prop="username">
            <el-input v-model="form.username" :prefix-icon="UserFilled" autocomplete="username" placeholder="3 至 64 个字符" size="large" />
          </el-form-item>
          <el-form-item label="姓名" prop="real_name">
            <el-input v-model="form.real_name" :prefix-icon="User" autocomplete="name" placeholder="请输入真实姓名" size="large" />
          </el-form-item>
          <el-form-item label="密码" prop="password">
            <el-input v-model="form.password" :prefix-icon="Lock" autocomplete="new-password" type="password" placeholder="至少 8 个字符" size="large" />
          </el-form-item>
          <el-form-item label="确认密码" prop="confirm_password">
            <el-input v-model="form.confirm_password" :prefix-icon="Lock" autocomplete="new-password" type="password" placeholder="请再次输入密码" size="large" />
          </el-form-item>
          <el-button class="login-submit" type="primary" size="large" :loading="submitting" @click="submit">注册账号</el-button>
          <p class="auth-switch">已有账号？<RouterLink to="/login">返回登录</RouterLink></p>
        </el-form>
      </el-card>
    </section>
  </main>
</template>
