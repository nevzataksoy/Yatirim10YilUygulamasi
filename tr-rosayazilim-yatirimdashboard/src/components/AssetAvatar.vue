<template>
  <q-avatar
    square
    :size="size"
    class="asset-avatar"
    :class="`asset-avatar--${asset.toLowerCase()}`"
  >
    {{ asset }}
  </q-avatar>
</template>

<script setup>
defineProps({
  asset: { type: String, required: true },
  size: { type: String, default: '42px' },
})
</script>

<style scoped>
.asset-avatar {
  border-radius: 12px !important;
  font-weight: 700;
  letter-spacing: -0.02em;
  overflow: hidden;
}
</style>
