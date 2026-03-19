export function cloneOutlinePayload(payload) {
  return JSON.parse(JSON.stringify(normalizeOutlinePayload(payload || { title: '', clarification: {}, sections: [] })))
}

export function hasRenderableOutlinePayload(payload) {
  if (!payload || typeof payload !== 'object') return false
  for (const section of payload.sections || []) {
    for (const page of section?.pages || []) {
      if ((page?.title || '').trim()) return true
      for (const block of page?.blocks || []) {
        if (normalizeBlockContent(block?.content).length) return true
      }
    }
  }
  return false
}

export function markdownToOutlinePayload(markdown, imageUrls = {}) {
  const lines = String(markdown || '')
    .split('\n')
    .map(line => line.trim())
    .filter(Boolean)

  const hasLevel3Pages = lines.some(line => line.startsWith('### '))
  const pageHeadingPrefix = hasLevel3Pages ? '### ' : '## '
  const pageCount = lines.filter(line => line.startsWith(pageHeadingPrefix)).length
  const legacyImageOffset = !hasLevel3Pages && imageUrls?.[0] != null && (imageUrls?.[String(pageCount)] ?? imageUrls?.[pageCount]) != null
  const sections = []
  let title = '未命名PPT'
  let currentSection = null
  let currentPage = null
  let currentBlock = null
  let pageIndex = -1

  for (const line of lines) {
    if (line.startsWith('# ')) {
      title = line.slice(2).trim() || title
      continue
    }

    if (line.startsWith('## ')) {
      const heading = line.slice(3).trim()
      if (hasLevel3Pages) {
        currentSection = {
          id: `section-${sections.length + 1}`,
          title: heading,
          pages: [],
        }
        sections.push(currentSection)
        currentPage = null
        currentBlock = null
      } else {
        currentSection = ensureDefaultSection(sections)
        pageIndex += 1
        currentPage = createPage(pageIndex, heading, imageUrls, pageCount, legacyImageOffset)
        currentSection.pages.push(currentPage)
        currentBlock = null
      }
      continue
    }

    if (line.startsWith('### ')) {
      currentSection = currentSection || ensureDefaultSection(sections)
      pageIndex += 1
      currentPage = createPage(pageIndex, line.slice(4).trim(), imageUrls, pageCount, legacyImageOffset)
      currentSection.pages.push(currentPage)
      currentBlock = null
      continue
    }

    if (line.startsWith('#### ')) {
      if (!currentPage) continue
      currentBlock = {
        id: `${currentPage.id}-block-${(currentPage.blocks || []).length + 1}`,
        title: line.slice(5).trim(),
        content: [],
      }
      currentPage.blocks.push(currentBlock)
      continue
    }

    if (!currentPage) continue
    const normalizedLine = line.startsWith('- ') ? line.slice(2).trim() : line
    if (!currentBlock) {
      currentBlock = {
        id: `${currentPage.id}-block-${(currentPage.blocks || []).length + 1}`,
        title: '',
        content: [],
      }
      currentPage.blocks.push(currentBlock)
    }
    currentBlock.content.push(normalizedLine)
  }

  return normalizeOutlinePayload({
    title,
    clarification: {},
    sections,
  })
}

export function payloadToMarkdown(payload) {
  const safePayload = normalizeOutlinePayload(payload || { title: '未命名PPT', sections: [] })
  const lines = [`# ${safePayload.title || '未命名PPT'}`, '']

  for (const section of safePayload.sections || []) {
    if (section?.title) {
      lines.push(`## ${section.title}`, '')
    }

    for (const page of section?.pages || []) {
      lines.push(`### ${page?.title || '未命名页面'}`, '')

      if (page?.subtitle) {
        lines.push(page.subtitle, '')
      }

      for (const block of page?.blocks || []) {
        if (block?.title) {
          lines.push(`#### ${block.title}`, '')
        }

        const entries = normalizeBlockContent(block?.content)
        for (const entry of entries) {
          lines.push(`- ${entry}`)
        }

        if (entries.length) {
          lines.push('')
        }
      }

      const selectedImage = (page?.image_candidates || []).find(item => item.id === page.selected_image_id)
      if (selectedImage?.url) {
        const selectedIndex = Math.max(
          1,
          (page.image_candidates || []).findIndex(item => item.id === page.selected_image_id) + 1,
        )
        lines.push(`![配图${selectedIndex}](${selectedImage.url})`, '')
      }
    }
  }

  while (lines.length && lines[lines.length - 1] === '') {
    lines.pop()
  }

  return lines.join('\n')
}

function normalizeBlockContent(content) {
  if (Array.isArray(content)) {
    return content.map(item => String(item).trim()).filter(Boolean)
  }
  return String(content || '')
    .split('\n')
    .map(item => item.trim())
    .filter(Boolean)
}

