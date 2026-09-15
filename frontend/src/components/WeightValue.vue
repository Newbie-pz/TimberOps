<script setup lang="ts">
defineProps<{
  value: string | null | undefined
  prominent?: boolean
}>()
</script>

<template>
  <span class="weight-value" :class="{ 'is-prominent': prominent }">
    {{ value ?? '—' }}<small v-if="value != null"> t</small>
  </span>
</template>
