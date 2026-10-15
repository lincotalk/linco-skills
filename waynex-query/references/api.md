# Waynex 开放查询 API v1

正式地址：`https://waynex.lincolab.com/api/open/v1`。所有请求（含字典和详情）需要 `Authorization: Bearer <API_KEY>`。脚本从 `WAYNEX_API_KEY` 读取，不读取浏览器 Cookie，不调用后台或个人数据接口。

测试时可将 `WAYNEX_API_BASE_URL` 设为 `https://join-test.lincotalk.com/api/open/v1` 或 loopback HTTP(S) 地址的 `/api/open/v1`，其他域名不允许。生产与测试 Key 不通用。

## 招聘列表

命令 `recruitments` → GET `/recruitments`。每条记录是招聘项目，不是单个岗位。

| 参数 | 类型和语义 |
| --- | --- |
| page / page_size | 从 1 开始；默认 1 / 20；每页最多 100 |
| search | 文本子串搜索，最多 2000 字符；不是语义匹配或布尔检索表达式 |
| location | 地点字典值，例如 city:440300；多选逗号分隔 |
| nature | 企业性质字典值；state_owned 为国企组合；多选逗号分隔 |
| industry | 行业字典代码；unknown 表示行业未说明；多选逗号分隔 |
| education | 专科及以上、本科及以上、硕士及以上、博士、要求未说明；单选 |
| graduation_year | 单个四位年份，字符串 |
| university_key | 单个学校标识，表示公告来源学校 |
| quick | 单个快捷条件；从字典获取支持值 |
| sort | updated（默认，更新时间倒序）或 deadline（截止时间正序，未知最后） |
| updated_since | 带时区的 ISO 时间，仅用于筛选，不能当作完整增量同步协议 |

省略筛选或用 all 表示不限（graduation_year、university_key、updated_since 除外）。脚本允许 location、nature、industry 使用 JSON 数组并转换为逗号形式。其他维度保持单选。

列表只返回公开可见项目；同项目内地点和学历条件需要落在同一岗位。详情命令 `recruitment <project_id>` → GET `/recruitments/:id`，不接受查询参数。

字典命令 `recruitment-filters` → GET `/filters/recruitments`，包含地点目录、企业性质、行业、学历、毕业届别、快捷条件和排序。location 使用目录中的 value；不要直接传城市名称。

## 校园活动列表

命令 `campus-events` → GET `/campus-events`。

| 参数 | 类型和语义 |
| --- | --- |
| page / page_size | 默认 1 / 20，最多 100 |
| search | 最多 200 字符，标题和学校名称子串搜索 |
| location | 举办地点目录值，支持 JSON 数组，多选转为重复参数 |
| province | 来源省份，支持重复参数；精确举办地点使用 location |
| university_key | 来源学校标识，支持重复参数 |
| event_type | presentation、bilateral_fair、group_fair、other、job_fair；job_fair 为两类招聘会组合 |
| date | YYYY-MM-DD，查询与指定当天有重叠的活动 |
| time_range | next7 或 next30，从上海当天起的 7 或 30 个自然日 |
| date_from / date_to | 必须同时提供 YYYY-MM-DD，含首尾日期，跨度最多 366 天 |

date、time_range、date_from/date_to 三种时间条件互斥。默认顺序：即将开始、正在进行、时间未知；按服务端时间规则排序并由 ID 稳定兜底。第一版不接受自定义 sort。

已按计划结束的活动沿用网站可见性规则，不保证可查询历史。详情用 `campus-event <event_id>` → GET `/campus-events/:id`，返回公开活动字段与来源，不含完整参会企业名单或内部采集状态。

字典命令 `campus-filters` → GET `/filters/campus-events`，包含地点、学校、来源省份和活动类型。

## 响应、额度与错误

列表：items、total、page、page_size、has_more、applied_filters、request_id。活动的相对时间在 applied_filters 中返回实际 date_from/date_to。详情：item、request_id。招聘常用 project_id、company_name、deadline、status、work_locations、updated_at、announcement_links；活动常用 event_id、title、university_name、start_at、venue、detail_url、sources。

详情 404 可能表示已撤回；不要用先前缓存绕过。翻到空页时 total 仍有值。未知字段保留 null/unknown；不要补写事实。分页中数据可能更新，不承诺跨请求快照。

默认按账号每天 1000 次、每分钟持续补充 60 次、突发 10 次，具体以网站账号配置为准。通过鉴权和额度检查后计次，参数错误或查询失败也可能占用一次额度。字典、列表、详情、HEAD 共用额度；Key 轮换不重置。X-Api-Daily-Remaining 和 X-RateLimit-Remaining 返回余量。上海时间次日零点重置。

错误格式：error.code、error.message、error.request_id。400 INVALID_QUERY：修正参数；401 INVALID_API_KEY：本地配置或重新生成；403：检查权限/账号状态；404：不存在或不可见；429 RATE_LIMITED/DAILY_QUOTA_EXCEEDED：遵守 Retry-After；503：等待恢复。不要自动创建、轮换或申请密钥。

## 参数文件示例

招聘 query.json：

```json
{"location":["city:440300"],"nature":["state_owned"],"education":"本科及以上","sort":"deadline","page":1,"page_size":20}
```

活动 query.json：

```json
{"location":["city:440100"],"event_type":"presentation","time_range":"next7","page":1,"page_size":20}
```

调用 `node <skill-dir>/scripts/query.mjs campus-events --params-file <query.json>`。参数文件只含查询条件；取下一页时仅递增 page，保留其余参数。
