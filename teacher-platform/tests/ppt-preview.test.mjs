import test from 'node:test'
import assert from 'node:assert/strict'

import {
  ZOOM_MAX_PERCENT,
  ZOOM_MIN_PERCENT,
  ZOOM_STEP_PERCENT,
  ZOOM_TOAST_DURATION_MS,
  getNextZoomPercent,
  getThumbnailRenderIndices,
} from '../src/utils/pptPreview.js'

test('zoom step snaps cleanly to 100 percent', () => {
  assert.equal(getNextZoomPercent(110, 1), 100)
  assert.equal(getNextZoomPercent(90, -1), 100)
})

test('zoom stays within configured bounds', () => {
  assert.equal(getNextZoomPercent(ZOOM_MAX_PERCENT, -1), ZOOM_MAX_PERCENT)
  assert.equal(getNextZoomPercent(ZOOM_MIN_PERCENT, 1), ZOOM_MIN_PERCENT)
})

test('thumbnail refresh renders all slides by default', () => {
  assert.deepEqual(getThumbnailRenderIndices({ slideCount: 4 }), [0, 1, 2, 3])
})

test('thumbnail refresh can target only one dirty slide', () => {
  assert.deepEqual(
    getThumbnailRenderIndices({ slideCount: 5, dirtySlideIndex: 2 }),
    [2],
  )
})

test('thumbnail refresh falls back to full rerender when index is invalid', () => {
  assert.deepEqual(
    getThumbnailRenderIndices({ slideCount: 3, dirtySlideIndex: 5 }),
    [0, 1, 2],
  )
})

test('zoom toast hides after two seconds', () => {
  assert.equal(ZOOM_STEP_PERCENT, 10)
  assert.equal(ZOOM_TOAST_DURATION_MS, 2000)
})
