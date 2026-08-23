<template>
  <div class="row items-start q-col-gutter-sm">
    <div class="col">
      <AppPopupSelect
        :model-value="modelValue"
        :options="options"
        :label="label"
        :dialog-title="dialogTitle"
        dialog-caption="Bu portföy hesabına bağlı Banka / Borsa / Aracı Kurum listesinden seçim yap."
        :searchable="true"
        :clearable="clearable"
        :disable="disabled"
        @update:model-value="emit('update:modelValue', $event)"
      />
    </div>
    <div class="col-auto">
      <q-btn
        round
        flat
        icon="add_business"
        color="primary"
        :disable="disabled"
        @click="dialogOpen = true"
      >
        <q-tooltip>Yeni kurum ekle</q-tooltip>
      </q-btn>
    </div>
  </div>

  <q-dialog v-model="dialogOpen">
    <q-card style="width: min(94vw, 620px)">
      <q-card-section>
        <div class="text-h6">Banka / Borsa / Aracı Kurum Ekle</div>
        <div class="text-caption text-grey-7">
          Kurum kullanıcı sözlüğüne eklenir ve aktif portföy hesabına bağlanır.
        </div>
      </q-card-section>
      <q-separator />
      <q-card-section class="row q-col-gutter-md">
        <div class="col-12">
          <q-input v-model.trim="draft.name" outlined label="Kurum Adı" autofocus />
        </div>
        <div class="col-12 col-sm-6">
          <AppPopupSelect
            v-model="draft.institutionType"
            :options="INSTITUTION_TYPES"
            label="Kurum Türü"
            :searchable="false"
          />
        </div>
        <div class="col-12 col-sm-6">
          <q-input
            v-model.trim="draft.countryCode"
            outlined
            maxlength="2"
            label="Ülke Kodu"
            hint="Örn. TR, US"
          />
        </div>
        <div class="col-12">
          <q-input v-model.trim="draft.website" outlined label="Web Sitesi (opsiyonel)" />
        </div>
        <div class="col-12">
          <q-input v-model.trim="draft.note" outlined type="textarea" autogrow label="Not" />
        </div>
      </q-card-section>
      <q-card-actions align="right" class="popup-action-footer q-pa-md">
        <q-btn push color="grey-3" text-color="grey-9" label="Vazgeç" v-close-popup no-caps />
        <q-btn
          push
          color="primary"
          icon="save"
          label="Kaydet ve Seç"
          :loading="saving"
          no-caps
          @click="save"
        />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useQuasar } from 'quasar'
import AppPopupSelect from '@/components/AppPopupSelect.vue'
import { INSTITUTION_TYPES, useInstitutionsStore } from '@/stores/institutions'
import { usePortfolioStore } from '@/stores/portfolio'

defineProps({
  modelValue: { type: String, default: '' },
  label: { type: String, default: 'Banka / Borsa / Aracı Kurum' },
  dialogTitle: { type: String, default: 'Kurum Seç' },
  clearable: { type: Boolean, default: true },
  disabled: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue'])
const $q = useQuasar()
const institutions = useInstitutionsStore()
const portfolio = usePortfolioStore()
const dialogOpen = ref(false)
const saving = ref(false)
const draft = reactive({
  name: '',
  institutionType: 'BANK',
  countryCode: 'TR',
  website: '',
  note: '',
})
const options = computed(() => institutions.optionsForAccount(portfolio.selectedAccountId))

onMounted(async () => {
  try {
    if (!institutions.institutions.length) await institutions.sync()
  } catch {
    // Parent form will surface Supabase errors on save; selector can stay empty.
  }
})

async function save() {
  saving.value = true
  try {
    const row = await institutions.createInstitution({
      name: draft.name,
      institutionType: draft.institutionType,
      countryCode: draft.countryCode,
      website: draft.website,
      note: draft.note,
      accountId: portfolio.selectedAccountId,
    })
    emit('update:modelValue', row.name)
    dialogOpen.value = false
    Object.assign(draft, {
      name: '',
      institutionType: 'BANK',
      countryCode: 'TR',
      website: '',
      note: '',
    })
    $q.notify({ type: 'positive', message: 'Kurum sözlüğe eklendi ve seçildi.' })
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error instanceof Error ? error.message : 'Kurum eklenemedi.',
    })
  } finally {
    saving.value = false
  }
}
</script>
