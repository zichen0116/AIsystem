import { defineStore } from 'pinia'

export const useAdminDigitalHumanStore = defineStore('adminDigitalHuman', {
  state: () => ({
    visible: true,
    voiceMode: false
  }),
  actions: {
    toggleVisible() {
      this.visible = !this.visible
      if (!this.visible) this.voiceMode = false
    },
    toggleVoiceMode() {
      if (!this.visible) this.visible = true
      this.voiceMode = !this.voiceMode
    }
  }
})

