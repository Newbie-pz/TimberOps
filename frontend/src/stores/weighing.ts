import { defineStore } from 'pinia'
import { ref } from 'vue'

const STORAGE_KEY = 'timberops:last-weighing-task'

export const useWeighingStore = defineStore('weighing', () => {
  const lastTaskId = ref<string | null>(localStorage.getItem(STORAGE_KEY))

  function rememberTask(id: string): void {
    lastTaskId.value = id
    localStorage.setItem(STORAGE_KEY, id)
  }

  return { lastTaskId, rememberTask }
})
