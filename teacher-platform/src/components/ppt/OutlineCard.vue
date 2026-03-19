<template>
  <div class="outline-card">
    <div class="outline-header">
      <div class="outline-title">PPT大纲</div>
      <div class="outline-actions">
        <button v-if="!editing" class="outline-btn" @click="$emit('regenerate')">重新生成</button>
        <button v-if="!editing && editable" class="outline-btn" @click="startEdit">编辑</button>
        <button v-if="editing" class="outline-btn" @click="cancelEdit">取消</button>
        <button v-if="editing" class="outline-btn" @click="saveEdit">保存</button>
        <button v-if="showApprove && !editing" class="outline-btn primary" @click="handleApprove">确认生成PPT</button>
      </div>
    </div>

    <div v-if="editing" class="outline-form">
      <div class="field">
        <label>主题</label>
        <input v-model="draft.title" class="field-input" />
      </div>
    </div>

    <div class="outline-sections">
      <section
        v-for="(section, sectionIndex) in workingSections"
        :key="section.id || `section-${sectionIndex}`"
        class="outline-section"
      >
        <div class="section-title-row">
          <input v-if="editing" v-model="section.title" class="field-input section-input" />
          <h3 v-else class="section-title">{{ section.title }}</h3>
        </div>

        <article
          v-for="(page, pageIndex) in section.pages || []"
          :key="page.id || `page-${sectionIndex}-${pageIndex}`"
          class="outline-page"
        >
          <div class="page-title-row">
            <input v-if="editing" v-model="page.title" class="field-input page-input" />
            <h4 v-else class="page-title">{{ page.title }}</h4>
          </div>

          <div v-if="editing" class="field">
            <label>副标题</label>
            <input v-model="page.subtitle" class="field-input" />
          </div>
          <div v-else-if="page.subtitle" class="page-subtitle">{{ page.subtitle }}</div>

          <div v-if="editing" class="field">
            <label>演讲备注</label>
            <textarea
              v-model="page.speaker_notes"
              class="field-textarea notes-textarea"
              rows="3"
              placeholder="这一页建议怎么讲、强调什么、如何过渡"
            />
          </div>
          <div v-else-if="page.speaker_notes" class="page-notes">{{ page.speaker_notes }}</div>

          <div
            v-for="(block, blockIndex) in page.blocks || []"
            :key="block.id || `block-${blockIndex}`"
            class="page-block"
          >
            <input
              v-if="editing"
              v-model="block.title"
              class="field-input block-input"
              placeholder="段落标题"
            />
            <div v-else-if="block.title" class="block-title">{{ block.title }}</div>

            <textarea
              v-if="editing"
              :value="formatBlockContent(block.content)"
              class="field-textarea"
              rows="4"
              placeholder="段落内容，每行会转成一个要点"
              @input="updateBlockContent(block, $event.target.value)"
            />
            <ul v-else class="block-list">
              <li v-for="(item, itemIndex) in normalizeBlockContent(block.content)" :key="itemIndex">{{ item }}</li>
            </ul>
          </div>

          <div v-if="(page.image_candidates || []).length" class="image-chooser">
            <div class="image-label">配图选择</div>
            <div class="image-grid">
              <button
                v-for="(image, imageIndex) in page.image_candidates"
                :key="image.id || imageIndex"
                type="button"
                class="image-option"
                :class="{ selected: page.selected_image_id === image.id }"
                @click="selectImage(page, image.id)"
              >
                <img :src="image.url" :alt="`候选配图 ${imageIndex + 1}`" />
                <span>配图{{ imageIndex + 1 }}</span>
              </button>
            </div>
            <button
              type="button"
              class="skip-image-btn"
              :class="{ selected: !page.selected_image_id }"
              @click="selectImage(page, null)"
            >
              不选图
            </button>
          </div>
        </article>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import {
  cloneOutlinePayload,
  hasRenderableOutlinePayload,
  markdownToOutlinePayload,
  payloadToMarkdown,
} from '../../utils/pptOutlineCard.js'

const props = defineProps({
  outline: { type: Object, required: true },
  editable: { type: Boolean, default: true },
  showApprove: { type: Boolean, default: true },
})

const emit = defineEmits(['approve', 'edit', 'regenerate'])

const editing = ref(false)
const draft = ref(createDraft())

const activePayload = computed(() => {
  if (editing.value) return draft.value
  return resolveOutlinePayload()
})

const workingSections = computed(() => activePayload.value.sections || [])

watch(
  () => props.outline,
  () => {
    if (!editing.value) {
      draft.value = createDraft()
    }
  },
  { deep: true },
)

function createFallbackPayload() {
  return markdownToOutlinePayload(props.outline.content || '', props.outline.image_urls || {})
}

function resolveOutlinePayload() {
  if (hasRenderableOutlinePayload(props.outline.outline_payload)) {
    return cloneOutlinePayload(props.outline.outline_payload)
  }
  return createFallbackPayload()
}

