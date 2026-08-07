<template>
  <q-card flat bordered class="metric-card">
    <q-card-section class="row items-start no-wrap q-pa-md">
      <div class="metric-card__icon flex flex-center" :class="toneClass">
        <q-icon :name="icon" size="22px" />
      </div>
      <div class="q-ml-md col min-width-0">
        <div class="text-caption text-grey-6">{{ label }}</div>
        <div class="metric-card__value ellipsis">{{ value }}</div>
        <div v-if="caption" class="text-caption text-grey-6 q-mt-xs">{{ caption }}</div>
      </div>
    </q-card-section>
  </q-card>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  label: { type: String, required: true },
  value: { type: String, required: true },
  caption: { type: String, default: '' },
  icon: { type: String, default: 'insights' },
  tone: { type: String, default: 'primary' },
})

const toneClass = computed(() => `metric-card__icon--${props.tone}`)
</script>
