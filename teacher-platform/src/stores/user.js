import { defineStore } from 'pinia'

export const useUserStore = defineStore('user', {
  state: () => ({
    isLoggedIn: false,
    userInfo: null
  }),
  actions: {
    login(userInfo) {
      this.isLoggedIn = true
      this.userInfo = userInfo
    },
    logout() {
      this.isLoggedIn = false
      this.userInfo = null
    }
  }
})
