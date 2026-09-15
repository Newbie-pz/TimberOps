<script setup lang="ts">
import { computed } from 'vue'
import type { TagProps } from 'element-plus'
import type { WeighingStatus, WeightResult } from '@/types'
import { statusLabel, weightResultLabel } from '@/utils/format'

const props = defineProps<{
  status?: WeighingStatus
  result?: WeightResult
}>()

const label = computed(() =>
  props.result ? weightResultLabel[props.result] : props.status ? statusLabel[props.status] : '—',
)
const type = computed<TagProps['type']>(() => {
  if (props.result === 'OVERWEIGHT') return 'danger'
  if (props.result === 'NORMAL' || props.status === 'COMPLETED') return 'success'
  if (props.status === 'CANCELLED') return 'info'
  if (props.status === 'WAIT_GROSS' || props.status === 'GROSS_COMPLETED') return 'warning'
  return 'primary'
})
</script>

<template>
  <el-tag :type="type" effect="light" round>{{ label }}</el-tag>
</template>
