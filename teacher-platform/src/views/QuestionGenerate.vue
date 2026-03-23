<script setup>
import { ref, computed, nextTick, onMounted } from 'vue'
import { apiRequest, getToken } from '../api/http.js'

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

/** 左侧：服务端保存的试卷列表（按登录用户隔离） */
const sidebarCollapsed = ref(false)
const savedPapers = ref([])
const activeSavedId = ref(null)
const savedListLoading = ref(false)

/** 保存试卷弹窗 */
const showSaveModal = ref(false)
const saveModalTitle = ref('')
const saveModalSubmitting = ref(false)

/** 从左侧记录加载预览时隐藏「生成新试题」卡片，关闭预览后恢复 */
const hideGenerateCard = ref(false)

/** 单题编辑草稿（按下标），保存后写回 questions 并移除 */
const questionEditDrafts = ref({})

function clearQuestionEditDrafts() {
  questionEditDrafts.value = {}
}

const hasUnsavedQuestionEdits = computed(() => {
  for (const key of Object.keys(questionEditDrafts.value)) {
    const i = Number(key)
    const draft = questionEditDrafts.value[i]
    const orig = questions.value[i]
    if (!draft || !orig) continue
    if (JSON.stringify(draft) !== JSON.stringify(orig)) return true
  }
  return false
})

function startEditQuestion(index) {
  const q = questions.value[index]
  if (!q) return
  if (questionEditDrafts.value[index] != null) return
  const draft = JSON.parse(JSON.stringify(q))
  if (draft.type === 'mc') {
    if (!Array.isArray(draft.options) || !draft.options.length) {
      draft.options = [
        { label: 'A', text: '' },
        { label: 'B', text: '' },
        { label: 'C', text: '' },
        { label: 'D', text: '' }
      ]
    }
    const labels = draft.options.map((o) => o.label)
    if (draft.answer == null || draft.answer === '' || !labels.includes(String(draft.answer))) {
      draft.answer = labels[0] || 'A'
    }
  }
  if (draft.type === 'tf' && (draft.answer == null || draft.answer === '')) {
    draft.answer = 'true'
  }
  if (draft.type === 'sa' || draft.type === 'essay') {
    if (draft.answer == null) draft.answer = ''
    if (draft.analysis == null) draft.analysis = ''
  } else if (draft.type !== 'mc' && draft.type !== 'tf') {
    if (draft.answer == null) draft.answer = ''
    if (draft.analysis == null) draft.analysis = ''
  }
  questionEditDrafts.value = { ...questionEditDrafts.value, [index]: draft }
}

function saveEditQuestion(index) {
  const draft = questionEditDrafts.value[index]
  if (!draft) return
  const next = [...questions.value]
  next[index] = JSON.parse(JSON.stringify(draft))
  questions.value = next
  const { [index]: _, ...rest } = questionEditDrafts.value
  questionEditDrafts.value = rest
}

function cancelEditQuestion(index) {
  const draft = questionEditDrafts.value[index]
  if (!draft) return
  const orig = questions.value[index]
  if (orig && JSON.stringify(draft) !== JSON.stringify(orig)) {
    if (!confirm('放弃对本题的修改？')) return
  }
  const { [index]: _, ...rest } = questionEditDrafts.value
  questionEditDrafts.value = rest
}

/** 关闭记录预览：只保留左侧记录 +「生成新试题」，不再展示右侧试题预览 */
function closePreviewFromRecord() {
  if (hasUnsavedQuestionEdits.value) {
    if (!confirm('尚有未保存的题目修改，关闭预览后将无法恢复。确定关闭？')) return
  }
  sidebarCollapsed.value = false
  startNewPaper()
}

async function fetchSavedPapersList() {
  if (!getToken()) {
    savedPapers.value = []
    return
  }
  savedListLoading.value = true
  try {
    const data = await apiRequest('/api/v1/question-papers')
    savedPapers.value = Array.isArray(data.items) ? data.items : []
  } catch (e) {
    console.error(e)
    savedPapers.value = []
  } finally {
    savedListLoading.value = false
  }
}

onMounted(() => {
  fetchSavedPapersList()
})