function ensureDefaultSection(sections) {
  if (sections.length) return sections[0]
  const section = { id: 'section-1', title: '内容大纲', pages: [] }
  sections.push(section)
  return section
}

function createPage(pageIndex, title, imageUrls, pageCount, legacyImageOffset) {
  return {
    id: `page-${pageIndex + 1}`,
    title,
    subtitle: '',
    blocks: [],
    speaker_notes: '',
    image_candidates: buildPageCandidates(pageIndex, imageUrls, pageCount, legacyImageOffset),
    selected_image_id: null,
  }
}

function buildPageCandidates(pageIndex, imageUrls, pageCount, legacyImageOffset) {
  let value = legacyImageOffset
    ? (imageUrls?.[String(pageIndex + 1)] ?? imageUrls?.[pageIndex + 1])
    : (imageUrls?.[String(pageIndex)] ?? imageUrls?.[pageIndex])
  const shiftedValue = imageUrls?.[String(pageIndex + 1)] ?? imageUrls?.[pageIndex + 1]
  const hasLegacyOffset = (imageUrls?.[String(pageCount)] ?? imageUrls?.[pageCount]) != null
  if (value == null && shiftedValue != null && hasLegacyOffset) {
    value = shiftedValue
  }
  if (!value) return []
  const candidates = Array.isArray(value) ? value : [value]
  return candidates.slice(0, 2).map((candidate, index) => {
    if (candidate && typeof candidate === 'object') {
      return {
        id: candidate.id || `page-${pageIndex + 1}-img-${index + 1}`,
        url: candidate.url || '',
      }
    }
    return {
      id: `page-${pageIndex + 1}-img-${index + 1}`,
      url: String(candidate || ''),
    }
  }).filter(item => item.url)
}

export function resolveSpeakerNotes(payload, slideIndex) {
  if (!payload || typeof payload !== 'object' || !Number.isInteger(slideIndex) || slideIndex < 0) {
    return ''
  }
  let pageCursor = 0
  for (const section of payload.sections || []) {
    for (const page of section?.pages || []) {
      if (pageCursor === slideIndex) {
        return String(page?.speaker_notes || '').trim()
      }
      pageCursor += 1
    }
  }
  return ''
}

function normalizeOutlinePayload(payload) {
  const safePayload = payload || { title: '', clarification: {}, sections: [] }
  return {
    title: String(safePayload.title || '').trim(),
    clarification: safePayload.clarification && typeof safePayload.clarification === 'object'
      ? JSON.parse(JSON.stringify(safePayload.clarification))
      : {},
    sections: (safePayload.sections || []).map((section, sectionIndex) => {
      const fallbackPageBase = `section-${sectionIndex + 1}`
      return {
        id: section?.id || `section-${sectionIndex + 1}`,
        title: String(section?.title || ''),
        pages: (section?.pages || []).map((page, pageIndex) => {
          const pageId = page?.id || `${fallbackPageBase}-page-${pageIndex + 1}`
          return {
            id: pageId,
            title: String(page?.title || ''),
            subtitle: String(page?.subtitle || ''),
            blocks: (page?.blocks || []).map((block, blockIndex) => ({
              id: block?.id || `${pageId}-block-${blockIndex + 1}`,
              title: String(block?.title || ''),
              content: normalizeBlockContent(block?.content),
            })),
            speaker_notes: normalizeSpeakerNotes(page),
            image_candidates: (page?.image_candidates || []).map((image, imageIndex) => ({
              id: image?.id || `${pageId}-img-${imageIndex + 1}`,
              url: String(image?.url || ''),
            })).filter(image => image.url),
            selected_image_id: page?.selected_image_id ?? null,
          }
        }),
      }
    }),
  }
}

function normalizeSpeakerNotes(page) {
  const current = String(page?.speaker_notes || '').trim()
  if (current) return current

  const topic = String(page?.title || '').trim() || '本页内容'
  const subtitle = String(page?.subtitle || '').trim()
  const details = []
  if (subtitle) details.push(subtitle)

  for (const block of page?.blocks || []) {
    if (block?.title) details.push(String(block.title).trim())
    for (const item of normalizeBlockContent(block?.content).slice(0, 3)) {
      details.push(item)
    }
    if (details.length >= 3) break
  }

  const uniqueDetails = details.filter((detail, index) => detail && details.indexOf(detail) === index)
  if (!uniqueDetails.length) {
    return `这一页主要讲${topic}，可以先说明核心主题，再自然过渡到下一页。`
  }
  if (uniqueDetails.length === 1) {
    return `这一页主要讲${topic}，可以先点出${uniqueDetails[0]}，再补充课堂里的关键含义。`
  }
  return `这一页主要讲${topic}，先说明${uniqueDetails[0]}，再结合${uniqueDetails[1]}展开，最后用一句话做好过渡。`
}
