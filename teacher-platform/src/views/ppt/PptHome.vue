<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { usePptStore } from '@/stores/ppt'
import { getUserTemplates, extractStyleFromImage } from '@/api/ppt'
import { resolveApiUrl, getToken } from '@/api/http'

const pptStore = usePptStore()

const creationType = ref('dialog')
const mainText = ref('')
const aspectRatio = ref('16:9')
const showAspectMenu = ref(false)
const aspectDropdownRef = ref(null)
const aspectMenuStyle = ref({})
const selectedTemplateId = ref(null)
const selectedPresetTemplateId = ref(null)
const useTextStyle = ref(false)
const templateStyle = ref('')
const uploadedTemplateFile = ref(null)
const hoveredPresetId = ref(null)
const isUploadingTemplate = ref(false)
const isRecognizingImage = ref(false)
const uploadedStyleImage = ref(null)
const referenceFileInput = ref(null)
const isRecording = ref(false)
let recognition = null
const uploadedReferenceFiles = ref([])
const userTemplates = ref([])
const showLibPicker = ref(false)
const selectedLibIds = ref([])
const personalLibs = ref([])
const systemLibs = ref([])

// 文件生成 / 翻新 专用上传文件
const uploadedFile = ref(null) // File object for file-generation / renovation
const isDragging = ref(false)
const isCreating = ref(false)

const MAX_THEME_LENGTH = 50

// 预设风格 - 描述来自 banana-slides
const stylePresets = [
  { id: '1', name: '简约商务', color: '#0B1F3B', desc: '视觉描述：极致扁平化与强秩序网格，强调专业、稳重、克制。背景锁定海军蓝（#0B1F3B），标题文字纯白，强调色天蓝（#38BDF8）占比不超过3%。禁止渐变、发光、拟物纹理。光照为均匀演播室漫射光，无硬阴影。材质为平滑矢量色块，全稿默认不使用阴影。字体：无衬线体系，中英文统一基线。图表仅限2D扁平矢量，禁止饼图。', previewImage: '/preset-previews/business-simple.webp' },
  { id: '2', name: '现代科技', color: '#7C3AED', desc: '视觉描述：融合赛博朋克与现代SaaS产品的未来感。背景为午夜黑（#0B0F19），主色调电光蓝（#00A3FF）与赛博紫（#7C3AED）线性渐变。材质使用半透明玻璃、发光的网格线、金属光泽几何体。包含悬浮3D几何元素，带线框渲染效果。排版使用等宽字体或现代无衬线体。渲染强调光线追踪、辉光效果和景深控制。', previewImage: '/preset-previews/tech-modern.webp' },
  { id: '3', name: '严谨学术', color: '#7F1D1D', desc: '视觉描述：模仿高质量印刷出版物或经典论文的排版风格。背景为米白色（#F8F7F2），前景色为纯黑和深炭灰，强调色深红或深蓝占比不超过5%。材质为高质量纸质印刷效果。字体使用衬线体（Times New Roman或Garamond）。布局采用左右分栏或上下结构的严谨对齐方式。渲染为超高分辨率扫描件风格。', previewImage: '/preset-previews/academic-formal.webp' },
  { id: '4', name: '活泼创意', color: '#FF6A00', desc: '视觉描述：如同充满活力的初创公司Pitch Deck或儿童教育应用界面。背景为暖黄色（#FFD54A），配色大胆混合活力橙（#FF6A00）、草绿（#22C55E）、天蓝（#38BDF8）的撞色效果。材质模拟手绘涂鸦、剪纸风格。包含手绘风格插图元素、涂鸦箭头、星星、波浪线。字体为圆润可爱的圆体或手写体。渲染为Dribbble热门插画风格。', previewImage: '/preset-previews/creative-fun.webp' },
  { id: '5', name: '极简清爽', color: '#6B7280', desc: '视觉描述：借鉴北欧设计（Scandinavian Design）和Kinfolk杂志的审美。背景为极浅的雾霾灰（#F5F5F7），前景色仅使用中灰和低饱和度莫兰迪色系。材质体现细腻哑光质感。构图核心是留白，占据画面70%以上。字体为纤细优雅的非衬线体，行间距宽大。渲染为极简主义摄影风格，高动态范围。', previewImage: '/preset-previews/minimalist-clean.webp' },
  { id: '6', name: '高端奢华', color: '#F7E7CE', desc: '视觉描述：融合高端腕表广告或五星级酒店的品牌形象。背景为曜石黑（#0B0B0F），前景色主要为香槟金（#F7E7CE）。材质体现哑光黑天鹅绒背景与拉丝金属前景。排版采用经典居中对齐或对称布局，强调仪式感。字体为高雅的衬线体，字间距适当加宽。渲染为电影级写实渲染，强调PBR材质属性。', previewImage: '/preset-previews/luxury-premium.webp' },
  { id: '7', name: '自然清新', color: '#14532D', desc: '视觉描述：唤起人们对大自然、环保和健康生活的向往。背景为柔和的米色（#EAD9C6），配色使用森林绿（#14532D）和大地棕（#7A4E2D）。材质强调天然纹理，再生纸颗粒感和植物叶片脉络。融合伸展的绿植叶片元素作为背景装饰或前景框架。字体为圆润亲和型。渲染为微距摄影风格结合3D渲染，强调植物表面的透光感。', previewImage: '/preset-previews/nature-fresh.webp' },
  { id: '8', name: '渐变活力', color: '#2563EB', gradient: 'linear-gradient(135deg,#2563EB,#7C3AED,#DB2777)', desc: '视觉描述：对标现代科技独角兽公司官网视觉，呈现极光般的流动美感。背景即前景，使用全屏弥散渐变，配色以宝石蓝（#2563EB）为基底平滑过渡到紫罗兰（#7C3AED）和洋红色（#DB2777）。材质锁定为磨砂玻璃质感。核心是缓慢流动的有机波浪形状。渲染为C4D流体模拟，强调丝绸般顺滑光泽。', previewImage: '/preset-previews/gradient-vibrant.webp' }
]

// 预设模板列表 - 与 banana-slides 保持一致
const templates = ref([
  { id: '1', name: '复古卷轴', preview: '/templates/template_y.png', thumb: '/templates/template_y-thumb.webp' },
  { id: '2', name: '矢量插画', preview: '/templates/template_vector_illustration.png', thumb: '/templates/template_vector_illustration-thumb.webp' },
  { id: '3', name: '玻璃感', preview: '/templates/template_glass.png', thumb: '/templates/template_glass-thumb.webp' }
])

// 从 API 加载用户模板
onMounted(async () => {
  try {
    // 只加载用户模板，预设模板使用硬编码（与 banana-slides 保持一致）
    const userTpls = await getUserTemplates()
    if (userTpls) {
      userTemplates.value = Array.isArray(userTpls) ? userTpls : (userTpls.data || [])
    }
  } catch (error) {
    console.error('加载用户模板失败:', error)
  }
})

onMounted(async () => {
  selectedLibIds.value = Array.isArray(pptStore.selectedKnowledgeLibraryIds)
    ? [...pptStore.selectedKnowledgeLibraryIds]
    : []
  await fetchLibraries()
  document.addEventListener('click', handleClickOutside)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside)
})

async function fetchLibraries() {
  try {
    const token = getToken()
    const headers = token ? { Authorization: `Bearer ${token}` } : {}
    const [personalRes, systemRes] = await Promise.all([
      fetch(resolveApiUrl('/api/v1/libraries?scope=personal'), { headers }),
      fetch(resolveApiUrl('/api/v1/libraries?scope=system'), { headers })
    ])
    if (personalRes.ok) {
      personalLibs.value = (await personalRes.json()).items || []
    }
    if (systemRes.ok) {
      systemLibs.value = (await systemRes.json()).items || []
    }
  } catch (error) {
    console.error('鍔犺浇鐭ヨ瘑搴撳垪琛ㄥけ璐?', error)
  }
}

