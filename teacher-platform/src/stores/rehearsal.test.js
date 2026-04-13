import assert from 'node:assert/strict'

import { getSceneSubtitle, mapRehearsalScene } from './rehearsalSceneMapping.js'

function run() {
  const mapped = mapRehearsalScene({
    id: 7,
    scene_order: 0,
    title: 'Page 1',
    slide_content: null,
    actions: null,
    key_points: [],
    scene_status: 'fallback',
    audio_status: 'ready',
    page_image_url: 'https://oss.example/page-1.png',
    page_text: 'Page text',
    script_text: 'Narration text',
    audio_url: 'https://oss.example/page-1.mp3',
  }, 'upload')

  assert.equal(mapped.sceneOrder, 0)
  assert.equal(mapped.sceneStatus, 'fallback')
  assert.equal(mapped.slideContent.elements[0].src, 'https://oss.example/page-1.png')
  assert.equal(mapped.actions[0].text, 'Narration text')
  assert.equal(mapped.actions[0].persistent_audio_url, 'https://oss.example/page-1.mp3')
  assert.equal(getSceneSubtitle(mapped), 'Narration text')
  assert.equal(getSceneSubtitle({
    title: 'Fallback title',
    scriptText: 'Resume subtitle',
    actions: [],
  }), 'Resume subtitle')
}

run()
