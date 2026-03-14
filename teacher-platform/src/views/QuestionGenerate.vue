<script setup>
import { ref, computed } from 'vue'

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

function toggleDifficulty(level) {
  form.value.difficulty = level
}

function toggleType(key) {
  form.value.types[key] = !form.value.types[key]
}

function handleGenerate() {
  hasGenerated.value = true
}

const difficultyLabel = computed(() => {
  const map = { easy: '简单', medium: '中等', hard: '困难' }
  return map[form.value.difficulty]
})
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
          <button type="button" class="link-btn">上传 PDF / 文档</button>
        </div>
        <textarea
          v-model="form.source"
          class="source-input"
          placeholder="粘贴教学材料、知识点列表，或输入希望考察的内容..."
          rows="5"
        />
      </div>

      <button type="button" class="primary-btn" @click="handleGenerate">
        生成试题
      </button>
    </section>

    <!-- 右侧：生成后预览 -->
    <section v-if="hasGenerated" class="preview-card">
      <header class="preview-header">
        <h2 class="preview-title">试题预览</h2>
        <button type="button" class="outline-btn">保存试卷</button>
      </header>

      <div class="preview-body">
        <div class="question-block">
          <div class="q-tag">第 1 题 · 单选题</div>
          <p class="q-text">以下哪种排序算法在最坏情况下的时间复杂度为 O(n log n)?</p>
          <ul class="option-list">
            <li class="option">A. 冒泡排序</li>
            <li class="option active">B. 归并排序</li>
            <li class="option">C. 插入排序</li>
            <li class="option">D. 选择排序</li>
          </ul>
        </div>

        <div v-if="form.types.essay" class="question-block">
          <div class="q-tag yellow">第 2 题 · 论述题</div>
          <p class="q-text">
            请比较过程式编程与面向对象编程的不同，并举例说明在什么情境下更适合使用面向对象编程。
          </p>
          <div class="answer-hint">
            <div class="hint-title">参考要点：</div>
            <ul class="hint-list">
              <li>模块化与封装性</li>
              <li>继承、多态对代码复用的影响</li>
              <li>在大型项目或复杂业务建模中的优势</li>
            </ul>
          </div>
        </div>
      </div>

      <footer class="preview-footer">
        <button type="button" class="outline-btn">导出 PDF</button>
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
  align-items: center;
  justify-content: center;
}

.page-wrap.with-preview {
  align-items: stretch;
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
  border: none;
  background: transparent;
  color: #2563eb;
  font-size: 14px;
  cursor: pointer;
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

