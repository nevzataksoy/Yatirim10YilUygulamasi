<template>
  <q-avatar :size="size" class="asset-avatar" :class="`asset-avatar--${asset.toLowerCase()}`">
    {{ asset }}
  </q-avatar>
</template>

<script setup>
defineProps({
  asset: { type: String, required: true },
  size: { type: String, default: '42px' },
})
</script>
