/**
 * 工作台改造的真机验证（Chrome DevTools Protocol）。
 *
 * 为什么不用 `--screenshot`：静态截图点不了按钮、拿不到 console。
 * 本脚本用 Node 22 内置 WebSocket 直连 CDP，能验证「输入 → 发送 → 请求 →
 * 分组渲染 → 状态变化」这类只有真实交互才会暴露的行为。
 *
 * 用法：
 *   node scripts/verify-workbench.mjs [前端地址] [临时sender_id]
 * 依赖：Chrome（默认路径见 CHROME_CANDIDATES，可用 CHROME_PATH 覆盖）
 */
import { spawn } from 'node:child_process'
import { existsSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const BASE = process.argv[2] || 'http://127.0.0.1:5173'
const TEST_SENDER = process.argv[3] || `uverify${Date.now().toString().slice(-6)}`
const CDP_PORT = 9333
const SHOT_DIR = 'F:/customer-service-backend/docs/verify'

const CHROME_CANDIDATES = [
  process.env.CHROME_PATH,
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
].filter(Boolean)

const chromePath = CHROME_CANDIDATES.find((p) => existsSync(p))
if (!chromePath) {
  console.error('找不到 Chrome/Edge，可用环境变量 CHROME_PATH 指定')
  process.exit(2)
}

mkdirSync(SHOT_DIR, { recursive: true })
const profileDir = mkdtempSync(join(tmpdir(), 'wb-cdp-'))

const results = []
function check(name, ok, detail = '') {
  results.push({ name, ok, detail })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? `  — ${detail}` : ''}`)
}

class Cdp {
  constructor(ws) {
    this.ws = ws
    this.seq = 0
    this.pending = new Map()
    this.logs = []
  }

  static async connect(url) {
    const ws = new WebSocket(url)
    await new Promise((resolve, reject) => {
      ws.onopen = resolve
      ws.onerror = () => reject(new Error('CDP WebSocket 连接失败'))
    })
    const cdp = new Cdp(ws)
    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data)
      if (msg.id && cdp.pending.has(msg.id)) {
        const { resolve, reject } = cdp.pending.get(msg.id)
        cdp.pending.delete(msg.id)
        if (msg.error) reject(new Error(`${msg.error.message}`))
        else resolve(msg.result)
        return
      }
      // 页面 console / 异常 / 日志 —— 排障最需要的部分
      if (msg.method === 'Runtime.consoleAPICalled') {
        cdp.logs.push(`[${msg.params.type}] ${msg.params.args.map((a) => a.value ?? a.description ?? '').join(' ')}`)
      } else if (msg.method === 'Runtime.exceptionThrown') {
        cdp.logs.push(`[exception] ${msg.params.exceptionDetails.exception?.description || msg.params.exceptionDetails.text}`)
      } else if (msg.method === 'Log.entryAdded') {
        cdp.logs.push(`[log:${msg.params.entry.level}] ${msg.params.entry.text}`)
      } else if (msg.method === 'Network.responseReceived') {
        const { status, url } = msg.params.response
        if (status >= 400) cdp.logs.push(`[http ${status}] ${url}`)
      }
    }
    return cdp
  }

  send(method, params = {}) {
    const id = ++this.seq
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject })
      this.ws.send(JSON.stringify({ id, method, params }))
    })
  }

  async eval(expression) {
    const res = await this.send('Runtime.evaluate', {
      expression,
      awaitPromise: true,
      returnByValue: true,
    })
    if (res.exceptionDetails) {
      throw new Error(res.exceptionDetails.exception?.description || res.exceptionDetails.text)
    }
    return res.result.value
  }

  async waitFor(expression, { timeout = 20000, interval = 250, label = expression } = {}) {
    const deadline = Date.now() + timeout
    let last = null
    while (Date.now() < deadline) {
      last = await this.eval(expression)
      if (last) return last
      await new Promise((r) => setTimeout(r, interval))
    }
    throw new Error(`等待超时：${label}（最后取值 ${JSON.stringify(last)}）`)
  }

  async shot(name) {
    const res = await this.send('Page.captureScreenshot', { format: 'png' })
    const file = join(SHOT_DIR, `${name}.png`)
    writeFileSync(file, Buffer.from(res.data, 'base64'))
    return file
  }
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

/** 输入框赋值 + 触发 Vue 的 v-model */
const SET_INPUT = (selector, value) => `(() => {
  const el = document.querySelector(${JSON.stringify(selector)})
  if (!el) return false
  const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set
  setter.call(el, ${JSON.stringify(value)})
  el.dispatchEvent(new Event('input', { bubbles: true }))
  return true
})()`

const chrome = spawn(
  chromePath,
  [
    '--headless=new',
    '--disable-gpu',
    '--hide-scrollbars',
    '--no-first-run',
    '--no-default-browser-check',
    `--remote-debugging-port=${CDP_PORT}`,
    `--user-data-dir=${profileDir}`,
    '--window-size=1440,900',
    'about:blank',
  ],
  { stdio: 'ignore' },
)

let cdp = null
try {
  // 等 CDP 端口就绪
  let targets = null
  for (let i = 0; i < 40; i += 1) {
    try {
      const res = await fetch(`http://127.0.0.1:${CDP_PORT}/json/list`)
      targets = await res.json()
      if (targets.some((t) => t.type === 'page')) break
    } catch (error) {
      /* 还没起来 */
    }
    await sleep(300)
  }
  const page = targets?.find((t) => t.type === 'page')
  if (!page) throw new Error('拿不到 page target')

  cdp = await Cdp.connect(page.webSocketDebuggerUrl)
  await cdp.send('Page.enable')
  await cdp.send('Runtime.enable')
  await cdp.send('Log.enable')
  await cdp.send('Network.enable')
  await cdp.send('Emulation.setDeviceMetricsOverride', {
    width: 1440,
    height: 900,
    deviceScaleFactor: 2,
    mobile: false,
  })

  // ── 1. 工作台（u1001，有历史数据）──────────────────────────────────
  await cdp.send('Page.navigate', { url: `${BASE}/#/` })
  await cdp.waitFor("!!document.querySelector('.workbench__grid')", { label: '工作台挂载' })
  await cdp.waitFor("document.querySelectorAll('.row').length > 0 || document.querySelector('.welcome')", {
    label: '消息流或欢迎态出现',
  })
  await sleep(1200)

  const layout = await cdp.eval(`(() => {
    const cols = [...document.querySelectorAll('.workbench__grid > *')]
    return cols.map((el) => {
      const r = el.getBoundingClientRect()
      return { cls: el.className.split(' ')[0], top: Math.round(r.top), bottom: Math.round(r.bottom), h: Math.round(r.height) }
    })
  })()`)
  const tops = layout.map((c) => c.top)
  const bottoms = layout.map((c) => c.bottom)
  check(
    '三栏顶部对齐',
    new Set(tops).size === 1,
    `top = ${tops.join(' / ')}`,
  )
  check(
    '三栏底部对齐',
    new Set(bottoms).size === 1,
    `bottom = ${bottoms.join(' / ')}`,
  )

  const shape = await cdp.eval(`(() => {
    const rows = [...document.querySelectorAll('.row')]
    return {
      rows: rows.length,
      avatars: document.querySelectorAll('.row__gutter .avatar').length,
      dayLabels: [...document.querySelectorAll('.day__label span')].map((el) => el.textContent.trim()),
      turnCards: document.querySelectorAll('.turn-card').length,
      turnBadges: [...document.querySelectorAll('*')].filter((el) => /^Turn \\d+$/.test(el.textContent.trim())).length,
      bubbles: document.querySelectorAll('.bubble').length,
      objectCards: document.querySelectorAll('.object-card').length,
      sidebarItems: document.querySelectorAll('.sidebar__item').length,
      emojiLeft: (document.body.innerText.match(/[\\u{1F300}-\\u{1FAFF}]/gu) || []).length,
    }
  })()`)
  check('消息流已渲染', shape.rows > 0, `${shape.rows} 条消息 / ${shape.bubbles} 个气泡`)
  check('已无 Turn 卡片分块', shape.turnCards === 0 && shape.turnBadges === 0)
  check(
    '头像按「组」去重（头像数 < 消息数）',
    shape.avatars > 0 && shape.avatars < shape.rows,
    `头像 ${shape.avatars} / 消息 ${shape.rows}`,
  )
  check('历史消息归入「更早的记录」', shape.dayLabels.includes('更早的记录'), shape.dayLabels.join(' | '))
  check('右侧业务对象已加载', shape.sidebarItems > 0, `${shape.sidebarItems} 条`)
  check('页面无 emoji 图标残留', shape.emojiLeft === 0, `发现 ${shape.emojiLeft} 个`)

  const shot1 = await cdp.shot('01-workbench-u1001')

  // ── 2. 切到临时 sender + 真实发送 → 验证「今天」分组 ─────────────
  await cdp.eval(SET_INPUT('#workbench-sender', TEST_SENDER))
  await cdp.waitFor("!document.querySelector('.row')", { label: '切换 sender 后会话被重置' })
  await cdp.eval(SET_INPUT('#workbench-composer', '我要退款'))
  await sleep(200)
  const beforeRows = await cdp.eval("document.querySelectorAll('.row').length")
  await cdp.eval("document.querySelector('.composer button[type=submit]').click()")
  await cdp.waitFor("document.querySelectorAll('.row--out').length > 0", { label: '用户气泡出现' })
  // 等到「输入中」结束 —— 即本轮 bot 回复已经渲染完毕
  await cdp.waitFor("!document.querySelector('.typing')", { timeout: 60000, label: '本轮回复结束' })
  await cdp.waitFor(`document.querySelectorAll('.row').length >= ${beforeRows + 2}`, {
    timeout: 20000,
    label: '用户与客服消息都已渲染',
  })
  await sleep(1200)

  const after = await cdp.eval(`(() => {
    const rows = [...document.querySelectorAll('.row')]
    const t = (el) => el.textContent.replace(/\\s+/g, ' ').trim()
    return {
      rows: rows.length,
      avatars: document.querySelectorAll('.row__gutter .avatar').length,
      dayLabels: [...document.querySelectorAll('.day__label span')].map((el) => el.textContent.trim()),
      firstOut: t(document.querySelector('.row--out') || document.createElement('div')).slice(0, 60),
      metaText: [...document.querySelectorAll('.row__meta')].map(t),
      error: document.querySelector('.stream-wrap__alert')?.textContent.trim() || '',
      jump: document.querySelector('.jump') ? t(document.querySelector('.jump')) : '',
    }
  })()`)
  check('发送后出现用户气泡', after.rows >= beforeRows + 2, `${beforeRows} → ${after.rows} 条消息`)
  check('新消息归入「今天」分组', after.dayLabels.includes('今天'), after.dayLabels.join(' | '))
  check('组首显示时分', /\d{2}:\d{2}/.test(after.metaText.join(' ')), after.metaText.join(' / '))
  check('无错误提示', !after.error, after.error || '（无）')

  const shot2 = await cdp.shot('02-workbench-today-group')

  // ── 2b. Enter 键提交（P2-2：Composer 已移除 @enter，只应靠 form 隐式提交触发一次）──
  await cdp.eval(SET_INPUT('#workbench-composer', 'Enter 键提交测试'))
  await cdp.eval(`document.querySelector('#workbench-composer').focus()`)
  const outBeforeEnter = await cdp.eval("document.querySelectorAll('.row--out').length")
  // 注意：CDP 的 keyDown 必须带 text: '\r'，Chrome 才会合成 keypress，
  // form 隐式提交（Enter 发送）才会触发——这是 CDP 的手法要求，不是应用的坑。
  await cdp.send('Input.dispatchKeyEvent', {
    type: 'keyDown',
    key: 'Enter',
    code: 'Enter',
    text: '\r',
    windowsVirtualKeyCode: 13,
    nativeVirtualKeyCode: 13,
  })
  await cdp.send('Input.dispatchKeyEvent', {
    type: 'keyUp',
    key: 'Enter',
    code: 'Enter',
    windowsVirtualKeyCode: 13,
    nativeVirtualKeyCode: 13,
  })
  await cdp.waitFor(`document.querySelectorAll('.row--out').length === ${outBeforeEnter + 1}`, {
    timeout: 10000,
    label: 'Enter 提交后用户气泡 +1',
  })
  await sleep(2000) // 再等一拍，排除「迟到的第二次提交」
  const outAfterEnter = await cdp.eval("document.querySelectorAll('.row--out').length")
  check(
    'Enter 键经 form 隐式提交发送（恰好 +1，不双发）',
    outAfterEnter === outBeforeEnter + 1,
    `${outBeforeEnter} → ${outAfterEnter}`,
  )
  await cdp.waitFor("!document.querySelector('.typing')", { timeout: 60000, label: 'Enter 本轮回复结束' })

  // ── 3. 刷新后时间戳是否仍能命中（时间轴指纹的成败关键）+ 设置页偏好是否生效 ──
  await cdp.eval(
    `localStorage.setItem('cs-prefs', JSON.stringify({ defaultSenderId: ${JSON.stringify(TEST_SENDER)}, autoConnectAvatar: false, reduceMotion: false }))`,
  )
  await cdp.send('Page.navigate', { url: `${BASE}/#/` })
  await cdp.waitFor(
    `document.querySelector('#workbench-sender')?.value === ${JSON.stringify(TEST_SENDER)}`,
    { label: '系统设置里的 defaultSenderId 生效' },
  )
  check('系统设置 defaultSenderId 已生效', true, `切换到 ${TEST_SENDER}`)

  await cdp.waitFor("document.querySelectorAll('.row').length > 0", { label: '刷新后历史加载' })
  await sleep(1200)
  const reloaded = await cdp.eval(`(() => {
    return {
      rows: document.querySelectorAll('.row').length,
      dayLabels: [...document.querySelectorAll('.day__label span')].map((el) => el.textContent.trim()),
      metaText: [...document.querySelectorAll('.row__meta')].map((el) => el.textContent.replace(/\\s+/g, ' ').trim()),
    }
  })()`)
  check(
    '刷新后本地时间轴仍命中（仍归入「今天」）',
    reloaded.dayLabels.includes('今天'),
    reloaded.dayLabels.join(' | '),
  )
  check(
    '刷新后未退化为「更早的记录」',
    !reloaded.dayLabels.includes('更早的记录'),
    `${reloaded.dayLabels.join(' | ')}；meta: ${reloaded.metaText.join(' / ')}`,
  )
  const shot2b = await cdp.shot('02b-workbench-after-reload')

  // ── 4. ?debug=1 调试浮层 ─────────────────────────────────────────
  await cdp.send('Page.navigate', { url: `${BASE}/?debug=1#/` })
  await cdp.waitFor("!!document.querySelector('.workbench__grid')", { label: 'debug 模式挂载' })
  await sleep(1500)
  const debugInfo = await cdp.eval(`(() => {
    const items = [...document.querySelectorAll('.row__debug')].map((el) => el.textContent.trim())
    return { count: items.length, sample: items.slice(0, 4) }
  })()`)
  check('?debug=1 显示内部状态浮层', debugInfo.count > 0, `${debugInfo.count} 条，示例：${debugInfo.sample.join(' / ')}`)
  const shot3 = await cdp.shot('03-workbench-debug')

  // ── 5. 窄屏（CDP 设备模拟，不用 --window-size）────────────────────
  await cdp.send('Emulation.setDeviceMetricsOverride', {
    width: 390,
    height: 844,
    deviceScaleFactor: 2,
    mobile: true,
  })
  await cdp.send('Page.navigate', { url: `${BASE}/#/` })
  await cdp.waitFor("!!document.querySelector('.workbench__grid')", { label: '窄屏挂载' })
  await sleep(1500)
  const narrow = await cdp.eval(`(() => {
    const vw = window.innerWidth
    const over = [...document.querySelectorAll('body *')]
      .filter((el) => el.getBoundingClientRect().right > vw + 1)
      .slice(0, 5)
      .map((el) => el.className.toString().split(' ')[0] || el.tagName)
    return { vw, docScrollWidth: document.documentElement.scrollWidth, over }
  })()`)
  check(
    '390px 窄屏无横向溢出',
    narrow.docScrollWidth <= narrow.vw,
    `scrollWidth ${narrow.docScrollWidth} / viewport ${narrow.vw}${narrow.over.length ? ` 溢出元素：${narrow.over.join(',')}` : ''}`,
  )
  const shot4 = await cdp.shot('04-workbench-390')

  // ── 6. 其余三个路由仍可渲染 ───────────────────────────────────────
  for (const [label, hash] of [['会话记录', '#/sessions'], ['数据看板', '#/dashboard'], ['系统设置', '#/settings']]) {
    await cdp.send('Emulation.setDeviceMetricsOverride', {
      width: 1440, height: 900, deviceScaleFactor: 1, mobile: false,
    })
    await cdp.send('Page.navigate', { url: `${BASE}/${hash}` })
    await cdp.waitFor("!!document.querySelector('.admin-view')", { label: `${label} 挂载` })
    await sleep(900)
    const ok = await cdp.eval("document.querySelectorAll('.admin-view *').length > 20")
    check(`${label} 渲染正常`, ok)
  }

  // ── 7. console 报错 ──────────────────────────────────────────────
  const errors = cdp.logs.filter((l) => l.startsWith('[error]') || l.startsWith('[exception]'))
  check('页面无 JS 异常', errors.length === 0, errors.slice(0, 3).join(' || ') || '（无）')

  console.log('\n=== 截图 ===')
  for (const f of [shot1, shot2, shot2b, shot3, shot4]) console.log(f)
  if (cdp.logs.length) {
    console.log('\n=== 页面日志 ===')
    for (const line of cdp.logs.slice(0, 20)) console.log(line)
  }

  const failed = results.filter((r) => !r.ok)
  console.log(`\n=== 结果：${results.length - failed.length}/${results.length} 通过 ===`)
  if (failed.length) {
    for (const f of failed) console.log(`FAIL  ${f.name} — ${f.detail}`)
  }
  process.exitCode = failed.length ? 1 : 0
} catch (error) {
  console.error('验证中断：', error.message)
  if (cdp?.logs?.length) {
    console.error('--- 页面日志 ---')
    for (const line of cdp.logs.slice(0, 30)) console.error(line)
  }
  process.exitCode = 2
} finally {
  try { cdp?.ws?.close() } catch (error) { /* 忽略 */ }
  chrome.kill()
  await sleep(500)
  try { rmSync(profileDir, { recursive: true, force: true }) } catch (error) { /* 临时 profile，删不掉不影响结果 */ }
}
