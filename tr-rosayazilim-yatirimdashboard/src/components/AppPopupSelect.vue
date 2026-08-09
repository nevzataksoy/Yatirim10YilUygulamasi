<template>
  <div class="app-popup-select">
    <q-input
      :model-value="displayValue"
      :label="label"
      :placeholder="placeholder"
      :dense="dense"
      :disable="disabled"
      :readonly="true"
      :clearable="clearable && hasValue && !disabled"
      :error="error"
      :error-message="errorMessage"
      :hint="hint"
      outlined
      class="app-popup-select__field"
      @click="openDialog"
      @clear.stop="clearSelection"
    >
      <template #prepend><slot name="prepend" /></template>
      <template #append>
        <slot name="append">
          <q-icon name="arrow_drop_down" class="cursor-pointer" @click.stop="openDialog" />
        </slot>
      </template>
    </q-input>

    <q-dialog v-model="dialogOpen" :position="dialogPosition" :maximized="false" @hide="onDialogHide">
      <q-card class="popup-select-card">
        <q-card-section class="popup-select-card__header">
          <div class="row items-start no-wrap">
            <div class="col min-width-0">
              <div class="text-h6 text-weight-bold">{{ dialogTitle || label }}</div>
              <div v-if="dialogCaption" class="text-caption text-grey-6 q-mt-xs">
                {{ dialogCaption }}
              </div>
            </div>
            <q-btn flat round dense icon="close" v-close-popup aria-label="Kapat" />
          </div>
        </q-card-section>

        <q-card-section v-if="searchable" class="q-pt-none q-pb-sm">
          <q-input
            ref="searchInput"
            v-model="query"
            dense
            outlined
            clearable
            :label="searchLabel"
            :placeholder="searchPlaceholder"
          >
            <template #prepend><q-icon name="search" /></template>
          </q-input>
        </q-card-section>

        <div
          v-if="multiple && candidateArray.length"
          class="popup-select-card__selection-strip q-px-md q-pb-sm"
        >
          <q-chip
            v-for="opt in candidateOptions"
            :key="optionKey(opt)"
            dense
            removable
            color="primary"
            text-color="white"
            @remove="selectCandidate(opt)"
          >
            {{ opt.label }}
          </q-chip>
        </div>

        <q-separator />

        <q-scroll-area class="popup-select-card__scroll">
          <q-list separator>
            <q-item
              v-for="opt in filteredOptions"
              :key="optionKey(opt)"
              clickable
              v-ripple
              :disable="opt.disable"
              :active="isCandidate(opt.value)"
              active-class="popup-select-option--active"
              class="popup-select-option"
              @click="selectCandidate(opt)"
            >
              <q-item-section avatar>
                <q-icon
                  :name="selectionIcon(opt.value)"
                  :color="isCandidate(opt.value) ? 'primary' : 'grey-5'"
                />
              </q-item-section>
              <q-item-section v-if="opt.icon" avatar>
                <q-icon :name="opt.icon" color="primary" />
              </q-item-section>
              <q-item-section>
                <slot name="option" :option="opt" :selected="isCandidate(opt.value)">
                  <q-item-label class="text-weight-medium">{{ opt.label }}</q-item-label>
                  <q-item-label v-if="opt.caption" caption>{{ opt.caption }}</q-item-label>
                </slot>
              </q-item-section>
              <q-item-section v-if="opt.badge" side>
                <q-badge outline color="primary">{{ opt.badge }}</q-badge>
              </q-item-section>
            </q-item>
            <q-item v-if="!filteredOptions.length">
              <q-item-section class="text-center text-grey-6 q-py-xl">
                <q-icon name="search_off" size="32px" class="q-mb-sm" />
                <q-item-label>{{ emptyLabel }}</q-item-label>
              </q-item-section>
            </q-item>
          </q-list>
        </q-scroll-area>

        <q-separator />

        <q-card-actions class="popup-select-card__actions popup-action-footer q-pa-md">
          <q-btn
            v-if="clearable"
            push
            color="negative"
            icon="backspace"
            :label="clearLabel"
            no-caps
            class="popup-select-card__action popup-select-card__action--clear"
            @click="clearCandidate"
          />
          <q-space class="popup-select-card__action-spacer" />
          <q-btn
            push
            color="grey-3"
            text-color="grey-9"
            icon="close"
            :label="cancelLabel"
            no-caps
            class="popup-select-card__action popup-select-card__action--cancel"
            v-close-popup
          />
          <q-btn
            push
            color="primary"
            icon="check"
            :label="applyLabel"
            no-caps
            class="popup-select-card__action popup-select-card__action--apply"
            @click="applySelection"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { useQuasar } from 'quasar'

