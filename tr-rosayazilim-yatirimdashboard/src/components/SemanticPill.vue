<template>
  <span class="semantic-pill" :class="`semantic-pill--${tone}`">
    <span>{{ label }}</span>
    <span v-if="code" class="semantic-pill__code">{{ code }}</span>
  </span>
</template>

<script setup>
defineProps({
  label: { type: String, required: true },
  code: { type: String, default: '' },
  tone: { type: String, default: 'neutral' },
})
</script>
