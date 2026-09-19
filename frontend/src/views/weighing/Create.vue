<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import type { FormInstance, FormRules } from 'element-plus'
import { ArrowRight, Refresh } from '@element-plus/icons-vue'

import { listCustomers } from '@/api/customer'
import { listVehicles } from '@/api/vehicle'
import { createWeighingTask, getCargoCatalog } from '@/api/weighing'
import PageHeader from '@/components/PageHeader.vue'
import WeightValue from '@/components/WeightValue.vue'
import { useWeighingStore } from '@/stores/weighing'
import { vehicleTypeLabel } from '@/utils/format'
import type { CargoCatalog, CargoType, Customer, Vehicle, WeighingTaskCreate } from '@/types'

const router = useRouter()
const store = useWeighingStore()
const formRef = ref<FormInstance>()
const vehicles = ref<Vehicle[]>([])
const customers = ref<Customer[]>([])
const cargoCatalog = ref<CargoCatalog>({ COAL: [], ORE: [], TIMBER: [], OTHER: [] })
const loadingOptions = ref(false)
const submitting = ref(false)
const form = reactive({
  vehicle_id: '',
  customer_id: '',
  cargo_type: '' as CargoType | '',
  cargo_name: '',
  cargo_remark: '',
})

const selectedVehicle = computed(() =>
  vehicles.value.find((vehicle) => vehicle.id === form.vehicle_id),
)
const cargoNameOptions = computed(() =>
  form.cargo_type ? cargoCatalog.value[form.cargo_type] : [],
)
const rules: FormRules = {
  vehicle_id: [{ required: true, message: '请选择车辆', trigger: 'change' }],
  cargo_type: [{ required: true, message: '请选择货物类型', trigger: 'change' }],
}
const cargoOptions: Array<{ value: CargoType; label: string }> = [
  { value: 'ORE', label: '矿石' },
  { value: 'COAL', label: '煤炭' },
  { value: 'TIMBER', label: '木材' },
  { value: 'OTHER', label: '其他' },
]

async function loadOptions(): Promise<void> {
  loadingOptions.value = true
  try {
    const [vehicleItems, customerItems, catalog] = await Promise.all([
      listVehicles(),
      listCustomers(),
      getCargoCatalog(),
    ])
    vehicles.value = vehicleItems
    customers.value = customerItems
    cargoCatalog.value = catalog
  } finally {
    loadingOptions.value = false
  }
}

watch(
  () => form.cargo_type,
  () => {
    form.cargo_name = ''
  },
)

async function submit(): Promise<void> {
  if (!(await formRef.value?.validate())) return
  submitting.value = true
  const payload: WeighingTaskCreate = {
    vehicle_id: form.vehicle_id,
    customer_id: form.customer_id || null,
    weighing_direction: 'OUTBOUND',
    cargo_type: form.cargo_type as CargoType,
    cargo_name: form.cargo_name || null,
    cargo_remark: form.cargo_remark || null,
  }
  try {
    const task = await createWeighingTask(payload)
    store.rememberTask(task.id)
    ElMessage.success(`任务 ${task.task_no} 创建成功`)
    await router.push(`/weighing/workbench/${task.id}`)
  } finally {
    submitting.value = false
  }
}

onMounted(loadOptions)
</script>

<template>
  <PageHeader title="创建称重任务" description="登记车辆和本次货物，客户信息可选">
    <el-button :icon="Refresh" :loading="loadingOptions" @click="loadOptions">刷新档案</el-button>
  </PageHeader>

  <div class="form-page-grid">
    <el-card shadow="never" class="panel-card form-card">
      <template #header><strong>车辆与货物信息</strong></template>
      <el-alert v-if="!loadingOptions && !vehicles.length" type="warning" :closable="false" show-icon>
        <template #title>还没有车辆档案，请先前往车辆管理新增车辆。</template>
      </el-alert>
      <el-form ref="formRef" v-loading="loadingOptions" :model="form" :rules="rules" label-position="top">
        <div class="form-grid two-columns">
          <el-form-item label="车辆" prop="vehicle_id">
            <el-select v-model="form.vehicle_id" filterable placeholder="选择车牌号" style="width: 100%">
              <el-option v-for="vehicle in vehicles" :key="vehicle.id" :label="vehicle.plate_number" :value="vehicle.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="客户（可选）">
            <el-select v-model="form.customer_id" clearable filterable placeholder="不关联客户" style="width: 100%">
              <el-option v-for="customer in customers" :key="customer.id" :label="customer.name" :value="customer.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="货物类型" prop="cargo_type">
            <el-select v-model="form.cargo_type" placeholder="选择货物类型" style="width: 100%">
              <el-option v-for="item in cargoOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="货物名称" prop="cargo_name">
            <el-select
              v-model="form.cargo_name"
              clearable
              filterable
              :disabled="!form.cargo_type || !cargoNameOptions.length"
              placeholder="可不选具体品种"
              style="width: 100%"
            >
              <el-option v-for="name in cargoNameOptions" :key="name" :label="name" :value="name" />
            </el-select>
          </el-form-item>
        </div>
        <el-form-item label="货物备注"><el-input v-model="form.cargo_remark" type="textarea" :rows="3" /></el-form-item>
        <el-button type="primary" size="large" :icon="ArrowRight" :disabled="!vehicles.length" :loading="submitting" @click="submit">
          创建并进入称重工作台
        </el-button>
      </el-form>
    </el-card>

    <el-card shadow="never" class="panel-card vehicle-snapshot-card">
      <template #header><strong>车辆档案快照</strong></template>
      <template v-if="selectedVehicle">
        <p class="snapshot-plate">{{ selectedVehicle.plate_number }}</p>
        <dl class="detail-list">
          <div><dt>司机</dt><dd>{{ selectedVehicle.driver_name || '未登记' }}</dd></div>
          <div><dt>联系电话</dt><dd>{{ selectedVehicle.driver_phone || '未登记' }}</dd></div>
          <div><dt>车辆类型</dt><dd>{{ selectedVehicle.vehicle_type ? vehicleTypeLabel[selectedVehicle.vehicle_type] : '待标准化' }}</dd></div>
          <div><dt>核定总质量</dt><dd><WeightValue :value="selectedVehicle.allowed_gross_weight_tons" prominent /></dd></div>
        </dl>
        <el-alert title="创建后核定总质量与司机信息将保存为任务快照" type="info" :closable="false" show-icon />
      </template>
      <el-empty v-else description="选择车辆后显示档案" />
    </el-card>
  </div>
</template>
