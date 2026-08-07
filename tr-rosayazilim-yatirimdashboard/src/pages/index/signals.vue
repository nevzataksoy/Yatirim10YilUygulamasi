<template>
  <q-page>
    <div class="page-wrap">
      <div class="q-mb-lg">
        <div class="row items-center q-gutter-sm">
          <div class="page-title">Yatırım Motoru</div>
          <q-badge outline color="primary">INVESTMENT_ENGINE</q-badge>
        </div>
        <div class="page-subtitle q-mt-xs">
          Model kararları, veri kalitesi, sağlık durumu ve gölge hazırlık görünümü.
        </div>
      </div>

      <div class="row q-col-gutter-md q-mb-lg">
        <div v-for="decision in engine.decisions" :key="decision.system" class="col-12 col-lg-6">
          <q-card flat class="section-card full-height">
            <q-card-section>
              <div class="row items-start no-wrap q-col-gutter-md">
                <div class="col min-width-0">
                  <div class="text-caption text-grey-6">{{ decision.system }}</div>
                  <div class="text-h5 text-weight-bold q-mt-xs">
                    {{ decision.direction || 'Yön Yok' }}
                  </div>
                  <div class="row items-center q-gutter-xs q-mt-xs">
                    <span class="text-caption text-grey-6">{{
                      regimeLabel(decision.regime_code)
                    }}</span>
                    <q-badge v-if="decision.regime_code" outline color="grey-7">{{
                      decision.regime_code
                    }}</q-badge>
                    <span class="text-caption text-grey-6">· {{ decision.model_version }}</span>
                  </div>
                </div>
                <SemanticPill
                  class="q-mt-xs"
                  :label="statusLabel(decision.status)"
                  :code="decision.status"
                  :tone="statusTone(decision.status)"
                />
              </div>
            </q-card-section>
            <q-separator />
            <q-card-section>
              <div class="row q-col-gutter-md">
                <div class="col-4 text-center">
                  <div class="text-caption text-grey-6">
                    Avantaj <q-badge outline color="grey-6">EDGE</q-badge>
                  </div>
                  <div class="text-h6 decision-score" :class="scoreClass(decision.edge_score)">
                    {{ metric(decision.edge_score) }}
                  </div>
                  <q-linear-progress rounded :value="ratio(decision.edge_score)" color="primary" />
                </div>
                <div class="col-4 text-center">
                  <div class="text-caption text-grey-6">
                    Güven <q-badge outline color="grey-6">CONFIDENCE</q-badge>
                  </div>
                  <div class="text-h6 decision-score" :class="scoreClass(decision.confidence)">
                    {{ metric(decision.confidence) }}
                  </div>
                  <q-linear-progress rounded :value="ratio(decision.confidence)" color="info" />
                </div>
                <div class="col-4 text-center">
                  <div class="text-caption text-grey-6">
                    Veri Kalitesi <q-badge outline color="grey-6">QUALITY</q-badge>
                  </div>
                  <div class="text-h6 decision-score" :class="scoreClass(decision.data_quality)">
                    {{ metric(decision.data_quality) }}
                  </div>
                  <q-linear-progress
                    rounded
                    :value="ratio(decision.data_quality)"
                    color="positive"
                  />
                </div>
              </div>
              <q-banner rounded class="surface-soft q-mt-lg">
                <template #avatar><q-icon name="verified_user" color="primary" /></template>
                <div class="row items-center q-gutter-sm">
                  <SemanticPill
                    :label="statusLabel(decision.status)"
                    :code="decision.status"
                    :tone="statusTone(decision.status)"
                  />
                  <span
                    >Minimum avantaj 70, güven 70 ve veri kalitesi 80 eşikleri değiştirilmeden
                    izleniyor.</span
                  >
                </div>
              </q-banner>
            </q-card-section>
          </q-card>
        </div>
      </div>

      <div class="row q-col-gutter-lg">
        <div class="col-12 col-lg-7">
          <q-card flat class="section-card">
            <q-card-section>
              <div class="text-h6 text-weight-bold">Motor Sağlık Durumu</div>
              <div class="text-caption text-grey-7">Veri kaynakları ve motor bileşenleri</div>
            </q-card-section>
            <q-separator />
            <q-list separator>
              <q-item v-for="item in engine.health" :key="item.component" class="q-py-md">
                <q-item-section avatar>
                  <q-avatar
                    :color="healthAvatarColor(item.status)"
                    :text-color="
                      statusTone(item.status) === 'positive'
                        ? 'positive'
                        : statusTone(item.status) === 'negative'
                          ? 'negative'
                          : 'warning'
                    "
                    :icon="healthIcon(item.status)"
                  />
                </q-item-section>
                <q-item-section>
                  <q-item-label class="row items-center q-gutter-xs">
                    <span class="text-weight-bold">{{ componentLabel(item.component) }}</span>
                    <q-badge outline color="grey-7">{{ item.component }}</q-badge>
                  </q-item-label>
                  <q-item-label caption class="q-mt-xs">{{ item.message }}</q-item-label>
                </q-item-section>
                <q-item-section side>
                  <SemanticPill
                    :label="statusLabel(item.status)"
                    :code="item.status"
                    :tone="statusTone(item.status)"
                  />
                </q-item-section>
              </q-item>
            </q-list>
          </q-card>
        </div>

        <div class="col-12 col-lg-5">
          <q-card flat class="section-card">
            <q-card-section class="row items-center">
              <div>
                <div class="text-h6 text-weight-bold">Model Doğrulama</div>
                <div class="text-caption text-grey-7">Hazırlık ve tarihsel doğrulama özeti</div>
              </div>
              <q-space />
              <q-btn flat round icon="refresh" :loading="engine.loading" @click="refresh"
                ><q-tooltip>Yenile</q-tooltip></q-btn
              >
            </q-card-section>
            <q-separator />
            <q-list separator>
              <q-item
                v-for="item in engine.validation"
                :key="`${item.validation_type}-${item.system}`"
                class="q-py-md"
              >
                <q-item-section>
                  <q-item-label class="row items-center q-gutter-xs">
                    <span class="text-weight-bold">{{
                      validationTypeLabel(item.validation_type)
                    }}</span>
                    <q-badge outline color="grey-7">{{ item.validation_type }}</q-badge>
                  </q-item-label>
                  <q-item-label caption class="row items-center q-gutter-xs q-mt-xs">
                    <span>{{ systemLabel(item.system) }}</span>
                    <q-badge v-if="item.system" outline color="grey-6">{{ item.system }}</q-badge>
                    <span>· {{ item.model_version }}</span>
                  </q-item-label>
                </q-item-section>
                <q-item-section side>
                  <SemanticPill
                    :label="statusLabel(item.status)"
                    :code="item.status"
                    :tone="statusTone(item.status)"
                  />
                </q-item-section>
              </q-item>
            </q-list>
          </q-card>
        </div>
      </div>
    </div>
  </q-page>
