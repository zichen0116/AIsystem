<script setup>
import { ref, computed, nextTick } from 'vue'

const form = ref({
  subject: '计算机科学',
  difficulty: 'medium', // easy | medium | hard
  types: {
    mc: true,
    tf: false,
    sa: false,
    essay: true
  },
  count: 10,
  source: ''
})

const hasGenerated = ref(false)
const uploading = ref(false)
const generating = ref(false)
const uploadPreview = ref('')
const uploadedFilename = ref('')
const questions = ref([])
const errorMsg = ref('')
const previewRef = ref(null)
const exporting = ref(false)

function formatTfAnswer(ans) {
  const s = (ans ?? '').toString().trim().toLowerCase()
  if (s === 'true' || s === 't' || s === '1' || s.includes('正确')) return '正确'
  if (s === 'false' || s === 'f' || s === '0' || s.includes('错误')) return '错误'
  return ans ?? ''
}

function isTfTrue(ans) {
  const s = (ans ?? '').toString().trim().toLowerCase()
  return s === 'true' || s === 't' || s === '1' || s.includes('正确')
}

function toggleDifficulty(level) {
  form.value.difficulty = level
}

function toggleType(key) {
  form.value.types[key] = !form.value.types[key]
}

const difficultyLabel = computed(() => {
  const map = { easy: '简单', medium: '中等', hard: '困难' }
  return map[form.value.difficulty]
})

const hasSource = computed(() => {
  return !!form.value.source || !!uploadPreview.value
})

const finalSource = computed(() => {
  if (form.value.source && uploadPreview.value) {
    return `${form.value.source}\n\n【以下为上传文档解析内容】\n${uploadPreview.value}`
  }
  return form.value.source || uploadPreview.value || ''
})

function selectFile() {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = '.pdf,.doc,.docx,.ppt,.pptx,.txt'
  input.onchange = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    await handleUpload(file)
  }
  input.click()
}

async function handleUpload(file) {
  uploading.value = true
  errorMsg.value = ''
  try {
    const formData = new FormData()
    formData.append('file', file)

    const resp = await fetch('/api/v1/html/upload', {
      method: 'POST',
      body: formData
    })

    if (!resp.ok) {
      const data = await resp.json().catch(() => ({}))
      throw new Error(data.detail || '上传失败')
    }

    const data = await resp.json()
    uploadPreview.value = data.preview || ''
    uploadedFilename.value = data.filename || file.name
  } catch (e) {
    console.error(e)
    errorMsg.value = e.message || '上传失败，请稍后重试'
  } finally {
    uploading.value = false
  }
}

