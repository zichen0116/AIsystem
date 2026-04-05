<script setup>
import { ref, computed, onMounted } from 'vue'
import { usePptStore } from '@/stores/ppt'
import { createProject, getUserTemplates, extractStyleFromImage } from '@/api/ppt'
import { uploadReferenceFile } from '@/api/ppt'

const pptStore = usePptStore()

const creationType = ref('dialog')
const mainText = ref('')
const aspectRatio = ref('16:9')
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

// Examples removed per user request

const modeDescriptions = {
  dialog: '输入你的想法，AI 将为你生成完整的 PPT',
  file: '上传或粘贴文档内容，AI 自动解析并生成教学演示文稿',
  renovation: '上传 PDF 或 PPTX，AI 会解析并输出翻新版本 PPT'
}

const modeDescription = computed(() => modeDescriptions[creationType.value])

function selectMode(mode) {
  creationType.value = mode
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
      url: URL.createObjectURL(file),
      size: file.size
    })
  }
  event.target.value = ''
}

// 移除参考文件
function removeReferenceFile(index) {
  uploadedReferenceFiles.value.splice(index, 1)
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
  try {
    const templateImageUrl = resolveSelectedTemplateUrl()
    const effectiveTheme = (mainText.value || '').trim() || null
    const effectiveTemplateStyle = useTextStyle.value ? (templateStyle.value || '').trim() : null

    if (effectiveTheme && effectiveTheme.length > MAX_THEME_LENGTH) {
      alert(`主题（theme）最多 ${MAX_THEME_LENGTH} 个字符，请精简 main-textarea 内容。`)
      return
    }

    if (useTextStyle.value && !effectiveTemplateStyle) {
      alert('请先填写风格描述，或关闭“文字描述风格”。')
      return
    }
    const effectiveTemplateId = useTextStyle.value
      ? null
      : (selectedTemplateId.value || selectedPresetTemplateId.value || null)

    // 构建 settings
    const settings = {
      aspect_ratio: aspectRatio.value,
      template_id: effectiveTemplateId,
      template_image_url: templateImageUrl,
      template_style: effectiveTemplateStyle
    }

    const data = {
      title: mainText.value.slice(0, 100) || '未命名PPT',
      creation_type: creationType.value,
      outline_text: mainText.value,
      theme: effectiveTheme,
      template_style: effectiveTemplateStyle,
      settings: settings
    }

    const response = await createProject(data)
    pptStore.projectId = response.id
    pptStore.projectData = response
    pptStore.creationType = creationType.value
    pptStore.selectedPresetTemplateId = effectiveTemplateId
    pptStore.templateStyle = effectiveTemplateStyle || ''
    pptStore.aspectRatio = aspectRatio.value
    pptStore.outlineText = mainText.value
    pptStore.projectSettings = { ...pptStore.projectSettings, ...response.settings, ...settings }

    // Navigate to appropriate phase
    if (creationType.value === 'dialog') {
      pptStore.setPhase('dialog')
    } else if (creationType.value === 'file') {
      pptStore.setPhase('outline')
    } else if (creationType.value === 'renovation') {
      pptStore.setPhase('outline')
    }
  } catch (error) {
    console.error('create project failed:', error)
    const rawMessage = String(error?.message || '')
    const detailLines = parseBackendValidationDetails(rawMessage)
    alert(`创建项目失败：\n${detailLines.join('\n')}`)
  }
}
</script>

<template>
  <div class="ppt-home">
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

        <div class="composer">
          <textarea
            v-model="mainText"
            class="main-textarea"
            :placeholder="creationType === 'dialog' ? '输入你想制作的PPT主题，例如：帮我制作一份关于人工智能发展历程的教学演示文稿...' : creationType === 'file' ? '上传或粘贴文档内容...' : '上传 PDF 或 PPTX...'"
          ></textarea>
          <div class="composer-toolbar">
            <div class="toolbar-left">
              <button class="icon-btn" type="button" title="上传参考文件" @click="triggerReferenceFileUpload">📎</button>
              <button class="icon-btn" type="button" :title="isRecording ? '停止录音' : '语音输入'" @click="toggleVoiceInput">🎙️</button>
              <select v-model="aspectRatio" class="aspect-select">
                <option value="16:9">16:9</option>
                <option value="4:3">4:3</option>
                <option value="1:1">1:1</option>
              </select>
            </div>
            <div class="toolbar-right">
              <button class="next-btn" type="button" @click="handleNext">下一步</button>
            </div>
          </div>
        </div>

        <!-- 隐藏的参考文件上传输入框 -->
        <input
          ref="referenceFileInput"
          type="file"
          accept=".pdf,.ppt,.pptx,.doc,.docx"
          multiple
          @change="handleReferenceFileUpload"
          hidden
        >

        <!-- 已上传的参考文件显示 -->
        <div v-if="uploadedReferenceFiles.length > 0" class="reference-files">
          <div v-for="(file, index) in uploadedReferenceFiles" :key="index" class="reference-file-item">
            <span class="file-name">{{ file.name }}</span>
            <button class="file-remove" @click="removeReferenceFile(index)">×</button>
          </div>
        </div>

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
  </div>
