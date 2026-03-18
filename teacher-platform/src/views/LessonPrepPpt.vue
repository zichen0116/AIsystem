<script setup>
/**
 * LessonPrepPpt.vue - PPT生成主页面
 *
 * 作为 LessonPrep 的子tab，接入后端API实现完整PPT生成流程。
 * 阶段：欢迎页 -> 对话+大纲 -> 预览+编辑
 */
import { ref, onMounted } from 'vue'
import WelcomePanel from '../components/ppt/WelcomePanel.vue'
import ChatPanel from '../components/ppt/ChatPanel.vue'
import ChatInput from '../components/ppt/ChatInput.vue'
import OutlineCard from '../components/ppt/OutlineCard.vue'
import TemplateSelector from '../components/ppt/TemplateSelector.vue'
import KnowledgeLibraryModal from '../components/ppt/KnowledgeLibraryModal.vue'
import PptSidebar from '../components/ppt/PptSidebar.vue'
import PptThumbnailList from '../components/ppt/PptThumbnailList.vue'
import PptCanvas from '../components/ppt/PptCanvas.vue'
import {
  createSession, listSessions, getSessionDetail,
  approveOutline, getResultDetail, downloadResult,
  streamPptSSE,
} from '../api/ppt.js'

// ========== 状态 ==========
const stage = ref('welcome') // welcome | chat | preview
const sidebarCollapsed = ref(false)

// 会话
const sessions = ref([])
const currentSessionId = ref(null)
const currentSession = ref(null)

// 消息
const messages = ref([])
const userInput = ref('')
const isStreaming = ref(false)
const streamingText = ref('')
let abortController = null

// 大纲
const currentOutline = ref(null)
const showOutlineCard = ref(false)

// 模板 & 知识库
const selectedTemplateId = ref(null)
const selectedKnowledgeIds = ref([])
const showTemplateSelector = ref(false)
const showKnowledgeModal = ref(false)

// PPT结果
const currentResult = ref(null)
const pptxProperty = ref('')
const slides = ref([])
const activeSlideIndex = ref(0)
const isGeneratingPpt = ref(false)
const genCurrentPage = ref(0)
const genTotalPages = ref(0)

// ========== 生命周期 ==========
onMounted(async () => {
  try {
    sessions.value = await listSessions()
  } catch { /* ignore */ }
})

// ========== 会话管理 ==========
async function handleNewSession() {
  try {
    const s = await createSession()
    sessions.value.unshift(s)
    currentSessionId.value = s.id
    currentSession.value = s
    resetState()
    stage.value = 'welcome'
  } catch (e) {
    console.error('创建会话失败:', e)
  }
}

async function handleSelectSession(id) {
  currentSessionId.value = id
  try {
    const detail = await getSessionDetail(id)
    currentSession.value = detail
    messages.value = detail.messages || []

    const currentOl = detail.outlines?.find(o => o.is_current)
    currentOutline.value = currentOl || null
    showOutlineCard.value = !!currentOl

    const currentRes = detail.results?.find(r => r.is_current)
    currentResult.value = currentRes || null

    if (currentRes && currentRes.status === 'completed') {
      stage.value = 'preview'
      await loadResultDetail(currentRes.id)
    } else if (currentOl) {
      stage.value = 'chat'
    } else {
      stage.value = 'welcome'
    }
  } catch (e) {
    console.error('加载会话失败:', e)
  }
}

function resetState() {
  messages.value = []
  userInput.value = ''
  streamingText.value = ''
  currentOutline.value = null
  showOutlineCard.value = false
  currentResult.value = null
  pptxProperty.value = ''
  slides.value = []
  activeSlideIndex.value = 0
}

// ========== 发送消息 ==========
async function handleSend() {
  const text = userInput.value.trim()
  if (!text || isStreaming.value) return

  // 确保有会话
  if (!currentSessionId.value) {
    await handleNewSession()
  }

  stage.value = 'chat'
  messages.value.push({ role: 'user', message_type: 'text', content: text })
  userInput.value = ''

  // 如果已有大纲，走修改流程
  if (currentOutline.value) {
    await streamModifyOutline(text)
  } else {
    await streamGenerateOutline(text)
  }
}