function handleClickOutside(event) {
  if (showLibPicker.value && !event.target.closest('.lib-picker') && !event.target.closest('.knowledge-btn')) {
    showLibPicker.value = false
  }
  if (showAspectMenu.value && !event.target.closest('.aspect-dropdown')) {
    showAspectMenu.value = false
  }
}

// Examples removed per user request

const modeDescriptions = {
  dialog: '输入你的想法，AI 将为你生成完整的 PPT',
  file: '上传或粘贴文档内容，AI 自动解析并生成教学演示文稿',
  renovation: '上传 PDF 或 PPTX，AI 会解析并输出翻新版本 PPT'
}

const modeDescription = computed(() => modeDescriptions[creationType.value])
const selectedLibraries = computed(() => {
  const all = [...personalLibs.value, ...systemLibs.value]
  return all.filter(item => selectedLibIds.value.includes(item.id))
})

function removeSelectedLibrary(libraryId) {
  selectedLibIds.value = selectedLibIds.value.filter(id => id !== libraryId)
}

function toggleLibSelection(libraryId) {
  const index = selectedLibIds.value.indexOf(libraryId)
  if (index > -1) {
    selectedLibIds.value.splice(index, 1)
  } else {
    selectedLibIds.value.push(libraryId)
  }
}

function selectMode(mode) {
  creationType.value = mode
}

function selectAspect(ratio) {
  aspectRatio.value = ratio
  showAspectMenu.value = false
}

function toggleAspectMenu() {
  showAspectMenu.value = !showAspectMenu.value
  if (showAspectMenu.value) {
    // 计算菜单位置
    nextTick(() => {
      if (aspectDropdownRef.value) {
        const rect = aspectDropdownRef.value.getBoundingClientRect()
        aspectMenuStyle.value = {
          top: `${rect.bottom + 8}px`,
          left: `${rect.left}px`
        }
      }
    })
  }
}

function closeAspectDropdown() {
  showAspectMenu.value = false
}

function selectTemplate(templateId) {
  if (useTextStyle.value) return
  selectedTemplateId.value = templateId
  selectedPresetTemplateId.value = null
  uploadedTemplateFile.value = null
}

function selectUserTemplate(template) {
  selectedTemplateId.value = String(template.id)
  selectedPresetTemplateId.value = null
  uploadedTemplateFile.value = null
}

function selectPresetTemplate(presetId) {
  selectedPresetTemplateId.value = presetId
  selectedTemplateId.value = null
  uploadedTemplateFile.value = null
}

function applyPreset(preset) {
  templateStyle.value = preset.desc
}

// Hover 预设风格显示样例图片
function onPresetHover(presetId) {
  hoveredPresetId.value = presetId
}

function onPresetLeave() {
  hoveredPresetId.value = null
}

// 上传模板到后端
async function handleTemplateUpload(event) {
  const file = event.target.files?.[0]
  if (!file) return

  isUploadingTemplate.value = true
  try {
    const { uploadUserTemplate, createUserTemplate } = await import('@/api/ppt')
    const templateName = file.name.replace(/\.[^/.]+$/, '')

    // Step 1: 先上传文件到 OSS，获取真实 URL
    const uploadRes = await uploadUserTemplate(file)
    const coverUrl = uploadRes.url || uploadRes.cover_url

    // Step 2: 用真实 URL 创建模板记录
    const response = await createUserTemplate({
      name: templateName,
      description: '',
      template_data: {},
      cover_url: coverUrl
    })

    if (response && response.id) {
      const newTemplate = {
        id: response.id,
        name: response.name || templateName,
        cover_url: response.cover_url || coverUrl,
        thumbnail: response.cover_url || coverUrl
      }
      userTemplates.value.unshift(newTemplate)
      selectUserTemplate(newTemplate)
    }
  } catch (error) {
    console.error('上传模板失败:', error)
    alert('上传模板失败，请重试')
  } finally {
    isUploadingTemplate.value = false
  }
  event.target.value = ''
}

// 删除用户模板
async function deleteUserTemplate(templateId) {
  // 确保 templateId 是数字类型（API 返回的是整数，local 模板是字符串）
  const numericId = Number(templateId)
  const template = userTemplates.value.find(t => Number(t.id) === numericId)
  // 如果是本地模板（未持久化），直接删除
  if (template && template.isLocal) {
    userTemplates.value = userTemplates.value.filter(t => Number(t.id) !== numericId)
    if (selectedTemplateId.value === String(templateId)) {
      selectedTemplateId.value = null
    }
    return
  }

  // 如果是已持久化的模板，调用后端 API 删除
  try {
    const { deleteUserTemplate: deleteTpl } = await import('@/api/ppt')
    await deleteTpl(numericId)
    userTemplates.value = userTemplates.value.filter(t => Number(t.id) !== numericId)
    if (selectedTemplateId.value === String(templateId)) {
      selectedTemplateId.value = null
    }
  } catch (error) {
    console.error('删除模板失败:', error)
  }
}

// 移除已上传的模板
function removeUploadedTemplate() {
  uploadedTemplateFile.value = null
}

function resolveSelectedTemplateUrl() {
  if (useTextStyle.value) {
    return null
  }

  if (selectedTemplateId.value) {
    const userTemplate = userTemplates.value.find(t => String(t.id) === String(selectedTemplateId.value))
    if (userTemplate?.cover_url || userTemplate?.thumbnail) {
      return userTemplate.cover_url || userTemplate.thumbnail
    }

    const presetTemplate = templates.value.find(t => String(t.id) === String(selectedTemplateId.value))
    if (presetTemplate?.preview || presetTemplate?.thumb) {
      return presetTemplate.preview || presetTemplate.thumb
    }
  }

  if (selectedPresetTemplateId.value) {
    const presetTemplate = templates.value.find(t => String(t.id) === String(selectedPresetTemplateId.value))
    if (presetTemplate?.preview || presetTemplate?.thumb) {
      return presetTemplate.preview || presetTemplate.thumb
    }
  }

  return null
}

// 触发参考文件上传
function triggerReferenceFileUpload() {
  referenceFileInput.value?.click()
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
    mainText.value += transcript
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

// 处理参考文件上传
async function handleReferenceFileUpload(event) {
  const files = event.target.files
  if (!files || files.length === 0) return

  for (const file of files) {
    // 只显示本地预览，不上传到后端（项目创建时再上传）
    uploadedReferenceFiles.value.push({
      name: file.name,
      size: file.size,
      rawFile: file
    })
  }
  event.target.value = ''
}

// 移除参考文件
function removeReferenceFile(index) {
  uploadedReferenceFiles.value.splice(index, 1)
}

// 文件类型判断
function isImageFile(filename) {
  const ext = filename.split('.').pop().toLowerCase()
  return ['png', 'jpg', 'jpeg', 'webp', 'gif', 'bmp'].includes(ext)
}

function isVideoFile(filename) {
  const ext = filename.split('.').pop().toLowerCase()
  return ['mp4', 'mov', 'avi', 'mkv', 'webm'].includes(ext)
}

// 格式化文件大小
function formatFileSize(bytes) {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 10) / 10 + ' ' + sizes[i]
}

// 文件 hover 状态
function handleFileHover(index, isHovered) {
  if (uploadedReferenceFiles.value[index]) {
    uploadedReferenceFiles.value[index].isHovered = isHovered
  }
}

function goToHistory() {
  pptStore.setPhase('history')
}

// ============ 文件生成/翻新 文件上传 ============

const fileAcceptMap = {
  file: '.pdf,.doc,.docx',
  renovation: '.pdf,.ppt,.pptx'
}

const fileAccept = computed(() => fileAcceptMap[creationType.value] || '')

function handleFileUpload(event) {
  const file = event.target.files?.[0]
  if (file) uploadedFile.value = file
  event.target.value = ''
}

