<template>
  <div class="app-logo row items-center no-wrap">
    <div class="app-logo__mark flex flex-center">
      <q-icon name="candlestick_chart" size="24px" />
    </div>
    <div v-if="!compact" class="q-ml-sm">
      <div class="app-logo__title">Rosa Yatırım</div>
      <div class="app-logo__subtitle">10 yıllık portföy planı</div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  compact: { type: Boolean, default: false },
})
</script>
