<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { Check, CloseBold, Refresh, Search } from '@element-plus/icons-vue'

import {
  listBillingRecords,
  payBillingRecord,
  waiveBillingRecord,
} from '@/api/billing'
import { listCustomers } from '@/api/customer'
import { listVehicles } from '@/api/vehicle'
import PageHeader from '@/components/PageHeader.vue'
import { useAuthStore } from '@/stores/auth'
import type {
  BillingListItem,
  BillingRecordFilters,
  Customer,
  PaymentStatus,
  Vehicle,
  VehicleType,
} from '@/types'
import { formatDateTime, vehicleTypeLabel } from '@/utils/format'

const authStore = useAuthStore()
const records = ref<BillingListItem[]>([])
const vehicles = ref<Vehicle[]>([])
const customers = ref<Customer[]>([])
const loading = ref(false)
const updatingId = ref<string | null>(null)
const filters = reactive<{
  date_range: string[]
  vehicle_id: string
  customer_id: string
  payment_status: PaymentStatus | ''
}>({
  date_range: [],
  vehicle_id: '',
  customer_id: '',
  payment_status: '',
})

const paymentLabels: Record<PaymentStatus, string> = {
  UNPAID: '未支付',
  PAID: '已支付',
  WAIVED: '已免除',
}

function paymentTagType(status: PaymentStatus): 'warning' | 'success' | 'info' {
  if (status === 'PAID') return 'success'
  if (status === 'WAIVED') return 'info'
  return 'warning'
}

function paymentLabel(status: PaymentStatus): string {
  return paymentLabels[status]
}

function vehicleTypeName(vehicleType: VehicleType): string {
  return vehicleTypeLabel[vehicleType]
}

function buildQuery(): BillingRecordFilters {
  const query: BillingRecordFilters = {}
  if (filters.date_range.length === 2) {
    query.start_date = filters.date_range[0]
    query.end_date = filters.date_range[1]
  }
  if (filters.vehicle_id) query.vehicle_id = filters.vehicle_id
  if (filters.customer_id) query.customer_id = filters.customer_id
  if (filters.payment_status) query.payment_status = filters.payment_status
  return query
}

async function load(): Promise<void> {
  loading.value = true
  try {
    records.value = await listBillingRecords(buildQuery())
  } finally {
    loading.value = false
  }
}

function reset(): void {
  Object.assign(filters, {
    date_range: [],
    vehicle_id: '',
    customer_id: '',
    payment_status: '',
  })
  void load()
}

async function markPaid(record: BillingListItem): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `确认已收到任务 ${record.task_no} 的 ${record.fee_amount} 元费用？`,
      '确认支付',
      { confirmButtonText: '确认已支付', cancelButtonText: '取消', type: 'success' },
    )
  } catch {
    return
  }
  updatingId.value = record.id
  try {
    await payBillingRecord(record.id)
    ElMessage.success('费用已标记为支付')
    await load()
  } finally {
    updatingId.value = null
  }
}

async function waive(record: BillingListItem): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `确认免除任务 ${record.task_no} 的 ${record.fee_amount} 元费用？该操作不可改为支付。`,
      '免除费用',
      { confirmButtonText: '确认免除', cancelButtonText: '取消', type: 'warning' },
    )
  } catch {
    return
  }
  updatingId.value = record.id
  try {
    await waiveBillingRecord(record.id)
    ElMessage.success('费用已免除')
    await load()
  } finally {
    updatingId.value = null
  }
}

onMounted(async () => {
  const [vehicleData, customerData] = await Promise.all([
    listVehicles(),
    listCustomers(),
  ])
  vehicles.value = vehicleData
  customers.value = customerData
  await load()
})
</script>

<template>
  <PageHeader title="费用管理" description="查询自动计费记录，确认支付或由管理员免除费用" />

  <el-card shadow="never" class="filter-card">
    <el-form inline>
      <el-form-item label="费用日期">
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
      <el-form-item label="车辆">
        <el-select v-model="filters.vehicle_id" clearable filterable placeholder="全部车辆" style="width: 160px">
          <el-option v-for="vehicle in vehicles" :key="vehicle.id" :label="vehicle.plate_number" :value="vehicle.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="客户">
        <el-select v-model="filters.customer_id" clearable filterable placeholder="全部客户" style="width: 180px">
          <el-option v-for="customer in customers" :key="customer.id" :label="customer.name" :value="customer.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="费用状态">
        <el-select v-model="filters.payment_status" clearable placeholder="全部" style="width: 130px">
          <el-option label="未支付" value="UNPAID" />
          <el-option label="已支付" value="PAID" />
          <el-option label="已免除" value="WAIVED" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :icon="Search" @click="load">查询</el-button>
        <el-button :icon="Refresh" @click="reset">重置</el-button>
      </el-form-item>
    </el-form>
  </el-card>

  <el-card shadow="never" class="table-card">
    <el-table v-loading="loading" :data="records" stripe>
      <el-table-column prop="task_no" label="任务编号" min-width="210" />
      <el-table-column prop="plate_number" label="车牌号" min-width="130">
        <template #default="{ row }"><strong class="plate-number">{{ row.plate_number }}</strong></template>
      </el-table-column>
      <el-table-column prop="customer_name" label="客户" min-width="160">
        <template #default="{ row }">{{ row.customer_name || '—' }}</template>
      </el-table-column>
      <el-table-column label="车辆类型" min-width="120">
        <template #default="{ row }">{{ vehicleTypeName(row.vehicle_type_snapshot) }}</template>
      </el-table-column>
      <el-table-column label="金额" min-width="120" align="right">
        <template #default="{ row }"><strong class="billing-amount">{{ row.fee_amount }} 元</strong></template>
      </el-table-column>
      <el-table-column label="状态" min-width="110">
        <template #default="{ row }">
          <el-tag :type="paymentTagType(row.payment_status)" effect="light" round>{{ paymentLabel(row.payment_status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="完成时间" min-width="180">
        <template #default="{ row }">{{ formatDateTime(row.completed_at) }}</template>
      </el-table-column>
      <el-table-column label="计费时间" min-width="180">
        <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <template v-if="row.payment_status === 'UNPAID'">
            <el-button
              v-if="authStore.hasPermission('billing:update')"
              link
              type="success"
              :icon="Check"
              :loading="updatingId === row.id"
              @click="markPaid(row)"
            >确认支付</el-button>
            <el-button
              v-if="authStore.hasPermission('billing:waive')"
              link
              type="warning"
              :icon="CloseBold"
              :loading="updatingId === row.id"
              @click="waive(row)"
            >免除</el-button>
          </template>
          <span v-else class="table-subtext">已处理</span>
        </template>
      </el-table-column>
      <template #empty><el-empty description="没有符合条件的费用记录" /></template>
    </el-table>
  </el-card>
</template>
