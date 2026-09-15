<script setup lang="ts">
import ToolCallCard from '@/components/ai/ToolCallCard.vue'
import type { ChatMessage } from '@/types'

defineProps<{
  message: ChatMessage
}>()

function formatTime(value: string): string {
  return new Intl.DateTimeFormat('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}
</script>

<template>
  <article class="chat-message" :class="`is-${message.role}`">
    <div class="chat-message-meta">
      <strong>{{ message.role === 'assistant' ? '智能助手' : '操作员' }}</strong>
      <time :datetime="message.createdAt">{{ formatTime(message.createdAt) }}</time>
    </div>
    <div class="chat-message-bubble">
      <p>{{ message.content }}</p>
      <section v-if="message.role === 'assistant' && message.toolCalls?.length" class="message-tools">
        <h4>业务工具调用（{{ message.toolCalls.length }}）</h4>
        <ToolCallCard
          v-for="(toolCall, index) in message.toolCalls"
          :key="`${message.id}-${toolCall.name}-${index}`"
          :tool-call="toolCall"
        />
      </section>
    </div>
  </article>
</template>