function removeUploadedFile() {
  uploadedFile.value = null
}

function handleDragOver(event) {
  event.preventDefault()
  if (creationType.value === 'file' || creationType.value === 'renovation') {
    isDragging.value = true
  }
}

function handleDragLeave() {
  isDragging.value = false
}

function handleDrop(event) {
  event.preventDefault()
  isDragging.value = false
  if (creationType.value !== 'file' && creationType.value !== 'renovation') return

  const file = event.dataTransfer?.files?.[0]
  if (!file) return

  const ext = '.' + file.name.split('.').pop().toLowerCase()
  const allowed = fileAcceptMap[creationType.value].split(',')
  if (!allowed.includes(ext)) {
    alert(`不支持的文件类型 ${ext}，请上传 ${allowed.join('、')} 格式`)
    return
  }
  uploadedFile.value = file
}

// 上传图片自动识别风格
async function handleStyleImageUpload(event) {
  const file = event.target.files?.[0]
  if (!file) return

  isRecognizingImage.value = true
  try {
    // 保存预览图片
    uploadedStyleImage.value = URL.createObjectURL(file)

    // 调用后端API识别图片风格
    const response = await extractStyleFromImage(file)
    if (response && response.data && response.data.style_description) {
      templateStyle.value = response.data.style_description
    } else if (response && response.style_description) {
      // 兼容不同的响应格式
      templateStyle.value = response.style_description
    }
  } catch (error) {
    console.error('识别风格失败:', error)
    alert('风格提取失败，请重试')
  } finally {
    isRecognizingImage.value = false
  }
  event.target.value = ''
}

function parseBackendValidationDetails(rawMessage) {
  const fallback = rawMessage || '请求失败，请稍后重试。'
  if (!rawMessage) return [fallback]

  let parsed = null
  try {
    parsed = JSON.parse(rawMessage)
  } catch (_) {
    return [fallback]
  }

  const details = Array.isArray(parsed)
    ? parsed
    : (parsed && Array.isArray(parsed.detail) ? parsed.detail : [])

  if (!details.length) {
    if (parsed && typeof parsed.detail === 'string') return [parsed.detail]
    return [fallback]
  }

  const fieldLabelMap = {
    'body.theme': 'theme（主题短标签）',
    'body.template_style': 'template_style（风格描述）',
    'body.settings.template_style': 'settings.template_style（风格描述）'
  }

  const messages = details
    .map((item) => {
      if (!item || typeof item !== 'object') return ''
      const fieldPath = Array.isArray(item.loc) ? item.loc.join('.') : ''
      const fieldLabel = fieldLabelMap[fieldPath] || fieldPath || '字段'
      const maxLength = Number(item?.ctx?.max_length || 0)

      if (item.type === 'string_too_long' && maxLength > 0 && fieldPath.endsWith('theme')) {
        return `${fieldLabel} 最多 ${maxLength} 个字符；长风格描述请填写到 template_style。`
      }
      if (item.type === 'string_too_long' && maxLength > 0) {
        return `${fieldLabel} 最多 ${maxLength} 个字符。`
      }
      if (item.msg) {
        return `${fieldLabel}: ${item.msg}`
      }
      return ''
    })
    .filter(Boolean)

  return messages.length ? messages : [fallback]
}

async function handleNext() {
  if (isCreating.value) return
  isCreating.value = true
  try {
    const templateImageUrl = resolveSelectedTemplateUrl()
    const effectiveTheme = (mainText.value || '').trim() || null
    const effectiveTemplateStyle = useTextStyle.value ? (templateStyle.value || '').trim() : null

    if (creationType.value === 'dialog' && effectiveTheme && effectiveTheme.length > MAX_THEME_LENGTH) {
      alert(`主题（theme）最多 ${MAX_THEME_LENGTH} 个字符，请精简 main-textarea 内容。`)
      return
    }

    if (useTextStyle.value && !effectiveTemplateStyle) {
      alert('请先填写风格描述，或关闭”文字描述风格”。')
      return
    }

    const effectiveTemplateId = useTextStyle.value
      ? null
      : (selectedTemplateId.value || selectedPresetTemplateId.value || null)

    const settings = {
      aspect_ratio: aspectRatio.value,
      template_id: effectiveTemplateId,
      template_image_url: templateImageUrl,
      template_style: effectiveTemplateStyle
    }

    // ---- 文件生成模式 ----
    if (creationType.value === 'file') {
      const hasFile = !!uploadedFile.value
      const hasText = !!(mainText.value || '').trim()
      if (!hasFile && !hasText) {
        alert('请上传文档或粘贴文本内容')
        return
      }
      const res = await pptStore.createFileGenerationProject({
        file: uploadedFile.value || undefined,
        sourceText: hasText ? mainText.value.trim() : undefined,
        title: (mainText.value || '').slice(0, 100) || '未命名PPT',
        theme: effectiveTheme,
        templateStyle: effectiveTemplateStyle,
        settings
      })
      pptStore.projectSettings = { ...pptStore.projectSettings, ...settings }
      pptStore.setPhase('outline')
      pptStore.pollFileGenerationTask(res.project_id, res.task_id)
      return
    }

    // ---- PPT 翻新模式 ----
    if (creationType.value === 'renovation') {
      if (!uploadedFile.value) {
        alert('请先上传 PDF 或 PPTX 文件')
        return
      }
      const res = await pptStore.createRenovationProjectAction({
        file: uploadedFile.value,
        keepLayout: false,
        templateStyle: effectiveTemplateStyle,
        language: 'zh'
      })
      pptStore.projectSettings = { ...pptStore.projectSettings, ...settings }
      pptStore.setPhase('outline')
      pptStore.pollRenovationTask(res.project_id, res.task_id)
      return
    }

    // ---- 普通对话模式 ----
    const data = {
      title: mainText.value.slice(0, 100) || '未命名PPT',
      creation_type: creationType.value,
      outline_text: mainText.value,
      theme: effectiveTheme,
      template_style: effectiveTemplateStyle,
      settings: settings,
      knowledge_library_ids: selectedLibIds.value
    }

    await pptStore.createProject(data)
    pptStore.selectedKnowledgeLibraryIds = [...selectedLibIds.value]
    for (const item of uploadedReferenceFiles.value) {
      if (!item?.rawFile) continue
      try {
        const uploaded = await pptStore.uploadReferenceFile(pptStore.projectId, item.rawFile)
        await pptStore.parseReferenceFile(pptStore.projectId, uploaded.id)
      } catch (uploadError) {
        console.error('reference upload failed:', uploadError)
      }
    }
    pptStore.projectSettings = { ...pptStore.projectSettings, ...settings }
    pptStore.setPhase('dialog')
  } catch (error) {
    console.error('create project failed:', error)
    const rawMessage = String(error?.message || '')
    const detailLines = parseBackendValidationDetails(rawMessage)
    alert(`创建项目失败：\n${detailLines.join('\n')}`)
  } finally {
    isCreating.value = false
  }
}
</script>