async function handleGenerate() {
  errorMsg.value = ''
  generating.value = true
  try {
    const selectedTypes = Object.entries(form.value.types)
      .filter(([, v]) => v)
      .map(([k]) => k)

    if (!selectedTypes.length) {
      errorMsg.value = '请至少选择一种题目类型'
      generating.value = false
      return
    }

    const payload = {
      subject: form.value.subject || '未指定学科',
      difficulty: form.value.difficulty,
      types: selectedTypes,
      count: form.value.count || 1,
      source: finalSource.value || null
    }

    const resp = await fetch('/api/v1/question-generate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    })

    if (!resp.ok) {
      const data = await resp.json().catch(() => ({}))
      throw new Error(data.detail || '生成试题失败')
    }

    const data = await resp.json()

    if (Array.isArray(data.questions) && data.questions.length > 0) {
      questions.value = data.questions
    } else if (data.raw_text) {
      questions.value = [
        {
          type: 'essay',
          stem: '模型未按预期返回结构化题目，以下为原始文本：',
          answer: data.raw_text
        }
      ]
    } else {
      questions.value = []
    }

    hasGenerated.value = true
  } catch (e) {
    console.error(e)
    errorMsg.value = e.message || '生成试题失败，请稍后重试'
  } finally {
    generating.value = false
  }
}

async function handleExportPdf() {
  if (!hasGenerated.value || !previewRef.value || exporting.value) return
  try {
    exporting.value = true
    await nextTick()

    const { default: html2pdf } = await import('html2pdf.js')
    const element = previewRef.value

    const opt = {
      margin: [10, 10, 10, 10],
      filename: `${form.value.subject || '试题'}.pdf`,
      image: { type: 'jpeg', quality: 0.98 },
      html2canvas: { scale: 2, useCORS: true },
      jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' }
    }

    await html2pdf().set(opt).from(element).save()
  } catch (e) {
    console.error(e)
    errorMsg.value = '导出 PDF 失败，请稍后重试'
  } finally {
    exporting.value = false
  }
}
</script>

<template>
  <div class="page-wrap" :class="{ 'with-preview': hasGenerated }">
    <!-- 左侧：参数配置 -->
    <section class="config-card">
      <header class="header">
        <h1 class="title">生成新试题</h1>
        <p class="subtitle">配置试题参数，AI 将根据你的要求自动生成题目。</p>
      </header>

      <div class="field">
        <label class="label">学科</label>
        <div class="subject-input">
          <span class="subject-icon">📘</span>
          <input v-model="form.subject" type="text" class="subject-text" />
          <span class="subject-chevron">▾</span>
        </div>
      </div>

      <div class="field">
        <label class="label">题目类型</label>
        <div class="type-grid">
          <button
            type="button"
            class="type-btn"
            :class="{ active: form.types.mc }"
            @click="toggleType('mc')"
          >
            <span class="box" />
            单选题
          </button>
          <button
            type="button"
            class="type-btn"
            :class="{ active: form.types.tf }"
            @click="toggleType('tf')"
          >
            <span class="box" />
            判断题
          </button>
          <button
            type="button"
            class="type-btn"
            :class="{ active: form.types.sa }"
            @click="toggleType('sa')"
          >
            <span class="box" />
            简答题
          </button>
          <button
            type="button"
            class="type-btn"
            :class="{ active: form.types.essay }"
            @click="toggleType('essay')"
          >
            <span class="box" />
            论述题
          </button>
        </div>
      </div>

      <div class="field">
        <div class="label-row">
          <div>
            <label class="label">难度等级：{{ difficultyLabel }}</label>
            <div class="pill-group">
              <button
                type="button"
                class="pill-btn"
                :class="{ active: form.difficulty === 'easy' }"
                @click="toggleDifficulty('easy')"
              >
                简单
              </button>
              <button
                type="button"
                class="pill-btn"
                :class="{ active: form.difficulty === 'medium' }"
                @click="toggleDifficulty('medium')"
              >
                中等
              </button>
              <button
                type="button"
                class="pill-btn"
                :class="{ active: form.difficulty === 'hard' }"
                @click="toggleDifficulty('hard')"
              >
                困难
              </button>
            </div>
          </div>
          <div class="count-wrap">
            <label class="label small-label">题目数量</label>
            <input
              v-model.number="form.count"
              type="number"
              min="1"
              max="100"
              class="number-input"
              placeholder="例如：20"
            />
          </div>
        </div>
      </div>

      <div class="field">
        <div class="label-row">
          <label class="label">来源材料 / 知识点</label>
          <button
            type="button"
            class="link-btn"
            :disabled="uploading"
            @click="selectFile"
          >
            {{ uploading ? '上传中...' : '上传 PDF / 文档' }}
          </button>
        </div>
        <textarea
          v-model="form.source"
          class="source-input"
          placeholder="粘贴教学材料、知识点列表，或输入希望考察的内容..."
          rows="5"
        />
        <p v-if="uploadedFilename || uploadPreview" class="upload-hint">
          已上传：{{ uploadedFilename }}；
          提取文本长度：{{ uploadPreview.length }} 字
        </p>
      </div>

      <p v-if="errorMsg" class="error-text">
        {{ errorMsg }}
      </p>

      <button
        type="button"
        class="primary-btn"
        :disabled="generating"
        @click="handleGenerate"
      >
        {{ generating ? '生成中...' : '生成试题' }}
      </button>
    </section>

    <!-- 右侧：生成后预览 -->
    <section
      v-if="hasGenerated"
      ref="previewRef"
      class="preview-card"
      :class="{ exporting: exporting }"
    >
      <header class="preview-header">
        <h2 class="preview-title">试题预览</h2>
        <button type="button" class="outline-btn">保存试卷</button>
      </header>

      <div class="preview-body">
        <div
          v-for="(q, index) in questions"
          :key="index"
          class="question-block"
        >
          <div
            class="q-tag"
            :class="{ yellow: q.type === 'essay' || q.type === 'sa' }"
          >
            第 {{ index + 1 }} 题 ·
            {{
              q.type === 'mc'
                ? '单选题'
                : q.type === 'tf'
                  ? '判断题'
                  : q.type === 'sa'
                    ? '简答题'
                    : '论述题'
            }}
          </div>
          <p class="q-text">
            {{ q.stem }}
          </p>

          <!-- 单选题：选项列表 -->
          <ul v-if="q.type === 'mc' && q.options && q.options.length" class="option-list">
            <li
              v-for="opt in q.options"
              :key="opt.label"
              class="option"
              :class="{ active: opt.label === q.answer }"
            >
              {{ opt.label }}. {{ opt.text }}
            </li>
          </ul>

          <!-- 判断题：正确/错误 -->
          <div v-if="q.type === 'tf'" class="tf-wrap">
            <span class="tf-pill" :class="{ active: isTfTrue(q.answer) }">正确</span>
            <span class="tf-pill" :class="{ active: !isTfTrue(q.answer) }">错误</span>
            <span class="tf-answer">答案：{{ formatTfAnswer(q.answer) }}</span>
          </div>

          <!-- 简答/论述：答案与解析 -->
          <div v-if="(q.type === 'sa' || q.type === 'essay') && (q.answer || q.analysis)" class="answer-hint">
            <div class="hint-title">参考答案与解析：</div>
            <div class="hint-text" v-if="q.answer">
              <div class="hint-k">答案</div>
              <div class="hint-v">{{ q.answer }}</div>
            </div>
            <div class="hint-text" v-if="q.analysis">
              <div class="hint-k">解析</div>
              <div class="hint-v">{{ q.analysis }}</div>
            </div>
          </div>

          <!-- 兜底：显示答案/解析 -->
          <div v-if="q.type !== 'tf' && q.type !== 'mc' && q.type !== 'sa' && q.type !== 'essay' && (q.answer || q.analysis)" class="answer-hint">
            <div class="hint-title">参考答案与解析：</div>
            <ul class="hint-list">
              <li v-if="q.answer">答案：{{ q.answer }}</li>
              <li v-if="q.analysis">解析：{{ q.analysis }}</li>
            </ul>
          </div>
        </div>
      </div>

      <footer class="preview-footer">
        <button type="button" class="outline-btn" @click="handleExportPdf">导出 PDF</button>
      </footer>
    </section>
  </div>
</template>

<style scoped>
.page-wrap {
  min-height: 100vh;
  padding: 24px 32px 32px;
  background: linear-gradient(180deg, #f3f8ff 0%, #f9fbff 100%);
  display: flex;
  gap: 20px;
  align-items: flex-start;
  justify-content: center;
}

.page-wrap.with-preview {
  justify-content: flex-start;
}

.config-card {
  width: 720px;
  max-width: 800px;
  background: #ffffff;
  border-radius: 18px;
  padding: 28px 28px 32px;
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.12);
  border: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  /* 由内容自然撑开高度，避免按钮被挤出卡片外 */
  min-height: 520px;
}

.page-wrap.with-preview .config-card {
  width: auto;
  flex: 0 0 420px;
  max-width: 460px;
}

.header {
  margin-bottom: 20px;
}

.title {
  margin: 0 0 6px;
  font-size: 26px;
  font-weight: 700;
  color: #0f172a;
}

.subtitle {
  margin: 0;
  font-size: 14px;
  color: #64748b;
}

.field {
  margin-bottom: 16px;
}

.label {
  display: block;
  margin-bottom: 6px;
  font-size: 14px;
  font-weight: 500;
  color: #4b5563;
}

.subject-input {
  display: flex;
  align-items: center;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  background: #f9fafb;
  gap: 10px;
}

.subject-icon {
  font-size: 18px;
}

.subject-text {
  flex: 1;
  border: none;
  background: transparent;
  font-size: 15px;
  outline: none;
}

.subject-chevron {
  font-size: 10px;
  color: #9ca3af;
}

.pill-group {
  display: inline-flex;
  padding: 3px;
  border-radius: 999px;
  background: #eef2ff;
}

.pill-btn {
  border: none;
  background: transparent;
  padding: 6px 18px;
  font-size: 14px;
  color: #6b7280;
  border-radius: 999px;
  cursor: pointer;
}

.pill-btn.active {
  background: #ffffff;
  color: #2563eb;
  box-shadow: 0 4px 10px rgba(15, 23, 42, 0.12);
}

.type-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.type-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  background: #ffffff;
  font-size: 14px;
  color: #4b5563;
  cursor: pointer;
}

