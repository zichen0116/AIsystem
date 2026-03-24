/**
 * 登录页左侧角色插画眼球 / 身体动画（与 1.html 逻辑一致）
 */
import { ref, onMounted, onBeforeUnmount } from 'vue'

export function useLoginCharactersAnim({ showPassword, form }) {
  const purpleEl = ref(null)
  const blackEl = ref(null)
  const orangeEl = ref(null)
  const yellowEl = ref(null)
  const purpleEyes = ref(null)
  const blackEyes = ref(null)
  const orangeEyes = ref(null)
  const yellowEyes = ref(null)
  const yellowMouth = ref(null)

  let mouseX = 0
  let mouseY = 0
  let isTyping = false
  let lookingAtEachOther = false
  let purpleBlink = false
  let blackBlink = false
  let purplePeeking = false
  let rafId = 0
  let peekInterval = null

  function triggerLookAtEachOther() {
    lookingAtEachOther = true
    setTimeout(() => {
      lookingAtEachOther = false
    }, 800)
  }

  function scheduleBlink(setter) {
    const delay = Math.random() * 4000 + 3000
    setTimeout(() => {
      setter(true)
      setTimeout(() => {
        setter(false)
        scheduleBlink(setter)
      }, 150)
    }, delay)
  }

  function schedulePeek() {
    const passwordLen = (form.value.password || '').length
    const show = showPassword.value
    if (passwordLen > 0 && show) {
      const delay = Math.random() * 3000 + 2000
      setTimeout(() => {
        if ((form.value.password || '').length > 0 && showPassword.value) {
          purplePeeking = true
          setTimeout(() => {
            purplePeeking = false
            schedulePeek()
          }, 800)
        }
      }, delay)
    }
  }

  function onMouseMove(e) {
    mouseX = e.clientX
    mouseY = e.clientY
  }

  function onPhoneFocus() {
    isTyping = true
    triggerLookAtEachOther()
  }
  function onPhoneBlur() {
    isTyping = false
    lookingAtEachOther = false
  }
  function onPasswordFocus() {
    isTyping = true
    triggerLookAtEachOther()
  }
  function onPasswordBlur() {
    isTyping = false
    lookingAtEachOther = false
  }

  function calcPos(el) {
    if (!el) return { faceX: 0, faceY: 0, bodySkew: 0 }
    const rect = el.getBoundingClientRect()
    const cx = rect.left + rect.width / 2
    const cy = rect.top + rect.height / 3
    const dx = mouseX - cx
    const dy = mouseY - cy
    return {
      faceX: Math.max(-15, Math.min(15, dx / 20)),
      faceY: Math.max(-10, Math.min(10, dy / 30)),
      bodySkew: Math.max(-6, Math.min(6, -dx / 120)),
    }
  }

  function eyePupilOffset(el, maxDist, forceX, forceY) {
    if (forceX !== undefined && forceY !== undefined) return { x: forceX, y: forceY }
    if (!el) return { x: 0, y: 0 }
    const rect = el.getBoundingClientRect()
    const cx = rect.left + rect.width / 2
    const cy = rect.top + rect.height / 2
    const dx = mouseX - cx
    const dy = mouseY - cy
    const dist = Math.min(Math.sqrt(dx * dx + dy * dy), maxDist)
    const angle = Math.atan2(dy, dx)
    return { x: Math.cos(angle) * dist, y: Math.sin(angle) * dist }
  }

  function setPupil(eyeEl, maxDist, forceX, forceY) {
    if (!eyeEl) return
    const pupil = eyeEl.querySelector('.pupil')
    if (!pupil) return
    const o = eyePupilOffset(eyeEl, maxDist, forceX, forceY)
    pupil.style.transform = `translate(${o.x}px, ${o.y}px)`
  }

  function setPupilOnly(el, maxDist, forceX, forceY) {
    if (!el) return
    const o = eyePupilOffset(el, maxDist, forceX, forceY)
    el.style.transform = `translate(${o.x}px, ${o.y}px)`
  }

  function render() {
    const $purple = purpleEl.value
    const $black = blackEl.value
    const $orange = orangeEl.value
    const $yellow = yellowEl.value
    const $purpleEyes = purpleEyes.value
    const $blackEyes = blackEyes.value
    const $orangeEyes = orangeEyes.value
    const $yellowEyes = yellowEyes.value
    const $yellowMouth = yellowMouth.value

    const passwordLen = (form.value.password || '').length
    const isShowingPw = passwordLen > 0 && showPassword.value
    const isHiding = passwordLen > 0 && !showPassword.value

    const pp = calcPos($purple)
    const bp = calcPos($black)
    const op = calcPos($orange)
    const yp = calcPos($yellow)

    if ($purple && $purpleEyes) {
      if (isShowingPw) {
        $purple.style.transform = 'skewX(0deg)'
        $purple.style.height = '400px'
      } else if (isTyping || isHiding) {
        $purple.style.transform = `skewX(${(pp.bodySkew || 0) - 12}deg) translateX(40px)`
        $purple.style.height = '440px'
      } else {
        $purple.style.transform = `skewX(${pp.bodySkew || 0}deg)`
        $purple.style.height = '400px'
      }
      const purpleEyeL = $purpleEyes.children[0]
      const purpleEyeR = $purpleEyes.children[1]
      if (purpleEyeL) purpleEyeL.style.height = purpleBlink ? '2px' : '18px'
      if (purpleEyeR) purpleEyeR.style.height = purpleBlink ? '2px' : '18px'
      let pfx
      let pfy
      if (isShowingPw) {
        $purpleEyes.style.left = '20px'
        $purpleEyes.style.top = '35px'
        pfx = purplePeeking ? 4 : -4
        pfy = purplePeeking ? 5 : -4
      } else if (lookingAtEachOther) {
        $purpleEyes.style.left = '55px'
        $purpleEyes.style.top = '65px'
        pfx = 3
        pfy = 4
      } else {
        $purpleEyes.style.left = `${45 + pp.faceX}px`
        $purpleEyes.style.top = `${40 + pp.faceY}px`
        pfx = undefined
        pfy = undefined
      }
      setPupil(purpleEyeL, 5, pfx, pfy)
      setPupil(purpleEyeR, 5, pfx, pfy)
    }

    if ($black && $blackEyes) {
      if (isShowingPw) {
        $black.style.transform = 'skewX(0deg)'
      } else if (lookingAtEachOther) {
        $black.style.transform = `skewX(${(bp.bodySkew || 0) * 1.5 + 10}deg) translateX(20px)`
      } else if (isTyping || isHiding) {
        $black.style.transform = `skewX(${(bp.bodySkew || 0) * 1.5}deg)`
      } else {
        $black.style.transform = `skewX(${bp.bodySkew || 0}deg)`
      }
      const blackEyeL = $blackEyes.children[0]
      const blackEyeR = $blackEyes.children[1]
      if (blackEyeL) blackEyeL.style.height = blackBlink ? '2px' : '16px'
      if (blackEyeR) blackEyeR.style.height = blackBlink ? '2px' : '16px'
      let bfx
      let bfy
      if (isShowingPw) {
        $blackEyes.style.left = '10px'
        $blackEyes.style.top = '28px'
        bfx = -4
        bfy = -4
      } else if (lookingAtEachOther) {
        $blackEyes.style.left = '32px'
        $blackEyes.style.top = '12px'
        bfx = 0
        bfy = -4
      } else {
        $blackEyes.style.left = `${26 + bp.faceX}px`
        $blackEyes.style.top = `${32 + bp.faceY}px`
        bfx = undefined
        bfy = undefined
      }
      setPupil(blackEyeL, 4, bfx, bfy)
      setPupil(blackEyeR, 4, bfx, bfy)
    }

    if ($orange && $orangeEyes) {
      $orange.style.transform = isShowingPw ? 'skewX(0deg)' : `skewX(${op.bodySkew || 0}deg)`
      let ofx
      let ofy
      if (isShowingPw) {
        $orangeEyes.style.left = '50px'
        $orangeEyes.style.top = '85px'
        ofx = -5
        ofy = -4
      } else {
        $orangeEyes.style.left = `${82 + (op.faceX || 0)}px`
        $orangeEyes.style.top = `${90 + (op.faceY || 0)}px`
        ofx = undefined
        ofy = undefined
      }
      setPupilOnly($orangeEyes.children[0], 5, ofx, ofy)
      setPupilOnly($orangeEyes.children[1], 5, ofx, ofy)
    }

    if ($yellow && $yellowEyes && $yellowMouth) {
      $yellow.style.transform = isShowingPw ? 'skewX(0deg)' : `skewX(${yp.bodySkew || 0}deg)`
      let yfx
      let yfy
      if (isShowingPw) {
        $yellowEyes.style.left = '20px'
        $yellowEyes.style.top = '35px'
        $yellowMouth.style.left = '10px'
        $yellowMouth.style.top = '88px'
        yfx = -5
        yfy = -4
      } else {
        $yellowEyes.style.left = `${52 + (yp.faceX || 0)}px`
        $yellowEyes.style.top = `${40 + (yp.faceY || 0)}px`
        $yellowMouth.style.left = `${40 + (yp.faceX || 0)}px`
        $yellowMouth.style.top = `${88 + (yp.faceY || 0)}px`
        yfx = undefined
        yfy = undefined
      }
      setPupilOnly($yellowEyes.children[0], 5, yfx, yfy)
      setPupilOnly($yellowEyes.children[1], 5, yfx, yfy)
    }

    rafId = requestAnimationFrame(render)
  }

  onMounted(() => {
    document.addEventListener('mousemove', onMouseMove)
    scheduleBlink((v) => {
      purpleBlink = v
    })
    scheduleBlink((v) => {
      blackBlink = v
    })
    peekInterval = setInterval(() => {
      const passwordLen = (form.value.password || '').length
      if (passwordLen > 0 && showPassword.value && !purplePeeking) schedulePeek()
    }, 1000)
    rafId = requestAnimationFrame(render)
  })

  onBeforeUnmount(() => {
    document.removeEventListener('mousemove', onMouseMove)
    if (peekInterval != null) clearInterval(peekInterval)
    if (rafId) cancelAnimationFrame(rafId)
  })

  return {
    purpleEl,
    blackEl,
    orangeEl,
    yellowEl,
    purpleEyes,
    blackEyes,
    orangeEyes,
    yellowEyes,
    yellowMouth,
    onPhoneFocus,
    onPhoneBlur,
    onPasswordFocus,
    onPasswordBlur,
  }
}
