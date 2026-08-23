<template>
  <q-layout view="hHh Lpr fFf" class="app-shell">
    <q-header class="app-header" height-hint="64">
      <q-toolbar class="q-px-sm q-px-sm-md app-toolbar" style="min-height: 64px">
        <q-btn
          v-if="$q.screen.lt.md"
          flat
          round
          dense
          icon="menu"
          aria-label="Menü"
          class="q-mr-xs"
          @click="drawerOpen = !drawerOpen"
        />
        <AppLogo :compact="$q.screen.lt.sm" />
        <q-space />
        <q-chip
          v-if="auth.isDemo"
          dense
          outline
          color="warning"
          icon="science"
          :label="$q.screen.lt.sm ? undefined : 'Demo'"
          class="q-mr-xs"
        >
          <q-tooltip v-if="$q.screen.lt.sm">Demo Modu</q-tooltip>
        </q-chip>
        <q-btn-dropdown
          flat
          :dense="!$q.screen.lt.sm"
          no-caps
          :icon="$q.screen.lt.sm ? undefined : 'currency_exchange'"
          :label="ui.displayAsset"
          class="display-currency-btn"
          menu-anchor="bottom right"
          menu-self="top right"
          :menu-offset="[0, 8]"
        >
          <q-list
            separator
            bordered
            class="display-currency-menu-list bg-white"
            :style="
              $q.screen.lt.sm ? { minWidth: '230px', maxWidth: '82vw' } : { minWidth: '190px' }
            "
          >
            <q-item-label header class="text-weight-bold text-grey-8 q-py-sm">
              <div class="row items-center no-wrap q-gutter-sm">
                <q-icon name="currency_exchange" color="primary" size="20px" />
                <span>Görüntüleme Birimi</span>
              </div>
            </q-item-label>
            <q-separator />
            <q-item
              v-for="asset in displayAssets"
              :key="asset"
              clickable
              v-ripple
              v-close-popup
              :active="ui.displayAsset === asset"
              active-class="bg-teal-1 text-primary"
              class="q-py-sm"
              @click="ui.setDisplayAsset(asset)"
            >
              <q-item-section avatar>
                <q-avatar
                  size="34px"
                  :color="ui.displayAsset === asset ? 'teal-1' : 'grey-2'"
                  :text-color="ui.displayAsset === asset ? 'primary' : 'grey-8'"
                  class="text-caption text-weight-bold"
                >
                  {{ asset }}
                </q-avatar>
              </q-item-section>
              <q-item-section>
                <q-item-label class="text-weight-bold">{{ asset }}</q-item-label>
                <q-item-label caption>{{ displayAssetDescription(asset) }}</q-item-label>
              </q-item-section>
              <q-item-section side>
                <q-icon
                  :name="ui.displayAsset === asset ? 'check_circle' : 'chevron_right'"
                  :color="ui.displayAsset === asset ? 'primary' : 'grey-5'"
                />
              </q-item-section>
            </q-item>
          </q-list>
          <q-tooltip>Dashboard ve raporların görüntüleme birimi</q-tooltip>
        </q-btn-dropdown>
        <q-btn
          v-if="!$q.screen.lt.sm"
          flat
          round
          icon="refresh"
          :loading="syncing"
          @click="syncAll"
        >
          <q-tooltip>Verileri Yenile</q-tooltip>
        </q-btn>
        <q-btn
          v-if="!auth.isDemo"
          flat
          round
          dense
          icon="notifications"
          class="q-ml-xs"
          @click="notificationDrawerOpen = true"
        >
          <q-badge v-if="notifications.unreadCount" floating color="negative" rounded>
            {{ notifications.unreadCount > 99 ? '99+' : notifications.unreadCount }}
          </q-badge>
          <q-tooltip>Bildirimler</q-tooltip>
        </q-btn>
        <q-btn flat round dense icon="account_circle" class="q-ml-xs">
          <q-menu anchor="bottom right" self="top right">
            <q-list style="min-width: 230px">
              <q-item>
                <q-item-section>
                  <q-item-label>{{ displayName }}</q-item-label>
                  <q-item-label caption>{{ auth.user?.email }}</q-item-label>
                </q-item-section>
              </q-item>
              <q-separator />
              <q-item class="q-py-md">
                <q-item-section>
                  <AppPopupSelect
                    v-if="accountOptions.length"
                    v-model="selectedAccountModel"
                    :options="accountOptions"
                    label="Aktif Portföy Hesabı"
                    dialog-title="Çalışma Portföyünü Seç"
                    dialog-caption="Dashboard, işlemler ve raporlar seçtiğin hesaba göre yenilenir."
                    :searchable="accountOptions.length > 6"
                    :clearable="false"
                    dense
                  >
                    <template #prepend><q-icon name="account_balance_wallet" /></template>
                  </AppPopupSelect>
                  <q-btn
                    v-else
                    flat
                    color="primary"
                    icon="add"
                    label="İlk portföy hesabını oluştur"
                    no-caps
                    to="/accounts"
                    v-close-popup
                  />
                </q-item-section>
              </q-item>
              <q-separator />
              <q-item v-if="$q.screen.lt.sm" clickable v-close-popup @click="syncAll">
                <q-item-section avatar><q-icon name="refresh" /></q-item-section>
                <q-item-section>Verileri Yenile</q-item-section>
              </q-item>
              <q-item clickable v-close-popup to="/profile">
                <q-item-section avatar><q-icon name="manage_accounts" /></q-item-section>
                <q-item-section>Profilim</q-item-section>
              </q-item>
              <q-item clickable v-close-popup to="/accounts">
                <q-item-section avatar><q-icon name="wallet" /></q-item-section>
                <q-item-section>Portföy Hesaplarım</q-item-section>
              </q-item>
              <q-item clickable v-close-popup to="/institutions">
                <q-item-section avatar><q-icon name="account_balance" /></q-item-section>
                <q-item-section>Banka / Borsa / Aracı Kurumlar</q-item-section>
              </q-item>
              <q-item v-if="!auth.isDemo" clickable v-close-popup to="/notifications">
                <q-item-section avatar><q-icon name="notifications_active" /></q-item-section>
                <q-item-section>Bildirim Yönetimi</q-item-section>
              </q-item>
              <q-item clickable v-close-popup to="/settings">
                <q-item-section avatar><q-icon name="settings" /></q-item-section>
                <q-item-section>Ayarlar</q-item-section>
              </q-item>
              <q-item clickable v-close-popup @click="logout">
                <q-item-section avatar><q-icon name="logout" /></q-item-section>
                <q-item-section>Çıkış Yap</q-item-section>
              </q-item>
            </q-list>
          </q-menu>
        </q-btn>
      </q-toolbar>
    </q-header>
    <q-drawer
      v-model="drawerOpen"
      :show-if-above="true"
      :mini="!$q.screen.lt.md && drawerMini"
      :width="260"
      :mini-width="76"
      bordered
      class="app-drawer"
    >
      <div class="q-pa-md row items-center">
        <AppLogo :compact="drawerMini && !$q.screen.lt.md" />
      </div>
      <q-list padding>
        <q-item
          v-for="item in navItems"
          :key="item.to"
          clickable
          :to="item.to"
          :active="isActive(item.to)"
          active-class="q-item--active"
        >
          <q-item-section avatar><q-icon :name="item.icon" /></q-item-section>
          <q-item-section>{{ item.label }}</q-item-section>
        </q-item>
      </q-list>
      <div v-if="!$q.screen.lt.md" class="absolute-bottom q-pa-sm">
        <q-btn
          flat
          class="full-width"
          :icon="drawerMini ? 'keyboard_double_arrow_right' : 'keyboard_double_arrow_left'"
          :label="drawerMini ? '' : 'Menüyü Daralt'"
          @click="drawerMini = !drawerMini"
        />
      </div>
    </q-drawer>
    <NotificationCenter v-if="!auth.isDemo" v-model="notificationDrawerOpen" />
    <q-page-container>
      <router-view />
    </q-page-container>
    <q-footer v-if="$q.screen.lt.md" class="app-bottom-nav text-grey-7">
      <q-tabs
        dense
        no-caps
        indicator-color="transparent"
        active-color="primary"
        class="text-caption"
      >
        <q-route-tab to="/" icon="space_dashboard" label="Özet" />
        <q-route-tab to="/portfolio" icon="account_balance_wallet" label="Portföy" />
        <q-route-tab to="/transactions" icon="swap_vert" label="İşlemler" />
        <q-route-tab to="/signals" icon="insights" label="Sinyal" />
        <q-route-tab to="/reports" icon="query_stats" label="Rapor" />
      </q-tabs>
    </q-footer>
    <q-page-sticky v-if="$q.screen.lt.md" position="bottom-right" :offset="[18, 82]">
      <q-fab color="primary" icon="add" direction="up">
        <q-fab-action color="primary" icon="inventory_2" label="Başlangıç" to="/opening" />
        <q-fab-action color="positive" icon="add_shopping_cart" label="Alım" to="/buy" />
        <q-fab-action color="info" icon="sync_alt" label="Dönüşüm" to="/conversion" />
        <q-fab-action color="warning" icon="payments" label="Sermaye" to="/cash" />
        <q-fab-action color="negative" icon="sell" label="Satış" to="/sell" />
      </q-fab>
    </q-page-sticky>
  </q-layout>