</template>

<style scoped>
.ppt-home {
  flex: 1;
  overflow-y: auto;
  background: #ffffff;
}

.shell {
  max-width: 1120px;
  margin: 0 auto;
  padding: 0 22px 72px;
}

.hero {
  text-align: center;
  padding: 42px 0 30px;
  animation: rise 0.55s ease;
}

.hero h1 {
  margin-top: 0;
  font-size: clamp(2rem, 5vw, 3.4rem);
  line-height: 1.12;
  letter-spacing: -0.02em;
  color: #173357;
  font-weight: 800;
}

.hero p {
  margin-top: 14px;
  font-size: clamp(0.98rem, 1.8vw, 1.12rem);
  color: #475569;
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
  border: 1px solid #bfd0e4;
  background: rgba(244, 250, 255, 0.64);
  color: #475569;
  border-radius: 14px;
  padding: 12px 10px;
  text-align: center;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
}

.mode-tab:hover {
  border-color: #9eb7d3;
  transform: translateY(-1px);
}

.mode-tab.active {
  border-color: rgb(76, 128, 245);
  color: rgb(76, 128, 245);
  background: rgba(76, 128, 245, 0.14);
  box-shadow: inset 0 0 0 1px rgba(76, 128, 245, 0.2);
}

.mode-desc {
  border: 1px solid #c7d7e8;
  background: rgba(241, 248, 255, 0.68);
  color: #475569;
  border-radius: 14px;
  padding: 12px 14px;
  font-size: 14px;
  margin-bottom: 16px;
}

.composer {
  border: 1px solid #adc2db;
  border-radius: 20px;
  background: linear-gradient(180deg, rgba(245, 250, 255, 0.7) 0%, rgba(232, 240, 250, 0.48) 100%);
  overflow: hidden;
  margin-bottom: 16px;
}

.main-textarea {
  width: 100%;
  min-height: 150px;
  resize: vertical;
  border: none;
  outline: none;
  padding: 16px;
  line-height: 1.7;
  font-size: 15px;
  color: #1e293b;
  background: transparent;
  font-family: inherit;
}

.main-textarea::placeholder {
  color: #7f94ab;
}

.composer-toolbar {
  border-top: 1px solid #bfd0e2;
  padding: 10px 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  background: rgba(232, 241, 251, 0.52);
}

.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.reference-files {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
  padding: 8px 12px;
  background: rgba(241, 248, 255, 0.68);
  border: 1px solid #c7d7e8;
  border-radius: 10px;
}

.reference-file-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: rgba(76, 128, 245, 0.1);
  border: 1px solid rgba(76, 128, 245, 0.3);
  border-radius: 6px;
  font-size: 12px;
  color: #3f5771;
}

.file-name {
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-remove {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: none;
  background: rgba(76, 128, 245, 0.2);
  color: #3f5771;
  font-size: 12px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

.file-remove:hover {
  background: rgba(76, 128, 245, 0.4);
}

.icon-btn {
  width: 34px;
  height: 34px;
  border-radius: 8px;
  border: 1px solid transparent;
  background: transparent;
  color: #4e6784;
  cursor: pointer;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
}

.icon-btn:hover {
  border-color: #aec2d8;
  background: rgba(245, 250, 255, 0.76);
  color: #1d3f69;
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
  border: 1px solid #b8cade;
  border-radius: 8px;
  padding: 8px 10px;
  color: #3f5771;
  background: rgba(246, 251, 255, 0.74);
  font-size: 13px;
  outline: none;
  cursor: pointer;
}

.next-btn {
  border: none;
  border-radius: 10px;
  padding: 9px 18px;
  color: #f6fbff;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.02em;
  cursor: pointer;
  background: linear-gradient(140deg, rgb(76, 128, 245) 0%, rgb(56, 107, 219) 100%);
  box-shadow: 0 8px 22px rgba(49, 90, 137, 0.26);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  font-family: inherit;
}

.next-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 11px 26px rgba(44, 83, 128, 0.33);
}

.template-head {
  margin-top: 6px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
}

.template-title {
  font-size: 15px;
  font-weight: 700;
  color: #1f436f;
  letter-spacing: 0.01em;
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
  width: 44px;
  height: 24px;
  border-radius: 999px;
  background: #b6c8dc;
  border: 1px solid #9fb4ca;
  position: relative;
  transition: background 0.2s ease;
}

.toggle::after {
  content: "";
  position: absolute;
  left: 2px;
  top: 2px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #f7fbff;
  box-shadow: 0 1px 2px rgba(33, 55, 80, 0.3);
  transition: transform 0.2s ease;
}

.toggle-input:checked + .toggle {
  background: rgb(76, 128, 245);
  border-color: rgb(56, 107, 219);
}

.toggle-input:checked + .toggle::after {
  transform: translateX(20px);
}

.template-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 12px;
}

