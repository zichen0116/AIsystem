import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '../stores/user'

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
  { path: '/:pathMatch(.*)*', redirect: '/' }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to) => {
  if (!to.meta?.requiresAuth) return true
  const userStore = useUserStore()
  if (userStore.isLoggedIn) return true
  return { path: '/login', query: { redirect: to.fullPath } }
})

export default router
