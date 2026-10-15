#!/usr/bin/env node
import { readFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const defaultBase = 'https://waynex.lincolab.com/api/open/v1'
const commands = {
  recruitments: '/recruitments', recruitment: '/recruitments/',
  'campus-events': '/campus-events', 'campus-event': '/campus-events/',
  'recruitment-filters': '/filters/recruitments', 'campus-filters': '/filters/campus-events',
}
export class QueryError extends Error {
  constructor(message, code, status = 0, retryAfter = 0, requestId) {
    super(message); this.code = code; this.status = status; this.retryAfter = retryAfter; this.requestId = requestId
  }
}
export function serviceBase(value = defaultBase) {
  const url = new URL(value)
  const loopback = ['localhost', '127.0.0.1', '[::1]'].includes(url.hostname)
  const trusted = ['https://waynex.lincolab.com', 'https://join-test.lincotalk.com'].includes(url.origin)
  if ((!trusted && !(loopback && ['http:', 'https:'].includes(url.protocol))) || url.username || url.password || url.search || url.hash || url.pathname.replace(/\/$/, '') !== '/api/open/v1') {
    throw new QueryError('服务地址必须是 Waynex 官方开放接口或本地测试接口', 'INVALID_BASE_URL')
  }
  return url.origin + '/api/open/v1'
}
export function buildUrl(command, id, params = {}, base = defaultBase) {
  if (!Object.hasOwn(commands, command)) throw new QueryError('不支持的查询命令；运行 --help 查看用法', 'INVALID_COMMAND')
  const detail = command === 'recruitment' || command === 'campus-event'
  if (detail && !/^[a-zA-Z0-9_-]{1,100}$/.test(id || '')) throw new QueryError('详情查询需要有效 ID', 'INVALID_ID')
  if (!detail && id) throw new QueryError('列表与字典命令不接受 ID', 'INVALID_ID')
  if (!params || typeof params !== 'object' || Array.isArray(params)) throw new QueryError('查询参数必须是 JSON 对象', 'INVALID_PARAMS')
  if ((detail || command.endsWith('-filters')) && Object.keys(params).length) throw new QueryError('详情与字典查询不接受筛选参数', 'INVALID_PARAMS')
  const url = new URL(serviceBase(base) + commands[command] + (detail ? encodeURIComponent(id) : ''))
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null) continue
    if (/api.?key|authorization|token|secret/i.test(key)) throw new QueryError('密钥只能通过 WAYNEX_API_KEY 环境变量提供', 'INVALID_PARAMS')
    const values = Array.isArray(value) ? value : [value]
    if (!values.length) throw new QueryError('多选参数不能为空数组；不筛选时请省略该参数', 'INVALID_PARAMS')
    if (values.some(item => !['string', 'number', 'boolean'].includes(typeof item))) throw new QueryError('参数值只支持字符串、数字或其数组', 'INVALID_PARAMS')
    if (command === 'recruitments') url.searchParams.set(key, values.join(','))
    else for (const item of values) url.searchParams.append(key, String(item))
  }
  return url
}
export async function query({ command, id, params, apiKey = process.env.WAYNEX_API_KEY,
  base = process.env.WAYNEX_API_BASE_URL || defaultBase, fetchImpl = fetch,
  wait = ms => new Promise(resolveWait => setTimeout(resolveWait, ms)) }) {
  if (!apiKey || !/^wxk_[A-Za-z0-9_-]{43}$/.test(apiKey)) throw new QueryError('请在本地配置有效的 WAYNEX_API_KEY；不要把密钥粘贴到聊天中', 'MISSING_API_KEY')
  const url = buildUrl(command, id, params, base)
  for (let attempt = 0; attempt < 2; attempt++) {
    let response
    try {
      response = await fetchImpl(url, { method: 'GET', redirect: 'error', credentials: 'omit',
        signal: AbortSignal.timeout(15000), headers: { Accept: 'application/json', Authorization: 'Bearer ' + apiKey } })
    } catch {
      throw new QueryError('无法连接 Waynex 服务，或请求超时；请检查网络后重试', 'NETWORK_ERROR')
    }
    const retryAfter = Math.max(0, Number(response.headers.get('Retry-After')) || 0)
    if (response.status === 429 && attempt === 0 && retryAfter > 0 && retryAfter <= 30) {
      await response.body?.cancel(); await wait(retryAfter * 1000); continue
    }
    let payload
    try { payload = await response.json() } catch { throw new QueryError('服务返回了无效 JSON', 'INVALID_RESPONSE', response.status) }
    if (!response.ok) throw new QueryError(String(payload?.error?.message || '查询失败').replaceAll(apiKey, '[REDACTED]'),
      payload?.error?.code || 'HTTP_ERROR', response.status, retryAfter, payload?.error?.request_id)
    if (!payload || typeof payload !== 'object' || Array.isArray(payload)) throw new QueryError('服务返回了无效查询结果', 'INVALID_RESPONSE', response.status)
    return JSON.parse(JSON.stringify(payload).replaceAll(apiKey, '[REDACTED]'))
  }
}
const help = `Waynex 公开数据查询（Node.js 20+）
用法：node query.mjs <command> [id] [--params '<JSON>' | --params-file <file>]
命令：recruitments、recruitment <id>、campus-events、campus-event <id>、recruitment-filters、campus-filters
在本地环境变量 WAYNEX_API_KEY 中配置密钥；无需通过命令行参数提供。
默认服务：https://waynex.lincolab.com/api/open/v1
列表默认第 1 页，每页 20 条；不会自动遍历或在本地过滤结果。`
export async function main(args = process.argv.slice(2)) {
  if (!args.length || args[0] === '--help' || args[0] === '-h') { process.stdout.write(help+'\n'); return }
  const [command, ...rest] = args
  let id, params = {}, configured = false
  for (let index = 0; index < rest.length; index++) {
    const arg = rest[index]
    if (arg === '--params' || arg === '--params-file') {
      if (configured || !rest[index + 1]) throw new QueryError('参数只能提供一次，且需要 JSON 或文件路径', 'INVALID_PARAMS')
      const value = rest[++index]; configured = true
      try { params = JSON.parse((arg === '--params-file' ? await readFile(value, 'utf8') : value).replace(/^\uFEFF/, '')) }
      catch { throw new QueryError('无法读取查询参数，请检查 JSON 或参数文件', 'INVALID_PARAMS') }
    } else if (!arg.startsWith('-') && !id) id = arg
    else throw new QueryError('不支持的命令参数；运行 --help 查看用法', 'INVALID_PARAMS')
  }
  process.stdout.write(JSON.stringify(await query({ command, id, params }), null, 2)+'\n')
}
if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch(error => {
    process.stderr.write(JSON.stringify({ error: { code: error instanceof QueryError ? error.code : 'QUERY_ERROR',
      message: error instanceof QueryError ? error.message : '查询未完成，请检查配置后重试',
      ...(error.status ? { status: error.status } : {}), ...(error.retryAfter ? { retry_after: error.retryAfter } : {}),
      ...(error.requestId ? { request_id: error.requestId } : {}) } })+'\n')
    process.exitCode = 1
  })
}
