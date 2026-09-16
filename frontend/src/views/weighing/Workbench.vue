<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Check, Refresh, WarningFilled } from '@element-plus/icons-vue'

import {
  completeWeighingTask,
  finishLoading,
  getWeighingTask,
  recordGross,
  recordReweigh,
  recordTare,
} from '@/api/weighing'
import PageHeader from '@/components/PageHeader.vue'
import StatusTag from '@/components/StatusTag.vue'
import WeightValue from '@/components/WeightValue.vue'
import { useWeighingStore } from '@/stores/weighing'
import type { TaskDetailResponse, WeighingTask, WeightType } from '@/types'
import {
  cargoTypeLabel,
  formatDateTime,
  isValidTons,
  positiveDifference,
  statusLabel,
  subtractTons,
  weightTypeLabel,
} from '@/utils/format'

const route = useRoute()
const router = useRouter()
const store = useWeighingStore()
const detail = ref<TaskDetailResponse | null>(null)
const loading = ref(false)
const acting = ref(false)
const tareForm = reactive({ weight_tons: '', remark: '' })
const grossForm = reactive({ weight_tons: '', remark: '' })
const reweighForm = reactive({ weight_tons: '', remark: '' })

const taskId = computed(() => String(route.params.id))
const task = computed<WeighingTask | null>(() => detail.value?.task || null)
const isOverweight = computed(() => task.value?.weight_result === 'OVERWEIGHT')
const currentGrossInput = computed(() =>
  isOverweight.value ? reweighForm.weight_tons : grossForm.weight_tons,
)
const preview = computed(() => {
  if (!task.value?.tare_weight_tons || !isValidTons(currentGrossInput.value)) return null
  return {
    net: subtractTons(currentGrossInput.value, task.value.tare_weight_tons),
    remaining: subtractTons(task.value.allowed_gross_weight_tons, currentGrossInput.value),
    overweight: positiveDifference(currentGrossInput.value, task.value.allowed_gross_weight_tons),
  }
})
const activeStep = computed(() => {
  switch (task.value?.status) {
    case 'WAIT_TARE': return 0
    case 'TARE_COMPLETED':
    case 'WAIT_GROSS': return 1
    case 'GROSS_COMPLETED': return 2
    case 'COMPLETED': return 3
    default: return 0
  }
})

async function loadTask(): Promise<void> {
  loading.value = true
  try {
    detail.value = await getWeighingTask(taskId.value)
    store.rememberTask(taskId.value)
  } finally {
    loading.value = false
  }
}

async function runAction(action: () => Promise<unknown>, successMessage: string): Promise<void> {
  acting.value = true
  try {
    await action()
    ElMessage.success(successMessage)
    await loadTask()
  } finally {
    acting.value = false
  }
}

function getWeightTypeLabel(type: WeightType): string {
  return weightTypeLabel[type]
}

async function submitTare(): Promise<void> {
  if (!isValidTons(tareForm.weight_tons)) {
    ElMessage.warning('请输入大于 0、最多三位小数的空车重量')
    return
  }
  await runAction(
    () => recordTare(taskId.value, { ...tareForm }),
    '空车称重已记录',
  )
}

async function submitGross(): Promise<void> {
  if (!isValidTons(grossForm.weight_tons)) {
    ElMessage.warning('请输入大于 0、最多三位小数的重车重量')
    return
  }
  await runAction(
    () => recordGross(taskId.value, { ...grossForm }),
    '重车称重已记录',
  )
}

async function submitReweigh(): Promise<void> {
  if (!isValidTons(reweighForm.weight_tons)) {
    ElMessage.warning('请输入有效的复磅重量')
    return
  }
  if (!reweighForm.remark.trim()) {
    ElMessage.warning('复磅必须填写卸货或调整说明')
    return
  }
  await runAction(
    () => recordReweigh(taskId.value, { ...reweighForm }),
    '复磅结果已记录',
  )
}

onMounted(loadTask)
</script>