.type-btn .box {
  width: 16px;
  height: 16px;
  border-radius: 4px;
  border: 1px solid #d1d5db;
  background: #ffffff;
}

.type-btn.active {
  border-color: #2563eb;
  background: #eff6ff;
  color: #1d4ed8;
}

.type-btn.active .box {
  border-color: #2563eb;
  background: #2563eb;
}

.label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.link-btn {
  border: 1px solid rgba(37, 99, 235, 0.25);
  background: rgba(37, 99, 235, 0.08);
  color: #1d4ed8;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  padding: 6px 12px;
  border-radius: 999px;
  transition: background 0.15s ease, border-color 0.15s ease, transform 0.15s ease;
}

.link-btn:hover:not(:disabled) {
  background: rgba(37, 99, 235, 0.12);
  border-color: rgba(37, 99, 235, 0.35);
  transform: translateY(-1px);
}

.link-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.source-input {
  width: 100%;
  margin-top: 6px;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  font-size: 14px;
  resize: vertical;
  min-height: 120px;
  outline: none;
}

.primary-btn {
  width: 100%;
  margin-top: 8px;
  border: none;
  border-radius: 12px;
  background: #2563eb;
  color: #ffffff;
  font-size: 16px;
  font-weight: 600;
  padding: 12px 16px;
  cursor: pointer;
  box-shadow: 0 12px 24px rgba(37, 99, 235, 0.4);
}