function formatSavedTime(iso) {
  if (!iso) return ''
  const date = new Date(iso)
  const now = new Date()
  const diffMs = now - date
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))
  if (diffDays === 0) {
    return `今天 ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
  }
  if (diffDays === 1) return '昨天'
  return `${date.getMonth() + 1}月${date.getDate()}日`
}

function startNewPaper() {
  clearQuestionEditDrafts()
  activeSavedId.value = null
  hasGenerated.value = false
  questions.value = []
  errorMsg.value = ''
  hideGenerateCard.value = false
}

async function loadSavedPaper(p) {
  if (!p?.id || !getToken()) return
  if (hasUnsavedQuestionEdits.value) {
    if (!confirm('尚有未保存的题目修改，加载其他试卷后将丢失。确定继续？')) return
  }
  errorMsg.value = ''
  try {
    const data = await apiRequest(`/api/v1/question-papers/${p.id}`)
    const qs = data.questions
    if (!Array.isArray(qs) || !qs.length) return
    clearQuestionEditDrafts()
    activeSavedId.value = p.id
    questions.value = JSON.parse(JSON.stringify(qs))
    hasGenerated.value = true
    form.value.subject = data.subject || form.value.subject
    if (data.difficulty) form.value.difficulty = data.difficulty
    hideGenerateCard.value = true
  } catch (e) {
    errorMsg.value = e.message || '加载试卷失败'
  }
}

async function deleteSavedPaper(p) {
  if (!getToken()) {
    errorMsg.value = '请先登录后再管理试题记录'
    return
  }
  if (!confirm(`确定删除「${p.title}」？`)) return
  try {
    await apiRequest(`/api/v1/question-papers/${p.id}`, { method: 'DELETE' })
    if (activeSavedId.value === p.id) startNewPaper()
    await fetchSavedPapersList()
  } catch (e) {
    errorMsg.value = e.message || '删除失败'
  }
}

function openSaveModal() {
  errorMsg.value = ''
  if (!getToken()) {
    errorMsg.value = '请先登录后再保存试卷'
    return
  }
  if (hasUnsavedQuestionEdits.value) {
    errorMsg.value = '尚有题目处于编辑中未保存，请先点击该题上的「保存」或「取消」后再保存试卷'
    return
  }
  if (!hasGenerated.value || !questions.value.length) {
    errorMsg.value = '请先生成试题后再保存'
    return
  }
  saveModalTitle.value = `${form.value.subject || '试卷'} ${new Date().toLocaleString('zh-CN', { hour12: false })}`
  showSaveModal.value = true
}

function closeSaveModal() {
  showSaveModal.value = false
  saveModalSubmitting.value = false
}

async function confirmSavePaper() {
  const t = (saveModalTitle.value || '').trim()
  if (!t) {
    errorMsg.value = '请输入试卷名称'
    return
  }
  if (hasUnsavedQuestionEdits.value) {
    errorMsg.value = '尚有题目处于编辑中未保存，请先完成题目上的保存'
    return
  }
  saveModalSubmitting.value = true
  errorMsg.value = ''
  try {
    const payload = {
      title: t,
      subject: form.value.subject || '未命名学科',
      difficulty: form.value.difficulty,
      questions: JSON.parse(JSON.stringify(questions.value))
    }
    const data = await apiRequest('/api/v1/question-papers', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    const paper = data.paper
    if (paper?.id) activeSavedId.value = paper.id
    closeSaveModal()
    await fetchSavedPapersList()
  } catch (e) {
    errorMsg.value = e.message || '保存失败'
  } finally {
    saveModalSubmitting.value = false
  }
}

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
  hideGenerateCard.value = false
  if (hasUnsavedQuestionEdits.value) {
    if (!confirm('尚有未保存的题目修改，重新生成后将丢失。确定继续？')) return
  }
  clearQuestionEditDrafts()
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
  if (hasUnsavedQuestionEdits.value) {
    errorMsg.value = '请先完成题目编辑处的「保存」，再导出 PDF'
    return
  }
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
  <div class="question-page">
    <!-- 左侧：保存记录（风格对齐教案页历史侧栏） -->
    <div class="sidebar-outer">
      <Transition name="sidebar-slide">
        <aside v-if="!sidebarCollapsed" class="saved-sidebar">
          <div class="sidebar-header">
            <div class="sidebar-title-block">
              <div class="sidebar-title">试题记录</div>
              <p class="sidebar-title-desc">已登录后保存的试卷会同步到云端，点击可加载到右侧预览</p>
            </div>
            <button
              type="button"
              class="collapse-btn"
              title="收起侧栏"
              @click="sidebarCollapsed = true"
            >
              ‹
            </button>
          </div>
          <div class="history-list">
            <div v-if="savedListLoading" class="empty-state">加载中...</div>
            <template v-else-if="!getToken()">
              <div class="empty-state">登录后可保存并查看试题记录</div>
            </template>
            <template v-else-if="!savedPapers.length">
              <div class="empty-state">暂无已保存记录</div>
            </template>
            <template v-else>
              <div
                v-for="p in savedPapers"
                :key="p.id"
                class="history-item"
                :class="{ active: p.id === activeSavedId }"
                @click="loadSavedPaper(p)"
              >
                <div class="item-content">
                  <div class="history-title">{{ p.title }}</div>
                  <div class="history-meta">
                    {{ p.subject }} · {{ p.question_count ?? 0 }} 题 · {{ formatSavedTime(p.created_at) }}
                  </div>
                </div>
                <button
                  type="button"
                  class="delete-btn"
                  title="删除"
                  @click.stop="deleteSavedPaper(p)"
                >
                  ×
                </button>
              </div>
            </template>
          </div>
        </aside>
      </Transition>
      <button
        v-if="sidebarCollapsed"
        type="button"
        class="sidebar-expand"
        title="展开试题记录"
        @click="sidebarCollapsed = false"
      >
        ›
      </button>
    </div>

    <!-- 右侧主区：表单 + 预览 -->
    <div
      class="page-wrap"
      :class="{
        'with-preview': hasGenerated,
        'preview-from-record': hideGenerateCard && hasGenerated
      }"
    >
    <section v-show="!hideGenerateCard" class="config-card">
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
        <div class="preview-header-actions">
          <button
            v-if="hideGenerateCard"
            type="button"
            class="outline-btn"
            @click.stop="closePreviewFromRecord"
          >
            关闭预览
          </button>
          <button type="button" class="outline-btn" @click="openSaveModal">保存试卷</button>
        </div>
      </header>

      <div class="preview-body">
        <div
          v-for="(q, index) in questions"
          :key="index"
          class="question-block"
          :class="{ 'is-editing-card': questionEditDrafts[index] != null }"
        >
          <div class="question-block-toolbar">
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
                      : q.type === 'essay'
                        ? '论述题'
                        : '题目'
              }}
            </div>
            <div class="question-toolbar-actions">
              <template v-if="questionEditDrafts[index] == null">
                <button type="button" class="q-edit-btn q-edit-btn-edit" @click="startEditQuestion(index)">
                  <svg
                    class="q-edit-icon"
                    xmlns="http://www.w3.org/2000/svg"
                    width="15"
                    height="15"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2.2"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    aria-hidden="true"
                  >
                    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                  </svg>
                  编辑
                </button>
              </template>
              <template v-else>
                <button type="button" class="q-edit-btn q-edit-btn-primary" @click="saveEditQuestion(index)">
                  保存
                </button>
                <button type="button" class="q-edit-btn" @click="cancelEditQuestion(index)">
                  取消
                </button>
              </template>
            </div>
          </div>

          <!-- 只读预览 -->
          <template v-if="questionEditDrafts[index] == null">
            <p class="q-text">
              {{ q.stem }}
            </p>

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

            <div v-if="q.type === 'tf'" class="tf-wrap">
              <span class="tf-pill" :class="{ active: isTfTrue(q.answer) }">正确</span>
              <span class="tf-pill" :class="{ active: !isTfTrue(q.answer) }">错误</span>
              <span class="tf-answer">答案：{{ formatTfAnswer(q.answer) }}</span>
            </div>

            <div v-if="(q.type === 'sa' || q.type === 'essay') && (q.answer || q.analysis)" class="answer-hint">
              <div class="hint-title">参考答案与解析：</div>
              <div v-if="q.answer" class="hint-text">
                <div class="hint-k">答案</div>
                <div class="hint-v">{{ q.answer }}</div>
              </div>
              <div v-if="q.analysis" class="hint-text">
                <div class="hint-k">解析</div>
                <div class="hint-v">{{ q.analysis }}</div>
              </div>
            </div>

            <div
              v-if="q.type !== 'tf' && q.type !== 'mc' && q.type !== 'sa' && q.type !== 'essay' && (q.answer || q.analysis)"
              class="answer-hint"
            >
              <div class="hint-title">参考答案与解析：</div>
              <ul class="hint-list">
                <li v-if="q.answer">答案：{{ q.answer }}</li>
                <li v-if="q.analysis">解析：{{ q.analysis }}</li>
              </ul>
            </div>
          </template>

          <!-- 编辑表单 -->
          <template v-else>
            <div class="edit-fields">
              <label class="edit-label">题干</label>
              <textarea v-model="questionEditDrafts[index].stem" class="edit-textarea" rows="4" />

              <template v-if="questionEditDrafts[index].type === 'mc'">
                <label class="edit-label">选项（点选「设为答案」标为正确项）</label>
                <div
                  v-for="(opt, oi) in questionEditDrafts[index].options"
                  :key="oi"
                  class="edit-option-row"
                >
                  <span class="edit-opt-label">{{ opt.label }}.</span>
                  <input v-model="opt.text" type="text" class="edit-input" placeholder="选项内容" />
                  <label class="edit-radio">
                    <input
                      v-model="questionEditDrafts[index].answer"
                      type="radio"
                      class="edit-radio-input"
                      :name="'mc-ans-' + index"
                      :value="opt.label"
                    />
                    设为答案
                  </label>
                </div>
              </template>

              <template v-else-if="questionEditDrafts[index].type === 'tf'">
                <label class="edit-label">答案</label>
                <div class="tf-edit-row">
                  <button
                    type="button"
                    class="tf-edit-btn"
                    :class="{ active: isTfTrue(questionEditDrafts[index].answer) }"
                    @click="questionEditDrafts[index].answer = 'true'"
                  >
                    正确
                  </button>
                  <button
                    type="button"
                    class="tf-edit-btn"
                    :class="{ active: !isTfTrue(questionEditDrafts[index].answer) }"
                    @click="questionEditDrafts[index].answer = 'false'"
                  >
                    错误
                  </button>
                </div>
              </template>

              <template v-else-if="questionEditDrafts[index].type === 'sa' || questionEditDrafts[index].type === 'essay'">
                <label class="edit-label">参考答案</label>
                <textarea v-model="questionEditDrafts[index].answer" class="edit-textarea" rows="5" />
                <label class="edit-label">解析（可选）</label>
                <textarea v-model="questionEditDrafts[index].analysis" class="edit-textarea" rows="4" />
              </template>

              <template v-else>
                <label class="edit-label">参考答案</label>
                <textarea v-model="questionEditDrafts[index].answer" class="edit-textarea" rows="4" />
                <label class="edit-label">解析（可选）</label>
                <textarea v-model="questionEditDrafts[index].analysis" class="edit-textarea" rows="3" />
              </template>
            </div>
          </template>
        </div>
      </div>

      <footer class="preview-footer">
        <button type="button" class="outline-btn" @click="handleExportPdf">导出 PDF</button>
      </footer>
    </section>
    </div>

    <!-- 保存试卷：名称弹窗 -->
    <Teleport to="body">
      <div v-if="showSaveModal" class="save-modal-overlay" @click.self="closeSaveModal">
        <div class="save-modal-box" role="dialog" aria-modal="true" aria-labelledby="save-modal-title">
          <h3 id="save-modal-title" class="save-modal-heading">保存试卷</h3>
          <p class="save-modal-tip">将当前试题保存到您的账号，可在左侧「试题记录」中随时打开。</p>
          <label class="save-modal-label">试卷名称</label>
          <input
            v-model="saveModalTitle"
            type="text"
            class="save-modal-input"
            placeholder="例如：期中复习 · 高等数学"
            @keyup.enter="confirmSavePaper"
          />
          <div class="save-modal-actions">
            <button type="button" class="save-modal-btn ghost" :disabled="saveModalSubmitting" @click="closeSaveModal">
              取消
            </button>
            <button type="button" class="save-modal-btn primary" :disabled="saveModalSubmitting" @click="confirmSavePaper">
              {{ saveModalSubmitting ? '保存中...' : '保存' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.question-page {
  display: flex;
  flex: 1;
  min-height: 0;
  align-items: stretch;
  background: linear-gradient(180deg, #f3f8ff 0%, #f9fbff 100%);
}

.sidebar-outer {
  position: relative;
  flex-shrink: 0;
  z-index: 2;
  align-self: stretch;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.saved-sidebar {
  width: 248px;
  min-width: 248px;
  background: #fff;
  border-right: 1px solid #eaedf0;
  display: flex;
  flex-direction: column;
  padding: 16px 12px;
  flex: 1;
  min-height: 0;
  box-sizing: border-box;
}

.sidebar-header {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  align-items: flex-start;
}

.sidebar-title-block {
  flex: 1;
  min-width: 0;
  padding: 2px 4px 0 0;
}

.sidebar-title {
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.3;
}

.sidebar-title-desc {
  margin: 6px 0 0;
  font-size: 12px;
  color: #64748b;
  line-height: 1.45;
}

.collapse-btn {
  width: 36px;
  flex-shrink: 0;
  background: #f7f8fa;
  border: 1px solid #e0e3e8;
  border-radius: 8px;
  cursor: pointer;
  color: #999;
  font-size: 18px;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.collapse-btn:hover {
  color: #2563eb;
  border-color: #2563eb;
  background: #f0f5ff;
}

.history-list {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}

.empty-state {
  padding: 24px 8px;
  text-align: center;
  color: #94a3b8;
  font-size: 13px;
}

.history-item {
  position: relative;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 6px;
  padding: 10px 10px;
  border-radius: 8px;
  font-size: 13px;
  color: #334155;
  cursor: pointer;
  margin-bottom: 4px;
  transition: background 0.2s;
}

.history-item:hover {
  background: #f0f5ff;
}

.history-item.active {
  background: #e8f0fe;
  color: #1d4ed8;
}

.item-content {
  flex: 1;
  min-width: 0;
}

.history-title {
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.history-meta {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 4px;
  line-height: 1.35;
}

.history-item.active .history-meta {
  color: #64748b;
}

.delete-btn {
  opacity: 0;
  width: 24px;
  height: 24px;
  border: none;
  border-radius: 4px;
  background: #e0e7ff;
  color: #6366f1;
  font-size: 16px;
  line-height: 1;
  cursor: pointer;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  transition: opacity 0.15s;
}

.history-item:hover .delete-btn {
  opacity: 1;
}

.delete-btn:hover {
  background: #c7d2fe;
  color: #4f46e5;
}

.sidebar-expand {
  position: sticky;
  top: 16px;
  left: 0;
  width: 28px;
  height: 44px;
  margin: 16px 0 0 0;
  background: #fff;
  border: 1px solid #eaedf0;
  border-left: none;
  border-radius: 0 8px 8px 0;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #94a3b8;
  font-size: 14px;
  box-shadow: 2px 0 8px rgba(15, 23, 42, 0.06);
}

.sidebar-expand:hover {
  color: #2563eb;
  background: #f0f5ff;
}

.sidebar-slide-enter-active,
.sidebar-slide-leave-active {
  transition: transform 0.28s ease, opacity 0.28s ease;
}

.sidebar-slide-enter-from,
.sidebar-slide-leave-to {
  transform: translateX(-12px);
  opacity: 0;
}

.page-wrap {
  flex: 1;
  min-width: 0;
  min-height: 0;
  padding: 24px 32px 32px;
  display: flex;
  gap: 20px;
  align-items: stretch;
  justify-content: center;
  box-sizing: border-box;
}

.page-wrap.with-preview {
  justify-content: flex-start;
}

/* 从左侧记录打开预览时隐藏中间表单，预览区占满剩余宽度 */
.page-wrap.preview-from-record {
  justify-content: flex-start;
}

.page-wrap.preview-from-record .preview-card {
  flex: 1 1 auto;
  max-width: min(1000px, 100%);
  width: 100%;
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
  min-height: 0;
  flex: 1 1 auto;
}

.page-wrap.with-preview .config-card {
  width: auto;
  flex: 0 0 420px;
  max-width: 460px;
  align-self: stretch;
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
  min-height: 0;
  background: #ffffff;
  border-radius: 18px;
  padding: 20px 22px 24px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 16px 32px rgba(15, 23, 42, 0.12);
  display: flex;
  flex-direction: column;
  min-width: 0;
  align-self: stretch;
}

.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}

.preview-header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
  flex-wrap: wrap;
  justify-content: flex-end;
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
  position: relative;
  margin-bottom: 18px;
  padding: 12px 14px 14px;
  border-radius: 12px;
  background: #f9fafb;
}

.question-block.is-editing-card {
  background: #f0f7ff;
  border: 1px solid #bfdbfe;
}

.question-block-toolbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.question-block-toolbar .q-tag {
  margin-bottom: 0;
}

.question-toolbar-actions {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  gap: 8px;
}

.q-edit-btn {
  border-radius: 999px;
  border: 1px solid #e2e8f0;
  background: #ffffff;
  font-size: 12px;
  color: #475569;
  padding: 5px 12px;
  cursor: pointer;
  transition: all 0.15s;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
}

.q-edit-btn:hover {
  border-color: #2563eb;
  color: #2563eb;
}

/* 题目卡片上的「编辑」：更醒目（描边 + 浅蓝底 + 图标） */
.q-edit-btn-edit {
  font-size: 13px;
  font-weight: 700;
  padding: 8px 16px;
  color: #1d4ed8;
  background: linear-gradient(180deg, #f0f7ff 0%, #e0edff 100%);
  border: 2px solid #93c5fd;
  box-shadow: 0 1px 3px rgba(37, 99, 235, 0.18);
}

.q-edit-btn-edit:hover {
  color: #1e40af;
  background: linear-gradient(180deg, #e0edff 0%, #dbeafe 100%);
  border-color: #2563eb;
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.28);
}

.q-edit-icon {
  flex-shrink: 0;
  opacity: 0.95;
}

.q-edit-btn-primary {
  background: #2563eb;
  border-color: #2563eb;
  color: #ffffff;
}

.q-edit-btn-primary:hover {
  background: #1d4ed8;
  border-color: #1d4ed8;
  color: #ffffff;
}

.edit-fields {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.edit-label {
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
  margin-top: 4px;
}

.edit-textarea,
.edit-input {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 8px 10px;
  font-size: 14px;
  color: #111827;
  background: #fff;
  font-family: inherit;
}

.edit-textarea {
  resize: vertical;
  min-height: 72px;
}

.edit-option-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 6px;
}

.edit-opt-label {
  font-weight: 700;
  color: #1d4ed8;
  min-width: 22px;
}

.edit-option-row .edit-input {
  flex: 1 1 160px;
  min-width: 0;
}

.edit-radio {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #64748b;
  cursor: pointer;
  white-space: nowrap;
}

.edit-radio-input {
  margin: 0;
  cursor: pointer;
}

.tf-edit-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.tf-edit-btn {
  border-radius: 999px;
  border: 1px solid #e2e8f0;
  background: #ffffff;
  padding: 8px 18px;
  font-size: 13px;
  font-weight: 600;
  color: #4b5563;
  cursor: pointer;
}

.tf-edit-btn.active {
  background: #2563eb;
  border-color: #2563eb;
  color: #ffffff;
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

/* 保存试卷弹窗 */
.save-modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 2000;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.save-modal-box {
  width: 100%;
  max-width: 420px;
  background: #fff;
  border-radius: 16px;
  padding: 22px 24px 20px;
  box-shadow: 0 24px 48px rgba(15, 23, 42, 0.2);
  border: 1px solid #e2e8f0;
}

.save-modal-heading {
  margin: 0 0 8px;
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
}

.save-modal-tip {
  margin: 0 0 16px;
  font-size: 13px;
  color: #64748b;
  line-height: 1.5;
}

.save-modal-label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: #475569;
  margin-bottom: 6px;
}

.save-modal-input {
  width: 100%;
  box-sizing: border-box;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  font-size: 14px;
  outline: none;
  margin-bottom: 20px;
}

.save-modal-input:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);
}

.save-modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.save-modal-btn {
  padding: 9px 18px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  border: none;
}

.save-modal-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.save-modal-btn.ghost {
  background: #f1f5f9;
  color: #475569;
}

.save-modal-btn.primary {
  background: #2563eb;
  color: #fff;
}

@media (max-width: 900px) {
  .question-page {
    flex-direction: column;
  }

  .saved-sidebar {
    width: 100%;
    min-width: 0;
    min-height: auto;
    max-height: 40vh;
    border-right: none;
    border-bottom: 1px solid #eaedf0;
  }

  .sidebar-expand {
    position: fixed;
    top: 72px;
    left: 0;
    z-index: 20;
    margin: 0;
  }

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

