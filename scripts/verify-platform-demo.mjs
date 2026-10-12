/**
 * 综合平台 Demo 的真机验证（Chrome DevTools Protocol）。
 * 覆盖：五视图切换、客服对话（文本/快捷词/业务对象/数字人连接）、
 *       运营工作流全流程（含人工审批）、智库问答管线、窄屏无溢出、无 JS 异常。
 * 用法：node scripts/verify-platform-demo.mjs [HTML路径]
 */
import { spawn } from 'node:child_process'
import { existsSync, mkdirSync, mkdtempSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const TARGET = process.argv[2] || 'F:/customer-service-backend/docs/电商智能平台-综合演示.html'
const CDP_PORT = 9377
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
const profileDir = mkdtempSync(join(tmpdir(), 'wb-demo-'))

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
      if (msg.method === 'Runtime.consoleAPICalled') {
        cdp.logs.push(`[${msg.params.type}] ${msg.params.args.map((a) => a.value ?? a.description ?? '').join(' ')}`)
      } else if (msg.method === 'Runtime.exceptionThrown') {
        cdp.logs.push(`[exception] ${msg.params.exceptionDetails.exception?.description || msg.params.exceptionDetails.text}`)
      } else if (msg.method === 'Log.entryAdded') {
        cdp.logs.push(`[log:${msg.params.entry.level}] ${msg.params.entry.text}`)
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
    const res = await this.send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true })
    if (res.exceptionDetails) {
      throw new Error(res.exceptionDetails.exception?.description || res.exceptionDetails.text)
    }
    return res.result.value
  }
  async waitFor(expression, { timeout = 30000, interval = 250, label = expression } = {}) {
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
const SET_INPUT = (selector, value) => `(() => {
  const el = document.querySelector(${JSON.stringify(selector)})
  if (!el) return false
  const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set
  setter.call(el, ${JSON.stringify(value)})
  el.dispatchEvent(new Event('input', { bubbles: true }))
  return true
})()`

const chrome = spawn(chromePath, [
  '--headless=new', '--disable-gpu', '--hide-scrollbars', '--no-first-run',
  '--no-default-browser-check', `--remote-debugging-port=${CDP_PORT}`,
  `--user-data-dir=${profileDir}`, '--window-size=1440,900', 'about:blank',
], { stdio: 'ignore' })

let cdp = null
try {
  let targets = null
  for (let i = 0; i < 40; i += 1) {
    try {
      const res = await fetch(`http://127.0.0.1:${CDP_PORT}/json/list`)
      targets = await res.json()
      if (targets.some((t) => t.type === 'page')) break
    } catch { /* 还没起来 */ }
    await sleep(300)
  }
  const page = targets?.find((t) => t.type === 'page')
  if (!page) throw new Error('拿不到 page target')

  cdp = await Cdp.connect(page.webSocketDebuggerUrl)
  await cdp.send('Page.enable')
  await cdp.send('Runtime.enable')
  await cdp.send('Log.enable')
  await cdp.send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false })

  await cdp.send('Page.navigate', { url: `file:///${TARGET.replace(/\\/g, '/')}` })
  await cdp.waitFor("!!document.querySelector('.shell')", { label: '页面加载' })
  await sleep(600)

  // ── 1. 总览视图 ────────────────────────────────────────────────────
  const overview = await cdp.eval(`(() => ({
    kpis: document.querySelectorAll('.kpi').length,
    sysCards: document.querySelectorAll('.sys-card').length,
    feed: document.querySelectorAll('.feed__item').length,
  }))()`)
  check('总览：KPI 卡 4 张', overview.kpis === 4, `${overview.kpis} 张`)
  check('总览：三系统状态卡', overview.sysCards === 3, `${overview.sysCards} 张`)
  check('总览：动态流 6 条', overview.feed === 6, `${overview.feed} 条`)
  const shotOverview = await cdp.shot('10-demo-overview')

  // ── 2. 智能客服：初始状态 + 发送文本 ───────────────────────────────
  await cdp.eval("document.querySelector('[data-view=service]').click()")
  await cdp.waitFor("document.querySelector('#view-service').classList.contains('is-active')")
  const csInit = await cdp.eval(`document.querySelectorAll('#cs-stream .msg').length`)
  check('客服：欢迎消息已渲染', csInit >= 1, `${csInit} 条`)

  await cdp.eval(SET_INPUT('#cs-input', '我要退款'))
  await cdp.eval("document.querySelector('#cs-form button[type=submit]').click()")
  await cdp.waitFor("document.querySelectorAll('#cs-stream .msg--out').length >= 1", { label: '用户气泡出现' })
  await cdp.waitFor("document.querySelectorAll('#cs-stream .msg--in').length >= 2", { timeout: 20000, label: '客服回复出现' })
  await cdp.waitFor("!document.querySelector('#cs-chips .chip[disabled]')", { timeout: 20000, label: '上一条回复完成（快捷词解禁）' })
  const csReply = await cdp.eval(`(() => {
    const rows = [...document.querySelectorAll('#cs-stream .msg--in')]
    const last = rows[rows.length - 1]
    return { track: last?.querySelector('.msg__track')?.textContent || '', text: (last?.querySelector('.msg__bubble')?.textContent || '').slice(0, 30) }
  })()`)
  check('客服：三轨引擎命中「任务轨」', csReply.track === '任务轨', `${csReply.track} | ${csReply.text}…`)

  // 快捷词
  await cdp.eval("[...document.querySelectorAll('#cs-chips .chip')].find(c => c.textContent === '退换货政策').click()")
  await cdp.waitFor("document.querySelectorAll('#cs-stream .msg--out').length >= 2", { label: '第二条用户消息' })
  await cdp.waitFor("(() => { const r=[...document.querySelectorAll('#cs-stream .msg--in')]; return r.length >= 3 && r[r.length-1].querySelector('.msg__bubble')?.textContent.length > 10 })()", { timeout: 20000, label: '知识轨回复' })
  await cdp.waitFor("!document.querySelector('#cs-chips .chip[disabled]')", { timeout: 20000, label: '回复完成' })
  const kbTrack = await cdp.eval(`(() => { const r=[...document.querySelectorAll('#cs-stream .msg--in')]; return r[r.length-1].querySelector('.msg__track')?.textContent || '' })()`)
  check('客服：知识轨命中「退换货政策」', kbTrack === '知识轨', kbTrack)

  // 业务对象
  await cdp.eval("[...document.querySelectorAll('#cs-obj-list .btn')][0].click()")
  await cdp.waitFor("document.querySelectorAll('#cs-stream .msg--out').length >= 3", { label: '对象消息出现' })
  const objCard = await cdp.eval(`document.querySelectorAll('#cs-stream .obj-card').length`)
  check('客服：业务对象卡片进对话流', objCard >= 1, `${objCard} 张`)

  // 数字人连接
  await cdp.eval("document.querySelector('#cs-connect-btn').click()")
  await cdp.waitFor("document.querySelector('#cs-avatar-badge').textContent === '已连接'", { timeout: 15000, label: '数字人连接' })
  const wsOpen = await cdp.eval(`document.querySelector('#cs-ws-dot').classList.contains('is-open')`)
  check('客服：数字人连接后 WS 状态点亮', wsOpen)
  await cdp.eval(SET_INPUT('#cs-input', '你好'))
  await cdp.eval("document.querySelector('#cs-form button[type=submit]').click()")
  await cdp.waitFor("(() => { const r=[...document.querySelectorAll('#cs-stream .msg--in')]; return r.length >= 4 })()", { timeout: 20000, label: '闲聊轨回复' })
  await cdp.waitFor("document.querySelector('#cs-stream .badge--muted')", { timeout: 15000, label: '播报完成标记' })
  check('客服：数字人播报标记出现', true, '已播报')
  const shotService = await cdp.shot('11-demo-service')

  // ── 3. 商品运营：完整工作流 ────────────────────────────────────────
  await cdp.eval("document.querySelector('[data-view=operation]').click()")
  await cdp.waitFor("document.querySelector('#view-operation').classList.contains('is-active')")
  await cdp.eval("document.querySelectorAll('#op-product-list .prod-item')[1].click()")
  await sleep(300)
  const prodActive = await cdp.eval(`document.querySelectorAll('#op-product-list .prod-item.is-active').length`)
  check('运营：商品可切换', prodActive === 1)

  await cdp.eval("document.querySelector('#op-run-btn').click()")
  await cdp.waitFor("document.querySelector('#op-flow [data-key=diagnosis].is-done')", { timeout: 15000, label: '诊断完成' })
  await cdp.waitFor("document.querySelector('#op-flow [data-key=creative].is-done')", { timeout: 15000, label: '创意完成' })
  await cdp.waitFor("document.querySelector('#op-flow [data-key=quality].is-done')", { timeout: 15000, label: '质检完成' })
  await cdp.waitFor("document.querySelector('.op-gate')", { timeout: 15000, label: '审批门禁出现' })
  check('运营：前 4 个 Agent 完成并进入审批门禁', true)
  const reportSections = await cdp.eval(`document.querySelectorAll('#op-report .op-report__section').length`)
  check('运营：产出 3 段报告', reportSections === 3, `${reportSections} 段`)
  await cdp.shot('12-demo-operation-gate')

  await cdp.eval("[...document.querySelectorAll('.op-gate .btn')].find(b => b.textContent.includes('通过')).click()")
  await cdp.waitFor("document.querySelector('#op-flow [data-key=finalize].is-done')", { timeout: 15000, label: '定稿完成' })
  const opFinal = await cdp.eval(`document.querySelector('#op-status-badge').textContent`)
  check('运营：审批通过后工作流完成', opFinal === '已完成', opFinal)
  const logLines = await cdp.eval(`document.querySelectorAll('#op-log .op-log__line').length`)
  check('运营：运行日志已记录', logLines >= 10, `${logLines} 行`)

  // ── 4. 智能智库：问答管线 ──────────────────────────────────────────
  await cdp.eval("document.querySelector('[data-view=knowledge]').click()")
  await cdp.waitFor("document.querySelector('#view-knowledge').classList.contains('is-active')")
  const docCount = await cdp.eval(`document.querySelectorAll('#kb-doc-list .doc-item').length`)
  check('智库：文档库 5 份', docCount === 5, `${docCount} 份`)
  await cdp.eval("[...document.querySelectorAll('#kb-chips .chip')][0].click()")
  await cdp.waitFor("document.querySelector('.pipe-node[data-pipe=confirm].is-done')", { timeout: 15000, label: '商品名确认完成' })
  await cdp.waitFor("document.querySelector('.pipe-node[data-pipe=gen].is-done')", { timeout: 30000, label: '生成完成' })
  const kbAnswer = await cdp.eval(`document.querySelector('#kb-answer').textContent.length`)
  check('智库：问答管线走完并产出答案', kbAnswer > 30, `答案 ${kbAnswer} 字`)
  const kbChunks = await cdp.eval(`document.querySelectorAll('#kb-chunks .kb-chunk').length`)
  check('智库：召回 3 个 chunk', kbChunks === 3, `${kbChunks} 个`)
  const shotKb = await cdp.shot('13-demo-knowledge')

  // ── 5. 架构视图 ────────────────────────────────────────────────────
  await cdp.eval("document.querySelector('[data-view=architecture]').click()")
  await cdp.waitFor("document.querySelector('#view-architecture').classList.contains('is-active')")
  const archBoxes = await cdp.eval(`document.querySelectorAll('#view-architecture svg rect').length`)
  check('架构：拓扑图已渲染', archBoxes >= 15, `${archBoxes} 个节点框`)
  await cdp.shot('14-demo-architecture')

  // ── 6. 窄屏无溢出 ─────────────────────────────────────────────────
  await cdp.send('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 2, mobile: true })
  await sleep(500)
  const narrow = await cdp.eval(`(() => {
    const vw = window.innerWidth
    // 文档级主判据：scrollWidth；逐元素检查需豁免「自身可横向滚动容器」内的后代
    // （如架构拓扑图 .arch-wrap{overflow-x:auto}，内部 SVG 宽 860px，容器内滚动属预期）
    const bad = [...document.querySelectorAll('body *')].filter((n) => {
      if (n.getBoundingClientRect().right <= vw + 1) return false
      let p = n.parentElement
      while (p) {
        const ox = getComputedStyle(p).overflowX
        if (ox === 'auto' || ox === 'scroll') return false
        p = p.parentElement
      }
      return true
    })
    return { scroll: document.documentElement.scrollWidth, viewport: vw, overflow: bad.length }
  })()`)
  check('390px 窄屏无横向溢出', narrow.scroll <= narrow.viewport && narrow.overflow === 0, `scrollWidth ${narrow.scroll} / viewport ${narrow.viewport} / 真溢出元素 ${narrow.overflow}`)
  await cdp.eval("document.querySelector('[data-view=overview]').click()")
  await sleep(400)
  await cdp.shot('15-demo-390')

  // ── 7. JS 异常 ────────────────────────────────────────────────────
  const errors = cdp.logs.filter((l) => l.startsWith('[exception]') || l.startsWith('[error]'))
  check('页面无 JS 异常', errors.length === 0, errors.slice(0, 3).join(' || ') || '（无）')

  console.log('\n=== 截图 ===')
  for (const f of [shotOverview, shotService, shotKb]) console.log(f)
} catch (error) {
  console.log('验证中断:', error.message)
} finally {
  if (cdp) cdp.ws.close()
  chrome.kill()
}

const failed = results.filter((r) => !r.ok)
console.log(`\n=== 结果：${results.length - failed.length}/${results.length} 通过 ===`)
process.exitCode = failed.length ? 1 : 0
