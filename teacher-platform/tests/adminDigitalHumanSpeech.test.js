import test from 'node:test'
import assert from 'node:assert/strict'

async function loadSpeechHelpers() {
  try {
    return await import('../src/components/BigScreen/adminDigitalHumanSpeech.js')
  } catch {
    return null
  }
}

function makeResult(transcript, isFinal) {
  return {
    0: { transcript },
    length: 1,
    isFinal
  }
}

function makeEvent(results, resultIndex = 0) {
  return { resultIndex, results }
}

test('keeps usable speech text even when browser has not marked the turn final yet', async () => {
  const mod = await loadSpeechHelpers()
  assert.ok(mod?.getRecognitionSnapshot, 'expected getRecognitionSnapshot to exist')

  const snapshot = mod.getRecognitionSnapshot(
    makeEvent([makeResult('向我介绍系统', false)]),
    ''
  )

  assert.equal(snapshot.finalText, '')
  assert.equal(snapshot.interimText, '向我介绍系统')
  assert.equal(snapshot.mergedText, '向我介绍系统')
})

test('merges earlier final text with the latest interim text for the same turn', async () => {
  const mod = await loadSpeechHelpers()
  assert.ok(mod?.getRecognitionSnapshot, 'expected getRecognitionSnapshot to exist')

  const snapshot = mod.getRecognitionSnapshot(
    makeEvent([makeResult('管理员端情况', false)]),
    '介绍一下'
  )

  assert.equal(snapshot.finalText, '介绍一下')
  assert.equal(snapshot.interimText, '管理员端情况')
  assert.equal(snapshot.mergedText, '介绍一下管理员端情况')
})

test('prefers finalized transcript when the browser provides it', async () => {
  const mod = await loadSpeechHelpers()
  assert.ok(mod?.getRecognitionSnapshot, 'expected getRecognitionSnapshot to exist')

  const snapshot = mod.getRecognitionSnapshot(
    makeEvent([
      makeResult('介绍一下', true),
      makeResult('管理员系统', false)
    ]),
    ''
  )

  assert.equal(snapshot.finalText, '介绍一下')
  assert.equal(snapshot.interimText, '管理员系统')
  assert.equal(snapshot.mergedText, '介绍一下管理员系统')
})
