import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

const root = path.resolve(import.meta.dirname, '..', 'src', 'components', 'ppt')
const chatMessage = fs.readFileSync(path.join(root, 'ChatMessage.vue'), 'utf8')
const outlineCard = fs.readFileSync(path.join(root, 'OutlineCard.vue'), 'utf8')

test('chat messages use wider max widths', () => {
  assert.match(chatMessage, /max-width:\s*82%/)
  assert.match(chatMessage, /max-width:\s*min\(1180px,\s*100%\)/)
})

test('outline card uses wider layout width', () => {
  assert.match(outlineCard, /width:\s*min\(1180px,\s*100%\)/)
})
