import { App } from '@capacitor/app'
import { Capacitor } from '@capacitor/core'
import { Device } from '@capacitor/device'
import { PushNotifications } from '@capacitor/push-notifications'

let listenerHandles = []

function normalizePermission(value) {
  const normalized = String(value || '').toLowerCase()
  if (normalized === 'granted') return 'GRANTED'
  if (normalized === 'denied') return 'DENIED'
  if (normalized === 'prompt' || normalized === 'prompt-with-rationale') return 'PROMPT'
  return 'UNKNOWN'
}

export function isNativePushSupported() {
  return Capacitor.isNativePlatform()
}

export async function clearPushListeners() {
  for (const handle of listenerHandles) {
    try { await handle.remove() } catch { /* no-op */ }
  }
  listenerHandles = []
}

export async function registerNativePush({ onReceived, onAction } = {}) {
  if (!isNativePushSupported()) {
    return { supported: false, permissionStatus: 'UNKNOWN', pushTarget: null }
  }

  await clearPushListeners()
  const [deviceId, deviceInfo, appInfo] = await Promise.all([
    Device.getId(),
    Device.getInfo(),
    App.getInfo().catch(() => null),
  ])
  const deviceContext = {
    installationId: deviceId.identifier,
    deviceName: deviceInfo.name || deviceInfo.model || 'Mobil Cihaz',
    platform: Capacitor.getPlatform(),
    operatingSystem: deviceInfo.operatingSystem || null,
    osVersion: deviceInfo.osVersion || null,
    appVersion: appInfo?.version || null,
    metadata: {
      manufacturer: deviceInfo.manufacturer || null,
      model: deviceInfo.model || null,
      isVirtual: Boolean(deviceInfo.isVirtual),
    },
  }

  let permission = await PushNotifications.checkPermissions()
  if (permission.receive === 'prompt') permission = await PushNotifications.requestPermissions()
  const permissionStatus = normalizePermission(permission.receive)
  if (permissionStatus !== 'GRANTED') {
    return { supported: true, permissionStatus, pushTarget: null, targetKind: 'TOKEN', ...deviceContext }
  }

  let resolveToken
  let rejectToken
  const tokenPromise = new Promise((resolve, reject) => {
    resolveToken = resolve
    rejectToken = reject
  })
  const timeout = setTimeout(
    () => rejectToken(new Error('FCM kayıt anahtarı alınamadı.')),
    15000,
  )
  listenerHandles.push(
    await PushNotifications.addListener('registration', (token) => {
      clearTimeout(timeout)
      resolveToken(token.value)
    }),
  )
  listenerHandles.push(
    await PushNotifications.addListener('registrationError', (error) => {
      clearTimeout(timeout)
      rejectToken(new Error(error?.error || 'Push registration başarısız.'))
    }),
  )

  if (onReceived) {
    listenerHandles.push(
      await PushNotifications.addListener('pushNotificationReceived', onReceived),
    )
  }
  if (onAction) {
    listenerHandles.push(
      await PushNotifications.addListener('pushNotificationActionPerformed', onAction),
    )
  }

  await PushNotifications.register()
  const pushTarget = await tokenPromise

  return {
    supported: true,
    permissionStatus,
    pushTarget,
    targetKind: 'TOKEN',
    ...deviceContext,
  }
}
