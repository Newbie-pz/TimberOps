<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { Refresh, Search, View } from '@element-plus/icons-vue'

import { listAuditLogs } from '@/api/audit'
import PageHeader from '@/components/PageHeader.vue'
import type { AuditLog, AuditLogFilters } from '@/types'
import { formatDateTime } from '@/utils/format'

const logs = ref<AuditLog[]>([])
const loading = ref(false)
const detailVisible = ref(false)
const selectedLog = ref<AuditLog | null>(null)
const knownOperators = ref(new Map<string, string>())
const filters = reactive<{
  date_range: string[]
  operator_id: string
  action: string
  target_type: string
}>({ date_range: [], operator_id: '', action: '', target_type: '' })

const actionLabels: Record<string, string> = {
  WEIGHING_TASK_CREATED: '创建称重任务',
  TARE_RECORDED: '记录皮重',
  GROSS_RECORDED: '记录毛重',
  REWEIGH_RECORDED: '记录复磅',
  WEIGHING_TASK_COMPLETED: '完成称重任务',
  WEIGHING_TASK_CANCELLED: '取消称重任务',
  WEIGHING_TASK_DELETED: '删除称重任务',
  VEHICLE_DELETED: '删除车辆',
  CUSTOMER_DELETED: '删除客户',
  BILLING_PAID: '费用支付',
  BILLING_WAIVED: '费用免除',
}

const targetTypeLabels: Record<string, string> = {
  WeighingTask: '称重任务',
  WEIGHING_TASK: '称重任务',
  Vehicle: '车辆',
  VEHICLE: '车辆',
  Customer: '客户',
  CUSTOMER: '客户',
  BillingRecord: '费用记录',
  BILLING_RECORD: '费用记录',
}

const actionOptions = Object.entries(actionLabels).map(([value, label]) => ({ value, label }))
const targetTypeOptions = [
  { value: 'WeighingTask', label: '称重任务' },
  { value: 'Vehicle', label: '车辆' },
  { value: 'Customer', label: '客户' },
  { value: 'BillingRecord', label: '费用记录' },
]
const operatorOptions = computed(() =>
  Array.from(knownOperators.value, ([value, label]) => ({ value, label }))
    .sort((left, right) => left.label.localeCompare(right.label, 'zh-CN')),
)

function actionLabel(action: string): string {
  return actionLabels[action] || action
}

function targetTypeLabel(targetType: string): string {
  return targetTypeLabels[targetType] || targetType
}

function buildQuery(): AuditLogFilters {
  const query: AuditLogFilters = {}
  if (filters.date_range.length === 2) {
    query.start_date = filters.date_range[0]
    query.end_date = filters.date_range[1]
  }
  if (filters.operator_id) query.operator_id = filters.operator_id
  if (filters.action) query.action = filters.action
  if (filters.target_type) query.target_type = filters.target_type
  return query
}

function rememberOperators(items: AuditLog[]): void {
  const next = new Map(knownOperators.value)
  for (const item of items) {
    if (item.operator_id && item.operator_name) {
      next.set(item.operator_id, item.operator_name)
    }
  }
  knownOperators.value = next
}

async function load(): Promise<void> {
  loading.value = true
  try {
    const result = await listAuditLogs(buildQuery())
    logs.value = result
    rememberOperators(result)
  } finally {
    loading.value = false
  }
}

function reset(): void {
  Object.assign(filters, {
    date_range: [],
    operator_id: '',
    action: '',
    target_type: '',
  })
  void load()
}

function showDetail(log: AuditLog): void {
  selectedLog.value = log
  detailVisible.value = true
}

function prettyJson(value: Record<string, unknown> | null): string {
  return value ? JSON.stringify(value, null, 2) : '无'
}

onMounted(load)
</script>

<template>
  <PageHeader title="审计日志" description="查看关键业务操作记录与数据变更详情" />

  <el-card shadow="never" class="filter-card">
    <el-form inline>
      <el-form-item label="操作日期">
        <el-date-picker
          v-model="filters.date_range"
          type="daterange"
          value-format="YYYY-MM-DD"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          style="width: 250px"
        />
      </el-form-item>
      <el-form-item label="操作人">
        <el-select v-model="filters.operator_id" clearable filterable placeholder="全部操作人" style="width: 160px">
          <el-option v-for="item in operatorOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
      </el-form-item>
      <el-form-item label="操作类型">
        <el-select v-model="filters.action" clearable filterable placeholder="全部操作" style="width: 180px">
          <el-option v-for="item in actionOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
      </el-form-item>
      <el-form-item label="对象类型">
        <el-select v-model="filters.target_type" clearable placeholder="全部对象" style="width: 150px">
          <el-option v-for="item in targetTypeOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :icon="Search" @click="load">查询</el-button>
        <el-button :icon="Refresh" @click="reset">重置</el-button>
      </el-form-item>
    </el-form>
  </el-card>

  <el-card shadow="never" class="table-card">
    <el-table v-loading="loading" :data="logs" stripe>
      <el-table-column label="操作时间" min-width="180">
        <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作人" min-width="140">
        <template #default="{ row }">{{ row.operator_name || '系统' }}</template>
      </el-table-column>
      <el-table-column label="操作" min-width="170">
        <template #default="{ row }">
          <span>{{ actionLabel(row.action) }}</span>
          <small class="table-subtext">{{ row.action }}</small>
        </template>
      </el-table-column>
      <el-table-column label="业务对象" min-width="260">
        <template #default="{ row }">
          <strong>{{ row.target_display || '—' }}</strong>
          <small class="table-subtext">{{ targetTypeLabel(row.target_type) }}</small>
        </template>
      </el-table-column>
      <el-table-column prop="reason" label="原因/备注" min-width="180" show-overflow-tooltip>
        <template #default="{ row }">{{ row.reason || '—' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="90" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" :icon="View" @click="showDetail(row)">详情</el-button>
        </template>
      </el-table-column>
      <template #empty><el-empty description="没有符合条件的审计日志" /></template>
    </el-table>
  </el-card>

  <el-dialog v-model="detailVisible" title="审计日志详情" width="680px">
    <template v-if="selectedLog">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="操作时间">{{ formatDateTime(selectedLog.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="操作人">{{ selectedLog.operator_name || '系统' }}</el-descriptions-item>
        <el-descriptions-item label="操作类型">{{ actionLabel(selectedLog.action) }}</el-descriptions-item>
        <el-descriptions-item label="对象类型">{{ targetTypeLabel(selectedLog.target_type) }}</el-descriptions-item>
        <el-descriptions-item label="日志ID" :span="2"><code>{{ selectedLog.id }}</code></el-descriptions-item>
        <el-descriptions-item label="对象ID" :span="2"><code>{{ selectedLog.target_id || '—' }}</code></el-descriptions-item>
        <el-descriptions-item label="业务对象名称" :span="2">{{ selectedLog.target_display || '—' }}</el-descriptions-item>
        <el-descriptions-item label="原因/备注" :span="2">{{ selectedLog.reason || '—' }}</el-descriptions-item>
      </el-descriptions>
      <div class="audit-change-grid">
        <section>
          <strong>变更前</strong>
          <pre>{{ prettyJson(selectedLog.before_value) }}</pre>
        </section>
        <section>
          <strong>变更后</strong>
          <pre>{{ prettyJson(selectedLog.after_value) }}</pre>
        </section>
      </div>
    </template>
    <template #footer><el-button @click="detailVisible = false">关闭</el-button></template>
  </el-dialog>
</template>
