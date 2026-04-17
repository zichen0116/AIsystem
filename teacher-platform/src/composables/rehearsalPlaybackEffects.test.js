import assert from 'node:assert/strict'

import { applySpotlightAction } from './rehearsalPlaybackEffects.js'

function run() {
  {
    const store = { spotlightTarget: null }
    const scheduled = []

    applySpotlightAction(
      store,
      { elementId: 'el_1', dimOpacity: 0.5 },
      (timerName, durationMs, clearFn) => {
        scheduled.push({ timerName, durationMs })
        clearFn()
      },
    )

    assert.deepEqual(scheduled, [{ timerName: 'spotlight', durationMs: 3000 }])
    assert.equal(store.spotlightTarget, null)
  }

  {
    const store = { spotlightTarget: null }
    let capturedDuration = null

    applySpotlightAction(
      store,
      { elementId: 'el_2', duration: 1800 },
      (_timerName, durationMs) => {
        capturedDuration = durationMs
      },
    )

    assert.equal(capturedDuration, 1800)
    assert.deepEqual(store.spotlightTarget, {
      elementId: 'el_2',
      dimOpacity: 0.4,
    })
  }
}

run()
