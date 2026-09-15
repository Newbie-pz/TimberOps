<script setup lang="ts">
defineProps<{
  title: string
  description: string
}>()
</script>

<template>
  <div class="page-heading">
    <div>
      <h2>{{ title }}</h2>
      <p>{{ description }}</p>
    </div>
    <div class="page-heading-actions">
      <slot />
    </div>
  </div>
</template>