function handlePreset(presetText) {
  userInput.value = presetText
  handleSend()
}

// ========== 流式生成大纲 ==========
async function streamGenerateOutline(text) {
  isStreaming.value = true
  streamingText.value = ''
  abortController = new AbortController()

  try {
    await streamPptSSE(
      '/api/v1/ppt/stream/outline',
      {
        session_id: currentSessionId.value,
        user_input: text,
        knowledge_library_ids: selectedKnowledgeIds.value,
        template_id: selectedTemplateId.value,
      },
      {
        onChunk(content) { streamingText.value += content },
        onOutlineReady(data) {
          currentOutline.value = {
            id: data.outline_id,
            content: data.content,
            image_urls: data.image_urls || {},
            is_current: true,
          }
          showOutlineCard.value = true
          messages.value.push({
            role: 'assistant', message_type: 'outline',
            content: data.content,
          })
          streamingText.value = ''
        },
        onDone() {},
        onError(msg) {
          messages.value.push({ role: 'assistant', message_type: 'error', content: msg })
        },
      },
      abortController.signal,
    )
  } catch (e) {
    if (e.name !== 'AbortError') {
      messages.value.push({ role: 'assistant', message_type: 'error', content: e.message })
    }
  } finally {
    isStreaming.value = false
    abortController = null
  }
}

// ========== 流式修改大纲 ==========
async function streamModifyOutline(text) {
  if (!currentResult.value) {
    // 还没生成PPT，走大纲修改
    isStreaming.value = true
    streamingText.value = ''
    showOutlineCard.value = false
    abortController = new AbortController()

    try {
      await streamPptSSE(
        '/api/v1/ppt/stream/outline',
        {
          session_id: currentSessionId.value,
          user_input: text,
          knowledge_library_ids: selectedKnowledgeIds.value,
          template_id: selectedTemplateId.value,
        },
        {
          onChunk(content) { streamingText.value += content },
          onOutlineReady(data) {
            currentOutline.value = {
              id: data.outline_id,
              content: data.content,
              image_urls: data.image_urls || {},
              is_current: true,
            }
            showOutlineCard.value = true
            messages.value.push({
              role: 'assistant', message_type: 'outline',
              content: data.content,
            })
            streamingText.value = ''
          },
          onDone() {},
          onError(msg) {
            messages.value.push({ role: 'assistant', message_type: 'error', content: msg })
          },
        },
        abortController.signal,
      )
    } catch (e) {
      if (e.name !== 'AbortError') {
        messages.value.push({ role: 'assistant', message_type: 'error', content: e.message })
      }
    } finally {
      isStreaming.value = false
      abortController = null
    }
    return
  }

  // 已有PPT结果，走修改流程
  await streamModifyPpt(text)
}

// ========== 审批大纲 -> 生成PPT ==========
async function handleApproveOutline(payload) {
  if (!currentOutline.value) return

  try {
    await approveOutline(
      currentOutline.value.id,
      payload?.content || null,
      payload?.image_urls || null,
    )

    if (!selectedTemplateId.value) {
      showTemplateSelector.value = true
      return
    }

    await streamGeneratePpt()
  } catch (e) {
    console.error('审批失败:', e)
  }
}

function handleTemplateSelected(t) {
  selectedTemplateId.value = t.id
  showTemplateSelector.value = false
  if (currentOutline.value) {
    streamGeneratePpt()
  }
}

