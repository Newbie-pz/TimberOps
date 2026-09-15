<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Refresh, Search } from '@element-plus/icons-vue'

import { listVehicles } from '@/api/vehicle'
import { listWeighingTasks } from '@/api/weighing'
import PageHeader from '@/components/PageHeader.vue'
import StatusTag from '@/components/StatusTag.vue'
import WeightValue from '@/components/WeightValue.vue'
import type { CargoType, Vehicle, WeighingStatus, WeighingTask, WeighingTaskFilters } from '@/types'
import { cargoTypeLabel, formatDateTime, statusLabel } from '@/utils/format'

const router = useRouter()
const tasks = ref<WeighingTask[]>([])
const vehicles = ref<Vehicle[]>([])
const loading = ref(false)
const filters = reactive({ cargo_type: '', status: '', vehicle_id: '' })
const vehicleMap = computed(() => new Map(vehicles.value.map((item) => [item.id, item.plate_number])))
const cargoOptions: CargoType[] = ['ORE', 'COAL', 'TIMBER', 'OTHER']
const statusOptions: WeighingStatus[] = [
  'WAIT_TARE', 'TARE_COMPLETED', 'LOADING', 'WAIT_GROSS',
  'GROSS_COMPLETED', 'COMPLETED', 'CANCELLED',
]

async function load(): Promise<void> {
  loading.value = true
  const query: WeighingTaskFilters = {}
  if (filters.cargo_type) query.cargo_type = filters.cargo_type as CargoType
  if (filters.status) query.status = filters.status as WeighingStatus
  if (filters.vehicle_id) query.vehicle_id = filters.vehicle_id
  try {
    tasks.value = await listWeighingTasks(query)
  } finally {
    loading.value = false
  }
}

function reset(): void {
  Object.assign(filters, { cargo_type: '', status: '', vehicle_id: '' })
  void load()
}

onMounted(async () => {
  vehicles.value = await listVehicles()
  await load()
})
</script>

<template>
  <PageHeader title="称重历史" description="查询任务当前汇总并进入工作台查看完整读数">
    <el-button type="primary" @click="router.push('/weighing/create')">创建任务</el-button>
  </PageHeader>

  <el-card shadow="never" class="filter-card">
    <el-form inline>
      <el-form-item label="货物类型">
        <el-select v-model="filters.cargo_type" clearable placeholder="全部" style="width: 140px">
          <el-option v-for="item in cargoOptions" :key="item" :label="cargoTypeLabel[item]" :value="item" />
        </el-select>
      </el-form-item>
      <el-form-item label="任务状态">
        <el-select v-model="filters.status" clearable placeholder="全部" style="width: 180px">
          <el-option v-for="item in statusOptions" :key="item" :label="statusLabel[item]" :value="item" />
        </el-select>
      </el-form-item>
      <el-form-item label="车辆">
        <el-select v-model="filters.vehicle_id" clearable filterable placeholder="全部车辆" style="width: 170px">
          <el-option v-for="vehicle in vehicles" :key="vehicle.id" :label="vehicle.plate_number" :value="vehicle.id" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :icon="Search" @click="load">查询</el-button>
        <el-button :icon="Refresh" @click="reset">重置</el-button>
      </el-form-item>
    </el-form>
  </el-card>

  <el-card shadow="never" class="table-card">
    <el-table v-loading="loading" :data="tasks" stripe @row-click="(row: WeighingTask) => router.push(`/weighing/workbench/${row.id}`)">
      <el-table-column prop="task_no" label="任务编号" min-width="210" />
      <el-table-column label="车牌号" min-width="130">
        <template #default="{ row }"><strong class="plate-number">{{ vehicleMap.get(row.vehicle_id) || '—' }}</strong></template>
      </el-table-column>
      <el-table-column label="货物" min-width="120">
        <template #default="{ row }">{{ cargoTypeLabel[row.cargo_type as CargoType] }}<small v-if="row.cargo_name" class="table-subtext">{{ row.cargo_name }}</small></template>
      </el-table-column>
      <el-table-column label="流程状态" min-width="145"><template #default="{ row }"><StatusTag :status="row.status" /></template></el-table-column>
      <el-table-column label="称重结果" min-width="100"><template #default="{ row }"><StatusTag :result="row.weight_result" /></template></el-table-column>
      <el-table-column label="净货重" min-width="120"><template #default="{ row }"><WeightValue :value="row.net_weight_tons" /></template></el-table-column>
      <el-table-column label="更新时间" min-width="180"><template #default="{ row }">{{ formatDateTime(row.updated_at) }}</template></el-table-column>
      <el-table-column label="操作" width="90" fixed="right"><template #default="{ row }"><el-button link type="primary" @click.stop="router.push(`/weighing/workbench/${row.id}`)">查看</el-button></template></el-table-column>
      <template #empty><el-empty description="没有符合条件的称重任务" /></template>
    </el-table>
  </el-card>
</template>
