<script setup>
import { ref, computed, onMounted, nextTick, reactive } from 'vue'
import { usePptStore } from '@/stores/ppt'
import { chat, getSessions } from '@/api/ppt'

const pptStore = usePptStore()

const userMessage = ref('')
const isSending = ref(false)
const isGenerating = ref(false)
const isRecording = ref(false)
const messagesContainer = ref(null)
let recognition = null

// State matching the prototype
const state = reactive({
  round: 0,
  confidence: 36,
  readyForConfirmation: false,
  intentConfirmed: false,
  confirmed: [],
  pending: [
    '受众基础层次',
    '核心教学目标',
    '课时与目标页数',
    '互动与约束条件'
  ],
  scores: {
    goal: 32,
    audience: 38,
    structure: 30,
    interaction: 26
  },
  snapshots: [],
  intentSummary: {}
})

// Context from store and dynamic intent
const context = computed(() => {
  // 优先用 state.intentSummary（确认后从 confirmedIntent 恢复的），其次用 pptStore.confirmedIntent
  const summary = state.intentSummary && Object.keys(state.intentSummary).length > 0
    ? state.intentSummary
    : (pptStore.confirmedIntent || {})
  return {
    template: pptStore.selectedPresetTemplateId || '未选择',
    topic: summary.topic || pptStore.outlineText?.slice(0, 20) || '待输入',
    duration: summary.duration || '待确认',
    pages: summary.constraints?.includes('页') ? summary.constraints : (summary.pages || '待确认')
  }
})

// Messages
const messages = ref([
  {
    role: 'ai',
    content: '太好了，收到你的主题了！为了把这个 PPT 做得真正适合你的课堂，我来和你聊几个小问题，不用紧张，我们慢慢来 :\n\n1. 学生情况：方便说说你的学生是哪个年级/什么专业吗？他们对这个主题大概了解多少？\n2. 课时安排：这节课大概多长时间呀？页数上有没有什么想法？\n3. 教学风格：你喜欢偏严谨一点的风格，还是轻松活泼一些的呢？'
  }
])

const canSend = computed(() => userMessage.value.trim().length > 0 && !isSending.value)

// Flow steps
const flowSteps = [
  { step: 1, label: '模板与主题已锁定', desc: '从首页透传上下文' },
  { step: 2, label: '教学意图反复澄清', desc: '目标、受众、边界对齐' },
  { step: 3, label: '确认意图进入大纲', desc: '整理意图后跳转大纲页' },
  { step: 4, label: '大纲页/描述页/预览页', desc: '生成PPT内容' }
]

const currentFlowStep = computed(() => {
  if (state.intentConfirmed) return 3
  return 2
})

const phaseText = computed(() => {
  if (state.intentConfirmed) return '已确认'
  return '澄清中'
})

const chatStatus = computed(() => {
  if (state.intentConfirmed) return '意图已确认，准备进入大纲页'
  if (state.readyForConfirmation) return '意图已澄清，请确认或继续补充'
  return '正在进行意图澄清'
})

const generateBlockReason = computed(() => {
  if (state.intentConfirmed) return ''
  if (!state.pending.length) return '当前仍在澄清阶段，请继续补充教学意图后再确认意图。'
  return `请继续完善：${state.pending.join('、')}。`
})

const confirmBtnDisabled = computed(() => {
  if (isGenerating.value) return true
  if (state.intentConfirmed) return false
  // 直接绑定 pending.length，不仅依赖 readyForConfirmation
  if (state.pending.length > 0) return true
  if (!state.readyForConfirmation) return true
  return false
})

const confirmBtnText = computed(() => {
  if (isGenerating.value) return '确认中...'
  if (state.intentConfirmed) return '返回大纲页 →'
  return '确认意图，进入大纲页'
})

