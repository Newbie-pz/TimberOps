<script setup lang="ts">
import { ArrowRight } from '@element-plus/icons-vue'

const emit = defineEmits<{
  select: [question: string, autoSend: boolean]
}>()

const questions = [
  { text: '今天煤炭一共称了多少吨？', autoSend: true },
  { text: '今天有没有发生过超重？', autoSend: true },
  { text: '蒙H12345最近称过什么货？', autoSend: true },
  { text: '查询某个称重任务的完整称重记录', autoSend: false },
]
</script>

<template>
  <div class="suggested-questions">
    <button
      v-for="question in questions"
      :key="question.text"
      type="button"
      @click="emit('select', question.text, question.autoSend)"
    >
      <span>{{ question.text }}</span>
      <small>{{ question.autoSend ? '立即查询' : '填入后编辑' }}</small>
      <el-icon><ArrowRight /></el-icon>
    </button>
  </div>
</template>