function createDraft() {
  return cloneOutlinePayload(resolveOutlinePayload())
}

function startEdit() {
  draft.value = createDraft()
  editing.value = true
}

function cancelEdit() {
  editing.value = false
  draft.value = createDraft()
}

function saveEdit() {
  const outlinePayload = cloneOutlinePayload(draft.value)
  emit('edit', {
    content: payloadToMarkdown(outlinePayload),
    outline_payload: outlinePayload,
    image_urls: buildImagePayload(outlinePayload),
  })
  editing.value = false
}

function handleApprove() {
  const outlinePayload = cloneOutlinePayload(activePayload.value)
  emit('approve', {
    content: payloadToMarkdown(outlinePayload),
    outline_payload: outlinePayload,
    image_urls: buildImagePayload(outlinePayload),
  })
}

function normalizeBlockContent(content) {
  if (Array.isArray(content)) return content.filter(Boolean)
  return String(content || '').split('\n').map(item => item.trim()).filter(Boolean)
}

function formatBlockContent(content) {
  return normalizeBlockContent(content).join('\n')
}

function updateBlockContent(block, value) {
  block.content = value
    .split('\n')
    .map(item => item.trim())
    .filter(Boolean)
}

function selectImage(page, imageId) {
  if (!editing.value) {
    const outlinePayload = cloneOutlinePayload(resolveOutlinePayload())
    for (const section of outlinePayload.sections || []) {
      const targetPage = (section.pages || []).find(item => item.id === page.id)
      if (targetPage) {
        targetPage.selected_image_id = imageId
      }
    }
    emit('edit', {
      content: payloadToMarkdown(outlinePayload),
      outline_payload: outlinePayload,
      image_urls: buildImagePayload(outlinePayload),
    })
    return
  }
  page.selected_image_id = imageId
}

function buildImagePayload(payload) {
  const imageMap = {}
  let pageCursor = 0
  for (const section of payload.sections || []) {
    for (const page of section.pages || []) {
      const candidates = page.image_candidates || []
      if (candidates.length) {
        imageMap[String(pageCursor)] = candidates.map(item => item.url)
      }
      pageCursor += 1
    }
  }
  return imageMap
}
</script>

<style scoped>
.outline-card {
  width: min(1180px, 100%);
  margin: 24px 0;
  padding: 28px;
  background: #fff;
  border-radius: 18px;
  border: 1px solid #e8ecf4;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.06);
}

.outline-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}

.outline-title {
  font-size: 18px;
  font-weight: 700;
  color: #1f2937;
}

.outline-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.outline-btn {
  padding: 10px 16px;
  border: 1px solid #d7deea;
  background: #fff;
  border-radius: 10px;
  font-size: 14px;
  cursor: pointer;
}

.outline-btn.primary {
  background: #3a61ea;
  color: #fff;
  border-color: #3a61ea;
}

.outline-form,
.outline-page,
.outline-section {
  display: flex;
  flex-direction: column;
}

.outline-sections {
  gap: 22px;
  display: flex;
  flex-direction: column;
}

.outline-section {
  gap: 14px;
}

.outline-page {
  gap: 12px;
  padding: 18px;
  border-radius: 14px;
  background: #f8fafc;
}

.section-title,
.page-title,
.block-title {
  margin: 0;
  color: #111827;
}

.section-title {
  font-size: 18px;
}

.page-title {
  font-size: 16px;
  font-weight: 700;
}

.page-subtitle {
  font-size: 14px;
  color: #667085;
}

.page-notes {
  font-size: 14px;
  line-height: 1.7;
  color: #475467;
  background: #fff;
  border: 1px solid #e4e7ec;
  border-radius: 12px;
  padding: 12px 14px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-input,
.field-textarea {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #d0d5dd;
  border-radius: 10px;
  padding: 10px 12px;
  font-size: 14px;
  background: #fff;
}

.field-textarea {
  resize: vertical;
  font-family: inherit;
}

.notes-textarea {
  min-height: 96px;
}

.block-list {
  margin: 0;
  padding-left: 20px;
  color: #334155;
}

.image-chooser {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.image-label {
  font-size: 13px;
  font-weight: 600;
  color: #667085;
}

.image-grid {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.image-option {
  width: 144px;
  border: 2px solid transparent;
  border-radius: 12px;
  padding: 8px;
  background: #fff;
  cursor: pointer;
}

.image-option.selected,
.skip-image-btn.selected {
  border-color: #3a61ea;
  box-shadow: 0 0 0 3px rgba(58, 97, 234, 0.12);
}

.image-option img {
  width: 100%;
  height: 92px;
  object-fit: cover;
  border-radius: 8px;
  display: block;
}

.image-option span {
  display: block;
  margin-top: 8px;
  font-size: 13px;
  color: #475467;
}

.skip-image-btn {
  align-self: flex-start;
  border: 1px solid #d7deea;
  background: #fff;
  border-radius: 10px;
  padding: 8px 12px;
  cursor: pointer;
}
</style>
