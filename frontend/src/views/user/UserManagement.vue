<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Refresh } from '@element-plus/icons-vue'

import {
  assignUserRole,
  listRoles,
  listUsers,
  removeUserRole,
} from '@/api/users'
import PageHeader from '@/components/PageHeader.vue'
import type { ManagedUser, Role } from '@/types'
import { formatDateTime } from '@/utils/format'

const users = ref<ManagedUser[]>([])
const roles = ref<Role[]>([])
const loading = ref(false)
const mutatingKey = ref('')
const selectedRoles = ref<Record<string, string>>({})

const roleLabels: Record<Role['name'], string> = {
  ADMIN: '管理员',
  OPERATOR: '操作员',
  VIEWER: '查看员',
}
const roleMap = computed(() => new Map(roles.value.map((role) => [role.id, role])))

function roleLabel(name: Role['name']): string {
  return roleLabels[name]
}

function availableRoles(user: ManagedUser): Role[] {
  const assigned = new Set(user.roles.map((role) => role.id))
  return roles.value.filter((role) => !assigned.has(role.id))
}

async function load(): Promise<void> {
  loading.value = true
  try {
    const [userItems, roleItems] = await Promise.all([listUsers(), listRoles()])
    users.value = userItems
    roles.value = roleItems
  } finally {
    loading.value = false
  }
}

async function assign(user: ManagedUser): Promise<void> {
  const roleId = selectedRoles.value[user.id]
  if (!roleId) return
  const role = roleMap.value.get(roleId)
  const key = `${user.id}:assign`
  mutatingKey.value = key
  try {
    await assignUserRole(user.id, roleId)
    ElMessage.success(`已为 ${user.real_name} 分配${role ? roleLabels[role.name] : '角色'}`)
    selectedRoles.value[user.id] = ''
    await load()
  } finally {
    mutatingKey.value = ''
  }
}

async function remove(user: ManagedUser, role: Role): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `确认移除 ${user.real_name} 的${roleLabels[role.name]}角色？`,
      '移除角色',
      { type: 'warning', confirmButtonText: '确认移除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  const key = `${user.id}:${role.id}`
  mutatingKey.value = key
  try {
    await removeUserRole(user.id, role.id)
    ElMessage.success('角色已移除')
    await load()
  } finally {
    mutatingKey.value = ''
  }
}

onMounted(load)
</script>

<template>
  <PageHeader title="用户管理" description="管理企业内部账号角色，权限变更实时生效">
    <el-button :icon="Refresh" :loading="loading" @click="load">刷新</el-button>
  </PageHeader>

  <el-alert
    class="user-management-note"
    title="账号创建暂沿用公开注册或初始化流程；本页面仅管理已有用户的角色。"
    type="info"
    :closable="false"
    show-icon
  />

  <el-card shadow="never" class="table-card">
    <el-table v-loading="loading" :data="users" stripe>
      <el-table-column prop="username" label="用户名" min-width="150" />
      <el-table-column prop="real_name" label="姓名" min-width="140" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'">
            {{ row.is_active ? '启用' : '停用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="当前角色" min-width="260">
        <template #default="{ row }">
          <div class="role-tags">
            <el-tag
              v-for="role in row.roles"
              :key="role.id"
              closable
              :disable-transitions="true"
              @close="remove(row, role)"
            >
              {{ roleLabel(role.name) }}
            </el-tag>
            <span v-if="!row.roles.length" class="table-subtext">未分配角色</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="创建时间" min-width="180">
        <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="分配角色" min-width="290" fixed="right">
        <template #default="{ row }">
          <div class="role-assignment">
            <el-select
              v-model="selectedRoles[row.id]"
              placeholder="选择角色"
              :disabled="!availableRoles(row).length"
              style="width: 150px"
            >
              <el-option
                v-for="role in availableRoles(row)"
                :key="role.id"
                :label="roleLabels[role.name]"
                :value="role.id"
              />
            </el-select>
            <el-button
              type="primary"
              :disabled="!selectedRoles[row.id]"
              :loading="mutatingKey === `${row.id}:assign`"
              @click="assign(row)"
            >
              分配
            </el-button>
          </div>
        </template>
      </el-table-column>
      <template #empty><el-empty description="暂无用户" /></template>
    </el-table>
  </el-card>
</template>
