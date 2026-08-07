<template>
  <div class="transaction-context" :class="{ 'transaction-context--compact': compact }">
    <div class="transaction-context__header">
      <div>
        <div class="transaction-context__eyebrow">Aktif Hesap</div>
        <div class="transaction-context__account">
          <q-icon name="account_balance_wallet" size="18px" />
          <span>{{ portfolio.selectedAccount?.name || 'Yatırım Hesabı' }}</span>
        </div>
      </div>

      <AppPopupSelect
        v-if="accountSelectable && accountOptions.length > 1"
        v-model="selectedAccountModel"
        :options="accountOptions"
        label="Hesap"
        dense
        :searchable="accountOptions.length > 6"
        class="transaction-context__account-select"
      />
      <q-badge v-else outline color="primary"
        >{{ portfolio.selectedAccount?.base_currency || 'USD' }} BASE</q-badge
      >
    </div>

    <div class="transaction-context__flow">
      <div class="transaction-context__asset">
        <div class="transaction-context__asset-head">
          <AssetAvatar v-if="sourceAsset" :asset="sourceAsset" size="38px" />
          <q-avatar v-else size="38px" color="grey-2" text-color="grey-7" icon="public" />
          <div>
            <div class="transaction-context__asset-label">Kaynak</div>
            <div class="transaction-context__asset-name">
              {{ sourceAsset || sourceExternalLabel }}
            </div>
          </div>
        </div>

        <div v-if="sourceAsset" class="transaction-context__numbers">
          <div>
            <span>Önce</span>
            <strong>{{ formatQuantity(sourceBefore, sourceAsset) }}</strong>
          </div>
          <div>
            <span>İşlem</span>
            <strong :class="sourceDelta < 0 ? 'amount-negative' : 'amount-positive'">
              {{ signedQuantity(sourceDelta, sourceAsset) }}
            </strong>
          </div>
          <div>
            <span>Sonra</span>
            <strong :class="sourceAfter < -epsilon ? 'amount-negative' : 'amount-strong'">
              {{ formatQuantity(sourceAfter, sourceAsset) }}
            </strong>
          </div>
        </div>
        <div v-else class="transaction-context__external-note">Portföy dışından gelen kaynak</div>
      </div>

      <div class="transaction-context__arrow">
        <q-icon name="arrow_forward" size="24px" />
      </div>

      <div class="transaction-context__asset">
        <div class="transaction-context__asset-head">
          <AssetAvatar v-if="targetAsset" :asset="targetAsset" size="38px" />
          <q-avatar v-else size="38px" color="grey-2" text-color="grey-7" icon="outbound" />
          <div>
            <div class="transaction-context__asset-label">Hedef</div>
            <div class="transaction-context__asset-name">
              {{ targetAsset || targetExternalLabel }}
            </div>
          </div>
        </div>

        <div v-if="targetAsset" class="transaction-context__numbers">
          <div>
            <span>Önce</span>
            <strong>{{ formatQuantity(targetBefore, targetAsset) }}</strong>
          </div>
          <div>
            <span>İşlem</span>
            <strong :class="targetDelta < 0 ? 'amount-negative' : 'amount-positive'">
              {{ signedQuantity(targetDelta, targetAsset) }}
            </strong>
          </div>
          <div>
            <span>Sonra</span>
            <strong :class="targetAfter < -epsilon ? 'amount-negative' : 'amount-strong'">
              {{ formatQuantity(targetAfter, targetAsset) }}
            </strong>
          </div>
        </div>
        <div v-else class="transaction-context__external-note">Portföy dışına çıkan kaynak</div>
      </div>
    </div>

    <div v-if="hasNegativeBalance" class="transaction-context__warning">
      <q-icon name="warning" />
      <span>İşlem sonrası bakiye negatife düşüyor. Miktarları kontrol et.</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import AppPopupSelect from '@/components/AppPopupSelect.vue'
import AssetAvatar from '@/components/AssetAvatar.vue'
import { useFormatters } from '@/composables/useFormatters'
import { usePortfolioStore } from '@/stores/portfolio'

const props = defineProps({
  sourceAsset: { type: String, default: null },
  sourceDelta: { type: Number, default: 0 },
  targetAsset: { type: String, default: null },
  targetDelta: { type: Number, default: 0 },
  sourceExternalLabel: { type: String, default: 'Dış Kaynak' },
  targetExternalLabel: { type: String, default: 'Portföy Dışı' },
  compact: { type: Boolean, default: false },
  accountSelectable: { type: Boolean, default: true },
  baseQuantities: { type: Object, default: null },
})

const portfolio = usePortfolioStore()
const { formatNumber } = useFormatters()
const epsilon = 1e-10

const accountOptions = computed(() =>
  portfolio.activeAccounts.map((account) => ({
    label: account.name,
    value: account.id,
    caption: account.base_currency ? `${account.base_currency} baz` : '',
  })),
)
const selectedAccountModel = computed({
  get: () => portfolio.selectedAccountId,
  set: (value) => {
    portfolio.selectAccount(value)
  },
})

function beforeQuantity(asset) {
  if (!asset) return 0
  if (props.baseQuantities && Object.prototype.hasOwnProperty.call(props.baseQuantities, asset)) {
    return Number(props.baseQuantities[asset] || 0)
  }
  return Number(portfolio.quantities[asset] || 0)
}

const sourceBefore = computed(() => beforeQuantity(props.sourceAsset))
const targetBefore = computed(() => beforeQuantity(props.targetAsset))
const sourceAfter = computed(() => sourceBefore.value + Number(props.sourceDelta || 0))
const targetAfter = computed(() => targetBefore.value + Number(props.targetDelta || 0))
const hasNegativeBalance = computed(
  () =>
    (props.sourceAsset && sourceAfter.value < -epsilon) ||
    (props.targetAsset && targetAfter.value < -epsilon),
)

function digitsFor(asset) {
  if (asset === 'BTC') return 8
  if (asset === 'ETH') return 6
  if (asset === 'URA') return 4
  return 2
}

function formatQuantity(value, asset) {
  return `${formatNumber(value, digitsFor(asset))} ${asset}`
}

function signedQuantity(value, asset) {
  const numeric = Number(value || 0)
  const prefix = numeric > 0 ? '+' : ''
  return `${prefix}${formatNumber(numeric, digitsFor(asset))} ${asset}`
}
</script>