// ========== 流式生成PPT ==========
async function streamGeneratePpt() {
  isGeneratingPpt.value = true
  stage.value = 'preview'
  abortController = new AbortController()

  try {
    await streamPptSSE(
      '/api/v1/ppt/stream/generate',
      {
        session_id: currentSessionId.value,
        outline_id: currentOutline.value.id,
        template_id: selectedTemplateId.value,
      },
      {
        onProgress(data) {
          genCurrentPage.value = data.current || 0
          genTotalPages.value = data.total || 0
        },
        onResultReady(data) {
          currentResult.value = data
          pptxProperty.value = data.pptx_property || ''
          genTotalPages.value = data.total_pages || 0
          genCurrentPage.value = data.total_pages || 0
          isGeneratingPpt.value = false
          messages.value.push({
            role: 'assistant', message_type: 'ppt_result',
            content: `PPT已生成完成，共${data.total_pages}页`,
          })
        },
        onDone() { isGeneratingPpt.value = false },
        onError(msg) {
          isGeneratingPpt.value = false
          messages.value.push({ role: 'assistant', message_type: 'error', content: msg })
        },
      },
      abortController.signal,
    )
  } catch (e) {
    isGeneratingPpt.value = false
    if (e.name !== 'AbortError') {
      messages.value.push({ role: 'assistant', message_type: 'error', content: e.message })
    }
  } finally {
    abortController = null
  }
}

// ========== 继续修改 ==========
function handleModify() {
  stage.value = 'chat'
}

async function handleModifySend() {
  const text = userInput.value.trim()
  if (!text || isStreaming.value) return
  messages.value.push({ role: 'user', message_type: 'text', content: text })
  userInput.value = ''
  await streamModifyPpt(text)
}

async function streamModifyPpt(text) {
  if (!currentResult.value?.result_id) return
  isStreaming.value = true
  streamingText.value = ''
  abortController = new AbortController()

  try {
    await streamPptSSE(
      `/api/v1/ppt/results/${currentResult.value.result_id}/modify`,
      { instruction: text },
      {
        onChunk(content) { streamingText.value += content },
        onOutlineReady(data) {
          currentOutline.value = {
            id: data.outline_id,
            content: data.content,
            image_urls: data.image_urls || {},
            is_current: true,
          }
          showOutlineCard.value = true
          messages.value.push({
            role: 'assistant', message_type: 'outline',
            content: '大纲已更新，点击确认后重新生成PPT',
          })
          streamingText.value = ''
        },
        onDone() {},
        onError(msg) {
          messages.value.push({ role: 'assistant', message_type: 'error', content: msg })
        },
      },
      abortController.signal,
    )
  } catch (e) {
    if (e.name !== 'AbortError') {
      messages.value.push({ role: 'assistant', message_type: 'error', content: e.message })
    }
  } finally {
    isStreaming.value = false
    abortController = null
  }
}

// ========== 下载 ==========
async function handleDownload() {
  if (!currentResult.value?.result_id) return
  try {
    const data = await downloadResult(currentResult.value.result_id)
    if (data.file_url) {
      window.open(data.file_url, '_blank')
    }
  } catch (e) {
    console.error('下载失败:', e)
  }
}

// ========== 加载结果详情 ==========
async function loadResultDetail(resultId) {
  try {
    const detail = await getResultDetail(resultId)
    pptxProperty.value = detail.source_pptx_property || detail.edited_pptx_property || ''
    genTotalPages.value = detail.total_pages || 0
  } catch (e) {
    console.error('加载结果失败:', e)
  }
}
</script>

