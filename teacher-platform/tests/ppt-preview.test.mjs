import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

import {
  ZOOM_MAX_PERCENT,
  ZOOM_MIN_PERCENT,
  ZOOM_STEP_PERCENT,
  ZOOM_TOAST_DURATION_MS,
  getPdfExportLayerPosition,
  getNextZoomPercent,
  getPptDownloadUrl,
  getThumbnailRenderIndices,
  openPendingPptDownloadWindow,
  triggerPptDownload,
} from '../src/utils/pptPreview.js'
import { resolveSpeakerNotes } from '../src/utils/pptOutlineCard.js'

const lessonPrepPptPath = path.resolve(import.meta.dirname, '..', 'src', 'views', 'LessonPrepPpt.vue')
const lessonPrepPptSource = fs.readFileSync(lessonPrepPptPath, 'utf8')

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

test('preview notes follow active slide index', () => {
  const payload = {
    title: '中国传统文化',
    sections: [
      {
        title: '内容大纲',
        pages: [
          { title: '第 1 页', speaker_notes: 'page-1 note' },
          { title: '第 2 页', speaker_notes: 'page-2 note' },
        ],
      },
    ],
  }

  assert.equal(resolveSpeakerNotes(payload, 1), 'page-2 note')
})

test('preview notes fall back to empty string when missing', () => {
  assert.equal(resolveSpeakerNotes(null, 0), '')
})

test('pdf export layer stays offscreen before capture', () => {
  assert.deepEqual(getPdfExportLayerPosition(false), {
    left: '-99999px',
    top: '0px',
    zIndex: '-1',
  })
})

test('pdf export layer stays offscreen during capture because canvases are exported directly', () => {
  assert.deepEqual(getPdfExportLayerPosition(true), {
    left: '-99999px',
    top: '0px',
    zIndex: '-1',
  })
})

test('ppt download pre-opens a controllable window handle', () => {
  const popup = { close() {} }
  const calls = []

  const result = openPendingPptDownloadWindow({
    openWindow(url, target, features) {
      calls.push({ url, target, features })
      return popup
    },
  })

  assert.equal(result, popup)
  assert.deepEqual(calls, [{
    url: 'about:blank',
    target: '_blank',
    features: undefined,
  }])
})

test('ppt download reuses pre-opened window when available', () => {
  const popup = { location: { href: '' } }
  const ok = triggerPptDownload('https://example.com/demo.pptx', {
    presetWindow: popup,
  })

  assert.equal(ok, true)
  assert.equal(popup.location.href, 'https://example.com/demo.pptx')
})

test('ppt download falls back to anchor click when popup is unavailable', () => {
  const events = []
  const anchor = {
    href: '',
    target: '',
    rel: '',
    click() {
      events.push('clicked')
    },
  }

  const ok = triggerPptDownload('https://example.com/demo.pptx', {
    openWindow() {
      return null
    },
    createAnchor() {
      return anchor
    },
    appendToBody(node) {
      events.push(`append:${node === anchor}`)
    },
    removeNode() {
      events.push('removed')
    },
  })

  assert.equal(ok, true)
  assert.equal(anchor.href, 'https://example.com/demo.pptx')
  assert.deepEqual(events, ['append:true', 'clicked', 'removed'])
})

test('ppt download falls back to cached file url when latest request returns empty', () => {
  assert.equal(
    getPptDownloadUrl('', 'https://example.com/cached.pptx'),
    'https://example.com/cached.pptx',
  )
  assert.equal(
    getPptDownloadUrl('https://example.com/latest.pptx', 'https://example.com/cached.pptx'),
    'https://example.com/latest.pptx',
  )
  assert.equal(getPptDownloadUrl('   ', '   '), '')
})

test('ppt download refreshes the current session result before requesting backend download', () => {
  assert.match(lessonPrepPptSource, /getSessionDetail\(currentSessionId\.value\)/)
  assert.match(lessonPrepPptSource, /latestSessionDetail\.results\?\.find\(r => r\.is_current\)/)
  assert.match(lessonPrepPptSource, /await loadResultDetail\(latestResult\.id\)/)
})

test('pdf export uses canvas renderer instead of svg export layer', () => {
  assert.match(lessonPrepPptSource, /import\s+\{\s*Ppt2Canvas\s*\}\s+from\s+'..\/utils\/docmee\/ppt2canvas\.js'/)
  assert.match(lessonPrepPptSource, /import\(\s*'jspdf'\s*\)/)
  assert.match(lessonPrepPptSource, /class="pdf-export-canvas"/)
})
