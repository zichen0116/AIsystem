# 教室备课平台

基于 Vue 3 + Vite 构建的智能备课平台，支持课件管理、知识库与 AI 备课辅助。

## 功能概览

- **平台封面**：顶部导航栏，含 [进入备课]、[课件管理]、[知识库] 三个入口，右侧圆形头像
- **进入备课**：左侧导航含 [生成ppt和教案]、[做动画和小游戏]、[数据分析]、[知识图谱]，默认显示生成 PPT 与教案界面
- **课件管理**：展示课件列表，支持按日期、文件类型筛选，可添加新课件
- **知识库**：RAG 文档管理，文档仓库、来源映射、知识库容量展示
- **个人中心**：未登录时头像为灰色，点击弹出登录/注册弹窗；登录后点击进入个人中心

## 快速开始

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build
```

## 技术栈

- Vue 3
- Vue Router 4
- Pinia
- Vite

## 项目结构

```
src/
├── components/       # 公共组件
│   ├── LoginRegisterModal.vue   # 登录/注册弹窗
│   ├── LayoutWithNav.vue        # 带导航的布局
│   └── TopNav.vue               # 顶部导航栏
├── views/            # 页面
│   ├── Home.vue                 # 平台封面
│   ├── LessonPrep.vue           # 备课中心
│   ├── CoursewareManage.vue     # 课件管理
│   ├── KnowledgeBase.vue        # 知识库
│   └── PersonalCenter.vue       # 个人中心
├── stores/           # Pinia 状态
│   └── user.js
└── router/
    └── index.js
```