function nowText() {
  return new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function showToast(text) {
  // Simple alert for now, could be replaced with a toast component
  console.log(text)
}

function pushSnapshot(text) {
  state.snapshots.unshift(text)
  if (state.snapshots.length > 4) state.snapshots = state.snapshots.slice(0, 4)
}

function formatTime(value) {
  if (!value) return nowText()
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return nowText()
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function applyIntentState(intentState, pushSummary = true) {
  if (!intentState || typeof intentState !== 'object') return

  if (Array.isArray(intentState.confirmed)) {
    const newConfirmed = intentState.confirmed.filter(item => typeof item === 'string' && item.trim())
    const existingSet = new Set(state.confirmed)
    newConfirmed.forEach(item => existingSet.add(item))
    state.confirmed = [...existingSet]
  }

  if (Array.isArray(intentState.pending)) {
    state.pending = intentState.pending.filter(item => typeof item === 'string' && item.trim())
  }

  if (intentState.scores && typeof intentState.scores === 'object') {
    state.scores.goal = Number.isFinite(intentState.scores.goal) ? Math.max(0, Math.min(100, Number(intentState.scores.goal))) : state.scores.goal
    state.scores.audience = Number.isFinite(intentState.scores.audience) ? Math.max(0, Math.min(100, Number(intentState.scores.audience))) : state.scores.audience
    state.scores.structure = Number.isFinite(intentState.scores.structure) ? Math.max(0, Math.min(100, Number(intentState.scores.structure))) : state.scores.structure
    state.scores.interaction = Number.isFinite(intentState.scores.interaction) ? Math.max(0, Math.min(100, Number(intentState.scores.interaction))) : state.scores.interaction
  }

  if (Number.isFinite(intentState.confidence)) {
    state.confidence = Math.max(0, Math.min(100, Number(intentState.confidence)))
  }

  state.readyForConfirmation = Boolean(intentState.ready_for_confirmation)

  // 保存意图摘要 - 仅在ready_for_confirmation=true时才应用（用户确认后的最终摘要）
  if (intentState.ready_for_confirmation && intentState.intent_summary && typeof intentState.intent_summary === 'object') {
    state.intentSummary = intentState.intent_summary
  }

  if (pushSummary && typeof intentState.summary === 'string' && intentState.summary.trim()) {
    pushSnapshot(`第${state.round || 1}轮：${intentState.summary.trim()}`)
  }
}

async function sendMessage() {
  if (!canSend.value) return

  const text = userMessage.value.trim()
  messages.value.push({
    role: 'user',
    content: text,
    time: nowText()
  })
  userMessage.value = ''
  isSending.value = true

  await nextTick()
  scrollToBottom()

  try {
    if (!pptStore.projectId) {
      throw new Error('项目未创建，请返回首页重新开始。')
    }

    const response = await chat(pptStore.projectId, text)
    state.round = Number.isFinite(response?.round) ? Number(response.round) : (state.round + 1)

    if (response?.intent_state) {
      applyIntentState(response.intent_state)
    }

    // 保存意图摘要
    if (response?.intent_summary && typeof response.intent_summary === 'object') {
      state.intentSummary = response.intent_summary
    }

    const reply = response?.message || '我已收到，让我们继续完善教学意图。'

    messages.value.push({
      role: 'ai',
      content: reply,
      time: nowText()
    })
  } catch (error) {
    console.error('对话失败:', error)
    messages.value.push({
      role: 'ai',
      content: '当前与教学智能体连接失败，我先记录你的意图。你可以继续补充，稍后重试。',
      time: nowText()
    })
  } finally {
    isSending.value = false
    await nextTick()
    scrollToBottom()
  }
}

function scrollToBottom() {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

async function confirmIntentAndGo() {
  if (!pptStore.projectId) {
    showToast('项目未创建，请返回首页重新开始。')
    return
  }

  // 已确认过意图，直接跳转大纲页
  if (state.intentConfirmed) {
    pptStore.setPhase('outline')
    return
  }

  isGenerating.value = true

  try {
    await pptStore.confirmIntent(pptStore.projectId)
    state.intentConfirmed = true
    state.readyForConfirmation = true
    state.pending = []
    state.confidence = Math.max(state.confidence, 95)
    pushSnapshot('系统：意图已确认，准备进入大纲页。')

    messages.value.push({
      role: 'ai',
      content: '太棒了！教学意图已确认，我们准备进入大纲页，系统会根据你确认的意图生成大纲。',
      time: nowText()
    })

    setTimeout(() => {
      pptStore.setPhase('outline')
    }, 800)
  } catch (error) {
    console.error('确认意图失败:', error)
    messages.value.push({
      role: 'ai',
      content: '确认意图时出现错误，请稍后重试。',
      time: nowText()
    })
  }

  isGenerating.value = false
  await nextTick()
  scrollToBottom()
}

function goToOutline() {
  pptStore.setPhase('outline')
}

function goBack() {
  pptStore.setPhase('home')
}

function fillQuickAction(text) {
  userMessage.value = text
}

// 语音输入
function toggleVoiceInput() {
  if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
    alert('当前浏览器不支持语音输入，请使用 Chrome 或 Edge')
    return
  }
  if (isRecording.value) {
    recognition?.stop()
    return
  }
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
  recognition = new SpeechRecognition()
  recognition.lang = 'zh-CN'
  recognition.continuous = true
  recognition.interimResults = false
  recognition.onresult = (event) => {
    const transcript = event.results[event.results.length - 1][0].transcript
    userMessage.value += transcript
  }
  recognition.onend = () => {
    isRecording.value = false
  }
  recognition.onerror = () => {
    isRecording.value = false
  }
  recognition.start()
  isRecording.value = true
}

function addAudience() {
  userMessage.value = '受众补充：高一学生，理解基础概念，但缺乏完整发展脉络。'
}

function addGoal() {
  userMessage.value = '教学目标：学生能复述AI发展的三个阶段，并说明两个真实应用案例。'
}

function addConstraint() {
  userMessage.value = '约束条件：总页数不超过10页，语言通俗，避免复杂数学推导，保留课堂复盘页。'
}

onMounted(async () => {
  if (!pptStore.projectId) return

  try {
    // 优先从 confirmedIntent 恢复
    if (pptStore.confirmedIntent && Object.keys(pptStore.confirmedIntent).length > 0) {
      state.intentSummary = pptStore.confirmedIntent
      state.intentConfirmed = true
      state.readyForConfirmation = true
      state.confidence = Math.max(state.confidence, 95)
      state.pending = []
    }

    const sessions = await getSessions(pptStore.projectId)
    if (!Array.isArray(sessions) || sessions.length === 0) return

    messages.value = sessions.map((session) => ({
      role: session.role === 'assistant' ? 'ai' : 'user',
      content: session.content,
      time: formatTime(session.created_at)
    }))

    state.round = sessions.reduce((maxRound, session) => Math.max(maxRound, Number(session.round) || 0), 0)

    // 从所有历史 sessions 累积恢复 confirmed
    if (!pptStore.confirmedIntent || Object.keys(pptStore.confirmedIntent).length === 0) {
      const allConfirmed = new Set()
      let latestIntentState = null

      for (const session of sessions) {
        if (session.role === 'assistant' && session.metadata?.intent_state) {
          latestIntentState = session.metadata.intent_state
          const confirmed = latestIntentState.confirmed || []
          confirmed.forEach(item => {
            if (typeof item === 'string' && item.trim()) allConfirmed.add(item)
          })
        }
      }

      if (latestIntentState) {
        applyIntentState(latestIntentState, false)
        state.confirmed = [...allConfirmed]
      }
    }

    await nextTick()
    scrollToBottom()
  } catch (error) {
    console.error('加载对话历史失败:', error)
  }
})

// Draft content (now shows intent summary)
const draftContent = computed(() => {
  const summary = state.intentSummary
  if (!summary || Object.keys(summary).length === 0) {
    return state.readyForConfirmation
      ? '意图已初步澄清，请在右侧确认或继续补充。'
      : '请与教学智能体继续交流，完善教学意图。'
  }

  const parts = []
  if (summary.topic) parts.push(`主题：${summary.topic}`)
  if (summary.audience) parts.push(`受众：${summary.audience}`)
  if (summary.goal) parts.push(`目标：${summary.goal}`)
  if (summary.duration) parts.push(`课时：${summary.duration}`)
  if (summary.style) parts.push(`风格：${summary.style}`)
  if (summary.interaction) parts.push(`互动：${summary.interaction}`)
  if (summary.constraints) parts.push(`约束：${summary.constraints}`)
  if (summary.extra) parts.push(`其他：${summary.extra}`)

  return parts.join('\n\n')
})
</script>

<template>
  <div class="ppt-dialog">
    <!-- Top Bar -->
    <header class="topbar">
      <div class="identity">
        <button class="back-btn" @click="goBack" title="返回首页">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
            <polyline points="15 18 9 12 15 6"/>
          </svg>
          返回
        </button>
        <h1>教学意图澄清工作台</h1>
        <p>将零散想法整理成可执行教学意图</p>
      </div>

      <div class="session-metrics">
        <div class="metric">
          <div class="metric-label">澄清轮次</div>
          <div class="metric-value">{{ state.round }}</div>
        </div>
        <div class="metric">
          <div class="metric-label">意图置信度</div>
          <div class="metric-value">{{ state.confidence }}%</div>
        </div>
        <div class="metric">
          <div class="metric-label">当前阶段</div>
          <div class="metric-value">{{ phaseText }}</div>
        </div>
      </div>
    </header>

    <!-- Flow Strip -->
    <section class="flow-strip">
      <div
        v-for="item in flowSteps"
        :key="item.step"
        class="flow-step"
        :class="{
          done: currentFlowStep > item.step,
          active: currentFlowStep === item.step
        }"
      >
        <span class="flow-index">{{ item.step }}</span>
        <div>
          <div class="flow-label">{{ item.label }}</div>
          <div class="flow-desc">{{ item.desc }}</div>
        </div>
      </div>
    </section>

    <!-- Main Grid -->
    <section class="main-grid">
      <!-- Left: Dialogue Panel -->
      <section class="panel dialogue-panel">
        <header class="panel-head">
          <div class="panel-title">
            <i></i>
            教学智能体对话区
          </div>
          <span class="status-chip">{{ chatStatus }}</span>
        </header>

        <div class="context-ribbon">
          <div class="context-item">
            <span>模板</span>
            <b>{{ context.template }}</b>
          </div>
          <div class="context-item">
            <span>主题</span>
            <b>{{ context.topic }}</b>
          </div>
          <div class="context-item">
            <span>课时长度</span>
            <b>{{ context.duration }}</b>
          </div>
          <div class="context-item">
            <span>目标页数</span>
            <b>{{ context.pages }}</b>
          </div>
        </div>

        <!-- Messages -->
        <div ref="messagesContainer" class="messages">
          <div
            v-for="(msg, index) in messages"
            :key="index"
            class="message"
            :class="msg.role"
          >
            <div class="avatar">
              <svg v-if="msg.role === 'ai'" viewBox="0 0 24 24" aria-hidden="true">
                <rect x="5" y="7" width="14" height="11" rx="3"></rect>
                <path d="M12 4v3"></path>
                <circle cx="9" cy="12" r="1"></circle>
                <circle cx="15" cy="12" r="1"></circle>
              </svg>
              <svg v-else viewBox="0 0 24 24" aria-hidden="true">
                <circle cx="12" cy="8" r="3.5"></circle>
                <path d="M5 20c1.8-3.4 4.3-5 7-5s5.2 1.6 7 5"></path>
              </svg>
            </div>
            <div class="bubble-wrap">
              <div class="bubble">{{ msg.content }}</div>
              <span class="meta">{{ msg.time || '刚刚' }}</span>
            </div>
          </div>

          <!-- Typing indicator -->
          <div v-if="isSending" class="message ai">
            <div class="avatar">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <rect x="5" y="7" width="14" height="11" rx="3"></rect>
                <path d="M12 4v3"></path>
                <circle cx="9" cy="12" r="1"></circle>
                <circle cx="15" cy="12" r="1"></circle>
              </svg>
            </div>
            <div class="typing">
              <i></i>
              <i></i>
              <i></i>
            </div>
          </div>
        </div>

        <!-- Quick Actions -->
        <div class="quick-row">
          <button class="quick-btn" @click="fillQuickAction('受众是高一学生，知道AI概念但对发展阶段不清晰。')">补充受众背景</button>
          <button class="quick-btn" @click="fillQuickAction('教学目标是让学生讲清楚AI从规则系统到大模型的演进逻辑。')">明确学习目标</button>
          <button class="quick-btn" @click="fillQuickAction('希望课堂中有2次提问互动和1个生活案例讨论。')">设置互动频次</button>
          <button class="quick-btn" @click="fillQuickAction('页数控制在10页，表达通俗，不要复杂公式。')">添加约束条件</button>
        </div>

        <!-- Composer -->
        <div class="composer">
          <div class="input-shell">
            <textarea
              v-model="userMessage"
              class="message-input"
              placeholder="继续补充真实需求，例如：重点放在近十年大模型发展，结尾给一个课堂小测与复盘页。"
              rows="1"
              @keydown.enter.exact.prevent="sendMessage"
            ></textarea>
            <div class="tool-row">
              <div class="tool-group">
                <button class="tool-btn" type="button" @click="addAudience">+ 受众设定</button>
                <button class="tool-btn" type="button" @click="addGoal">+ 教学目标</button>
                <button class="tool-btn" type="button" @click="addConstraint">+ 页面约束</button>
                <button class="tool-btn" type="button" :class="{ recording: isRecording }" @click="toggleVoiceInput">
                  {{ isRecording ? '🎙️ 录音中...' : '🎙️ 语音输入' }}
                </button>
              </div>
              <div class="composer-right">
                <span class="hint">Enter 发送，Shift+Enter 换行</span>
                <button class="send-btn" :disabled="!canSend" @click="sendMessage">发送</button>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Right: Insight Panel -->
      <aside class="panel insight-panel">
        <header class="panel-head">
          <div class="panel-title"><i></i>意图结构看板</div>
          <span class="status-chip">置信度 {{ state.confidence }}%</span>
        </header>

        <div class="insight-body">
          <!-- Intent Matrix -->
          <section class="card">
            <div class="card-title">
              教学意图矩阵
              <span class="chip">实时更新</span>
            </div>
            <div class="matrix">
              <div class="metric-row">
                <span>目标</span>
                <div class="bar"><div class="bar-fill" :style="{ width: state.scores.goal + '%' }"></div></div>
                <b>{{ state.scores.goal }}</b>
              </div>
              <div class="metric-row">
                <span>受众</span>
                <div class="bar"><div class="bar-fill" :style="{ width: state.scores.audience + '%' }"></div></div>
                <b>{{ state.scores.audience }}</b>
              </div>
              <div class="metric-row">
                <span>结构</span>
                <div class="bar"><div class="bar-fill" :style="{ width: state.scores.structure + '%' }"></div></div>
                <b>{{ state.scores.structure }}</b>
              </div>
              <div class="metric-row">
                <span>互动</span>
                <div class="bar"><div class="bar-fill" :style="{ width: state.scores.interaction + '%' }"></div></div>
                <b>{{ state.scores.interaction }}</b>
              </div>
            </div>
          </section>

          <!-- Confirmed List -->
          <section class="card">
            <div class="card-title">
              已确认诉求
              <span class="chip">{{ state.confirmed.length }} 项</span>
            </div>
            <ul class="intent-list">
              <li v-for="(item, idx) in state.confirmed" :key="idx">{{ item }}</li>
              <li v-if="state.confirmed.length === 0">暂无已确认项</li>
            </ul>
          </section>

          <!-- Pending List -->
          <section class="card">
            <div class="card-title">
              待确认要点
              <span class="chip">{{ state.pending.length }} 项</span>
            </div>
            <ul class="intent-list">
              <li v-for="(item, idx) in state.pending" :key="idx">{{ item }}</li>
              <li v-if="state.pending.length === 0">已无待确认要点，可直接生成初版大纲。</li>
            </ul>
          </section>

          <!-- Snapshots -->
          <section class="card">
            <div class="card-title">
              轮次摘要
              <span class="chip">最近 4 条</span>
            </div>
            <ul class="snapshot-list">
              <li v-for="(item, idx) in state.snapshots" :key="idx">{{ item }}</li>
              <li v-if="state.snapshots.length === 0">等待用户输入第一轮澄清信息。</li>
            </ul>
          </section>

          <!-- Draft Block -->
          <section class="draft-block">
            <div class="draft-title">意图摘要确认</div>
            <div class="draft-content">{{ draftContent }}</div>
          </section>

          <!-- Actions -->
          <div class="actions">
            <button class="btn secondary" :class="{ 'btn-confirmed': state.intentConfirmed }" :disabled="confirmBtnDisabled" @click="confirmIntentAndGo">
              {{ confirmBtnText }}
            </button>
            <p class="handoff-note">确认后系统将根据你的意图在大纲页生成 PPT 大纲，你仍可以在大纲页进行调整。</p>
            <p v-if="!state.readyForConfirmation && !state.intentConfirmed" class="handoff-warning">{{ generateBlockReason }}</p>
          </div>
        </div>
      </aside>
    </section>
  </div>
</template>

<style scoped>
.ppt-dialog {
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: 100%;
  padding: 16px 14px 24px;
  max-width: 1360px;
  margin: 0 auto;
  width: 100%;
  box-sizing: border-box;
}

.topbar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 10px;
  padding: 6px 2px 2px;
}

