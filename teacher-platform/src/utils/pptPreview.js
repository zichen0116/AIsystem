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

export function getPdfExportLayerPosition(isCapturing) {
  return isCapturing
    ? { left: '0px', top: '0px', zIndex: '-1' }
    : { left: '-99999px', top: '0px', zIndex: '-1' }
}

export function triggerPptDownload(fileUrl, options = {}) {
  const url = String(fileUrl || '').trim()
  if (!url) return false

  const presetWindow = options.presetWindow || null
  if (presetWindow && presetWindow.location) {
    presetWindow.location.href = url
    return true
  }

  const openWindow = options.openWindow
    || ((nextUrl, target, features) => window.open(nextUrl, target, features))
  const popup = openWindow('', '_blank', 'noopener,noreferrer')
  if (popup && popup.location) {
    popup.location.href = url
    return true
  }

  const createAnchor = options.createAnchor || (() => document.createElement('a'))
  const appendToBody = options.appendToBody || (node => document.body.appendChild(node))
  const removeNode = options.removeNode || (node => node.remove())
  const anchor = createAnchor()
  anchor.href = url
  anchor.target = '_blank'
  anchor.rel = 'noopener noreferrer'
  appendToBody(anchor)
  if (typeof anchor.click === 'function') {
    anchor.click()
  }
  removeNode(anchor)
  return true
}