</template>
<script setup>
import { computed, ref } from 'vue'
import { useQuasar } from 'quasar'
import { useRoute, useRouter } from 'vue-router'
import AppLogo from '@/components/AppLogo.vue'
import AppPopupSelect from '@/components/AppPopupSelect.vue'
import NotificationCenter from '@/components/NotificationCenter.vue'
import { refreshDisplayQuotesNow } from '@/services/display-quotes/displayQuoteScheduler'
import { useAuthStore } from '@/stores/auth'
import { useEngineStore } from '@/stores/engine'
import { useInstitutionsStore } from '@/stores/institutions'
import { useNotificationsStore } from '@/stores/notifications'
import { usePortfolioStore } from '@/stores/portfolio'
import { DISPLAY_ASSETS, useUiStore } from '@/stores/ui'
const $q = useQuasar()
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const portfolio = usePortfolioStore()
const engine = useEngineStore()
const institutions = useInstitutionsStore()
const notifications = useNotificationsStore()
const ui = useUiStore()
const drawerOpen = ref(true)
const drawerMini = ref(false)
const notificationDrawerOpen = ref(false)
const syncing = ref(false)
const displayAssets = DISPLAY_ASSETS
const navItems = computed(() => [
  { label: 'Dashboard', icon: 'space_dashboard', to: '/' },
  { label: 'Portföy', icon: 'account_balance_wallet', to: '/portfolio' },
  { label: 'Portföy Hesaplarım', icon: 'wallet', to: '/accounts' },
  { label: 'Kurumlar', icon: 'account_balance', to: '/institutions' },
  { label: 'İşlemler', icon: 'swap_vert', to: '/transactions' },
  { label: 'Sinyaller', icon: 'insights', to: '/signals' },
  { label: 'Raporlar', icon: 'query_stats', to: '/reports' },
  ...(!auth.isDemo
    ? [{ label: 'Bildirimler', icon: 'notifications_active', to: '/notifications' }]
    : []),
  { label: 'Profilim', icon: 'manage_accounts', to: '/profile' },
  { label: 'Ayarlar', icon: 'settings', to: '/settings' },
])
const displayName = computed(() => {
  const name = [auth.user?.firstName, auth.user?.lastName].filter(Boolean).join(' ')
  return name || auth.user?.email || 'Yatırımcı'
})
const accountOptions = computed(() =>
  portfolio.activeAccounts.map((account) => ({
    label: account.name,
    value: account.id,
    caption: `${account.base_currency || 'USD'} baz para birimi`,
    badge: account.is_default ? 'Varsayılan' : '',
    icon: 'account_balance_wallet',
  })),
)
const selectedAccountModel = computed({
  get: () => portfolio.selectedAccountId,
  set: (value) => portfolio.selectAccount(value),
})
function displayAssetDescription(asset) {
  const labels = {
    USD: 'ABD Doları',
    TRY: 'Türk Lirası',
    EUR: 'Euro',
    BTC: 'Bitcoin',
    ETH: 'Ethereum',
  }
  return labels[asset] || asset
}
function isActive(path) {
  if (path === '/') return route.path === '/'
  return route.path.startsWith(path)
}
async function syncAll() {
  syncing.value = true
  try {
    await Promise.all([portfolio.sync(), engine.sync()])
    await Promise.all([
      refreshDisplayQuotesNow(),
      institutions.sync().catch(() => null),
      notifications.sync().catch(() => null),
    ])
    $q.notify({ type: 'positive', message: 'Veriler güncellendi.' })
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error instanceof Error ? error.message : 'Güncelleme başarısız.',
    })
  } finally {
    syncing.value = false
  }
}
async function logout() {
  await auth.signOut()
  portfolio.reset()
  institutions.reset()
  notifications.reset()
  await router.replace('/login')
}
</script>
