import { defineStore } from 'pinia'
import {
  fetchAllCourseware,
  uploadCourseware as apiUpload,
  updateCourseware as apiUpdate,
  deleteCoursewareItem as apiDelete,
  getDownloadUrl,
} from '../api/courseware.js'
import { apiRequest } from '../api/http.js'
import { deleteProject } from '../api/ppt.js'

export const useCoursewareStore = defineStore('courseware', {
  state: () => ({
    allCoursewareList: [],       // full unfiltered list (for favorites)
    filteredCoursewareList: [],  // current filtered view
    loading: false,
    error: null,
    favorites: new Set(),        // in-memory only
  }),

  getters: {
    favoritedList(state) {
      return state.allCoursewareList.filter(item => state.favorites.has(item.id))
    },
  },

  actions: {
    async fetchAll() {
      try {
        const data = await fetchAllCourseware()
        this.allCoursewareList = data.items || []
      } catch (e) {
        console.error('fetchAll failed:', e)
      }
    },

    async fetchFiltered(filters = {}) {
      this.loading = true
      this.error = null
      try {
        const data = await fetchAllCourseware(filters)
        this.filteredCoursewareList = data.items || []
      } catch (e) {
        this.error = e.message
      } finally {
        this.loading = false
      }
    },

    toggleFavorite(id) {
      if (this.favorites.has(id)) {
        this.favorites.delete(id)
      } else {
        this.favorites.add(id)
      }
      // Trigger reactivity (Set is not reactive by default in Pinia)
      this.favorites = new Set(this.favorites)
    },

    async deleteCourseware(id) {
      const [prefix, rawId] = _parseId(id)
      if (prefix === 'ppt') {
        await deleteProject(Number(rawId))
      } else if (prefix === 'lp') {
        await apiRequest(`/api/v1/lesson-plan/${rawId}`, { method: 'DELETE' })
      } else {
        await apiDelete(Number(rawId))
      }
      // Remove from both lists
      this.allCoursewareList = this.allCoursewareList.filter(i => i.id !== id)
      this.filteredCoursewareList = this.filteredCoursewareList.filter(i => i.id !== id)
      this.favorites.delete(id)
      this.favorites = new Set(this.favorites)
    },

    async updateCoursewareItem(id, data) {
      const [prefix, rawId] = _parseId(id)
      if (prefix === 'ppt') {
        await apiRequest(`/api/v1/ppt/projects/${rawId}`, {
          method: 'PUT',
          body: JSON.stringify({ title: data.title }),
        })
      } else if (prefix === 'lp') {
        await apiRequest(`/api/v1/lesson-plan/${rawId}`, {
          method: 'PATCH',
          body: JSON.stringify({ title: data.title }),
        })
      } else {
        await apiUpdate(Number(rawId), data)
      }
      // Update in both lists
      const updateItem = (item) => {
        if (item.id !== id) return item
        return { ...item, ...data, name: data.title || item.name }
      }
      this.allCoursewareList = this.allCoursewareList.map(updateItem)
      this.filteredCoursewareList = this.filteredCoursewareList.map(updateItem)
    },

    async uploadCourseware(file, meta) {
      const newItem = await apiUpload(file, meta)
      this.allCoursewareList.unshift(newItem)
      this.filteredCoursewareList.unshift(newItem)
      return newItem
    },

    downloadCourseware(item) {
      const [prefix, rawId] = _parseId(item.id)
      const sourceType = prefix === 'ppt' ? 'ppt' : prefix === 'lp' ? 'lesson_plan' : 'uploaded'
      const url = getDownloadUrl(sourceType, Number(rawId))
      window.open(url, '_blank')
    },
  },
})

function _parseId(id) {
  const idx = id.indexOf('_')
  return [id.slice(0, idx), id.slice(idx + 1)]
}
