export function normalizeText(text) {
  return String(text || '').replace(/\s+/g, ' ').trim()
}

function joinRecognitionText(left, right) {
  const first = normalizeText(left)
  const second = normalizeText(right)

  if (!first) return second
  if (!second) return first

  const needsSpace =
    /[A-Za-z0-9]$/.test(first) &&
    /^[A-Za-z0-9]/.test(second)

  return normalizeText(needsSpace ? `${first} ${second}` : `${first}${second}`)
}

export function getRecognitionSnapshot(event, carriedFinalText = '') {
  let finalText = normalizeText(carriedFinalText)
  let interimText = ''

  const resultIndex = Number.isInteger(event?.resultIndex) ? event.resultIndex : 0
  const results = Array.from(event?.results || [])

  for (let i = resultIndex; i < results.length; i += 1) {
    const result = results[i]
    const transcript = normalizeText(result?.[0]?.transcript || '')
    if (!transcript) continue

    if (result?.isFinal) {
      finalText = joinRecognitionText(finalText, transcript)
    } else {
      interimText = joinRecognitionText(interimText, transcript)
    }
  }

  return {
    finalText,
    interimText,
    mergedText: joinRecognitionText(finalText, interimText)
  }
}