<template>
  <div class="ppt-home">
    <button class="history-entry-btn" @click="goToHistory">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">
        <circle cx="12" cy="12" r="10"/>
        <polyline points="12 6 12 12 16 14"/>
      </svg>
      历史项目
    </button>
    <div class="shell">
      <section class="hero">
        <h1>智能 PPT 生成</h1>
        <p>从灵感到成稿，一次输入就能完成教学演示设计</p>
      </section>

      <section class="workspace">
        <div class="mode-tabs">
          <button
            v-for="mode in ['dialog', 'file', 'renovation']"
            :key="mode"
            class="mode-tab"
            :class="{ active: creationType === mode }"
            @click="selectMode(mode)"
          >
            {{ mode === 'dialog' ? '对话生成' : mode === 'file' ? '文件生成' : 'PPT 翻新' }}
          </button>
        </div>

        <p class="mode-desc">{{ modeDescription }}</p>

        <!-- 文件上传区域（file / renovation 模式） -->
        <div
          v-if="creationType === 'file' || creationType === 'renovation'"
          class="file-upload-zone"
          :class="{ dragging: isDragging, 'has-file': !!uploadedFile }"
          @dragover="handleDragOver"
          @dragleave="handleDragLeave"
          @drop="handleDrop"
        >
          <template v-if="uploadedFile">
            <div class="uploaded-file-info">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
              </svg>
              <span class="uploaded-file-name">{{ uploadedFile.name }}</span>
              <span class="uploaded-file-size">{{ (uploadedFile.size / 1024 / 1024).toFixed(2) }} MB</span>
              <button class="uploaded-file-remove" @click="removeUploadedFile">×</button>
            </div>
          </template>
          <template v-else>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="32" height="32" class="upload-icon">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
            <p class="upload-text">
              拖拽文件到此处，或
              <label class="upload-link">
                点击选择文件
                <input type="file" :accept="fileAccept" @change="handleFileUpload" hidden>
              </label>
            </p>
            <p class="upload-hint">
              {{ creationType === 'file' ? '支持 PDF、DOC、DOCX 格式' : '支持 PDF、PPT、PPTX 格式' }}
            </p>
          </template>
        </div>

        <div class="composer">
          <textarea
            v-model="mainText"
            class="main-textarea"
            :placeholder="creationType === 'dialog' ? '输入你想制作的PPT主题，例如：帮我制作一份关于人工智能发展历程的教学演示文稿...' : creationType === 'file' ? '粘贴或输入文本内容（可选，也可只上传文件）...' : '上传 PDF 或 PPTX 后点击下一步'"
            :rows="creationType === 'renovation' ? 2 : undefined"
          ></textarea>
          
          <!-- 参考文件标签区域 - 集成在输入框内 -->
          <div v-if="uploadedReferenceFiles.length > 0" class="reference-files-inline">
            <div class="reference-files-header">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/>
              </svg>
              <span class="reference-files-count">{{ uploadedReferenceFiles.length }} 个参考文件</span>
            </div>
            <div class="reference-files-list">
              <div 
                v-for="(file, index) in uploadedReferenceFiles" 
                :key="index" 
                class="reference-file-chip"
                @mouseenter="handleFileHover(index, true)"
                @mouseleave="handleFileHover(index, false)"
              >
                <div class="file-chip-icon">
                  <svg v-if="isImageFile(file.name)" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                    <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                    <circle cx="8.5" cy="8.5" r="1.5"/>
                    <polyline points="21 15 16 10 5 21"/>
                  </svg>
                  <svg v-else-if="isVideoFile(file.name)" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                    <polygon points="23 7 16 12 23 17 23 7"/>
                    <rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>
                  </svg>
                  <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                    <polyline points="14 2 14 8 20 8"/>
                  </svg>
                </div>
                <span class="file-chip-name">{{ file.name }}</span>
                <span class="file-chip-size">{{ formatFileSize(file.size) }}</span>
                <button 
                  class="file-chip-remove" 
                  @click="removeReferenceFile(index)"
                  :class="{ 'file-chip-remove-hover': file.isHovered }"
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12">
                    <line x1="18" y1="6" x2="6" y2="18"/>
                    <line x1="6" y1="6" x2="18" y2="18"/>
                  </svg>
                </button>
              </div>
            </div>
          </div>
          
          <div class="composer-toolbar">
            <div class="toolbar-left">
              <button
                class="icon-btn knowledge-btn"
                type="button"
                title="选择知识库"
                @click.stop="showLibPicker = !showLibPicker"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">
                  <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
                  <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
                </svg>
              </button>
              <button v-if="creationType === 'dialog'" class="icon-btn" type="button" title="上传参考文件" @click="triggerReferenceFileUpload">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">
                  <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/>
                </svg>
              </button>
              <button class="icon-btn" type="button" :title="isRecording ? '停止录音' : '语音输入'" @click="toggleVoiceInput">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">
                  <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
                  <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
                  <line x1="12" y1="19" x2="12" y2="23"/>
                  <line x1="8" y1="23" x2="16" y2="23"/>
                </svg>
              </button>
              
              <!-- 比例选择下拉菜单 -->
              <div class="aspect-dropdown" ref="aspectDropdownRef">
                <button 
                  type="button"
                  class="aspect-trigger"
                  @click="toggleAspectMenu"
                  :class="{ active: showAspectMenu }"
                  title="选择比例"
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
                    <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
                    <line x1="8" y1="21" x2="16" y2="21"/>
                    <line x1="12" y1="17" x2="12" y2="21"/>
                  </svg>
                  <span class="aspect-current">{{ aspectRatio }}</span>
                  <svg class="dropdown-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                    <polyline points="6 9 12 15 18 9"/>
                  </svg>
                </button>
                
                <!-- 下拉菜单 -->
                <Transition name="dropdown">
                  <div v-if="showAspectMenu" class="aspect-menu" :style="aspectMenuStyle">
                    <div class="aspect-menu-header">选择比例</div>
                    <button 
                      type="button"
                      class="aspect-menu-item"
                      :class="{ active: aspectRatio === '16:9' }"
                      @click="selectAspect('16:9')"
                    >
                      <div class="aspect-preview-small aspect-16-9-small"></div>
                      <div class="aspect-menu-item-info">
                        <span class="aspect-menu-label">16:9</span>
                        <span class="aspect-menu-desc">宽屏</span>
                      </div>
                    </button>
                    <button 
                      type="button"
                      class="aspect-menu-item"
                      :class="{ active: aspectRatio === '4:3' }"
                      @click="selectAspect('4:3')"
                    >
                      <div class="aspect-preview-small aspect-4-3-small"></div>
                      <div class="aspect-menu-item-info">
                        <span class="aspect-menu-label">4:3</span>
                        <span class="aspect-menu-desc">标准</span>
                      </div>
                    </button>
                    <button 
                      type="button"
                      class="aspect-menu-item"
                      :class="{ active: aspectRatio === '1:1' }"
                      @click="selectAspect('1:1')"
                    >
                      <div class="aspect-preview-small aspect-1-1-small"></div>
                      <div class="aspect-menu-item-info">
                        <span class="aspect-menu-label">1:1</span>
                        <span class="aspect-menu-desc">方形</span>
                      </div>
                    </button>
                  </div>
                </Transition>
              </div>
              
              <select v-model="aspectRatio" class="aspect-select" style="display: none;">
                <option value="16:9">16:9</option>
                <option value="4:3">4:3</option>
                <option value="1:1">1:1</option>
              </select>
            </div>
            <div class="toolbar-right">
              <button class="next-btn" type="button" @click="handleNext" :disabled="isCreating">
                {{ isCreating ? '创建中...' : '下一步' }}
              </button>
            </div>
          </div>
        </div>

        <div v-if="creationType === 'dialog' && selectedLibraries.length > 0" class="selected-lib-tags">
          <span v-for="lib in selectedLibraries" :key="lib.id" class="selected-lib-tag">
            {{ lib.name }}
            <button type="button" class="tag-remove" @click.stop="removeSelectedLibrary(lib.id)">×</button>
          </span>
        </div>

        <div v-if="creationType === 'dialog' && showLibPicker" class="lib-picker">
          <div class="lib-section">
            <div class="lib-section-title">个人知识库</div>
            <label v-for="lib in personalLibs" :key="lib.id" class="lib-option">
              <input type="checkbox" :value="lib.id" v-model="selectedLibIds">
              {{ lib.name }}
            </label>
            <div v-if="!personalLibs.length" class="lib-empty">暂无</div>
          </div>
          <div class="lib-section">
            <div class="lib-section-title">系统知识库</div>
            <label v-for="lib in systemLibs" :key="lib.id" class="lib-option">
              <input type="checkbox" :value="lib.id" v-model="selectedLibIds">
              {{ lib.name }}
            </label>
            <div v-if="!systemLibs.length" class="lib-empty">暂无</div>
          </div>
        </div>

        <!-- 隐藏的参考文件上传输入框 -->
        <input
          ref="referenceFileInput"
          type="file"
          accept=".pdf,.ppt,.pptx,.doc,.docx,.png,.jpg,.jpeg,.webp,.gif,.mp4,.mov,.avi,.mkv"
          multiple
          @change="handleReferenceFileUpload"
          hidden
        >

        <div class="template-head">
          <h3 class="template-title">选择风格模板</h3>
          <label class="toggle-wrap">
            <input type="checkbox" v-model="useTextStyle" class="toggle-input">
            <span class="toggle"></span>
            <span>使用文字描述风格</span>
          </label>
        </div>

        <!-- 模板选择区域 -->
        <div v-if="!useTextStyle" class="template-section">
          <!-- 我的模板区域 - 只有在有用户模板时才显示 -->
          <div v-if="userTemplates.length > 0" class="template-subsection">
            <h4 class="template-subsection-title">我的模板</h4>
            <div class="template-grid">
              <article
                v-for="template in userTemplates"
                :key="template.id"
                class="template-item"
                :class="{ selected: selectedTemplateId === String(template.id) }"
                @click="selectUserTemplate(template)"
              >
                <img
                  :src="template.cover_url || template.thumbnail"
                  :alt="template.name"
                  @error="($event.target.src = 'data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 viewBox=%270 0 200 150%27%3E%3Crect fill=%27%23658dbc%27 width=%27200%27 height=%27150%27/%3E%3C/svg%3E')"
                >
                <div v-if="selectedTemplateId === String(template.id)" class="template-selected-overlay">
                  <span class="template-selected-text">已选择</span>
                </div>
                <button
                  class="template-remove"
                  @click.stop="deleteUserTemplate(template.id)"
                  title="删除模板"
                >
                  ×
                </button>
                <span class="template-name">{{ template.name }}</span>
              </article>
            </div>
          </div>

          <!-- 预设模板区域 -->
          <div class="template-subsection">
            <h4 class="template-subsection-title">预设模板</h4>
            <div class="template-grid">
              <article
                v-for="template in templates"
                :key="template.id"
                class="template-item"
                :class="{ selected: selectedPresetTemplateId === template.id }"
                @click="selectPresetTemplate(template.id)"
              >
                <img
                  :src="template.preview"
                  :alt="template.name"
                  @error="($event.target.src = 'data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 viewBox=%270 0 200 150%27%3E%3Crect fill=%27%23658dbc%27 width=%27200%27 height=%27150%27/%3E%3C/svg%3E')"
                >
                <div v-if="selectedPresetTemplateId === template.id" class="template-selected-overlay">
                  <span class="template-selected-text">已选择</span>
                </div>
                <span class="template-name">{{ template.name }}</span>
              </article>
              <!-- 上传模板按钮 -->
              <label class="template-upload">
                <input
                  type="file"
                  accept="image/*"
                  @change="handleTemplateUpload"
                  :disabled="isUploadingTemplate"
                  hidden
                >
                <span v-if="isUploadingTemplate" style="font-size: 14px">上传中...</span>
                <template v-else>
                  <span style="font-size: 24px; line-height: 1">+</span>
                  <span>上传模板</span>
                </template>
              </label>
            </div>
          </div>
        </div>

        <section v-show="useTextStyle" class="text-style-panel" :class="{ active: useTextStyle }">
          <textarea
            v-model="templateStyle"
            class="style-textarea"
            placeholder="描述你希望的风格，例如：简约商务风格，蓝灰配色，图表优先，标题简洁有力..."
          ></textarea>

          <div class="preset-section">
            <p class="preset-label">快速选择预设风格：</p>
            <div class="preset-wrap">
              <div
                v-for="preset in stylePresets"
                :key="preset.id"
                class="preset-btn-wrap"
                @mouseenter="onPresetHover(preset.id)"
                @mouseleave="onPresetLeave"
              >
                <button
                  class="preset-btn"
                  type="button"
                  @click="applyPreset(preset)"
                  :class="{ active: templateStyle === preset.desc }"
                >
                  <span class="preset-dot" :style="{ background: preset.gradient || preset.color }"></span>
                  {{ preset.name }}
                </button>
                <!-- Hover 显示样例图片 + 描述 -->
                <div v-if="hoveredPresetId === preset.id && preset.previewImage" class="preset-preview">
                  <img :src="preset.previewImage" :alt="preset.name" class="preset-preview-img">
                  <p class="preset-preview-desc">{{ preset.desc }}</p>
                  <!-- 箭头 -->
                  <div class="preset-preview-arrow"></div>
                </div>
              </div>

              <!-- 上传图片自动识别风格按钮 -->
              <label class="preset-btn upload-style-btn">
                <input
                  type="file"
                  accept="image/*"
                  @change="handleStyleImageUpload"
                  :disabled="isRecognizingImage"
                  hidden
                >
                <span v-if="isRecognizingImage">识别中...</span>
                <span v-else>📷 从图片提取风格</span>
              </label>
            </div>
          </div>

          <p class="style-tip">💡 提示：点击预设风格可快速填充，也可以自由描述配色、版式、字体气质、图文比例等要求。</p>
        </section>
      </section>
    </div>

    <!-- 知识库选择弹窗 -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="showLibPicker" class="lib-modal-overlay" @click="showLibPicker = false">
          <div class="lib-modal" @click.stop>
            <div class="lib-modal-header">
              <h3 class="lib-modal-title">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20">
                  <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
                  <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
                </svg>
                选择知识库
              </h3>
              <button class="lib-modal-close" @click="showLibPicker = false">×</button>
            </div>
            <div class="lib-modal-body">
              <!-- 个人知识库 -->
              <div v-if="personalLibs.length > 0" class="lib-section">
                <div class="lib-section-title">个人知识库</div>
                <div class="lib-grid">
                  <div
                    v-for="lib in personalLibs"
                    :key="lib.id"
                    class="lib-card"
                    :class="{ 'lib-card-selected': selectedLibIds.includes(lib.id) }"
                    @click="toggleLibSelection(lib.id)"
                  >
                    <div class="lib-card-check">{{ selectedLibIds.includes(lib.id) ? '✓' : '' }}</div>
                    <div class="lib-card-info">
                      <div class="lib-card-name">{{ lib.name }}</div>
                      <div class="lib-card-desc">{{ lib.description || '暂无描述' }}</div>
                    </div>
                    <span class="lib-badge personal">个人</span>
                  </div>
                </div>
              </div>
              
              <!-- 系统知识库 -->
              <div v-if="systemLibs.length > 0" class="lib-section">
                <div class="lib-section-title">系统知识库</div>
                <div class="lib-grid">
                  <div
                    v-for="lib in systemLibs"
                    :key="lib.id"
                    class="lib-card"
                    :class="{ 'lib-card-selected': selectedLibIds.includes(lib.id) }"
                    @click="toggleLibSelection(lib.id)"
                  >
                    <div class="lib-card-check">{{ selectedLibIds.includes(lib.id) ? '✓' : '' }}</div>
                    <div class="lib-card-info">
                      <div class="lib-card-name">{{ lib.name }}</div>
                      <div class="lib-card-desc">{{ lib.description || '暂无描述' }}</div>
                    </div>
                    <span class="lib-badge system">系统</span>
                  </div>
                </div>
              </div>
              
              <!-- 空状态 -->
              <div v-if="personalLibs.length === 0 && systemLibs.length === 0" class="lib-empty">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="48" height="48">
                  <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
                  <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
                </svg>
                <p>暂无可用知识库</p>
                <p class="lib-empty-hint">请在知识库管理中创建知识库</p>
              </div>
            </div>
            <div class="lib-modal-footer">
              <span class="lib-modal-count">已选择 {{ selectedLibIds.length }} 个知识库</span>
              <button class="lib-modal-confirm" @click="showLibPicker = false">确认</button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