<template>
  <div class="ppt-page">
    <!-- 侧边栏 -->
    <PptSidebar
      :sessions="sessions"
      :active-id="currentSessionId"
      :collapsed="sidebarCollapsed"
      @new-session="handleNewSession"
      @select="handleSelectSession"
      @toggle="sidebarCollapsed = !sidebarCollapsed"
    />

    <!-- 主区域 -->
    <div class="ppt-main">
      <!-- Stage 1: 欢迎页 -->
      <template v-if="stage === 'welcome'">
        <WelcomePanel
          v-model="userInput"
          @send="handleSend"
          @select-preset="handlePreset"
          @open-templates="showTemplateSelector = true"
          @open-knowledge="showKnowledgeModal = true"
        />
      </template>

      <!-- Stage 2: 对话+大纲 -->
      <template v-else-if="stage === 'chat'">
        <div class="chat-layout">
          <div class="chat-left">
            <ChatPanel
              :messages="messages"
              :streaming-text="streamingText"
              :is-streaming="isStreaming"
            />

            <!-- 大纲卡片 -->
            <OutlineCard
              v-if="currentOutline && showOutlineCard"
              :outline="currentOutline"
              :show-approve="!currentResult"
              @approve="handleApproveOutline"
            />

            <ChatInput
              v-model="userInput"
              :disabled="isStreaming"
              :loading="isStreaming"
              :placeholder="currentOutline ? '输入修改意见...' : '描述你的PPT主题...'"
              @send="handleSend"
            />
          </div>

          <!-- 模板选择面板 -->
          <div v-if="showTemplateSelector" class="chat-right">
            <TemplateSelector
              v-model="selectedTemplateId"
              @select="handleTemplateSelected"
              @close="showTemplateSelector = false"
            />
          </div>
        </div>
      </template>

      <!-- Stage 3: 预览+编辑 -->
      <template v-else-if="stage === 'preview'">
        <div class="preview-layout">
          <div class="preview-thumbnails">
            <PptThumbnailList
              :slides="slides"
              :active-index="activeSlideIndex"
              @select="activeSlideIndex = $event"
            />
          </div>
          <div class="preview-center">
            <div class="preview-toolbar">
              <span class="preview-title">{{ currentSession?.title || 'PPT预览' }}</span>
              <div class="preview-actions">
                <button class="action-btn" @click="handleModify">继续修改</button>
                <button class="action-btn primary" @click="handleDownload">下载PPT</button>
              </div>
            </div>
            <PptCanvas
              :pptx-property="pptxProperty"
              :slide-index="activeSlideIndex"
              :generating="isGeneratingPpt"
              :current-page="genCurrentPage"
              :total-pages="genTotalPages"
            />
          </div>
          <!-- 右侧对话面板 -->
          <div class="preview-chat">
            <ChatPanel
              :messages="messages"
              :streaming-text="streamingText"
              :is-streaming="isStreaming"
            />
            <ChatInput
              v-model="userInput"
              :disabled="isStreaming"
              :loading="isStreaming"
              placeholder="输入修改意见..."
              @send="handleModifySend"
            />
          </div>
        </div>
      </template>
    </div>

    <!-- 知识库弹窗 -->
    <KnowledgeLibraryModal
      v-if="showKnowledgeModal"
      v-model="selectedKnowledgeIds"
      @close="showKnowledgeModal = false"
    />
  </div>
</template>

<style scoped>
.ppt-page {
  display: flex;
  height: 100%;
  background: #f5f7fa;
}
.ppt-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

/* Chat layout */
.chat-layout {
  flex: 1;
  display: flex;
  min-height: 0;
}
.chat-left {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  padding: 20px;
  gap: 16px;
}
.chat-right {
  width: 360px;
  border-left: 1px solid #e5e5e5;
  background: #fff;
  flex-shrink: 0;
}

/* Preview layout */
.preview-layout {
  flex: 1;
  display: flex;
  min-height: 0;
}
.preview-thumbnails {
  width: 160px;
  border-right: 1px solid #e5e5e5;
  background: #fff;
  overflow-y: auto;
  flex-shrink: 0;
}
.preview-center {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.preview-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  background: #fff;
  border-bottom: 1px solid #e5e5e5;
}
.preview-title {
  font-size: 15px;
  font-weight: 600;
  color: #333;
}
.preview-actions {
  display: flex;
  gap: 10px;
}
.action-btn {
  padding: 8px 18px;
  border: 1px solid #ddd;
  background: #fff;
  border-radius: 8px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;
}
.action-btn:hover { background: #f5f5f5; }
.action-btn.primary {
  background: #3a61ea;
  color: #fff;
  border-color: #3a61ea;
}
.action-btn.primary:hover { background: #2a4bcc; }
.preview-chat {
  width: 340px;
  border-left: 1px solid #e5e5e5;
  background: #fff;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  padding: 12px;
  gap: 10px;
}

@media (max-width: 900px) {
  .preview-layout { flex-direction: column; }
  .preview-thumbnails { width: 100%; height: 80px; flex-direction: row; overflow-x: auto; }
  .preview-chat { width: 100%; height: 200px; }
}
</style>