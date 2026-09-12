<template>
  <q-dialog
    :model-value="modelValue"
    persistent
    @update:model-value="emit('update:modelValue', $event)"
  >
    <q-card class="transaction-cancel-card">
      <q-card-section class="row items-start no-wrap">
        <div class="col min-width-0">
          <div class="text-h6 text-weight-bold">İşlemi İptal Et</div>
          <div class="text-caption text-grey-7 q-mt-xs">
            Kayıt silinmez. İşlemi geçersiz kılan yeni bir append-only iptal revizyonu oluşturulur.
          </div>
        </div>
        <q-btn flat round dense icon="close" aria-label="Kapat" :disable="saving" @click="close" />
      </q-card-section>

      <q-separator />

      <q-card-section>
        <q-banner rounded class="bg-red-1 text-red-10 q-mb-md">
          <template #avatar><q-icon name="warning" /></template>
          Sonraki işlemler bu kaydın oluşturduğu bakiyeyi kullanıyorsa iptal engellenir. Önce bağlı
          işlemleri revize etmen gerekir.
        </q-banner>

        <q-list v-if="transaction" bordered separator class="rounded-borders q-mb-md">
          <q-item>
            <q-item-section>İşlem</q-item-section>
            <q-item-section side>{{
              transactionTypeLabel(transaction.transaction_type)
            }}</q-item-section>
          </q-item>
          <q-item>
            <q-item-section>Tarih</q-item-section>
            <q-item-section side>{{ formatDate(transaction.transaction_at) }}</q-item-section>
          </q-item>
          <q-item>
            <q-item-section>Revizyon</q-item-section>
            <q-item-section side>{{
              portfolio.transactionRevisionNumber(transaction)
            }}</q-item-section>
          </q-item>
        </q-list>

        <q-input
          v-model.trim="reason"
          outlined
          type="textarea"
          autogrow
          label="İptal Nedeni"
          hint="Audit geçmişinde saklanır."
          :error="reasonError"
          error-message="İptal nedeni gerekli."
          @update:model-value="reasonError = false"
        />
      </q-card-section>

      <q-separator />
      <q-card-actions align="right" class="popup-action-footer q-pa-md">
        <q-btn
          push
          color="grey-3"
          text-color="grey-9"
          icon="close"
          label="Vazgeç"
          no-caps
          :disable="saving"
          @click="close"
        />
        <q-btn
          push
          color="negative"
          icon="block"
          label="İptali Kaydet"
          no-caps
          :loading="saving"
          @click="confirmCancellation"
        />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useQuasar } from 'quasar'
import { useFormatters } from '@/composables/useFormatters'
import { createTransactionRequestId } from '@/services/portfolioTransactions'
import { transactionTypeLabel } from '@/services/presentation'
import { usePortfolioStore } from '@/stores/portfolio'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  transaction: { type: Object, default: null },
})
const emit = defineEmits(['update:modelValue', 'cancelled'])
const $q = useQuasar()
const portfolio = usePortfolioStore()
const { formatDate } = useFormatters()
const reason = ref('')
const reasonError = ref(false)
const saving = ref(false)
const cancellationRequestId = ref(createTransactionRequestId())

watch(
  () => [props.modelValue, props.transaction?.id],
  ([open]) => {
    if (open) {
      cancellationRequestId.value = createTransactionRequestId()
      reason.value = ''
      reasonError.value = false
    }
  },
)

function close() {
  if (!saving.value) emit('update:modelValue', false)
}

async function confirmCancellation() {
  if (!reason.value) {
    reasonError.value = true
    return
  }
  if (!props.transaction) return

  saving.value = true
  try {
    const cancellation = await portfolio.cancelTransaction(
      props.transaction.id,
      reason.value,
      cancellationRequestId.value,
    )
    $q.notify({
      type: 'positive',
      message: 'İptal revizyonu kaydedildi; asıl işlem audit geçmişinde korundu.',
    })
    emit('cancelled', cancellation)
    emit('update:modelValue', false)
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error instanceof Error ? error.message : 'İşlem iptal edilemedi.',
    })
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.transaction-cancel-card {
  width: min(94vw, 620px);
  border-radius: 22px;
}
</style>