/* 引入现代字体 - 使用国内 CDN 镜像 */
@import url('https://fonts.loli.net/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
/* 备用方案：字节跳动 CDN */
/* @import url('https://sf1-cdn-tos.bytegoofy.com/obj/iconpark/fonts/PlusJakartaSans.css'); */

.ppt-home {
  flex: 1;
  overflow-y: auto;
  background: linear-gradient(180deg, #F8FAFC 0%, #FFFFFF 100%);
  position: relative;
  /* 使用现代系统字体栈，无需外部字体文件 */
  font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'Helvetica Neue', Helvetica, Arial, sans-serif;
}

.history-entry-btn {
  position: absolute;
  top: 20px;
  right: 32px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: 2px solid #E2E8F0;
  border-radius: 12px;
  background: #FFFFFF;
  color: #475569;
  font-size: 14px;
  font-weight: 600;
  padding: 10px 18px;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  font-family: inherit;
  z-index: 10;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.history-entry-btn:hover {
  border-color: #3B82F6;
  background: #F0F7FF;
  color: #1E40AF;
  box-shadow: 0 4px 16px rgba(59, 130, 246, 0.15);
  transform: translateY(-1px);
}

.shell {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 32px 80px;
}

.hero {
  text-align: center;
  padding: 56px 0 40px;
  animation: rise 0.55s ease;
}

.hero h1 {
  margin-top: 0;
  font-size: clamp(2.2rem, 5.5vw, 3.6rem);
  line-height: 1.1;
  letter-spacing: -0.03em;
  color: #0F172A;
  font-weight: 800;
  background: linear-gradient(135deg, #0F172A 0%, #1E40AF 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.hero p {
  margin-top: 16px;
  font-size: clamp(1rem, 2vw, 1.2rem);
  color: #64748B;
  font-weight: 400;
  line-height: 1.6;
}

.workspace {
  animation: rise 0.65s ease;
}

.mode-tabs {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 12px;
}

.mode-tab {
  border: 2px solid #E2E8F0;
  background: #FFFFFF;
  color: #475569;
  border-radius: 12px;
  padding: 14px 16px;
  text-align: center;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  font-family: inherit;
  position: relative;
  overflow: hidden;
}

.mode-tab:hover {
  border-color: #3B82F6;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.1);
  color: #1E40AF;
}

.mode-tab.active {
  border-color: #3B82F6;
  color: #FFFFFF;
  background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%);
  box-shadow: 0 4px 16px rgba(59, 130, 246, 0.25);
  transform: translateY(-1px);
}

.mode-desc {
  border: 1px solid #E2E8F0;
  background: #FFFFFF;
  color: #475569;
  border-radius: 12px;
  padding: 14px 18px;
  font-size: 14px;
  margin-bottom: 20px;
  font-weight: 400;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.composer {
  border: 2px solid #E2E8F0;
  border-radius: 16px;
  background: #FFFFFF;
  overflow: hidden;
  margin-bottom: 20px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06);
  transition: all 0.2s ease;
  display: flex;
  flex-direction: column;
}

.composer:focus-within {
  border-color: #3B82F6;
  box-shadow: 0 4px 24px rgba(59, 130, 246, 0.12);
}

.main-textarea {
  width: 100%;
  min-height: 160px;
  resize: vertical;
  border: none;
  outline: none;
  padding: 20px;
  line-height: 1.7;
  font-size: 15px;
  color: #0F172A;
  background: transparent;
  font-family: inherit;
  transition: all 0.2s ease;
  flex: 1;
}

.main-textarea::placeholder {
  color: #94A3B8;
  font-weight: 400;
}

.composer-toolbar {
  border-top: 1px solid #F1F5F9;
  padding: 12px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  background: #FAFBFC;
}

.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 参考文件内联显示区域 - 惊艳设计 */
.reference-files-inline {
  padding: 16px 20px 12px;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.03) 0%, rgba(37, 99, 235, 0.05) 100%);
  border-top: 1px solid rgba(59, 130, 246, 0.1);
  animation: slideDown 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes slideDown {
  from {
    opacity: 0;
    max-height: 0;
    padding-top: 0;
    padding-bottom: 0;
  }
  to {
    opacity: 1;
    max-height: 500px;
    padding-top: 16px;
    padding-bottom: 12px;
  }
}

.reference-files-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 10px;
  color: #3B82F6;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.3px;
}

.reference-files-header svg {
  opacity: 0.7;
}

.reference-files-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.reference-file-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px 8px 10px;
  background: #FFFFFF;
  border: 1.5px solid #E2E8F0;
  border-radius: 10px;
  cursor: default;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
  position: relative;
  overflow: hidden;
}

