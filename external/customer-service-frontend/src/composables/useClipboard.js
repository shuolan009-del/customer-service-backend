import { reactive } from 'vue'

/**
 * 剪贴板复制（带「已复制」态，key 为消息 id）。
 * 优先 navigator.clipboard，非安全上下文回落 execCommand。
 */

const copiedMap = reactive({})

function legacyCopy(text) {
  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.setAttribute('readonly', '')
  textarea.style.position = 'fixed'
  textarea.style.opacity = '0'
  document.body.appendChild(textarea)
  textarea.select()
  let ok = false
  try {
    ok = document.execCommand('copy')
  } catch (error) {
    ok = false
  }
  document.body.removeChild(textarea)
  return ok
}

export function useClipboard() {
  async function copy(text, key) {
    const value = String(text ?? '')
    if (!value) return false
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(value)
      } else if (!legacyCopy(value)) {
        throw new Error('copy not supported')
      }
    } catch (error) {
      if (!legacyCopy(value)) return false
    }
    const token = key ?? value
    copiedMap[token] = true
    setTimeout(() => { copiedMap[token] = false }, 1800)
    return true
  }

  function isCopied(key) {
    return Boolean(copiedMap[key])
  }

  return { copy, isCopied }
}