<template>
  <PageHeader title="称重工作台" description="按任务状态完成每一步操作，所有读数永久留痕">
    <el-button :icon="ArrowLeft" @click="router.push('/weighing/history')">返回历史</el-button>
    <el-button :icon="Refresh" :loading="loading" @click="loadTask">刷新</el-button>
  </PageHeader>

  <div v-loading="loading" class="workbench">
    <template v-if="task">
      <el-card shadow="never" class="panel-card task-banner" :class="{ overweight: isOverweight }">
        <div class="task-banner-main">
          <div>
            <p>任务编号</p>
            <h2>{{ task.task_no }}</h2>
          </div>
          <div class="task-tags">
            <StatusTag :status="task.status" />
            <StatusTag :result="task.weight_result" />
          </div>
        </div>
        <div class="task-meta">
          <span>货物：{{ cargoTypeLabel[task.cargo_type] }}{{ task.cargo_name ? ` / ${task.cargo_name}` : '' }}</span>
          <span>司机：{{ task.driver_name_snapshot || '未登记' }}</span>
          <span>方向：出场装货</span>
        </div>
      </el-card>

      <el-card shadow="never" class="panel-card steps-card">
        <el-steps :active="activeStep" finish-status="success" align-center>
          <el-step title="空车称重" />
          <el-step title="重车称重" />
          <el-step title="结果确认" />
          <el-step title="完成出场" />
        </el-steps>
      </el-card>

      <div class="weight-summary-grid">
        <article><span>核定总质量</span><WeightValue :value="task.allowed_gross_weight_tons" prominent /></article>
        <article><span>空车皮重</span><WeightValue :value="task.tare_weight_tons" prominent /></article>
        <article><span>当前有效毛重</span><WeightValue :value="task.gross_weight_tons" prominent /></article>
        <article class="accent"><span>当前净货重</span><WeightValue :value="task.net_weight_tons" prominent /></article>
      </div>

      <el-alert
        v-if="isOverweight"
        class="overweight-alert"
        type="error"
        :closable="false"
        show-icon
      >
        <template #title>车辆超重 {{ task.overweight_tons }} t，禁止完成出厂</template>
        请卸下部分货物后重新称重。本次超重读数已永久保存，不会被复磅覆盖。
      </el-alert>

      <div class="workbench-grid">
        <el-card shadow="never" class="panel-card operation-card">
          <template #header>
            <div class="card-title-row">
              <strong>当前操作</strong>
              <span>{{ statusLabel[task.status] }}</span>
            </div>
          </template>

          <div v-if="task.status === 'WAIT_TARE'" class="operation-content">
            <p class="operation-index">步骤 01</p>
            <h3>记录空车重量</h3>
            <p>车辆保持空载并稳定停放在地磅上。</p>
            <label>空车重量（t）</label>
            <el-input v-model="tareForm.weight_tons" size="large" inputmode="decimal" placeholder="15.820">
              <template #append>t</template>
            </el-input>
            <el-input v-model="tareForm.remark" placeholder="备注（可选）" />
            <el-button type="primary" size="large" :loading="acting" @click="submitTare">提交空车称重</el-button>
          </div>

          <div v-else-if="task.status === 'TARE_COMPLETED'" class="operation-content centered">
            <div class="operation-symbol"><el-icon><Check /></el-icon></div>
            <h3>空车称重完成</h3>
            <p>已记录 <WeightValue :value="task.tare_weight_tons" />，装货完成后进入第二次称重。</p>
            <el-button type="primary" size="large" :loading="acting" @click="runAction(() => finishLoading(taskId), '已进入重车待称状态')">装货完成，等待重车称重</el-button>
          </div>

          <div v-else-if="task.status === 'WAIT_GROSS' && !isOverweight" class="operation-content">
            <p class="operation-index">步骤 02</p>
            <h3>记录重车重量</h3>
            <p>系统将在服务端计算净货重和超重结果。</p>
            <label>重车重量（t）</label>
            <el-input v-model="grossForm.weight_tons" size="large" inputmode="decimal" placeholder="47.360">
              <template #append>t</template>
            </el-input>
            <el-input v-model="grossForm.remark" placeholder="备注（可选）" />
            <el-button type="primary" size="large" :loading="acting" @click="submitGross">提交重车称重</el-button>
          </div>

          <div v-else-if="task.status === 'WAIT_GROSS' && isOverweight" class="operation-content danger-operation">
            <p class="operation-index"><el-icon><WarningFilled /></el-icon> 超重处置</p>
            <h3>卸货后重新称重</h3>
            <label>复磅重量（t）</label>
            <el-input v-model="reweighForm.weight_tons" size="large" inputmode="decimal" placeholder="48.600">
              <template #append>t</template>
            </el-input>
            <label>复磅说明（必填）</label>
            <el-input v-model="reweighForm.remark" type="textarea" :rows="3" placeholder="例如：卸货后重新称重" />
            <el-button type="danger" size="large" :loading="acting" @click="submitReweigh">提交复磅</el-button>
          </div>

          <div v-else-if="task.status === 'GROSS_COMPLETED'" class="operation-content centered">
            <div class="operation-symbol"><el-icon><Check /></el-icon></div>
            <h3>称重结果正常</h3>
            <p>最终净货重 <WeightValue :value="task.net_weight_tons" prominent />，可以完成出厂。</p>
            <el-button type="success" size="large" :loading="acting" @click="runAction(() => completeWeighingTask(taskId), '称重任务已完成')">确认完成出厂</el-button>
          </div>

          <div v-else-if="task.status === 'COMPLETED'" class="operation-content centered completed-state">
            <div class="operation-symbol"><el-icon><Check /></el-icon></div>
            <h3>任务已完成</h3>
            <p>完成时间：{{ formatDateTime(task.completed_at) }}</p>
            <WeightValue :value="task.net_weight_tons" prominent />
          </div>

          <el-result v-else-if="task.status === 'CANCELLED'" icon="info" title="任务已取消" sub-title="已取消任务不能恢复称重流程" />
        </el-card>

        <el-card shadow="never" class="panel-card preview-card">
          <template #header><strong>重量计算预览</strong></template>
          <template v-if="preview">
            <dl class="detail-list calculation-list">
              <div><dt>预计净货重</dt><dd>{{ preview.net }} t</dd></div>
              <div><dt>剩余载重</dt><dd :class="{ danger: preview.remaining?.startsWith('-') }">{{ preview.remaining }} t</dd></div>
              <div><dt>预计超重</dt><dd :class="{ danger: preview.overweight !== '0.000' }">{{ preview.overweight }} t</dd></div>
            </dl>
            <p class="preview-note">预览使用千分之一吨整数计算，最终结果以后端为准。</p>
          </template>
          <el-empty v-else description="输入重车或复磅重量后显示预览" :image-size="72" />
        </el-card>
      </div>

      <el-card shadow="never" class="table-card record-card">
        <template #header>
          <div class="card-title-row"><strong>称重记录</strong><span>共 {{ detail?.records.length || 0 }} 条 · 只追加不可覆盖</span></div>
        </template>
        <el-table :data="detail?.records || []" stripe>
          <el-table-column prop="sequence_no" label="序号" width="80" />
          <el-table-column label="读数类型" min-width="130"><template #default="{ row }">{{ getWeightTypeLabel(row.weight_type) }}</template></el-table-column>
          <el-table-column label="重量" min-width="130"><template #default="{ row }"><WeightValue :value="row.weight_tons" prominent /></template></el-table-column>
          <el-table-column prop="source" label="来源" min-width="100"><template #default="{ row }">{{ row.source === 'MANUAL' ? '人工录入' : '设备' }}</template></el-table-column>
          <el-table-column label="称重时间" min-width="190"><template #default="{ row }">{{ formatDateTime(row.recorded_at) }}</template></el-table-column>
          <el-table-column prop="remark" label="备注" min-width="220" show-overflow-tooltip />
          <template #empty><el-empty description="尚无称重记录" /></template>
        </el-table>
      </el-card>
    </template>
  </div>
</template>