.identity h1 {
  font-size: clamp(1.28rem, 2.2vw, 1.78rem);
  line-height: 1.2;
  font-weight: 820;
  color: #1d2d3f;
  letter-spacing: -0.02em;
  margin: 0;
}

.identity p {
  font-size: 13px;
  color: #3f4f61;
  line-height: 1.5;
  max-width: 780px;
  margin: 4px 0 0;
}

.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: 1px solid #d5dfed;
  border-radius: 8px;
  background: #f8fbff;
  color: #3f5f82;
  font-size: 13px;
  font-weight: 600;
  padding: 6px 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
  margin-bottom: 4px;
}

.back-btn:hover {
  border-color: #3b82f6;
  background: #eef5ff;
  color: #1e3a8a;
  transform: translateX(-2px);
}

.session-metrics {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.metric {
  min-width: 108px;
  border: 1px solid #d5dfed;
  border-radius: 12px;
  background: #f8fbff;
  padding: 8px 10px;
  text-align: right;
}

.metric-label {
  font-size: 11px;
  color: #64748b;
}

.metric-value {
  font-size: 18px;
  font-weight: 800;
  line-height: 1.15;
  color: #2f4f7f;
  margin-top: 2px;
}

.flow-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.flow-step {
  position: relative;
  overflow: hidden;
  border: 1px solid #d5dfed;
  border-radius: 12px;
  background: #f8fbff;
  padding: 10px;
  display: flex;
  gap: 8px;
  min-height: 56px;
  transition: border-color 0.2s ease, transform 0.2s ease, box-shadow 0.2s ease;
}

.flow-step::after {
  content: "";
  position: absolute;
  inset: auto -30px -28px auto;
  width: 86px;
  height: 86px;
  border-radius: 50%;
  background: rgba(59, 130, 246, 0.08);
}

.flow-step.active {
  border-color: #93c5fd;
  box-shadow: inset 0 0 0 1px rgba(59, 130, 246, 0.2);
  transform: translateY(-1px);
}

.flow-step.done {
  border-color: #94a3b8;
  background: #f3f6f8;
}

.flow-index {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 800;
  border: 1px solid #c4d5e8;
  color: #4a617c;
  background: #fff;
  position: relative;
  z-index: 1;
}

.flow-step.active .flow-index {
  border-color: var(--accent);
  color: #fff;
  background: #3b82f6;
}

.flow-step.done .flow-index {
  border-color: #64748b;
  color: #fff;
  background: #64748b;
}

.flow-label {
  font-size: 12px;
  font-weight: 700;
  line-height: 1.2;
  color: #2c3b4d;
  position: relative;
  z-index: 1;
}

.flow-desc {
  font-size: 11px;
  color: #64748b;
  line-height: 1.2;
  margin-top: 2px;
  position: relative;
  z-index: 1;
}

.main-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 380px;
  gap: 12px;
  flex: 1;
  min-height: 0;
}

