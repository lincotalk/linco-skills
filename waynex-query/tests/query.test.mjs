import test from 'node:test'
import assert from 'node:assert/strict'
import { buildUrl, query, serviceBase } from '../scripts/query.mjs'
const apiKey = 'wxk_' + 'a'.repeat(43)
test('multi-selects match each API encoding without shell or URL injection', () => {
  const url = buildUrl('recruitments', undefined, { search: '算法 & 研发', nature: ['private','state_owned'], page: 2 })
  assert.equal(url.searchParams.get('search'), '算法 & 研发')
  assert.equal(url.searchParams.get('nature'), 'private,state_owned')
  assert.deepEqual(buildUrl('campus-events', undefined, { location: ['city:440100','city:440300'] }).searchParams.getAll('location'), ['city:440100','city:440300'])
  assert.throws(() => buildUrl('recruitment', '../admin'), /有效 ID/)
  assert.throws(() => buildUrl('recruitments', undefined, { api_key: apiKey }), /环境变量/)
})
test('credentials never go to arbitrary hosts, redirects or cookies', async () => {
  for (const base of ['https://attacker.invalid/api/open/v1', 'https://waynex.lincolab.com.attacker.invalid/api/open/v1', 'https://user@waynex.lincolab.com/api/open/v1', 'http://waynex.lincolab.com/api/open/v1']) assert.throws(() => serviceBase(base))
  let calls=0
  await query({ command:'recruitments',apiKey,fetchImpl: async (url, init) => {
    calls++; assert.equal(init.redirect, 'error'); assert.equal(init.credentials,'omit');
    assert.equal(init.headers.Authorization,'Bearer '+apiKey); assert.ok(!String(url).includes(apiKey))
    return Response.json({ items:[],total:0,page:1,has_more:false })
  } })
  assert.equal(calls,1)
})
test('missing keys fail before network, short 429 retries once, daily quotas do not wait', async () => {
  let calls=0, waits=0
  await assert.rejects(query({ command:'recruitments',apiKey:'',fetchImpl:()=>{calls++} }),{code:'MISSING_API_KEY'})
  assert.equal(calls,0)
  const response=await query({command:'recruitments',apiKey,wait:async()=>{waits++},fetchImpl:async()=>{
    calls++; return calls===1 ? Response.json({error:{code:'RATE_LIMITED'}},{status:429,headers:{'Retry-After':'1'}}) : Response.json({items:[],total:0})
  }})
  assert.equal(response.total,0); assert.equal(calls,2); assert.equal(waits,1)
  await assert.rejects(query({command:'recruitments',apiKey,wait:async()=>{throw Error('must not wait')},fetchImpl:async()=>Response.json({error:{code:'DAILY_QUOTA_EXCEEDED',message:'额度用完'}},{status:429,headers:{'Retry-After':'3600'}})}),{code:'DAILY_QUOTA_EXCEEDED',retryAfter:3600})
})
test('server errors are bounded, preserve IDs and do not expose keys', async () => {
  await assert.rejects(query({command:'recruitments',apiKey,fetchImpl:async()=>Response.json({error:{code:'INVALID_API_KEY',message:apiKey,request_id:'trace'}},{status:401})}),error=>error.code==='INVALID_API_KEY'&&error.requestId==='trace'&&!error.message.includes(apiKey))
  const result=await query({command:'recruitments',apiKey,fetchImpl:async()=>Response.json({items:[],echo:apiKey})})
  assert.equal(result.echo,'[REDACTED]')
})