.template-item {
  position: relative;
  aspect-ratio: 4 / 3;
  border-radius: 12px;
  border: 2px solid transparent;
  background: linear-gradient(155deg, rgba(245, 250, 255, 0.85) 0%, rgba(219, 233, 248, 0.8) 100%);
  overflow: hidden;
  cursor: pointer;
  transition: all 0.2s ease;
}

.template-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.template-name {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 4px 6px;
  background: linear-gradient(transparent, rgba(0,0,0,0.6));
  color: white;
  font-size: 11px;
  font-weight: 500;
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.template-item:hover {
  border-color: #7a9fc7;
  transform: translateY(-2px);
  box-shadow: 0 8px 22px rgba(34, 64, 100, 0.1);
}

.template-item.selected {
  border-color: rgb(76, 128, 245);
  box-shadow: 0 0 0 3px rgba(76, 128, 245, 0.2);
}

.template-selected-overlay {
  position: absolute;
  inset: 0;
  background: rgba(76, 128, 245, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
}

.template-selected-text {
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
}

.template-remove {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.5);
  color: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.2s ease;
  z-index: 2;
}

.template-item.selected:hover .template-remove {
  opacity: 1;
}

.template-item:hover .template-remove {
  opacity: 1;
}

.template-upload {
  border: 2px dashed #a8bfd8;
  border-radius: 12px;
  aspect-ratio: 4 / 3;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 6px;
  color: #547395;
  font-size: 12px;
  font-weight: 600;
  background: rgba(241, 248, 255, 0.7);
  cursor: pointer;
  transition: all 0.2s ease;
}

.template-upload:hover {
  border-color: rgb(76, 128, 245);
  color: rgb(76, 128, 245);
  background: rgba(223, 236, 249, 0.76);
}

.text-style-panel {
  display: none;
  border: 1px solid #b6c8dd;
  border-radius: 14px;
  background: linear-gradient(170deg, rgba(243, 250, 255, 0.72) 0%, rgba(226, 237, 250, 0.64) 100%);
  padding: 14px;
  margin-bottom: 12px;
}

.text-style-panel.active {
  display: block;
  animation: rise 0.25s ease;
}

.style-textarea {
  width: 100%;
  min-height: 86px;
  resize: vertical;
  border-radius: 10px;
  border: 1px solid #a8bfd7;
  background: rgba(244, 250, 255, 0.8);
  padding: 11px 12px;
  outline: none;
  font-size: 14px;
  line-height: 1.6;
  color: #17395f;
  font-family: inherit;
  margin-bottom: 10px;
  transition: border-color 0.2s ease;
}

.style-textarea:focus {
  border-color: rgb(76, 128, 245);
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
  border: 1px solid #afc4db;
  border-radius: 999px;
  background: rgba(245, 251, 255, 0.82);
  color: #39587a;
  font-size: 12px;
  font-weight: 600;
  height: 32px;
  padding: 0 12px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
}

.preset-btn:hover {
  border-color: rgb(76, 128, 245);
  color: rgb(76, 128, 245);
  background: rgba(223, 237, 250, 0.84);
}

.preset-btn.active {
  border-color: rgb(76, 128, 245);
  color: rgb(76, 128, 245);
  background: rgba(223, 237, 250, 0.84);
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
  margin-bottom: 8px;
  width: 280px;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
  background: white;
  border: 2px solid rgb(76, 128, 245);
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
  font-size: 12px;
  color: #6a8099;
  line-height: 1.55;
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

  .toolbar-right {
    width: 100%;
  }

  .next-btn {
    width: 100%;
    justify-content: center;
  }
}
</style>