const props = defineProps({
  modelValue: { type: [String, Number, Boolean, Object, Array], default: null },
  options: { type: Array, default: () => [] },
  optionLabel: { type: [String, Function], default: 'label' },
  optionValue: { type: [String, Function], default: 'value' },
  optionDisable: { type: [String, Function], default: 'disable' },
  label: { type: String, default: 'Seçim' },
  placeholder: { type: String, default: 'Seçiniz' },
  dialogTitle: { type: String, default: '' },
  dialogCaption: { type: String, default: '' },
  searchLabel: { type: String, default: 'Ara' },
  searchPlaceholder: { type: String, default: 'Seçenekleri filtrele' },
  emptyLabel: { type: String, default: 'Eşleşen seçenek bulunamadı.' },
  clearLabel: { type: String, default: 'Temizle' },
  cancelLabel: { type: String, default: 'Vazgeç' },
  applyLabel: { type: String, default: 'Seçimi Uygula' },
  clearable: { type: Boolean, default: true },
  searchable: { type: Boolean, default: true },
  disabled: { type: Boolean, default: false },
  multiple: { type: Boolean, default: false },
  dense: { type: Boolean, default: false },
  emitValue: { type: Boolean, default: true },
  immediateSingle: { type: Boolean, default: false },
  displayLimit: { type: Number, default: 3 },
  hint: { type: String, default: '' },
  error: { type: Boolean, default: false },
  errorMessage: { type: String, default: '' },
  filterFn: { type: Function, default: null },
})

const emit = defineEmits(['update:modelValue', 'change', 'open', 'close'])
const $q = useQuasar()
const dialogOpen = ref(false)
const query = ref('')
const candidateValue = ref(normalizeModelValue(props.modelValue))
const searchInput = ref(null)

function readField(option, accessor, fallback) {
  if (typeof accessor === 'function') return accessor(option)
  if (option && typeof option === 'object' && accessor in option) return option[accessor]
  return fallback
}

const normalizedOptions = computed(() =>
  props.options.map((option, index) => {
    if (option && typeof option === 'object' && !Array.isArray(option)) {
      const value = readField(option, props.optionValue, option.value ?? index)
      return {
        raw: option,
        value,
        label: String(readField(option, props.optionLabel, option.label ?? value) ?? ''),
        disable: Boolean(readField(option, props.optionDisable, option.disable ?? false)),
        caption: option.caption || '',
        icon: option.icon || '',
        badge: option.badge || '',
      }
    }
    return {
      raw: option,
      value: option,
      label: String(option ?? ''),
      disable: false,
      caption: '',
      icon: '',
      badge: '',
    }
  }),
)

function normalizeModelValue(value) {
  if (props.multiple) return Array.isArray(value) ? [...value] : []
  return value ?? null
}

function comparable(value) {
  if (value && typeof value === 'object') {
    const normalized = normalizedOptions.value.find((opt) => opt.raw === value)
    return normalized?.value ?? value
  }
  return value
}

function valuesEqual(a, b) {
  return String(comparable(a) ?? '') === String(comparable(b) ?? '')
}

const selectedOptions = computed(() => {
  if (props.multiple) {
    const selected = Array.isArray(props.modelValue) ? props.modelValue : []
    return normalizedOptions.value.filter((opt) =>
      selected.some((value) => valuesEqual(value, opt.value)),
    )
  }
  const found = normalizedOptions.value.find(
    (opt) => valuesEqual(props.modelValue, opt.value) || (!props.emitValue && opt.raw === props.modelValue),
  )
  return found ? [found] : []
})

const displayValue = computed(() => {
  if (!selectedOptions.value.length) return ''
  if (!props.multiple) return selectedOptions.value[0].label
  if (selectedOptions.value.length <= props.displayLimit)
    return selectedOptions.value.map((opt) => opt.label).join(', ')
  return `${selectedOptions.value.slice(0, props.displayLimit).map((opt) => opt.label).join(', ')} +${selectedOptions.value.length - props.displayLimit}`
})

const hasValue = computed(() =>
  props.multiple
    ? Array.isArray(props.modelValue) && props.modelValue.length > 0
    : props.modelValue !== null && props.modelValue !== undefined && String(props.modelValue) !== '',
)

