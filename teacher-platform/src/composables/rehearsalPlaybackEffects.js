export const DEFAULT_SPOTLIGHT_DURATION_MS = 5000

export function applySpotlightAction(store, action, scheduleEffectClear) {
  if (!store || !action?.elementId) return

  store.spotlightTarget = {
    elementId: action.elementId,
    dimOpacity: action.dimOpacity ?? 0.4,
  }

  scheduleEffectClear?.('spotlight', action.duration || DEFAULT_SPOTLIGHT_DURATION_MS, () => {
    store.spotlightTarget = null
  })
}
