<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Box, DataLine, Goods, Odometer, TrendCharts, Warning } from '@element-plus/icons-vue'

import { getMockDashboardStats, type DashboardStats } from '@/api/dashboard.mock'
import PageHeader from '@/components/PageHeader.vue'

const router = useRouter()
const stats = ref<DashboardStats | null>(null)

const cards = [
  { key: 'vehicleCount', label: '今日称重车辆', unit: '辆', icon: Odometer, tone: 'blue' },
  { key: 'totalNetWeightTons', label: '今日净货总量', unit: 't', icon: DataLine, tone: 'green' },
  { key: 'coalWeightTons', label: '煤炭重量', unit: 't', icon: Goods, tone: 'slate' },
  { key: 'oreWeightTons', label: '矿石重量', unit: 't', icon: Box, tone: 'amber' },
  { key: 'timberWeightTons', label: '木材重量', unit: 't', icon: TrendCharts, tone: 'wood' },
  { key: 'overweightCount', label: '超重次数', unit: '次', icon: Warning, tone: 'red' },
] as const

onMounted(async () => {
  stats.value = await getMockDashboardStats()
})
</script>

<template>
  <PageHeader title="运营概览" description="今日磅房运行情况与货物称重汇总">
    <el-tag type="warning" effect="plain">统计接口未开放 · 当前为演示数据</el-tag>
  </PageHeader>

  <div v-if="stats" class="metric-grid">
    <article v-for="card in cards" :key="card.key" class="metric-card">
      <div class="metric-icon" :class="`tone-${card.tone}`">
        <el-icon><component :is="card.icon" /></el-icon>
      </div>
      <div>
        <p>{{ card.label }}</p>
        <strong>{{ stats[card.key] }} <small>{{ card.unit }}</small></strong>
      </div>
    </article>
  </div>

  <div class="dashboard-grid">
    <el-card shadow="never" class="panel-card quick-actions">
      <template #header><strong>快捷操作</strong></template>
      <button type="button" @click="router.push('/weighing/create')">
        <span>01</span>
        <div><strong>创建称重任务</strong><small>车辆入场登记并开始称重</small></div>
      </button>
      <button type="button" @click="router.push('/weighing/history')">
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
