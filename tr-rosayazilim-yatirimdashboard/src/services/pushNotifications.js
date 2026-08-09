import { App } from '@capacitor/app'
import { Capacitor } from '@capacitor/core'
import { Device } from '@capacitor/device'
import { PushNotifications } from '@capacitor/push-notifications'

let persistentListenerHandles = []

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

export async function getNativeDeviceContext() {
  if (!isNativePushSupported()) {
    return {
      supported: false,
      installationId: null,
      deviceName: null,
      platform: Capacitor.getPlatform(),
    }
  }

  const [deviceId, deviceInfo, appInfo] = await Promise.all([
    Device.getId(),
    Device.getInfo(),
    App.getInfo().catch(() => null),
  ])

  return {
    supported: true,
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
}

export async function clearPushListeners() {
  for (const handle of persistentListenerHandles) {
    try {
      await handle.remove()
    } catch {
      // no-op
    }
  }
  persistentListenerHandles = []
}

export async function attachNativePushListeners({ onReceived, onAction } = {}) {
  if (!isNativePushSupported()) return false
  await clearPushListeners()

  if (onReceived) {
    persistentListenerHandles.push(
      await PushNotifications.addListener('pushNotificationReceived', onReceived),
    )
  }
  if (onAction) {
    persistentListenerHandles.push(
      await PushNotifications.addListener('pushNotificationActionPerformed', onAction),
    )
  }
  return true
}

export async function unregisterNativePush() {
  if (!isNativePushSupported()) return
  await PushNotifications.unregister()
}

export async function registerNativePush() {
  if (!isNativePushSupported()) {
    return { supported: false, permissionStatus: 'UNKNOWN', pushTarget: null }
  }

  const deviceContext = await getNativeDeviceContext()
  let permission = await PushNotifications.checkPermissions()
  if (permission.receive === 'prompt') permission = await PushNotifications.requestPermissions()
  const permissionStatus = normalizePermission(permission.receive)

  if (permissionStatus !== 'GRANTED') {
    return {
      supported: true,
      permissionStatus,
      pushTarget: null,
      targetKind: 'TOKEN',
      ...deviceContext,
    }
  }

  let registrationHandle
  let registrationErrorHandle
  let timeout

  try {
    const tokenPromise = new Promise((resolve, reject) => {
      timeout = setTimeout(() => reject(new Error('FCM kayıt anahtarı 20 saniye içinde alınamadı.')), 20000)

      Promise.all([
        PushNotifications.addListener('registration', (token) => resolve(token.value)),
        PushNotifications.addListener('registrationError', (error) =>
          reject(new Error(error?.error || 'Push registration başarısız.')),
        ),
      ])
        .then(([successHandle, errorHandle]) => {
          registrationHandle = successHandle
          registrationErrorHandle = errorHandle
          return PushNotifications.register()
        })
        .catch(reject)
    })

    const pushTarget = await tokenPromise
    return {
      supported: true,
      permissionStatus,
      pushTarget,
      targetKind: 'TOKEN',
      ...deviceContext,
    }
  } finally {
    if (timeout) clearTimeout(timeout)
    await registrationHandle?.remove?.().catch(() => null)
    await registrationErrorHandle?.remove?.().catch(() => null)
  }
}