.reference-file-chip::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.05) 0%, rgba(37, 99, 235, 0.08) 100%);
  opacity: 0;
  transition: opacity 0.25s ease;
}

.reference-file-chip:hover {
  border-color: #3B82F6;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.12);
  transform: translateY(-2px);
}

.reference-file-chip:hover::before {
  opacity: 1;
}

.file-chip-icon {
  position: relative;
  z-index: 1;
  width: 26px;
  height: 26px;
  border-radius: 6px;
  background: linear-gradient(135deg, #EFF6FF 0%, #DBEAFE 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #3B82F6;
  flex-shrink: 0;
}

.file-chip-name {
  position: relative;
  z-index: 1;
  font-size: 13px;
  color: #0F172A;
  font-weight: 500;
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-chip-size {
  position: relative;
  z-index: 1;
  font-size: 11px;
  color: #94A3B8;
  font-weight: 400;
  flex-shrink: 0;
}

.file-chip-remove {
  position: relative;
  z-index: 1;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: none;
  background: transparent;
  color: #94A3B8;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.file-chip-remove:hover {
  background: #FEE2E2;
  color: #EF4444;
  transform: scale(1.1);
}

.file-chip-remove-hover {
  background: #FEE2E2;
  color: #EF4444;
}

.icon-btn {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  border: 1px solid transparent;
  background: transparent;
  color: #64748B;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  position: relative;
}

.icon-btn:hover {
  border-color: #E2E8F0;
  background: #F8FAFC;
  color: #0F172A;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.icon-btn.recording {
  border-color: #ef4444;
  background: #fef2f2;
  color: #dc2626;
  animation: pulse-recording 1s ease-in-out infinite;
}

@keyframes pulse-recording {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

.aspect-select {
  border: 2px solid #E2E8F0;
  border-radius: 10px;
  padding: 8px 12px;
  color: #0F172A;
  background: #FFFFFF;
  font-size: 13px;
  font-weight: 500;
  outline: none;
  cursor: pointer;
  transition: all 0.2s ease;
}

.aspect-select:hover {
  border-color: #CBD5E1;
}

.aspect-select:focus {
  border-color: #3B82F6;
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.08);
}

/* 比例下拉菜单 - 简洁设计 */
.aspect-dropdown {
  position: relative;
}

.aspect-trigger {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 36px;
  padding: 0 12px;
  border: 1px solid transparent;
  border-radius: 10px;
  background: transparent;
  color: #64748B;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  font-family: inherit;
  font-size: 13px;
  font-weight: 500;
}

.aspect-trigger:hover {
  border-color: #E2E8F0;
  background: #F8FAFC;
  color: #0F172A;
}

.aspect-trigger.active {
  border-color: #3B82F6;
  background: #EFF6FF;
  color: #3B82F6;
}

.aspect-current {
  font-weight: 600;
  min-width: 32px;
  text-align: center;
}

.dropdown-arrow {
  transition: transform 0.2s ease;
}

.aspect-trigger.active .dropdown-arrow {
  transform: rotate(180deg);
}

/* 下拉菜单 */
.aspect-menu {
  position: fixed;
  min-width: 150px;
  background: #FFFFFF;
  border: 1.5px solid #E2E8F0;
  border-radius: 12px;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.12);
  overflow: hidden;
  z-index: 1000;
  animation: dropdownSlideDown 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes dropdownSlideDown {
  from {
    opacity: 0;
    transform: translateY(-8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.aspect-menu-header {
  padding: 10px 14px 8px;
  font-size: 11px;
  font-weight: 700;
  color: #94A3B8;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 1px solid #F1F5F9;
}

.aspect-menu-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 10px 14px;
  border: none;
  background: transparent;
  cursor: pointer;
  transition: all 0.2s ease;
  color: #0F172A;
  font-family: inherit;
}

.aspect-menu-item:hover {
  background: #F8FAFC;
}

.aspect-menu-item.active {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.08) 0%, rgba(37, 99, 235, 0.12) 100%);
  color: #3B82F6;
}

.aspect-menu-item-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.aspect-menu-label {
  font-size: 13px;
  font-weight: 600;
}

.aspect-menu-desc {
  font-size: 11px;
  color: #94A3B8;
}

.aspect-menu-item.active .aspect-menu-desc {
  color: #3B82F6;
}

/* 小预览框 */
.aspect-preview-small {
  border: 1.5px solid currentColor;
  border-radius: 2px;
  position: relative;
  flex-shrink: 0;
}

.aspect-preview-small::after {
  content: '';
  position: absolute;
  inset: 1.5px;
  background: currentColor;
  opacity: 0.15;
  border-radius: 1px;
}

.aspect-menu-item.active .aspect-preview-small::after {
  opacity: 0.3;
}

.aspect-16-9-small {
  width: 20px;
  height: 11px;
}

.aspect-4-3-small {
  width: 16px;
  height: 12px;
}

.aspect-1-1-small {
  width: 14px;
  height: 14px;
}

/* Dropdown transition */
.dropdown-enter-active,
.dropdown-leave-active {
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

.next-btn {
  border: none;
  border-radius: 12px;
  padding: 10px 24px;
  color: #FFFFFF;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.01em;
  cursor: pointer;
  background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%);
  box-shadow: 0 4px 14px rgba(59, 130, 246, 0.3);
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  font-family: inherit;
  position: relative;
  overflow: hidden;
}

.next-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
  transition: left 0.5s ease;
}

.next-btn:hover::before {
  left: 100%;
}

.next-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(59, 130, 246, 0.4);
}

