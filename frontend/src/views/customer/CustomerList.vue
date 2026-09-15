<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { Plus, Refresh } from '@element-plus/icons-vue'

import { createCustomer, listCustomers, updateCustomer } from '@/api/customer'
import PageHeader from '@/components/PageHeader.vue'
import type { Customer, CustomerCreate } from '@/types'

const customers = ref<Customer[]>([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const editingId = ref<string | null>(null)
const formRef = ref<FormInstance>()
const form = reactive({ name: '', contact_name: '', phone: '', remark: '' })
const rules: FormRules = {
  name: [{ required: true, message: '请输入客户名称', trigger: 'blur' }],
}

async function loadCustomers(): Promise<void> {
  loading.value = true
  try {
    customers.value = await listCustomers()
  } finally {
    loading.value = false
  }
}

function openCreate(): void {
  editingId.value = null
  Object.assign(form, { name: '', contact_name: '', phone: '', remark: '' })
  formRef.value?.clearValidate()
  dialogVisible.value = true
}

function openEdit(customer: Customer): void {
  editingId.value = customer.id
  Object.assign(form, {
    name: customer.name,
    contact_name: customer.contact_name || '',
    phone: customer.phone || '',
    remark: customer.remark || '',
  })
  dialogVisible.value = true
}

async function submit(): Promise<void> {
  if (!(await formRef.value?.validate())) return
  saving.value = true
  const payload: CustomerCreate = {
    name: form.name,
    contact_name: form.contact_name || null,
    phone: form.phone || null,
    remark: form.remark || null,
  }
  try {
    if (editingId.value) {
      await updateCustomer(editingId.value, payload)
      ElMessage.success('客户信息已更新')
    } else {
      await createCustomer(payload)
      ElMessage.success('客户创建成功')
    }
    dialogVisible.value = false
    await loadCustomers()
  } finally {
    saving.value = false
  }
}

onMounted(loadCustomers)
</script>

<template>
  <PageHeader title="客户管理" description="维护称重任务可选关联的基础客户信息">
    <el-button :icon="Refresh" @click="loadCustomers">刷新</el-button>
    <el-button type="primary" :icon="Plus" @click="openCreate">新增客户</el-button>
  </PageHeader>

  <el-card shadow="never" class="table-card">
    <el-table v-loading="loading" :data="customers" stripe>
      <el-table-column prop="name" label="客户名称" min-width="220" />
      <el-table-column prop="contact_name" label="联系人" min-width="120" />
      <el-table-column prop="phone" label="联系电话" min-width="150" />
      <el-table-column prop="remark" label="备注" min-width="220" show-overflow-tooltip />
      <el-table-column label="操作" width="90" fixed="right">
        <template #default="{ row }"><el-button link type="primary" @click="openEdit(row)">编辑</el-button></template>
      </el-table-column>
      <template #empty><el-empty description="暂无客户，可直接新增或创建无客户称重任务" /></template>
    </el-table>
  </el-card>

  <el-dialog v-model="dialogVisible" :title="editingId ? '编辑客户' : '新增客户'" width="520px">
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
      <el-form-item label="客户名称" prop="name"><el-input v-model="form.name" /></el-form-item>
      <div class="form-grid two-columns">
        <el-form-item label="联系人"><el-input v-model="form.contact_name" /></el-form-item>
        <el-form-item label="联系电话"><el-input v-model="form.phone" /></el-form-item>
      </div>
      <el-form-item label="备注"><el-input v-model="form.remark" type="textarea" :rows="3" /></el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="submit">保存</el-button>
    </template>
  </el-dialog>
</template>
