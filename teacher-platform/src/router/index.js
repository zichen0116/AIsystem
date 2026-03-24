import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '../stores/user'
import { getToken } from '../api/http'

const routes = [
  { path: '/', name: 'Home', component: () => import('../views/Home.vue') },
  { path: '/login', name: 'Login', component: () => import('../views/LoginView.vue') },
  {
    path: '/lesson-prep',
    name: 'LessonPrep',
    component: () => import('../views/LessonPrep.vue'),
    meta: { requiresAuth: true, layout: 'nav' }
  },
  {
    path: '/courseware',
    name: 'CoursewareManage',
    component: () => import('../views/CoursewareManage.vue'),
    meta: { requiresAuth: true, layout: 'nav' }
  },
  {
    path: '/knowledge-base',
    name: 'KnowledgeBase',
    component: () => import('../views/KnowledgeBase.vue'),
    meta: { requiresAuth: true, layout: 'nav' }
  },
  {
    path: '/knowledge-base/:id',
    name: 'KnowledgeDetail',
    component: () => import('../views/KnowledgeDetail.vue'),
    meta: { requiresAuth: true, layout: 'nav' }
  },
  {
    path: '/personal-center',
    name: 'PersonalCenter',
    component: () => import('../views/PersonalCenter.vue'),
    meta: { requiresAuth: true, layout: 'nav' }
  },
  {
    path: '/question-gen',
    name: 'QuestionGenerate',
    component: () => import('../views/QuestionGenerate.vue'),
    meta: { requiresAuth: true, layout: 'nav' }
  },
  {
    path: '/resource-search',
    name: 'ResourceSearch',
    component: () => import('../views/ResourceSearch.vue'),
    meta: { requiresAuth: true, layout: 'nav' }
  },
  {
    path: '/admin',
    name: 'AdminDashboard',
    component: () => import('../views/admin/AdminDashboard.vue'),
    meta: { layout: 'nav' }
  },
  {
    path: '/admin/profile',
    name: 'AdminProfile',
    component: () => import('../views/admin/AdminProfile.vue'),
    meta: { requiresAuth: true, layout: 'nav' }
  },
  {
    path: '/admin/users',
    name: 'AdminUserManage',
    component: () => import('../views/admin/AdminUserManage.vue'),
    meta: { requiresAuth: true, layout: 'nav' }
  },
  {
    path: '/admin/audit',
    name: 'AdminResourceAudit',
    component: () => import('../views/admin/AdminResourceAudit.vue'),
    meta: { requiresAuth: true, layout: 'nav' }
  },
  {
    path: '/admin/logs',
    name: 'AdminSystemLogs',
    component: () => import('../views/admin/AdminSystemLogs.vue'),
    meta: { requiresAuth: true, layout: 'nav' }
  },
  { path: '/:pathMatch(.*)*', redirect: '/' }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 首屏是否已恢复登录态
let authRestored = false

router.beforeEach(async (to) => {
  const userStore = useUserStore()

  // 首屏：用 localStorage token 恢复登录态
  if (!authRestored) {
    authRestored = true
    if (getToken()) {
      await userStore.fetchUser()
    }
  }

  if (!to.meta?.requiresAuth) return true
  if (userStore.isLoggedIn) return true
  return { path: '/login', query: { redirect: to.fullPath } }
})

export default router
