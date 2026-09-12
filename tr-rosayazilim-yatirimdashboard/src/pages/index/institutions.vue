<template>
  <q-page>
    <div class="page-wrap">
      <div class="row items-center q-mb-lg">
        <div>
          <div class="page-title">Banka / Borsa / Aracı Kurumlar</div>
          <div class="page-subtitle q-mt-xs">
            İşlem formlarında kullanılan kurum sözlüğü ve portföy hesabı eşleştirmeleri.
          </div>
        </div>
        <q-space />
        <q-btn
          push
          color="primary"
          icon="add_business"
          label="Kurum Ekle"
          no-caps
          @click="dialogOpen = true"
        />
      </div>

      <q-banner rounded class="surface-soft q-mb-lg">
        Kurum adları işlem kayıtlarına standart biçimde bağlanır. Eski işlemlerdeki
        <strong>platform</strong>
        metni audit snapshot olarak korunur; yeni raporlar kurum kimliği üzerinden gruplanabilir.
      </q-banner>

      <q-card flat class="section-card">
        <q-list separator>
          <q-item v-for="item in institutions.institutions" :key="item.id" class="q-py-md">
            <q-item-section avatar>
              <q-avatar
                color="grey-2"
                text-color="primary"
                :icon="item.institution_type === 'BANK' ? 'account_balance' : 'currency_exchange'"
              />
            </q-item-section>
            <q-item-section>
              <q-item-label class="text-weight-bold">{{ item.name }}</q-item-label>
              <q-item-label caption>
                {{ institutions.typeLabel(item.institution_type) }}
                <span v-if="item.country_code"> · {{ item.country_code }}</span>
              </q-item-label>
            </q-item-section>
            <q-item-section side>
              <q-toggle
                :model-value="isMapped(item.id)"
                color="primary"
                label="Aktif hesapta kullan"
                left-label
                @update:model-value="setMapped(item.id, $event)"
              />
            </q-item-section>
          </q-item>
          <q-item v-if="!institutions.institutions.length && !institutions.loading">
            <q-item-section class="text-grey-7">Henüz kurum tanımlanmamış.</q-item-section>
          </q-item>
        </q-list>
      </q-card>
    </div>

    <q-dialog v-model="dialogOpen">
      <q-card style="width: min(94vw, 620px)">
        <q-card-section>
          <div class="text-h6">Yeni Kurum</div>
          <div class="text-caption text-grey-7">
            Kurum sözlüğe ve seçili portföy hesabına birlikte eklenir.
          </div>
        </q-card-section>
        <q-separator />
        <q-card-section class="row q-col-gutter-md">
          <div class="col-12"><q-input v-model.trim="draft.name" outlined label="Kurum Adı" /></div>
          <div class="col-12 col-sm-6">
            <AppPopupSelect
              v-model="draft.institutionType"
              :options="INSTITUTION_TYPES"
              label="Kurum Türü"
              :searchable="false"
            />
          </div>
          <div class="col-12 col-sm-6">
            <q-input v-model.trim="draft.countryCode" outlined maxlength="2" label="Ülke Kodu" />
          </div>
          <div class="col-12">
            <q-input v-model.trim="draft.website" outlined label="Web Sitesi" />
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
            label="Kaydet"
            :loading="saving"
            no-caps
            @click="save"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useQuasar } from 'quasar'
import AppPopupSelect from '@/components/AppPopupSelect.vue'
import { INSTITUTION_TYPES, useInstitutionsStore } from '@/stores/institutions'
import { usePortfolioStore } from '@/stores/portfolio'

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

onMounted(async () => {
  try {
    await institutions.sync()
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error instanceof Error ? error.message : 'Kurumlar alınamadı.',
    })
  }
})

function isMapped(institutionId) {
  return institutions.mappings.some(
    (item) =>
      item.account_id === portfolio.selectedAccountId &&
      item.institution_id === institutionId &&
      item.is_active !== false,
  )
}

async function setMapped(institutionId, active) {
  try {
    await institutions.setAccountMappingActive(portfolio.selectedAccountId, institutionId, active)
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error instanceof Error ? error.message : 'Eşleştirme güncellenemedi.',
    })
  }
}

async function save() {
  saving.value = true
  try {
    await institutions.createInstitution({ ...draft, accountId: portfolio.selectedAccountId })
    dialogOpen.value = false
    Object.assign(draft, {
      name: '',
      institutionType: 'BANK',
      countryCode: 'TR',
      website: '',
      note: '',
    })
    $q.notify({ type: 'positive', message: 'Kurum kaydedildi.' })
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error instanceof Error ? error.message : 'Kurum kaydedilemedi.',
    })
  } finally {
    saving.value = false
  }
}
</script>
