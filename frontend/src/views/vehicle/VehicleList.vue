<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Delete, Plus, Refresh } from '@element-plus/icons-vue'

import { createVehicle, deleteVehicle, listVehicles, updateVehicle } from '@/api/vehicle'
import PageHeader from '@/components/PageHeader.vue'
import WeightValue from '@/components/WeightValue.vue'
import type { Vehicle, VehicleCreate, VehicleType, VehicleUpdate } from '@/types'
import { useAuthStore } from '@/stores/auth'
import { isValidTons, vehicleTypeLabel } from '@/utils/format'

interface VehicleForm {
  plate_number: string
  driver_name: string
  driver_phone: string
  vehicle_type: VehicleType | ''
  allowed_gross_weight_tons: string
  remark: string
}

const vehicles = ref<Vehicle[]>([])
const authStore = useAuthStore()
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const editingId = ref<string | null>(null)
const formRef = ref<FormInstance>()
const form = reactive<VehicleForm>({
  plate_number: '',
  driver_name: '',
  driver_phone: '',
  vehicle_type: '',
  allowed_gross_weight_tons: '',
  remark: '',
})
const rules: FormRules<VehicleForm> = {
  plate_number: [{ required: true, message: '请输入车牌号', trigger: 'blur' }],
  vehicle_type: [{ required: true, message: '请选择车辆类型', trigger: 'change' }],
  allowed_gross_weight_tons: [
    { required: true, message: '请输入核定总质量', trigger: 'blur' },
    {
      validator: (_rule, value: string, callback) =>
        isValidTons(value) ? callback() : callback(new Error('请输入大于 0、最多三位小数的吨数')),
      trigger: 'blur',
    },
  ],
}

function clearForm(): void {
  Object.assign(form, {
    plate_number: '',
    driver_name: '',
    driver_phone: '',
    vehicle_type: '',
    allowed_gross_weight_tons: '',
    remark: '',
  })
  formRef.value?.clearValidate()
}

function openCreate(): void {
  editingId.value = null
  clearForm()
  dialogVisible.value = true
}

function openEdit(vehicle: Vehicle): void {
  editingId.value = vehicle.id
  Object.assign(form, {
    plate_number: vehicle.plate_number,
    driver_name: vehicle.driver_name || '',
    driver_phone: vehicle.driver_phone || '',
    vehicle_type: vehicle.vehicle_type || '',
    allowed_gross_weight_tons: vehicle.allowed_gross_weight_tons,
    remark: vehicle.remark || '',
  })
  dialogVisible.value = true
}

async function loadVehicles(): Promise<void> {
  loading.value = true
  try {
    vehicles.value = await listVehicles()
  } finally {
    loading.value = false
  }
}

async function submit(): Promise<void> {
  if (!(await formRef.value?.validate())) return
  saving.value = true
  const common: VehicleUpdate = {
    driver_name: form.driver_name || null,
    driver_phone: form.driver_phone || null,
    vehicle_type: form.vehicle_type as VehicleType,
    allowed_gross_weight_tons: form.allowed_gross_weight_tons,
    remark: form.remark || null,
  }
  try {
    if (editingId.value) {
      await updateVehicle(editingId.value, common)
      ElMessage.success('车辆档案已更新，历史任务快照不受影响')
    } else {
      const payload: VehicleCreate = { plate_number: form.plate_number, ...common }
      await createVehicle(payload)
      ElMessage.success('车辆创建成功')
    }
    dialogVisible.value = false
    await loadVehicles()
  } finally {
    saving.value = false
  }
}

async function removeVehicle(vehicle: Vehicle): Promise<void> {
  let reason = ''
  try {
    const result = await ElMessageBox.prompt(
      `请输入删除车辆 ${vehicle.plate_number} 的原因`,
      '删除车辆',
      {
        confirmButtonText: '确认删除',
        cancelButtonText: '取消',
        inputValidator: (value) => Boolean(value?.trim()) || '必须填写删除原因',
      },
    )
    reason = result.value.trim()
  } catch {
    return
  }
  await deleteVehicle(vehicle.id, reason)
  ElMessage.success('车辆已删除')
  await loadVehicles()
}

onMounted(loadVehicles)
</script>

<template>
  <PageHeader title="车辆管理" description="维护车辆、常用司机和当前核定总质量">
    <el-button :icon="Refresh" @click="loadVehicles">刷新</el-button>
    <el-button v-if="authStore.hasPermission('vehicle:create')" type="primary" :icon="Plus" @click="openCreate">新增车辆</el-button>
  </PageHeader>

  <el-card shadow="never" class="table-card">
    <el-table v-loading="loading" :data="vehicles" stripe>
      <el-table-column prop="plate_number" label="车牌号" min-width="130">
        <template #default="{ row }"><strong class="plate-number">{{ row.plate_number }}</strong></template>
      </el-table-column>
      <el-table-column prop="driver_name" label="司机" min-width="110" />
      <el-table-column prop="driver_phone" label="联系电话" min-width="140" />
      <el-table-column label="车辆类型" min-width="130">
        <template #default="{ row }">{{ row.vehicle_type ? vehicleTypeLabel[row.vehicle_type as VehicleType] : `待标准化${row.vehicle_type_legacy ? `（原值：${row.vehicle_type_legacy}）` : ''}` }}</template>
      </el-table-column>
      <el-table-column label="核定总质量" min-width="140">
        <template #default="{ row }"><WeightValue :value="row.allowed_gross_weight_tons" /></template>
      </el-table-column>
      <el-table-column prop="remark" label="备注" min-width="160" show-overflow-tooltip />
      <el-table-column v-if="authStore.hasPermission('vehicle:update') || authStore.hasPermission('vehicle:delete')" label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button v-if="authStore.hasPermission('vehicle:update')" link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button v-if="authStore.hasPermission('vehicle:delete')" link type="danger" :icon="Delete" @click="removeVehicle(row)">删除</el-button>
        </template>
      </el-table-column>
      <template #empty><el-empty description="暂无车辆，请先新增车辆" /></template>
    </el-table>
  </el-card>

  <el-dialog v-model="dialogVisible" :title="editingId ? '编辑车辆' : '新增车辆'" width="560px">
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
      <div class="form-grid two-columns">
        <el-form-item label="车牌号" prop="plate_number">
          <el-input v-model="form.plate_number" :disabled="Boolean(editingId)" placeholder="例如：蒙H12345" />
        </el-form-item>
        <el-form-item label="核定总质量（t）" prop="allowed_gross_weight_tons">
          <el-input v-model="form.allowed_gross_weight_tons" inputmode="decimal" placeholder="49.000" />
        </el-form-item>
        <el-form-item label="司机姓名"><el-input v-model="form.driver_name" /></el-form-item>
        <el-form-item label="联系电话"><el-input v-model="form.driver_phone" /></el-form-item>
        <el-form-item label="车辆类型" prop="vehicle_type">
          <el-select v-model="form.vehicle_type" placeholder="请选择车辆类型" style="width: 100%">
            <el-option label="小型货车" value="SMALL" />
            <el-option label="中型货车" value="MEDIUM" />
            <el-option label="大型货车" value="LARGE" />
          </el-select>
        </el-form-item>
      </div>
      <el-form-item label="备注"><el-input v-model="form.remark" type="textarea" :rows="2" /></el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="submit">保存</el-button>
    </template>
  </el-dialog>
</template>
