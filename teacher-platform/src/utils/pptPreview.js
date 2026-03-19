export const ZOOM_STEP_PERCENT = 10
export const ZOOM_MIN_PERCENT = 40
export const ZOOM_MAX_PERCENT = 250
export const ZOOM_TOAST_DURATION_MS = 2000

export function getNextZoomPercent(currentPercent, direction) {
  const delta = direction * ZOOM_STEP_PERCENT
  const nextPercent = currentPercent - delta
  return Math.max(ZOOM_MIN_PERCENT, Math.min(ZOOM_MAX_PERCENT, nextPercent))
}

export function getThumbnailRenderIndices({ slideCount, dirtySlideIndex = null } = {}) {
  const safeSlideCount = Math.max(0, Number(slideCount) || 0)
  const allIndices = Array.from({ length: safeSlideCount }, (_, index) => index)

  if (
    Number.isInteger(dirtySlideIndex)
    && dirtySlideIndex >= 0
    && dirtySlideIndex < safeSlideCount
  ) {
    return [dirtySlideIndex]
  }

  return allIndices
}
