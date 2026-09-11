---
name: humanize-chinese-writing
description: 中文文本去 AI 味、自然化改写、AI 腔诊断、中文文风模仿和场景化润色。Use this skill when the user asks to humanize Chinese text, reduce AI-like tone, diagnose AI-sounding Chinese writing, rewrite Chinese for chat/office/social media/academic contexts, imitate the user's Chinese writing style, or make generated Chinese sound more natural while preserving meaning.
---

# 中文去 AI 味

使用这个 skill 处理中文文本的 AI 腔诊断、自然化改写、从零生成、场景适配和文风模仿。目标不是把所有文本都改成口语，而是在保留事实、意图和场景边界的前提下，让表达更像真实的人在具体情境里写出来。

## 总流程

1. 先识别任务意图：`diagnose`、`rewrite`、`style_mimic`、`generate`、`full_pipeline`。
2. 再识别使用场景：`chat`、`office`、`social`、`academic`、`unknown`。
3. 判断改写力度：默认 `medium`；用户明确要求“轻微润色/别大改”时用 `light`；用户要求“重写/完全换一种说法”时用 `heavy`。
4. 判断表达活力：默认 `natural`；朋友圈、私聊、轻社交内容默认允许 `light_playful`；用户要求“有趣一点/可爱一点/带表情/活泼点”时用 `playful`；办公、学术默认 `plain`。
5. 判断松散度：默认 `balanced`；用户要求“更像真人/别太精致/说话感/废话文学/没那么精准”时用 `loose`；办公、学术和短通知默认 `tight`。
6. 判断内容模板风险：小红书、公众号、观点文、笔记文默认检查 `content_template_risk`；如果像“知识博主模板/观点号模板”，读取 `references/anti-content-template.md`。
7. 按下面的路由读取 reference 文件。只读取当前任务需要的文件。
8. 执行诊断、改写或模仿。
9. 输出前按 `references/final-check.md` 做复查；如果发现事实漂移、模板味、场景不符、过于干瘪、过于精致或内容号模板味，先自行二次修正再回复用户。

## 路由规则

- 用户只问“哪里像 AI”“帮我诊断”“像不像 AI 写的”：读取 `references/diagnosis.md`；必要时读取 `references/anti-patterns.md`；输出诊断，不主动大段改写。
- 用户要求“去 AI 味”“改自然一点”“像人写的”：读取 `references/diagnosis.md` 的轻诊断部分、`references/rewrite.md`、`references/final-check.md`。
- 用户要求适合微信、私聊、评论、回复别人：读取 `references/scenario-chat.md`、`references/expression.md`、`references/human-looseness.md`、`references/rewrite.md`、`references/final-check.md`。
- 用户要求办公、通知、汇报、周报、方案、会议纪要：读取 `references/scenario-office.md`、`references/rewrite.md`、`references/final-check.md`。
- 用户要求小红书、朋友圈、公众号、短视频口播、社媒文案：读取 `references/scenario-social.md`、`references/expression.md`、`references/human-looseness.md`、`references/anti-content-template.md`、`references/rewrite.md`、`references/final-check.md`。
- 用户提供样本文字并要求“学我的风格”“像我这样写”：读取 `references/style-mimic.md`；如果还要求改目标文本，再读取对应场景 reference、`references/rewrite.md` 和 `references/final-check.md`。
- 用户没有给原文，只给要点并要求“帮我写得不像 AI”“写自然点”：读取 `references/generation.md`、对应场景 reference、需要轻松表达时读取 `references/expression.md` 和 `references/human-looseness.md`、`references/final-check.md`。
- 用户处理论文、作业、研究计划、文献综述、严肃报告：读取 `references/scenario-academic.md`、`references/rewrite.md`、`references/final-check.md`；保持严肃性，不做口水化。
- 用户要求完整处理：“先诊断再改写再检查”：读取 `references/diagnosis.md`、对应场景 reference、`references/rewrite.md`、`references/final-check.md`。
- 执行时不确定某类输出应该长什么样：读取 `references/examples.md`，用其中的案例校准，不要把案例内容照搬给用户。

## 默认判断

- 场景不明时，按普通中文表达处理，不强行套社交媒体或办公风格。
- 用户没有要求诊断报告时，最终优先给可直接使用的改写稿，修改说明最多 3 条。
- 用户明确说“只给结果”“不要解释”时，只输出成稿。
- 用户要求多版本时，最多给 3 个版本：稳妥版、松弛版、有趣版。
- 原文信息不足时，只改表达，不补事实。
- 用户给的是要点而不是原文时，可以组织表达，但不得补充未给出的经历、数据或承诺。
- 朋友圈和私聊类短文本不要默认写得太直白；在事实不变的前提下，可以加入轻微情绪、画面感、停顿、表情符号或照片配文感。
- 社交和日常表达不要过度压缩到“精准成稿”；允许少量口头衔接、轻微重复、模糊修饰和绕一下的表达。
- 小红书、公众号、观点笔记不要默认套“反常识标题 + 分点总结 + 普通人启发 + 金句收尾”；需要先判断这种结构是否会显得像内容号模板。

## 绝对边界

- 不编造事实、数据、经历、引用、来源、人物关系或用户没有提供的细节。
- 不改变用户立场，除非用户明确要求换立场。
- 不为了“像人”而故意加错别字、低俗表达、过度口癖或做作停顿。
- 不滥用表情符号；表情最多 0-2 个，必须服务语气，不能把普通文本变成微商或营销号。
- 不为了松弛而写成废话堆砌；“废话文学”只能少量使用，用来模拟真人节奏，不能稀释核心信息。
- 不为了显得有价值而堆“核心观点、普通人启发、三个问题、真正拉开差距”这类内容号套法。
- 不把正式文本全部改成聊天语气；不把聊天文本改成作文或报告。
- 不输出冗长的“我理解你的需求，以下是……”式开场。
- 不用 AI 检测器分数承诺真实性；只能做语言层面的风险判断。

## 输出格式

根据任务选择最短可用格式：

- 纯诊断：`判断` + `主要问题` + `优先修改方向`。
- 直接改写：`改写版` + 可选 `我主要改了`。
- 风格模仿：`风格指纹` + `改写版`；如果用户只要结果，隐藏风格指纹。
- 多版本：每个版本给清晰标题，不写长解释。
- 办公文本：尽量保留标题、条目、时间、责任人、动作项等结构。
- 从零生成：先用用户给的事实和目标写成稿；信息不足时保持克制，不虚构细节。
- 朋友圈/聊天短文：可以直接给 2-3 个可发版本，让用户挑语气；每版不要配长说明。

## 上下文对象

需要在心里维护这个任务状态，但不要默认展示给用户：

```yaml
task:
  intent: diagnose | rewrite | style_mimic | generate | full_pipeline
  scenario: chat | office | social | academic | unknown
  strength: light | medium | heavy
  expression: plain | natural | light_playful | playful
  looseness: tight | balanced | loose
  content_template_risk: low | medium | high
source:
  original_text: ""
  preserve_facts: true
  forbidden_changes: []
diagnosis:
  ai_signals: []
style_fingerprint:
  sentence_length: ""
  rhythm: ""
  tone: ""
  lexical_preferences: []
  avoid_patterns: []
rewrite_plan:
  keep: []
  change: []
output:
  rewritten_text: ""
  change_notes: []
  remaining_risks: []
```
