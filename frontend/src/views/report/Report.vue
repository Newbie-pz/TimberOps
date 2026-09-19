<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import {
  CircleCheck,
  DataLine,
  Download,
  Money,
  Odometer,
  Search,
} from '@element-plus/icons-vue'

import {
  exportReport,
  getDailyReport,
  getMonthlyReport,
  type BusinessReport,
  type ReportSelection,
  type ReportType,
} from '@/api/report'
import PageHeader from '@/components/PageHeader.vue'
import { useAuthStore } from '@/stores/auth'
import type { CargoType } from '@/types'

const authStore = useAuthStore()
const reportType = ref<ReportType>('daily')
const dailyDate = ref(toLocalDateValue(new Date()))
const monthlyDate = ref(toLocalMonthValue(new Date()))
const report = ref<BusinessReport | null>(null)
const loading = ref(false)
const exporting = ref(false)

const cargoLabels: Record<CargoType, string> = {
  ORE: '矿石',
  COAL: '煤炭',
  TIMBER: '木材',
  OTHER: '其他货物',
}

const reportTitle = computed(() => reportType.value === 'daily' ? '经营日报' : '经营月报')
const cards = computed(() => {
  if (!report.value) return []
  return [
    { label: '任务数量', value: report.value.task_count, unit: '单', icon: Odometer, tone: 'blue' },
    { label: '完成数量', value: report.value.completed_task_count, unit: '单', icon: CircleCheck, tone: 'green' },
    { label: '完成净重量', value: report.value.completed_net_weight_tons, unit: 't', icon: DataLine, tone: 'wood' },
    { label: '收入', value: report.value.income, unit: '元', icon: Money, tone: 'amber' },
  ]
})

function toLocalDateValue(value: Date): string {
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function toLocalMonthValue(value: Date): string {
  return toLocalDateValue(value).slice(0, 7)
}

function selection(): ReportSelection {
  if (reportType.value === 'daily') {
    return { report_type: 'daily', report_date: dailyDate.value }
  }
  const [year, month] = monthlyDate.value.split('-').map(Number)
  return { report_type: 'monthly', year, month }
}

async function load(): Promise<void> {
  loading.value = true
  try {
    if (reportType.value === 'daily') {
      report.value = await getDailyReport(dailyDate.value)
    } else {
      const [year, month] = monthlyDate.value.split('-').map(Number)
      report.value = await getMonthlyReport(year, month)
    }
  } finally {
    loading.value = false
  }
}

async function download(): Promise<void> {
  exporting.value = true
  try {
    const file = await exportReport(selection())
    const url = URL.createObjectURL(file.blob)
    const link = document.createElement('a')
    link.href = url
    link.download = file.filename
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
    ElMessage.success('业务报表已导出')
  } finally {
    exporting.value = false
  }
}

watch(reportType, () => void load())
onMounted(load)
</script>

<template>
  <PageHeader :title="reportTitle" description="按北京时间查看周期经营数据并导出 Excel">
    <el-button
      v-if="authStore.hasPermission('report:export')"
      :icon="Download"
      :loading="exporting"
      @click="download"
    >导出 Excel</el-button>
  </PageHeader>

  <el-card shadow="never" class="filter-card report-toolbar">
    <el-form inline>
      <el-form-item label="报表类型">
        <el-radio-group v-model="reportType">
          <el-radio-button value="daily">日报</el-radio-button>
          <el-radio-button value="monthly">月报</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <el-form-item v-if="reportType === 'daily'" label="业务日期">
        <el-date-picker v-model="dailyDate" type="date" value-format="YYYY-MM-DD" :clearable="false" />
      </el-form-item>
      <el-form-item v-else label="业务月份">
        <el-date-picker v-model="monthlyDate" type="month" value-format="YYYY-MM" :clearable="false" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :icon="Search" :loading="loading" @click="load">生成报表</el-button>
      </el-form-item>
    </el-form>
  </el-card>

  <div v-loading="loading" class="report-content">
    <template v-if="report">
      <div class="dashboard-date-row">
        <span>统计周期 {{ report.period_start }} 至 {{ report.period_end }}</span>
        <small>{{ report.timezone }} · 金额单位 {{ report.currency }}</small>
      </div>

      <div class="metric-grid report-metric-grid">
        <article v-for="card in cards" :key="card.label" class="metric-card">
          <div class="metric-icon" :class="`tone-${card.tone}`">
            <el-icon><component :is="card.icon" /></el-icon>
          </div>
          <div>
            <p>{{ card.label }}</p>
            <strong>{{ card.value }} <small>{{ card.unit }}</small></strong>
          </div>
        </article>
      </div>

      <div class="report-ranking-grid">
        <el-card shadow="never" class="panel-card table-card">
          <template #header><strong>货物重量排行</strong></template>
          <el-table :data="report.cargo_ranking" empty-text="当前周期暂无完成数据">
            <el-table-column type="index" label="排名" width="70" />
            <el-table-column label="货物类型" min-width="130">
              <template #default="{ row }">{{ cargoLabels[row.cargo_type as CargoType] }}</template>
            </el-table-column>
            <el-table-column prop="completed_task_count" label="完成任务" min-width="110">
              <template #default="{ row }">{{ row.completed_task_count }} 单</template>
            </el-table-column>
            <el-table-column prop="total_net_weight_tons" label="净重量" min-width="130" align="right">
              <template #default="{ row }"><strong>{{ row.total_net_weight_tons }} t</strong></template>
            </el-table-column>
          </el-table>
        </el-card>

        <el-card shadow="never" class="panel-card table-card">
          <template #header><strong>车辆运输排行</strong></template>
          <el-table :data="report.vehicle_ranking" empty-text="当前周期暂无完成数据">
            <el-table-column type="index" label="排名" width="70" />
            <el-table-column prop="plate_number" label="车牌号" min-width="140">
              <template #default="{ row }"><strong class="plate-number">{{ row.plate_number }}</strong></template>
            </el-table-column>
            <el-table-column prop="completed_task_count" label="完成运输" min-width="110">
              <template #default="{ row }">{{ row.completed_task_count }} 单</template>
            </el-table-column>
            <el-table-column prop="total_net_weight_tons" label="净重量" min-width="130" align="right">
              <template #default="{ row }"><strong>{{ row.total_net_weight_tons }} t</strong></template>
            </el-table-column>
          </el-table>
        </el-card>
      </div>
    </template>
  </div>
</template>