.panel {
  border: 1px solid #e5e7eb;
  border-radius: 20px;
  background: #ffffff;
  box-shadow: 0 10px 24px rgba(14, 34, 71, 0.08);
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.dialogue-panel {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-head {
  border-bottom: 1px solid #e4ecf6;
  padding: 12px 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  background: linear-gradient(120deg, #f4f8ff 0%, #eef5ff 100%);
}

.panel-title {
  font-size: 14px;
  font-weight: 800;
  color: #2a3d4e;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.panel-title i {
  width: 18px;
  height: 18px;
  border-radius: 6px;
  border: 1px solid #9ec2f2;
  background: linear-gradient(135deg, #e6f0ff 0%, #d8e9ff 100%);
}

.status-chip {
  font-size: 12px;
  color: #2f5f9a;
  border: 1px solid #aac7ed;
  border-radius: 999px;
  background: #edf4ff;
  padding: 4px 10px;
  white-space: nowrap;
}

.context-ribbon {
  padding: 10px 14px;
  border-bottom: 1px solid #e4ecf6;
  background: #f7faff;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.context-item {
  border: 1px solid #d6e1ef;
  border-radius: 10px;
  background: #fff;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.context-item span {
  font-size: 11px;
  color: #64748b;
}

.context-item b {
  font-size: 13px;
  color: #263c52;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.messages {
  padding: 12px 14px 0;
  flex: 1;
  min-height: 0;
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
  scroll-behavior: smooth;
  background: linear-gradient(180deg, rgba(244, 248, 255, 0.9) 0%, rgba(247, 251, 255, 0.98) 100%);
}

.message {
  width: min(88%, 740px);
  display: flex;
  gap: 9px;
  animation: rise 0.2s ease;
}

.message.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.avatar svg {
  width: 14px;
  height: 14px;
  stroke: currentColor;
  fill: none;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.message.ai .avatar {
  background: #e7f0ff;
  color: #285892;
  border: 1px solid #aec8ee;
}

.message.user .avatar {
  background: #21435f;
  color: #fff;
  border: 1px solid #173046;
}

.bubble-wrap {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.bubble {
  font-size: 14px;
  line-height: 1.58;
  padding: 10px 12px;
  border-radius: 12px;
  white-space: pre-wrap;
  word-break: break-word;
}

.message.ai .bubble {
  background: #ffffff;
  border: 1px solid #d4dfed;
  color: #2b3b4d;
  border-bottom-left-radius: 4px;
}

.message.user .bubble {
  background: #e8eef3;
  border: 1px solid #b8c9d8;
  color: #223547;
  border-bottom-right-radius: 4px;
}

.meta {
  font-size: 11px;
  color: #8a98a9;
  padding: 0 4px;
}

.typing {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: 1px solid #c7d9ef;
  border-radius: 10px;
  background: #f1f6ff;
  padding: 8px 10px;
  width: fit-content;
}

.typing i {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #5b8fd6;
  animation: pulse 1.1s ease-in-out infinite;
}

.typing i:nth-child(2) {
  animation-delay: 0.15s;
}

.typing i:nth-child(3) {
  animation-delay: 0.3s;
}

.quick-row {
  margin-top: 10px;
  padding: 0 14px 10px;
  border-bottom: 1px solid #e4ecf6;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.quick-btn {
  border: 1px solid #cfd9e6;
  border-radius: 999px;
  background: #f5f8ff;
  color: #33475e;
  font-size: 12px;
  padding: 6px 11px;
  cursor: pointer;
  transition: 0.2s ease;
  font-family: inherit;
}

.quick-btn:hover {
  border-color: #3b82f6;
  background: #dbeafe;
  color: #1e3a6e;
  transform: translateY(-1px);
}

.composer {
  padding: 10px 12px 12px;
  display: block;
  background: #fff;
}

.input-shell {
  border: 1px solid #d3dfef;
  border-radius: 12px;
  overflow: hidden;
  background: #f8fbff;
}

.input-shell:focus-within {
  border-color: #3b82f6;
  box-shadow: inset 0 0 0 1px rgba(59, 130, 246, 0.2);
}

.message-input {
  width: 100%;
  border: none;
  resize: none;
  outline: none;
  padding: 10px 11px;
  min-height: 72px;
  max-height: 180px;
  font-size: 16px;
  line-height: 1.55;
  color: #2d3f52;
  background: transparent;
  font-family: inherit;
  overflow-y: auto;
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.message-input::-webkit-scrollbar {
  width: 0;
  height: 0;
  display: none;
}

.message-input::placeholder {
  color: #99a8b8;
}

.tool-row {
  border-top: 1px solid #e4ecf6;
  background: #f6f9ff;
  padding: 8px 10px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.composer-right {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  margin-left: auto;
}

.tool-group {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.tool-btn {
  border: 1px solid transparent;
  border-radius: 8px;
  background: transparent;
  color: #5d6e82;
  font-size: 12px;
  padding: 4px 8px;
  cursor: pointer;
  transition: 0.2s ease;
  font-family: inherit;
}

.handoff-warning {
  margin: 6px 0 0;
  font-size: 12px;
  line-height: 1.45;
  color: #9f1239;
}

.tool-btn:hover {
  border-color: #bdd3f5;
  background: #eaf2ff;
  color: #2a5893;
}

.tool-btn.recording {
  border-color: #ef4444;
  background: #fef2f2;
  color: #dc2626;
  animation: pulse-recording 1s ease-in-out infinite;
}

@keyframes pulse-recording {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

.hint {
  font-size: 11px;
  color: #8b9bad;
}

.send-btn {
  height: 36px;
  border: none;
  border-radius: 10px;
  padding: 0 14px;
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  background: linear-gradient(145deg, #2563eb 0%, #1e40af 100%);
  box-shadow: 0 10px 22px rgba(37, 99, 235, 0.28);
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  font-family: inherit;
}

.send-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 12px 24px rgba(37, 99, 235, 0.34);
}

.send-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

/* Insight Panel */
.insight-panel {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.insight-body {
  padding: 12px;
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.card {
  border: 1px solid #d6e1ef;
  border-radius: 12px;
  background: #fff;
  padding: 10px;
}

.card-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 12px;
  font-weight: 800;
  color: #2c4156;
}

.chip {
  font-size: 11px;
  color: #5f7287;
  border: 1px solid #d2deef;
  background: #f3f7ff;
  border-radius: 999px;
  padding: 2px 8px;
  white-space: nowrap;
}

.matrix {
  display: grid;
  gap: 8px;
}

.metric-row {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr) 34px;
  gap: 7px;
  align-items: center;
  font-size: 11px;
  color: #516172;
}

.bar {
  height: 8px;
  border-radius: 999px;
  background: #e3ecf7;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #3b82f6 0%, #60a5fa 100%);
  transition: width 0.26s ease;
}

.intent-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
  line-height: 1.45;
  color: #4d6075;
}

.intent-list li {
  border-radius: 8px;
  padding: 5px 7px;
  border: 1px solid #e0e8f4;
  background: #f8fbff;
  display: flex;
  align-items: flex-start;
  gap: 6px;
}

.intent-list li::before {
  content: "\2022";
  color: #71889f;
  line-height: 1;
  margin-top: 1px;
}

.snapshot-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
  color: #50647a;
  max-height: 138px;
  overflow: auto;
}

.snapshot-list li {
  border: 1px solid #dde7f4;
  border-left: 3px solid #93b8ef;
  border-radius: 8px;
  background: #f7faff;
  padding: 6px 7px;
  line-height: 1.45;
}

.draft-block {
  border: 1px dashed #c7d8ef;
  border-radius: 11px;
  background: #f5f9ff;
  padding: 10px;
}

.draft-title {
  font-size: 12px;
  font-weight: 800;
  color: #2f465c;
  margin-bottom: 7px;
}

.draft-content {
  font-size: 12px;
  color: #51657c;
  line-height: 1.6;
  white-space: pre-wrap;
  max-height: 190px;
  overflow: auto;
}

.actions {
  display: grid;
  gap: 8px;
  margin-top: 8px;
}

.btn {
  width: 100%;
  border: none;
  border-radius: 10px;
  padding: 10px 12px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
  font-family: inherit;
}

.btn.primary {
  color: #fff;
  background: linear-gradient(145deg, #3b82f6 0%, #1e40af 100%);
  box-shadow: 0 10px 22px rgba(59, 130, 246, 0.28);
}

.btn.primary:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 12px 24px rgba(37, 99, 235, 0.34);
}

.btn.secondary {
  border: 1px solid #c1d4ee;
  color: #385a8e;
  background: linear-gradient(145deg, #f5f8ff 0%, #e2edff 100%);
}

.btn.secondary:hover:not(:disabled) {
  border-color: #3b82f6;
  box-shadow: 0 8px 18px rgba(59, 130, 246, 0.2);
}

.btn.btn-confirmed {
  border-color: #059669;
  color: #065f46;
  background: linear-gradient(145deg, #ecfdf5 0%, #d1fae5 100%);
}

.btn.btn-confirmed:hover:not(:disabled) {
  border-color: #047857;
  box-shadow: 0 8px 18px rgba(5, 150, 105, 0.2);
}

.btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  box-shadow: none;
  transform: none;
}

.handoff-note {
  font-size: 11px;
  color: #7d8da1;
  line-height: 1.45;
  margin: 0;
}

@keyframes pulse {
  0%, 85%, 100% {
    transform: translateY(0);
    opacity: 0.35;
  }
  40% {
    transform: translateY(-3px);
    opacity: 1;
  }
}

@keyframes rise {
  from {
    opacity: 0;
    transform: translateY(6px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 1160px) {
  .main-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .insight-panel {
    min-height: 300px;
  }
}

@media (max-width: 820px) {
  .flow-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .context-ribbon {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