function normalizeSearchText(value) {
  return String(value ?? '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLocaleLowerCase('tr-TR')
    .trim()
}

const filteredOptions = computed(() => {
  const needle = normalizeSearchText(query.value)
  if (props.filterFn) return normalizedOptions.value.filter((opt) => props.filterFn(opt.raw, needle))
  if (!needle) return normalizedOptions.value
  return normalizedOptions.value.filter((opt) =>
    [opt.label, opt.value, opt.caption, opt.badge].some((value) => normalizeSearchText(value).includes(needle)),
  )
})

const candidateArray = computed(() =>
  props.multiple && Array.isArray(candidateValue.value) ? candidateValue.value : [],
)
const candidateOptions = computed(() =>
  normalizedOptions.value.filter((opt) =>
    candidateArray.value.some((value) => valuesEqual(value, opt.value)),
  ),
)
const dialogPosition = computed(() => ($q.screen.lt.md ? 'bottom' : undefined))

function optionKey(opt) {
  return `${String(opt.value)}-${opt.label}`
}
function isCandidate(value) {
  if (props.multiple) return candidateArray.value.some((candidate) => valuesEqual(candidate, value))
  return valuesEqual(candidateValue.value, value)
}
function selectionIcon(value) {
  if (props.multiple) return isCandidate(value) ? 'check_box' : 'check_box_outline_blank'
  return isCandidate(value) ? 'radio_button_checked' : 'radio_button_unchecked'
}
function openDialog() {
  if (props.disabled) return
  candidateValue.value = normalizeModelValue(props.modelValue)
  query.value = ''
  dialogOpen.value = true
  emit('open')
  nextTick(() => {
    if (props.searchable) searchInput.value?.focus?.()
  })
}
function selectCandidate(opt) {
  if (opt.disable) return
  if (props.multiple) {
    const current = [...candidateArray.value]
    const index = current.findIndex((value) => valuesEqual(value, opt.value))
    if (index >= 0) current.splice(index, 1)
    else current.push(opt.value)
    candidateValue.value = current
    return
  }
  candidateValue.value = opt.value
  if (props.immediateSingle) applySelection()
}
function emitValueFor(candidate) {
  if (props.emitValue) return candidate
  if (props.multiple) {
    const values = Array.isArray(candidate) ? candidate : []
    return normalizedOptions.value
      .filter((opt) => values.some((value) => valuesEqual(value, opt.value)))
      .map((opt) => opt.raw)
  }
  return normalizedOptions.value.find((opt) => valuesEqual(opt.value, candidate))?.raw ?? null
}
function applySelection() {
  const value = emitValueFor(normalizeModelValue(candidateValue.value))
  emit('update:modelValue', value)
  emit('change', value)
  dialogOpen.value = false
}
function clearCandidate() {
  candidateValue.value = props.multiple ? [] : null
}
function clearSelection() {
  if (props.disabled) return
  const value = props.multiple ? [] : null
  candidateValue.value = value
  emit('update:modelValue', value)
  emit('change', value)
  dialogOpen.value = false
}
function onDialogHide() {
  query.value = ''
  emit('close')
  nextTick(() => document.activeElement?.blur?.())
}

watch(
  () => props.modelValue,
  (value) => {
    if (!dialogOpen.value) candidateValue.value = normalizeModelValue(value)
  },
  { deep: true },
)

defineExpose({ openDialog, applySelection, clearSelection })
</script>

<style scoped>
.app-popup-select :deep(.q-field--outlined .q-field__control::before) {
  border-color: rgba(15, 118, 110, 0.46);
  border-width: 1.5px;
}
.app-popup-select :deep(.q-field--outlined.q-field--focused .q-field__control::after) {
  border-color: var(--q-primary);
  border-width: 2px;
}
.popup-select-card {
  width: min(760px, calc(100vw - 96px));
  max-width: 760px;
  max-height: min(78vh, 720px);
  border-radius: 20px;
  overflow: hidden;
}
.popup-select-card__header {
  padding-bottom: 12px;
}
.popup-select-card__scroll {
  height: min(46vh, 420px);
}
.popup-select-option {
  min-height: 54px;
}
.popup-select-option--active {
  background: rgba(15, 118, 110, 0.08);
}
.popup-select-card__selection-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.popup-select-card__actions {
  min-height: 68px;
}

@media (max-width: 767px) {
  .popup-select-card {
    width: 100vw;
    max-width: 100vw;
    max-height: 86vh;
    border-radius: 22px 22px 0 0;
  }
  .popup-select-card__scroll {
    height: min(50vh, 430px);
  }
}

@media (max-width: 599px) {
  .popup-select-card__actions {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    gap: 8px;
    padding: 12px !important;
  }
  .popup-select-card__action-spacer {
    display: none;
  }
  .popup-select-card__action {
    width: 100%;
    min-width: 0;
    margin: 0 !important;
  }
  .popup-select-card__action--clear {
    grid-column: 1 / -1;
  }
  .popup-select-card__action :deep(.q-btn__content) {
    flex-wrap: nowrap;
    white-space: nowrap;
    font-size: 0.78rem;
  }
}
</style>
