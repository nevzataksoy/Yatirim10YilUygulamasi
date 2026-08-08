<template>
<q-page>
<div class="page-wrap">
<div class="row items-center q-mb-lg">
<div>
<div class="page-title">Bildirim Yönetimi</div>
<div class="page-subtitle q-mt-xs">
Firebase Cloud Messaging, bağlı cihazlar, otomatik şablonlar ve gönderim logları.
</div>
</div>
<q-space />
<q-btn flat round icon="refresh" :loading="notifications.loading" @click="refresh" />
</div>
<q-banner rounded class="surface-soft q-mb-lg">
Firebase service-account private key bu ekrana girilmez. Quasar yalnız non-secret proje metadata'sını,
cihaz kayıtlarını ve otomasyon tercihlerini tutar; gerçek FCM gönderimi Python servisinden yapılır.
</q-banner>
<q-tabs v-model="tab" dense active-color="primary" indicator-color="primary" align="left" class="q-mb-md">
<q-tab name="settings" icon="settings" label="Firebase" />
<q-tab name="devices" icon="devices" label="Cihazlar" />
<q-tab name="templates" icon="schedule" label="Otomasyonlar" />
<q-tab name="logs" icon="receipt_long" label="Loglar" />
</q-tabs>
<q-tab-panels v-model="tab" animated class="bg-transparent">
<q-tab-panel name="settings" class="q-pa-none">
<q-card flat class="section-card">
<q-card-section class="row q-col-gutter-md">
<div class="col-12 col-sm-6">
<q-toggle v-model="provider.enabled" color="primary" label="FCM bildirimlerini etkinleştir" />
</div>
<div class="col-12 col-sm-6">
<q-input v-model.trim="provider.firebase_project_id" outlined label="Firebase Project ID" />
</div>
<div class="col-12 col-sm-6">
<q-input v-model.trim="provider.sender_id" outlined label="Sender ID / Project Number" />
</div>
<div class="col-12 col-sm-6">
<q-input v-model.trim="provider.android_package_name" outlined label="Android Package Name" />
</div>
<div class="col-12">
<q-input v-model.trim="provider.web_vapid_key" outlined label="Web VAPID Key (PWA kullanacaksan)" />
</div>
<div class="col-12">
<q-input v-model.trim="provider.note" outlined type="textarea" autogrow label="Not" />
</div>
<div class="col-12 row justify-end q-gutter-sm">
<q-btn push color="primary" icon="save" label="Firebase Ayarlarını Kaydet" no-caps @click="saveProvider" />
<q-btn push color="positive" icon="notifications_active" label="Bu Cihazı Kaydet" :loading="notifications.registering" no-caps @click="registerDevice" />
</div>
</q-card-section>
</q-card>
</q-tab-panel>
<q-tab-panel name="devices" class="q-pa-none">
<q-card flat class="section-card">
<q-list separator>
<q-item v-for="device in notifications.devices" :key="device.id" class="q-py-md">
<q-item-section avatar><q-avatar icon="smartphone" color="grey-2" text-color="primary" /></q-item-section>
<q-item-section>
<q-item-label class="text-weight-bold">{{ device.device_name || 'Mobil Cihaz' }}</q-item-label>
<q-item-label caption>
{{ device.platform }} · {{ device.operating_system || 'OS' }} {{ device.os_version || '' }} · App {{ device.app_version || '—' }}
</q-item-label>
<q-item-label caption>
İzin: {{ device.permission_status }} · Son görülme: {{ formatDate(device.last_seen_at) }}
</q-item-label>
</q-item-section>
<q-item-section side>
<q-toggle :model-value="device.is_active" color="primary" @update:model-value="setDeviceActive(device.id, $event)" />
</q-item-section>
</q-item>
<q-item v-if="!notifications.devices.length"><q-item-section class="text-grey-7">Kayıtlı cihaz yok.</q-item-section></q-item>
</q-list>
</q-card>
</q-tab-panel>
<q-tab-panel name="templates" class="q-pa-none">
<div class="row justify-end q-mb-md">
<q-btn push color="primary" icon="add" label="Otomasyon Şablonu" no-caps @click="newTemplate" />
</div>
<q-card flat class="section-card">
<q-list separator>
<q-item v-for="item in notifications.templates" :key="item.id" class="q-py-md">
<q-item-section avatar><q-avatar icon="schedule" color="grey-2" text-color="primary" /></q-item-section>
<q-item-section>
<q-item-label class="text-weight-bold">{{ item.name }}</q-item-label>
<q-item-label caption>
{{ eventLabel(item.event_type) }}
<span v-if="item.schedule_time"> · {{ String(item.schedule_time).slice(0,5) }} · {{ item.timezone }}</span>
<span> · {{ item.display_currency }}</span>
</q-item-label>
<q-item-label caption lines="2">{{ item.body_template }}</q-item-label>
</q-item-section>
<q-item-section side class="row items-center no-wrap q-gutter-xs">
<q-toggle :model-value="item.enabled" color="primary" @update:model-value="toggleTemplate(item, $event)" />
<q-btn flat round dense icon="edit" @click="editTemplate(item)" />
<q-btn flat round dense icon="delete" color="negative" @click="removeTemplate(item)" />
</q-item-section>
</q-item>
<q-item v-if="!notifications.templates.length"><q-item-section class="text-grey-7">Henüz otomasyon şablonu yok.</q-item-section></q-item>
</q-list>
</q-card>
</q-tab-panel>
<q-tab-panel name="logs" class="q-pa-none">
<q-card flat class="section-card">
<q-list separator>
<q-item v-for="log in notifications.logs" :key="log.id" class="q-py-md">
<q-item-section avatar>
<q-avatar :icon="log.status === 'SENT' ? 'check_circle' : 'error'" :color="log.status === 'SENT' ? 'green-1' : 'red-1'" :text-color="log.status === 'SENT' ? 'positive' : 'negative'" />
</q-item-section>
<q-item-section>
<q-item-label class="text-weight-bold">{{ log.status }} · {{ log.provider }}</q-item-label>
<q-item-label caption>{{ formatDate(log.created_at) }}</q-item-label>
<q-item-label v-if="log.error_message" caption class="text-negative">{{ log.error_message }}</q-item-label>
<q-item-label v-if="log.provider_message_id" caption>Provider ID: {{ log.provider_message_id }}</q-item-label>
</q-item-section>
</q-item>
<q-item v-if="!notifications.logs.length"><q-item-section class="text-grey-7">Henüz gönderim logu yok.</q-item-section></q-item>
</q-list>
</q-card>
</q-tab-panel>
</q-tab-panels>
</div>
<q-dialog v-model="templateDialog">
<q-card style="width: min(96vw, 760px)">
<q-card-section>
<div class="text-h6">Bildirim Otomasyonu</div>
<div class="text-caption text-grey-7">Şablon ve tetikleme koşulunu birlikte tanımla.</div>
</q-card-section>
<q-separator />
<q-card-section class="row q-col-gutter-md">
<div class="col-12 col-sm-6"><q-input v-model.trim="draft.name" outlined label="Şablon Adı" /></div>
<div class="col-12 col-sm-6">
<AppPopupSelect v-model="draft.event_type" :options="NOTIFICATION_EVENT_TYPES" label="Tetikleyici" :searchable="false" />
</div>
<div v-if="draft.event_type === 'PORTFOLIO_DAILY'" class="col-12 col-sm-6">
<AppPopupSelect v-model="draft.account_id" :options="accountOptions" label="Portföy Hesabı" />
</div>
<div v-if="draft.event_type === 'PORTFOLIO_DAILY'" class="col-12 col-sm-6">
<q-input v-model="draft.schedule_time" outlined type="time" label="Gönderim Saati" stack-label />
</div>
<div v-if="draft.event_type === 'PORTFOLIO_DAILY'" class="col-12 col-sm-6">
<AppPopupSelect
v-model="draft.display_currency"
:options="DISPLAY_ASSETS"
label="Gösterim Para Birimi"
:searchable="false"
/>
</div>
<div v-if="draft.event_type === 'PORTFOLIO_DAILY'" class="col-12 col-sm-6">
<q-input v-model.trim="draft.timezone" outlined label="Timezone" />
</div>
<div v-if="draft.event_type === 'PORTFOLIO_DAILY'" class="col-12">
<div class="text-caption text-grey-7 q-mb-xs">Çalışacağı Günler</div>
<q-option-group
v-model="draft.days_of_week"
:options="weekdayOptions"
type="checkbox"
color="primary"
inline
/>
</div>
<div class="col-12"><q-input v-model.trim="draft.title_template" outlined label="Bildirim Başlığı" /></div>
<div class="col-12"><q-input v-model.trim="draft.body_template" outlined type="textarea" autogrow label="Bildirim Metni" /></div>
<div class="col-12">
<q-banner rounded class="surface-soft text-caption">
Günlük portföy: <code>{{ '{{portfolio_value}}' }}</code>, <code>{{ '{{display_currency}}' }}</code>, <code>{{ '{{account_name}}' }}</code> ·
Sinyal: <code>{{ '{{system}}' }}</code>, <code>{{ '{{direction}}' }}</code>, <code>{{ '{{edge}}' }}</code>, <code>{{ '{{confidence}}' }}</code>, <code>{{ '{{data_quality}}' }}</code>.
</q-banner>
</div>
<div class="col-12"><q-toggle v-model="draft.enabled" color="primary" label="Şablon aktif" /></div>
</q-card-section>
<q-card-actions align="right" class="popup-action-footer q-pa-md">
<q-btn push color="grey-3" text-color="grey-9" label="Vazgeç" v-close-popup no-caps />
<q-btn push color="primary" icon="save" label="Şablonu Kaydet" no-caps @click="saveTemplate" />
</q-card-actions>
</q-card>
</q-dialog>
</q-page>
</template>
<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useQuasar } from 'quasar'
import AppPopupSelect from '@/components/AppPopupSelect.vue'
import { NOTIFICATION_EVENT_TYPES, useNotificationsStore } from '@/stores/notifications'
import { usePortfolioStore } from '@/stores/portfolio'
import { DISPLAY_ASSETS, useUiStore } from '@/stores/ui'
const $q = useQuasar()
const notifications = useNotificationsStore()
const portfolio = usePortfolioStore()
const ui = useUiStore()
const tab = ref('settings')
const templateDialog = ref(false)
const provider = reactive({ enabled: false, firebase_project_id: '', sender_id: '', android_package_name: 'tr.rosayazilim.yatirimdashboard', web_vapid_key: '', note: '' })
const draft = reactive({})
const weekdayOptions = [
{ label: 'Pzt', value: 1 },
{ label: 'Sal', value: 2 },
{ label: 'Çar', value: 3 },
{ label: 'Per', value: 4 },
{ label: 'Cum', value: 5 },
{ label: 'Cmt', value: 6 },
{ label: 'Paz', value: 7 },
]
const accountOptions = computed(() => portfolio.activeAccounts.map((item) => ({ label: item.name, value: item.id, caption: item.base_currency })))
function eventLabel(value) { return NOTIFICATION_EVENT_TYPES.find((item) => item.value === value)?.label || value }
function formatDate(value) { return value ? new Date(value).toLocaleString('tr-TR') : '—' }
function hydrateProvider() {
Object.assign(provider, {
enabled: notifications.providerSettings?.enabled || false,
firebase_project_id: notifications.providerSettings?.firebase_project_id || '',
sender_id: notifications.providerSettings?.sender_id || '',
android_package_name: notifications.providerSettings?.android_package_name || 'tr.rosayazilim.yatirimdashboard',
web_vapid_key: notifications.providerSettings?.web_vapid_key || '',
note: notifications.providerSettings?.note || '',
})
}
async function refresh() {
try { await notifications.sync(); hydrateProvider() }
catch (error) { $q.notify({ type: 'negative', message: error instanceof Error ? error.message : 'Bildirim verileri alınamadı.' }) }
}
async function saveProvider() {
try { await notifications.saveProviderSettings(provider); $q.notify({ type: 'positive', message: 'Firebase ayarları kaydedildi.' }) }
catch (error) { $q.notify({ type: 'negative', message: error instanceof Error ? error.message : 'Ayarlar kaydedilemedi.' }) }
}
async function registerDevice() {
try { await notifications.registerCurrentDevice(); $q.notify({ type: 'positive', message: 'Bu cihaz bildirim sistemine kaydedildi.' }) }
catch (error) { $q.notify({ type: 'negative', message: error instanceof Error ? error.message : 'Cihaz kaydedilemedi.' }) }
}
async function setDeviceActive(id, active) {
try { await notifications.setDeviceActive(id, active) }
catch (error) { $q.notify({ type: 'negative', message: error instanceof Error ? error.message : 'Cihaz güncellenemedi.' }) }
}
function resetDraft(item = null) {
Object.assign(draft, {
id: item?.id || null,
name: item?.name || '',
event_type: item?.event_type || 'PORTFOLIO_DAILY',
account_id: item?.account_id || portfolio.selectedAccountId,
enabled: item?.enabled !== false,
timezone: item?.timezone || 'Europe/Istanbul',
schedule_time: item?.schedule_time ? String(item.schedule_time).slice(0,5) : '09:00',
days_of_week: item?.days_of_week || [1,2,3,4,5,6,7],
display_currency: item?.display_currency || ui.displayAsset,
title_template: item?.title_template || 'Günlük Portföy Özeti',
body_template: item?.body_template || 'Portföy değeri: {{portfolio_value}} {{display_currency}}',
payload: item?.payload || {},
})
}
function newTemplate() { resetDraft(); templateDialog.value = true }
function editTemplate(item) { resetDraft(item); templateDialog.value = true }
async function saveTemplate() {
try { await notifications.saveTemplate(draft); templateDialog.value = false; $q.notify({ type: 'positive', message: 'Bildirim şablonu kaydedildi.' }) }
catch (error) { $q.notify({ type: 'negative', message: error instanceof Error ? error.message : 'Şablon kaydedilemedi.' }) }
}
async function toggleTemplate(item, enabled) {
try { await notifications.setTemplateEnabled(item.id, enabled) }
catch (error) { $q.notify({ type: 'negative', message: error instanceof Error ? error.message : 'Şablon güncellenemedi.' }) }
}
async function removeTemplate(item) {
try { await notifications.deleteTemplate(item.id); $q.notify({ type: 'positive', message: 'Şablon silindi.' }) }
catch (error) { $q.notify({ type: 'negative', message: error instanceof Error ? error.message : 'Şablon silinemedi.' }) }
}
onMounted(refresh)
</script>
