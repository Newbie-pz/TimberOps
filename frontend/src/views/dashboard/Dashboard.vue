<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  CircleCheck,
  Clock,
  DataLine,
  Money,
  Odometer,
  Refresh,
} from '@element-plus/icons-vue'

import {
  getDashboardOverview,
  type DashboardOverview,
} from '@/api/dashboard'
import PageHeader from '@/components/PageHeader.vue'
import { useAuthStore } from '@/stores/auth'
import type { CargoType, WeighingStatus } from '@/types'

const router = useRouter()
const authStore = useAuthStore()
const loading = ref(false)
const overview = ref<DashboardOverview | null>(null)

const statusLabels: Record<WeighingStatus, string> = {
  WAIT_TARE: '待称皮重',
  TARE_COMPLETED: '皮重已完成',
  WAIT_GROSS: '待称毛重',
  GROSS_COMPLETED: '毛重已完成',
  COMPLETED: '已完成',
  CANCELLED: '已取消',
}

const cargoLabels: Record<CargoType, string> = {
  ORE: '矿石',
  COAL: '煤炭',
  TIMBER: '木材',
  OTHER: '其他货物',
}

const cards = computed(() => {
  if (!overview.value) return []
  return [
    { label: '今日任务', value: overview.value.today_task_count, unit: '单', icon: Odometer, tone: 'blue' },
    { label: '今日完成', value: overview.value.today_completed_task_count, unit: '单', icon: CircleCheck, tone: 'green' },
    { label: '当前待处理', value: overview.value.pending_task_count, unit: '单', icon: Clock, tone: 'amber' },
    { label: '今日完成净重', value: overview.value.today_completed_net_weight_tons, unit: 't', icon: DataLine, tone: 'wood' },
    { label: '今日收入', value: overview.value.today_income, unit: '元', icon: Money, tone: 'slate' },
  ]
})

const maxStatusCount = computed(() => Math.max(
  1,
  ...(overview.value?.status_distribution.map((item) => item.count) ?? []),
))

const maxCargoWeight = computed(() => Math.max(
  1,
  ...(overview.value?.cargo_weight_ranking.map((item) => Number(item.total_net_weight_tons)) ?? []),
))

function barWidth(value: number, maximum: number): string {
  return `${Math.max(0, Math.min(100, (value / maximum) * 100))}%`
}

async function loadOverview(): Promise<void> {
  loading.value = true
  try {
    overview.value = await getDashboardOverview()
  } finally {
    loading.value = false
  }
}

onMounted(loadOverview)
</script>

<template>
  <PageHeader title="运营概览" description="今日磅房运行、计费与运输效率汇总（北京时间）">
    <el-button :icon="Refresh" :loading="loading" @click="loadOverview">刷新数据</el-button>
  </PageHeader>

  <div v-loading="loading" class="dashboard-overview">
    <template v-if="overview">
      <div class="dashboard-date-row">
        <span>业务日期 {{ overview.business_date }}</span>
        <small>{{ overview.timezone }} · 金额单位 {{ overview.currency }}</small>
      </div>

      <div class="metric-grid dashboard-metric-grid">
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

      <div class="dashboard-analytics-grid">
        <el-card shadow="never" class="panel-card dashboard-chart-card">
          <template #header>
            <div class="dashboard-card-heading">
              <strong>当前任务状态</strong>
              <span>未删除任务</span>
            </div>
          </template>
          <div class="dashboard-bars">
            <div v-for="item in overview.status_distribution" :key="item.status" class="dashboard-bar-row">
              <span>{{ statusLabels[item.status] }}</span>
              <div class="dashboard-bar-track">
                <i :style="{ width: barWidth(item.count, maxStatusCount) }" />
              </div>
              <strong>{{ item.count }}</strong>
            </div>
          </div>
        </el-card>

        <el-card shadow="never" class="panel-card dashboard-chart-card">
          <template #header>
            <div class="dashboard-card-heading">
              <strong>今日货物重量排行</strong>
              <span>仅统计已完成任务</span>
            </div>
          </template>
          <el-empty v-if="!overview.cargo_weight_ranking.length" description="今日暂无已完成货物" :image-size="72" />
          <div v-else class="dashboard-bars cargo-bars">
            <div v-for="item in overview.cargo_weight_ranking" :key="item.cargo_type" class="dashboard-bar-row">
              <span>{{ cargoLabels[item.cargo_type] }}</span>
              <div class="dashboard-bar-track">
                <i :style="{ width: barWidth(Number(item.total_net_weight_tons), maxCargoWeight) }" />
              </div>
              <strong>{{ item.total_net_weight_tons }} t</strong>
            </div>
          </div>
        </el-card>
      </div>

      <el-card shadow="never" class="panel-card dashboard-ranking-card">
        <template #header>
          <div class="dashboard-card-heading">
            <strong>TOP10 车辆运输排行</strong>
            <span>历史已完成任务累计</span>
          </div>
        </template>
        <el-table :data="overview.vehicle_transport_ranking" empty-text="暂无已完成运输记录">
          <el-table-column type="index" label="排名" width="80" />
          <el-table-column prop="plate_number" label="车牌号" min-width="180">
            <template #default="scope"><strong class="plate-number">{{ scope.row.plate_number }}</strong></template>
          </el-table-column>
          <el-table-column prop="completed_task_count" label="完成运输" min-width="140">
            <template #default="scope">{{ scope.row.completed_task_count }} 单</template>
          </el-table-column>
          <el-table-column prop="total_net_weight_tons" label="累计净重" min-width="180" align="right">
            <template #default="scope"><strong>{{ scope.row.total_net_weight_tons }} t</strong></template>
          </el-table-column>
        </el-table>
      </el-card>

      <div class="dashboard-grid">
        <el-card shadow="never" class="panel-card quick-actions">
          <template #header><strong>快捷操作</strong></template>
          <button v-if="authStore.hasPermission('weighing:create')" type="button" @click="router.push('/weighing/create')">
            <span>01</span>
            <div><strong>创建称重任务</strong><small>车辆入场登记并开始称重</small></div>
          </button>
          <button v-if="authStore.hasPermission('weighing:view')" type="button" @click="router.push('/weighing/history')">
            <span>02</span>
            <div><strong>查看称重历史</strong><small>查询任务状态与全部读数</small></div>
          </button>
        </el-card>

        <el-card shadow="never" class="panel-card process-card">
          <template #header><strong>标准出场流程</strong></template>
          <div class="process-line">
            <span>车辆登记</span><i />
            <span>空车称重</span><i />
            <span>装载货物</span><i />
            <span>重车称重</span><i />
            <span>完成出场</span>
          </div>
          <p>超重车辆必须卸货后复磅，系统永久保留每次称重记录。</p>
        </el-card>
      </div>
    </template>
  </div>
</template>