</template>

<script setup>
import { useQuasar } from 'quasar'
import SemanticPill from '@/components/SemanticPill.vue'
import {
  componentLabel,
  regimeLabel,
  statusLabel,
  statusTone,
  systemLabel,
  validationTypeLabel,
} from '@/services/presentation'
import { useEngineStore } from '@/stores/engine'

const $q = useQuasar()
const engine = useEngineStore()

function metric(value) {
  return Number(value || 0).toFixed(1)
}

function ratio(value) {
  return Math.max(0, Math.min(1, Number(value || 0) / 100))
}

function scoreClass(value) {
  const score = Number(value || 0)
  if (score >= 70) return 'decision-score--high'
  if (score >= 50) return 'decision-score--mid'
  return 'decision-score--low'
}

function healthAvatarColor(status) {
  const tone = statusTone(status)
  if (tone === 'positive') return 'green-1'
  if (tone === 'negative') return 'red-1'
  if (tone === 'info') return 'blue-1'
  return 'orange-1'
}

function healthIcon(status) {
  const tone = statusTone(status)
  if (tone === 'positive') return 'check_circle'
  if (tone === 'negative') return 'error'
  if (tone === 'info') return 'info'
  return 'warning'
}

async function refresh() {
  try {
    await engine.sync()
    $q.notify({ type: 'positive', message: 'Yatırım motoru verileri yenilendi.' })
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: error instanceof Error ? error.message : 'Veri alınamadı.',
    })
  }
}
</script>