.primary-btn.small {
  width: auto;
  box-shadow: none;
  padding-inline: 18px;
}

.count-wrap {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  min-width: 180px;
  margin-left: 12px;
}

.label.small-label {
  margin-bottom: 4px;
}

.number-input {
  width: 100%;
  max-width: 260px;
  padding: 9px 12px;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  font-size: 14px;
  outline: none;
}

.preview-card {
  flex: 1;
  background: #ffffff;
  border-radius: 18px;
  padding: 20px 22px 24px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 16px 32px rgba(15, 23, 42, 0.12);
  display: flex;
  flex-direction: column;
  min-width: 0;
  /* 右侧内部自己滚动，不影响左侧 */
  max-height: calc(100vh - 48px);
}

.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}

.preview-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #0f172a;
}

.outline-btn {
  border-radius: 999px;
  border: 1px solid #e2e8f0;
  background: #ffffff;
  font-size: 13px;
  color: #4b5563;
  padding: 6px 14px;
  cursor: pointer;
}

.preview-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding-right: 2px;
  /* 隐藏滚动条但保留滚动能力 */
  scrollbar-width: none; /* Firefox */
}

.preview-body::-webkit-scrollbar {
  display: none; /* Chrome / Edge / Safari */
}

/* 导出 PDF 时，取消高度限制和内部滚动，导出完整内容 */
.preview-card.exporting {
  max-height: none;
}

.preview-card.exporting .preview-body {
  overflow: visible;
  max-height: none;
  scrollbar-width: auto;
}

.question-block {
  margin-bottom: 18px;
  padding: 12px 14px 14px;
  border-radius: 12px;
  background: #f9fafb;
}

.q-tag {
  display: inline-flex;
  padding: 2px 10px;
  border-radius: 999px;
  background: #e0edff;
  color: #1d4ed8;
  font-size: 11px;
  font-weight: 600;
  margin-bottom: 8px;
}

.q-tag.yellow {
  background: #fef3c7;
  color: #b45309;
}

.q-text {
  margin: 0 0 8px;
  font-size: 14px;
  color: #111827;
}

.option-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.option {
  padding: 8px 10px;
  border-radius: 8px;
  background: #ffffff;
  font-size: 13px;
  color: #111827;
  margin-bottom: 6px;
}

.option.active {
  background: #2563eb;
  color: #ffffff;
}

.answer-hint {
  margin-top: 10px;
  padding: 10px 12px;
  border-radius: 10px;
  background: #ffffff;
  border: 1px dashed #e5e7eb;
}

.tf-wrap {
  margin-top: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.tf-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 6px 12px;
  border-radius: 999px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  color: #4b5563;
  font-size: 13px;
  font-weight: 600;
}

.tf-pill.active {
  background: #2563eb;
  border-color: #2563eb;
  color: #ffffff;
}

.tf-answer {
  font-size: 13px;
  color: #6b7280;
}

.hint-text {
  margin-top: 8px;
}

.hint-k {
  font-size: 12px;
  font-weight: 700;
  color: #6b7280;
  margin-bottom: 2px;
}

.hint-v {
  font-size: 13px;
  color: #111827;
  white-space: pre-wrap;
  line-height: 1.6;
}

.hint-title {
  font-size: 12px;
  font-weight: 600;
  color: #6b7280;
  margin-bottom: 4px;
}

.hint-list {
  margin: 0;
  padding-left: 18px;
  font-size: 12px;
  color: #4b5563;
}

.preview-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 10px;
}

@media (max-width: 900px) {
  .page-wrap {
    flex-direction: column;
  }

  .config-card {
    flex: none;
    width: 100%;
  }

  .preview-card {
    flex: none;
    width: 100%;
  }
}
</style>

