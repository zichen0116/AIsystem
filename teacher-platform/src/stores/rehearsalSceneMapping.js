function estimateSpeechDuration(text) {
  const normalized = String(text || '').trim()
  if (!normalized) return 3000
  const cjkChars = Array.from(normalized).filter(char => /[\u4e00-\u9fff]/.test(char)).length
  const latinWords = normalized.replace(/[\u4e00-\u9fff]/g, ' ').trim().split(/\s+/).filter(Boolean).length
  return Math.max(cjkChars * 150 + latinWords * 240, 2000)
}

function buildUploadSlide(rawScene) {
  if (rawScene.page_image_url) {
    return {
      id: `upload-slide-${rawScene.id || rawScene.scene_order}`,
      viewportSize: 1000,
      viewportRatio: 0.5625,
      background: { type: 'solid', color: '#0f172a' },
      elements: [
        {
          id: `upload-page-image-${rawScene.id || rawScene.scene_order}`,
          type: 'image',
          src: rawScene.page_image_url,
          left: 0,
          top: 0,
          width: 1000,
          height: 562,
        },
      ],
    }
  }

  return {
    id: `upload-fallback-${rawScene.id || rawScene.scene_order}`,
    viewportSize: 1000,
    viewportRatio: 0.5625,
    background: { type: 'solid', color: '#ffffff' },
    elements: [
      {
        id: `upload-title-${rawScene.id || rawScene.scene_order}`,
        type: 'text',
        content: `<p style="font-size:32px;font-weight:700;margin:0;">${rawScene.title || 'Uploaded page'}</p>`,
        left: 60,
        top: 56,
        width: 880,
        height: 56,
      },
      {
        id: `upload-text-${rawScene.id || rawScene.scene_order}`,
        type: 'text',
        content: `<p style="font-size:18px;line-height:1.8;margin:0;">${rawScene.page_text || rawScene.script_text || 'This page will be explained in narration mode.'}</p>`,
        left: 60,
        top: 144,
        width: 880,
        height: 320,
      },
    ],
  }
}

function buildUploadActions(rawScene) {
  const text = rawScene.script_text || rawScene.page_text || rawScene.title
  if (!text) return []

  return [{
    type: 'speech',
    text,
    duration: estimateSpeechDuration(text),
    audio_status: rawScene.audio_status || 'failed',
    ...(rawScene.audio_url ? { persistent_audio_url: rawScene.audio_url } : {}),
  }]
}

function getSceneSubtitle(scene) {
  if (!scene) return ''

  const speechAction = (scene.actions || []).find(action => action?.type === 'speech' && action.text)
  if (speechAction?.text) return speechAction.text

  return scene.scriptText || scene.title || ''
}

function getSceneImageUrls(scene) {
  const urls = []

  if (scene?.pageImageUrl) {
    urls.push(scene.pageImageUrl)
  }

  for (const element of scene?.slideContent?.elements || []) {
    if (element?.type === 'image' && element.src) {
      urls.push(element.src)
    }
  }

  return [...new Set(urls)]
}

function preloadImage(url) {
  if (!url || typeof Image === 'undefined') return Promise.resolve(false)

  return new Promise(resolve => {
    const img = new Image()
    img.onload = () => resolve(true)
    img.onerror = () => resolve(false)
    img.src = url
  })
}

async function preloadSceneImages(scene, limit = 1) {
  const urls = getSceneImageUrls(scene).slice(0, limit)
  if (urls.length === 0) return
  await Promise.all(urls.map(preloadImage))
}

function preloadUpcomingSceneImages(scenes, startIndex, lookahead = 2) {
  const targetScenes = (scenes || []).slice(startIndex, startIndex + lookahead)
  for (const scene of targetScenes) {
    for (const url of getSceneImageUrls(scene)) {
      preloadImage(url)
    }
  }
}

function mapRehearsalScene(rawScene, source = 'topic') {
  return {
    sceneOrder: rawScene.scene_order,
    title: rawScene.title,
    slideContent: rawScene.slide_content || buildUploadSlide(rawScene),
    actions: Array.isArray(rawScene.actions) && rawScene.actions.length > 0
      ? rawScene.actions
      : buildUploadActions(rawScene),
    keyPoints: rawScene.key_points,
    sceneStatus: rawScene.scene_status,
    audioStatus: rawScene.audio_status,
    source,
    pageImageUrl: rawScene.page_image_url,
    scriptText: rawScene.script_text,
  }
}

export {
  buildUploadActions,
  buildUploadSlide,
  estimateSpeechDuration,
  getSceneSubtitle,
  preloadSceneImages,
  preloadUpcomingSceneImages,
  mapRehearsalScene,
}