.next-btn:active {
  transform: translateY(0);
}

.template-head {
  margin-top: 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.template-title {
  font-size: 16px;
  font-weight: 700;
  color: #0F172A;
  letter-spacing: -0.01em;
}

.toggle-wrap {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #475569;
  font-weight: 600;
  cursor: pointer;
  user-select: none;
}

.toggle-input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}

.toggle {
  width: 48px;
  height: 26px;
  border-radius: 999px;
  background: #CBD5E1;
  border: 2px solid transparent;
  position: relative;
  transition: all 0.2s ease;
}

.toggle::after {
  content: "";
  position: absolute;
  left: 2px;
  top: 2px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #FFFFFF;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.15);
  transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.toggle-input:checked + .toggle {
  background: #3B82F6;
  border-color: #2563EB;
}

.toggle-input:checked + .toggle::after {
  transform: translateX(22px);
}

.template-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}

.template-item {
  position: relative;
  aspect-ratio: 4 / 3;
  border-radius: 14px;
  border: 2px solid #E2E8F0;
  background: #FFFFFF;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.template-item:hover {
  border-color: #3B82F6;
  transform: translateY(-4px);
  box-shadow: 0 12px 28px rgba(59, 130, 246, 0.15);
}

.template-item.selected {
  border-color: #3B82F6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15), 0 8px 24px rgba(59, 130, 246, 0.12);
}

.template-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s ease;
}

.template-item:hover img {
  transform: scale(1.03);
}

.template-name {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 8px 10px;
  background: linear-gradient(transparent, rgba(15, 23, 42, 0.75));
  color: white;
  font-size: 12px;
  font-weight: 600;
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  backdrop-filter: blur(4px);
}

.template-selected-overlay {
  position: absolute;
  inset: 0;
  background: rgba(59, 130, 246, 0.08);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  backdrop-filter: blur(2px);
}

.template-selected-text {
  color: #FFFFFF;
  font-size: 15px;
  font-weight: 700;
  text-shadow: 0 2px 8px rgba(59, 130, 246, 0.4);
  padding: 6px 14px;
  background: rgba(59, 130, 246, 0.9);
  border-radius: 8px;
}

.template-remove {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: rgba(239, 68, 68, 0.9);
  color: #FFFFFF;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: 700;
  cursor: pointer;
  opacity: 0;
  transition: all 0.2s ease;
  z-index: 2;
  box-shadow: 0 2px 8px rgba(239, 68, 68, 0.3);
}

.template-remove:hover {
  background: rgba(220, 38, 38, 1);
  transform: scale(1.1);
}

.template-upload {
  border: 2px dashed #CBD5E1;
  border-radius: 14px;
  aspect-ratio: 4 / 3;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 8px;
  color: #64748B;
  font-size: 13px;
  font-weight: 600;
  background: #FAFBFC;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.template-upload:hover {
  border-color: #3B82F6;
  color: #3B82F6;
  background: #F0F7FF;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.1);
}

.text-style-panel {
  display: none;
  border: 2px solid #E2E8F0;
  border-radius: 16px;
  background: #FFFFFF;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06);
}

.text-style-panel.active {
  display: block;
  animation: rise 0.3s ease;
}

.style-textarea {
  width: 100%;
  min-height: 100px;
  resize: vertical;
  border-radius: 12px;
  border: 2px solid #E2E8F0;
  background: #FAFBFC;
  padding: 14px 16px;
  outline: none;
  font-size: 14px;
  line-height: 1.7;
  color: #0F172A;
  font-family: inherit;
  margin-bottom: 16px;
  transition: all 0.2s ease;
}

.style-textarea:focus {
  border-color: #3B82F6;
  background: #FFFFFF;
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.08);
}

.preset-label {
  font-size: 12px;
  color: #48637f;
  font-weight: 600;
  margin-bottom: 8px;
}

.preset-section {
  margin-bottom: 8px;
}

.preset-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;
}

.preset-btn {
  border: 2px solid #E2E8F0;
  border-radius: 999px;
  background: #FFFFFF;
  color: #475569;
  font-size: 13px;
  font-weight: 600;
  height: 36px;
  padding: 0 16px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  font-family: inherit;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.preset-btn:hover {
  border-color: #3B82F6;
  color: #2563EB;
  background: #F0F7FF;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.1);
}

.preset-btn.active {
  border-color: #3B82F6;
  color: #FFFFFF;
  background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%);
  box-shadow: 0 4px 14px rgba(59, 130, 246, 0.25);
}

.preset-btn-wrap {
  position: relative;
}

.preset-preview {
  position: absolute;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%);
  z-index: 100;
  margin-bottom: 12px;
  width: 300px;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.2);
  background: white;
  border: 2px solid #3B82F6;
  animation: presetPreviewFadeIn 0.2s ease;
}

@keyframes presetPreviewFadeIn {
  from {
    opacity: 0;
    transform: translateX(-50%) translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
}

.preset-preview-img {
  width: 100%;
  height: 160px;
  object-fit: cover;
  display: block;
}

.preset-preview-desc {
  padding: 10px 12px;
  font-size: 12px;
  color: #48637f;
  line-height: 1.5;
  max-height: 60px;
  overflow: hidden;
}

.preset-preview-arrow {
  position: absolute;
  bottom: -7px;
  left: 50%;
  transform: translateX(-50%) rotate(45deg);
  width: 12px;
  height: 12px;
  background: white;
  border-right: 2px solid rgb(76, 128, 245);
  border-bottom: 2px solid rgb(76, 128, 245);
}

.upload-style-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 0 12px;
  border: 2px dashed #afc4db;
  border-radius: 999px;
  background: rgba(245, 251, 255, 0.82);
  color: #39587a;
  font-size: 12px;
  font-weight: 600;
  height: 32px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
}

