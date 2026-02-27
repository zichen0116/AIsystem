import { defineStore } from 'pinia'

export const useCoursewareStore = defineStore('courseware', {
  state: () => ({
    coursewareList: [
      { id: 1, name: '高等微积分与线性代数', type: 'pdf', size: '12.4 MB', subject: '数学', grade: '12年级', modifyDate: '2026年2月15日', daysAgo: 0, favorited: true },
      { id: 2, name: '光合作用与细胞呼吸', type: 'ppt', size: '45.0 MB', subject: '生物', grade: '10年级', modifyDate: '2026年2月14日', daysAgo: 1, favorited: true },
      { id: 3, name: 'Python入门编程', type: 'video', size: '210 MB', subject: '计算机科学', grade: '选修课', modifyDate: '2026年2月12日', daysAgo: 3, favorited: false },
      { id: 4, name: '第二次世界大战历史', type: 'pdf', size: '1.2 MB', subject: '历史', grade: '11年级', modifyDate: '2026年2月8日', daysAgo: 7, favorited: false },
      { id: 5, name: '量子力学基础', type: 'word', size: '8.4 MB', subject: '物理', grade: '12年级', modifyDate: '2026年2月5日', daysAgo: 10, favorited: false }
    ]
  }),
  getters: {
    favoritedList: (state) => state.coursewareList.filter(item => item.favorited)
  },
  actions: {
    toggleFavorite(id) {
      const item = this.coursewareList.find(i => i.id === id)
      if (item) item.favorited = !item.favorited
    },
    addCourseware(items) {
      const baseId = Math.max(0, ...this.coursewareList.map(i => i.id)) + 1
      items.forEach((item, i) => {
        this.coursewareList.unshift({ ...item, id: baseId + i })
      })
    }
  }
})
