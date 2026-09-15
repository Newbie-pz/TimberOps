<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import { Delete, Promotion } from '@element-plus/icons-vue'

import { chatWithAI } from '@/api/ai'
import ChatMessageView from '@/components/ai/ChatMessage.vue'
import SuggestedQuestions from '@/components/ai/SuggestedQuestions.vue'
import PageHeader from '@/components/PageHeader.vue'
import type { ChatMessage } from '@/types'

const messages = ref<ChatMessage[]>([])
const draft = ref('')
const loading = ref(false)
const errorMessage = ref('')
const conversationRef = ref<HTMLElement>()
let messageSequence = 0

const canSend = computed(() => Boolean(draft.value.trim()) && !loading.value)

function createMessage(
  role: ChatMessage['role'],
  content: string,
  toolCalls?: ChatMessage['toolCalls'],
): ChatMessage {
  messageSequence += 1
  return {
    id: `${Date.now()}-${messageSequence}`,
    role,
    content,
    toolCalls,
    createdAt: new Date().toISOString(),
  }
}

async function scrollToLatest(): Promise<void> {
  await nextTick()
  const container = conversationRef.value
  if (container) container.scrollTop = container.scrollHeight
}

async function sendMessage(): Promise<void> {
  const question = draft.value.trim()
  if (!question || loading.value) return

  loading.value = true
  errorMessage.value = ''
  messages.value.push(createMessage('user', question))
  draft.value = ''
  await scrollToLatest()

  try {
    const response = await chatWithAI({ message: question })
    messages.value.push(
      createMessage('assistant', response.answer, response.tool_calls),
    )
  } catch {
    errorMessage.value = '本次查询未完成。AI 服务可能未启用或暂时不可用，请稍后重试。'
    draft.value = question
  } finally {
    loading.value = false
    await scrollToLatest()
  }
}

function handleInputKeydown(event: KeyboardEvent): void {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    void sendMessage()
  }
}

function selectQuestion(question: string, autoSend: boolean): void {
  if (loading.value) return
  draft.value = question
  if (autoSend) void sendMessage()
}

function clearConversation(): void {
  if (loading.value) return
  messages.value = []
  draft.value = ''
  errorMessage.value = ''
}
</script>

<template>
  <PageHeader
    title="TimberOps 智能业务助手"
    description="基于企业真实称重数据提供自然语言查询与分析"
  >
    <el-button
      :icon="Delete"
      :disabled="!messages.length || loading"
      @click="clearConversation"
    >
      清空对话
    </el-button>
  </PageHeader>

  <section class="ai-assistant-panel">
    <div ref="conversationRef" class="ai-conversation">
      <div v-if="!messages.length" class="ai-welcome">
        <div class="ai-welcome-mark">AI</div>
        <p class="ai-welcome-eyebrow">READ-ONLY BUSINESS ASSISTANT</p>
        <h2>TimberOps 智能业务助手</h2>
        <p>您好，我可以依据 TimberOps 中的企业称重数据，协助完成以下查询：</p>
        <ul class="ai-capabilities">
          <li>查询今日称重汇总</li>
          <li>查询指定货物运输重量</li>
          <li>查询历史超重情况</li>
          <li>查询车辆称重历史</li>
          <li>查询具体称重任务</li>
        </ul>
        <SuggestedQuestions @select="selectQuestion" />
      </div>

      <div v-else class="chat-message-list">
        <ChatMessageView
          v-for="message in messages"
          :key="message.id"
          :message="message"
        />
        <div v-if="loading" class="assistant-loading" aria-live="polite">
          <span class="assistant-loading-dot" />
          正在查询业务数据…
        </div>
      </div>
    </div>

    <el-alert
      v-if="errorMessage"
      class="ai-error-alert"
      :title="errorMessage"
      type="error"
      show-icon
      closable
      @close="errorMessage = ''"
    />

    <div class="ai-composer">
      <el-input
        v-model="draft"
        type="textarea"
        :rows="3"
        resize="none"
        maxlength="2000"
        show-word-limit
        :disabled="loading"
        placeholder="输入业务问题，Enter 发送，Shift + Enter 换行"
        @keydown="handleInputKeydown"
      />
      <el-button
        type="primary"
        size="large"
        :icon="Promotion"
        :loading="loading"
        :disabled="!canSend"
        @click="sendMessage"
      >
        发送
      </el-button>
    </div>

    <footer class="ai-safety-note">
      当前智能助手仅支持只读业务查询，不会修改称重、车辆或客户数据。
    </footer>
  </section>
</template>