.upload-style-btn:hover {
  border-color: rgb(76, 128, 245);
  color: rgb(76, 128, 245);
  background: rgba(223, 237, 250, 0.84);
}

.preset-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  border: 1px solid rgba(0, 0, 0, 0.08);
}

.style-tip {
  font-size: 13px;
  color: #64748B;
  line-height: 1.6;
  font-weight: 400;
  padding: 10px 14px;
  background: #F8FAFC;
  border-radius: 10px;
  border-left: 3px solid #3B82F6;
}

/* File Upload Zone */
.file-upload-zone {
  border: 2px dashed #CBD5E1;
  border-radius: 16px;
  padding: 36px 24px;
  text-align: center;
  margin-bottom: 20px;
  background: #FAFBFC;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: default;
}

.file-upload-zone.dragging {
  border-color: #3B82F6;
  background: #F0F7FF;
  border-style: solid;
  transform: scale(1.01);
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.08);
}

.file-upload-zone.has-file {
  border-style: solid;
  border-color: #3B82F6;
  background: #F0F7FF;
  padding: 20px 24px;
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.08);
}

.upload-icon {
  color: #94A3B8;
  margin-bottom: 12px;
}

.upload-text {
  font-size: 15px;
  color: #475569;
  margin: 0 0 6px;
  font-weight: 500;
}

.upload-link {
  color: #3B82F6;
  cursor: pointer;
  font-weight: 600;
  text-decoration: underline;
  text-underline-offset: 2px;
  transition: color 0.2s ease;
}

.upload-link:hover {
  color: #2563EB;
}

.upload-hint {
  font-size: 13px;
  color: #94A3B8;
  margin: 0;
  font-weight: 400;
}

.uploaded-file-info {
  display: flex;
  align-items: center;
  gap: 12px;
  justify-content: center;
  color: #0F172A;
}

.uploaded-file-name {
  font-size: 15px;
  font-weight: 600;
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.uploaded-file-size {
  font-size: 13px;
  color: #64748B;
  font-weight: 500;
}

.uploaded-file-remove {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  border: 2px solid #FEE2E2;
  background: #FEF2F2;
  color: #EF4444;
  font-size: 18px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
  transition: all 0.2s ease;
}

.uploaded-file-remove:hover {
  background: #EF4444;
  border-color: #EF4444;
  color: #FFFFFF;
  transform: scale(1.1);
}

.selected-lib-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 16px;
}

.selected-lib-tag {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  border-radius: 999px;
  background: linear-gradient(135deg, #EFF6FF 0%, #DBEAFE 100%);
  color: #1E40AF;
  font-size: 13px;
  font-weight: 600;
  border: 1px solid #BFDBFE;
  transition: all 0.2s ease;
}

.selected-lib-tag:hover {
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.15);
}

.tag-remove {
  border: none;
  background: transparent;
  color: inherit;
  cursor: pointer;
  font-size: 16px;
  line-height: 1;
  opacity: 0.6;
  transition: opacity 0.2s ease;
}

.tag-remove:hover {
  opacity: 1;
}

/* 知识库弹窗样式 */
.lib-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.lib-modal {
  background: #FFFFFF;
  border-radius: 20px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  max-width: 600px;
  width: 100%;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: modalSlideIn 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes modalSlideIn {
  from {
    opacity: 0;
    transform: scale(0.95) translateY(10px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.lib-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid #E2E8F0;
}

.lib-modal-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: #0F172A;
}

.lib-modal-title svg {
  color: #3B82F6;
}

.lib-modal-close {
  width: 32px;
  height: 32px;
  border: none;
  background: #F8FAFC;
  border-radius: 8px;
  font-size: 20px;
  color: #64748B;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.lib-modal-close:hover {
  background: #F1F5F9;
  color: #0F172A;
}

.lib-modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
}

.lib-section {
  margin-bottom: 24px;
}

.lib-section:last-child {
  margin-bottom: 0;
}

.lib-section-title {
  font-size: 12px;
  font-weight: 700;
  color: #64748B;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 12px;
}

.lib-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 12px;
}

.lib-card {
  position: relative;
  border: 2px solid #E2E8F0;
  border-radius: 12px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s;
  background: #FFFFFF;
}

.lib-card:hover {
  border-color: #CBD5E1;
  background: #FAFBFC;
}

.lib-card-selected {
  border-color: #3B82F6;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.04) 0%, rgba(37, 99, 235, 0.06) 100%);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
}

.lib-card-check {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #3B82F6;
  color: #FFFFFF;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: bold;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);
}

.lib-card-info {
  margin-right: 40px;
}

.lib-card-name {
  font-size: 14px;
  font-weight: 600;
  color: #0F172A;
  margin-bottom: 4px;
}

.lib-card-desc {
  font-size: 12px;
  color: #64748B;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.lib-badge {
  position: absolute;
  bottom: 12px;
  right: 12px;
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
}

.lib-badge.personal {
  background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%);
  color: #FFFFFF;
}

.lib-badge.system {
  background: linear-gradient(135deg, #10B981 0%, #059669 100%);
  color: #FFFFFF;
}

.lib-empty {
  text-align: center;
  padding: 48px 20px;
  color: #94A3B8;
}

.lib-empty svg {
  margin-bottom: 16px;
  opacity: 0.4;
}

.lib-empty p {
  margin: 8px 0;
  font-size: 14px;
}

.lib-empty-hint {
  font-size: 12px;
  color: #CBD5E1;
}

.lib-modal-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  border-top: 1px solid #E2E8F0;
  background: #FAFBFC;
}

.lib-modal-count {
  font-size: 13px;
  color: #64748B;
  font-weight: 500;
}

.lib-modal-confirm {
  padding: 10px 24px;
  background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%);
  color: #FFFFFF;
  border: none;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

.lib-modal-confirm:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(59, 130, 246, 0.4);
}

/* Modal transition */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-active .lib-modal,
.modal-leave-active .lib-modal {
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.modal-enter-from .lib-modal,
.modal-leave-to .lib-modal {
  transform: scale(0.95) translateY(10px);
}

/* 旧样式保留用于兼容，但不使用 */
.lib-picker {
  display: none;
}

.lib-section {
  display: none;
}

.lib-section-title {
  display: none;
}

.lib-option {
  display: none;
}

.lib-empty {
  display: none;
}

.next-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none !important;
}

@keyframes rise {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 模板子区域样式 */
.template-subsection {
  margin-bottom: 28px;
}

.template-subsection:last-child {
  margin-bottom: 0;
}

.template-subsection-title {
  font-size: 15px;
  font-weight: 700;
  color: #0F172A;
  margin-bottom: 14px;
  letter-spacing: -0.01em;
  display: flex;
  align-items: center;
  gap: 8px;
}

.template-subsection-title::before {
  content: '';
  width: 4px;
  height: 18px;
  background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%);
  border-radius: 2px;
}

@media (max-width: 1024px) {
  .template-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .shell {
    padding: 0 14px 54px;
  }

  .hero {
    padding: 32px 0 22px;
  }

  .mode-tabs {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .template-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .template-head {
    flex-direction: column;
    align-items: flex-start;
  }

  .composer-toolbar {
    flex-direction: column;
    align-items: flex-start;
  }

  .lib-picker {
    grid-template-columns: 1fr;
  }

  .toolbar-right {
    width: 100%;
  }

  .next-btn {
    width: 100%;
    justify-content: center;
  }
}
</style>
