const MATERIALS_SECTION_TITLE = '## 项目资料提炼'
const NEXT_SECTION_RE = /\n##\s+/
const STALE_COMPLETED_TEXT = '已完成解析，可用于内容参考'
const LEGACY_VIDEO_MARKERS = ['[时间块', '视频关键帧', '【看到】', '【听到】', '[音频转录]']
const LOW_INFORMATION_ASR = new Set([
  'thank you',
  'thank you.',
  'thanks',
  'thanks.',
  '谢谢',
  '谢谢。',
  '谢谢大家',
  '谢谢大家。',
  '谢谢观看',
  '谢谢观看。',
])

function cleanText(value) {
  return String(value || '').trim()
}

function truncate(text, maxLength = 220) {
  const value = cleanText(text).replace(/\s+/g, ' ')
  return value.length > maxLength ? `${value.slice(0, maxLength)}...` : value
}

function looksLikeLegacyVideoText(text) {
  const value = cleanText(text)
  return LEGACY_VIDEO_MARKERS.some(marker => value.includes(marker))
}

function stripVideoLogMarkers(text) {
  return cleanText(text)
    .replace(/\[时间块[^\]]*\]/g, ' ')
    .replace(/\[视频关键帧[^\]]*\]/g, ' ')
    .replace(/【看到】/g, ' ')
    .replace(/【听到】/g, ' ')
    .replace(/\[音频转录\]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

function isInformativeVideoSummary(text) {
  const value = stripVideoLogMarkers(text)
  if (!value) return false

  const normalized = value.replace(/[\s.!！。?？,，]+/g, ' ').trim().toLowerCase()
  const compact = value.replace(/[\s.!！。?？,，]+/g, '').toLowerCase()
  if (LOW_INFORMATION_ASR.has(normalized) || LOW_INFORMATION_ASR.has(compact)) {
    return false
  }

  const cjkCount = (value.match(/[\u4e00-\u9fff]/g) || []).length
  const letterCount = (value.match(/[A-Za-z]/g) || []).length
  const digitCount = (value.match(/\d/g) || []).length
  return cjkCount + letterCount + digitCount >= 12
}

function extractVideoChannelText(text, channel) {
  const pattern = channel === 'audio'
    ? /(?:【听到】|\[音频转录\])\s*([\s\S]*?)(?=(?:【看到】|\[时间块|$))/g
    : /【看到】\s*([\s\S]*?)(?=(?:【听到】|\[时间块|$))/g
  const parts = []
  let match = pattern.exec(text)
  while (match) {
    if (cleanText(match[1])) parts.push(match[1])
    match = pattern.exec(text)
  }
  return stripVideoLogMarkers(parts.join(' '))
}

function condenseLegacyVideoText(text) {
  const value = cleanText(text)
  if (!value) return ''

  const audioText = extractVideoChannelText(value, 'audio')
  if (isInformativeVideoSummary(audioText)) return truncate(`视频概要：${audioText}`)

  const visualText = extractVideoChannelText(value, 'visual') || stripVideoLogMarkers(value)
  if (isInformativeVideoSummary(visualText)) return truncate(`视频概要：${visualText}`)

  return audioText ? truncate(`视频概要：${audioText}`) : ''
}

function formatSummaryText(text) {
  const value = cleanText(text)
  if (!value) return ''
  return looksLikeLegacyVideoText(value) ? condenseLegacyVideoText(value) : truncate(value)
}

export function extractReferenceFileSummary(file) {
  const parsed = file?.parsed_content || file?.parsedContent || {}
  let summary = cleanText(
    parsed.video_summary
    || parsed.summary
    || parsed.searchable_text
    || parsed.normalized_text
  )

  if (!summary) {
    for (const chunk of parsed.chunks_meta || []) {
      if (!chunk || typeof chunk !== 'object') continue
      summary = cleanText(
        chunk.video_summary
        || chunk.summary
        || chunk.searchable_text
        || chunk.content
        || chunk.raw_content
      )
      if (summary) break
    }
  }

  return formatSummaryText(summary)
}

function buildReferenceSummaryLines(referenceFiles = []) {
  const lines = []
  for (const file of referenceFiles) {
    const filename = cleanText(file?.filename || file?.name)
    const summary = extractReferenceFileSummary(file)
    if (!filename || !summary) continue
    lines.push({ filename, line: `- ${filename}：${summary}` })
  }
  return lines
}

function mergeLinesIntoMaterialSection(sectionText, summaryLines) {
  let nextSection = sectionText

  for (const { filename, line } of summaryLines) {
    const escapedFilename = filename.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    const staleLineRe = new RegExp(`-\\s*${escapedFilename}：[^\\n]*${STALE_COMPLETED_TEXT}[^\\n]*`, 'u')
    const existingLineRe = new RegExp(`-\\s*${escapedFilename}：[^\\n]*`, 'u')

    if (staleLineRe.test(nextSection)) {
      nextSection = nextSection.replace(staleLineRe, line)
      continue
    }

    const existingLine = nextSection.match(existingLineRe)?.[0] || ''
    if (
      existingLine
      && (
        looksLikeLegacyVideoText(existingLine)
        || existingLine.includes('截图显示')
        || existingLine.includes('画面展示')
        || existingLine.includes('关键帧')
      )
    ) {
      nextSection = nextSection.replace(existingLineRe, line)
      continue
    }

    if (nextSection.includes(line) || nextSection.includes(`- ${filename}：`) && !nextSection.includes(STALE_COMPLETED_TEXT)) {
      continue
    }

    nextSection = `${nextSection.trimEnd()}\n${line}`
  }

  return nextSection
}

export function mergeReferenceSummariesIntoPlanningContext(planningContextText, referenceFiles = []) {
  const contextText = cleanText(planningContextText)
  const summaryLines = buildReferenceSummaryLines(referenceFiles)
  if (!contextText || summaryLines.length === 0) return contextText

  const sectionStart = contextText.indexOf(MATERIALS_SECTION_TITLE)
  if (sectionStart === -1) {
    return `${contextText}\n\n${MATERIALS_SECTION_TITLE}\n${summaryLines.map(item => item.line).join('\n')}`.trim()
  }

  const afterTitleStart = sectionStart + MATERIALS_SECTION_TITLE.length
  const afterTitle = contextText.slice(afterTitleStart)
  const nextMatch = afterTitle.match(NEXT_SECTION_RE)
  const sectionEnd = nextMatch ? afterTitleStart + nextMatch.index : contextText.length
  const beforeSection = contextText.slice(0, sectionStart)
  const materialSection = contextText.slice(sectionStart, sectionEnd)
  const afterSection = contextText.slice(sectionEnd)
  const mergedSection = mergeLinesIntoMaterialSection(materialSection, summaryLines)

  return `${beforeSection}${mergedSection}${afterSection}`.trim()
}
