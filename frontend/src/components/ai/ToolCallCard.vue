<script setup lang="ts">
import { computed } from 'vue'

import type { AIToolCall } from '@/types'

const props = defineProps<{
  toolCall: AIToolCall
}>()

const toolLabels: Record<string, string> = {
  get_today_weighing_summary: '今日称重汇总',
  get_cargo_weight_summary: '货物重量汇总',
  get_overweight_records: '超重记录查询',
  get_vehicle_weighing_history: '车辆称重历史',
  get_weighing_task_detail: '称重任务详情',
}

const argumentEntries = computed(() => Object.entries(props.toolCall.arguments))
const statusLabel = computed(() => {
  if (props.toolCall.status === 'completed') return '已完成'
  if (props.toolCall.status === 'failed') return '执行失败'
  if (props.toolCall.status === 'requested') return '已请求'
  return props.toolCall.status
})
const statusTone = computed(() => {
  if (props.toolCall.status === 'completed') return 'success'
  if (props.toolCall.status === 'failed') return 'danger'
  return 'info'
})

function formatArgument(value: unknown): string {
  if (value === null) return 'null'
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  try {
    return JSON.stringify(value)
  } catch {
    return '[无法显示的参数]'
  }
}
</script>

<template>
  <details class="tool-call-card">
    <summary>
      <span class="tool-call-identity">
        <code>{{ toolCall.name }}</code>
        <small>{{ toolLabels[toolCall.name] || '业务查询工具' }}</small>
      </span>
      <el-tag :type="statusTone" size="small" effect="plain">{{ statusLabel }}</el-tag>
    </summary>
    <div class="tool-call-body">
      <p class="tool-arguments-title">调用参数</p>
      <dl v-if="argumentEntries.length" class="tool-arguments">
        <div v-for="([key, value]) in argumentEntries" :key="key">
          <dt>{{ key }}</dt>
          <dd>{{ formatArgument(value) }}</dd>
        </div>
      </dl>
      <p v-else class="tool-empty-arguments">无参数</p>
    </div>
  </details>
</template>
