# 多模态 Agent 能力地图：从听、说、看、生成到运行时治理

> 更新时间：2026-05-15
>
> 本文记录当前多模态能力对 Agent 开发的影响，重点关注语音、视觉理解、图像/视频生成、实时多模态交互，以及这些能力进入 Agent Runtime 后带来的工程治理问题。

## 目录

- [文档定位](#文档定位)
- [一、核心判断](#一核心判断)
- [二、多模态能力成熟度地图](#二多模态能力成熟度地图)
- [三、主要能力方向](#三主要能力方向)
- [四、国内外代表平台与服务](#四国内外代表平台与服务)
- [五、多模态对 Agent Runtime 的影响](#五多模态对-agent-runtime-的影响)
- [六、方法论：不要把多模态当成“多接几个 API”](#六方法论不要把多模态当成多接几个-api)
- [七、对项目 E 的启发与实践路线](#七对项目-e-的启发与实践路线)
- [八、风险与治理清单](#八风险与治理清单)
- [九、结论](#九结论)
- [参考资料](#参考资料)

## 文档定位

本文和 `agent-runtime-philosophy.md`、`agent-frameworks-and-services-landscape.md` 互补：

- `agent-runtime-philosophy.md` 讨论 Agent 为什么需要 runtime/governance。
- `agent-frameworks-and-services-landscape.md` 讨论现成 Agent 框架和服务如何选型。
- 本文讨论多模态能力进入 Agent 后，runtime/governance 需要新增哪些设计。

本文不是图像生成或语音模型教程，也不是单纯的模型排行榜。它关注的是：

- 多模态能力已经成熟到什么程度。
- 哪些能力可以直接进入 Agent 项目。
- 哪些能力仍然需要谨慎实验。
- 多模态输入输出会如何改变 state、artifact、trace、eval、guardrails 和成本控制。

## 一、核心判断

多模态能力正在从“附加功能”变成 Agent 的基础感知和表达能力。

早期 Agent 多数是文本系统：

```text
用户文本 -> LLM -> 工具调用 -> 文本结果
```

多模态 Agent 逐渐变成：

```text
语音 / 图像 / 文档 / 视频 / 屏幕 / 摄像头
  -> 感知与结构化
  -> 推理与工具调用
  -> 文本 / 语音 / 图像 / 视频 / 操作结果
```

这带来一个重要变化：Agent 不再只是“读文字、写文字”，而是开始具备“听、说、看、生成、操作界面”的能力。

另一个同样重要的变化是：多模态能力不再只属于最大模型。很多小模型和中等规模模型已经具备可进入项目的视觉、语音、OCR、文档理解和短视频理解能力。它们未必适合做最终裁判或复杂规划者，但很适合做 Agent Runtime 里的“低成本感知层”和“专用工具层”。

但这也意味着复杂度从 prompt 层迁移到 runtime 层：

- 媒体输入需要采集、压缩、抽帧、转写、OCR、分段和存储。
- 媒体输出需要异步任务、轮询、下载、版权标记和审核。
- 实时语音需要 VAD、打断、回声消除、低延迟和会话状态。
- 视频理解需要时间戳、片段定位和多轮追问。
- 视觉 Agent / computer use 需要屏幕权限、点击权限、确认机制和 prompt injection 防护。
- 生成图像、视频、声音涉及肖像、声音克隆、版权、深度伪造和内容安全。

因此，多模态 Agent 的本质不是“给 Agent 多接几个 API”，而是让 Agent Runtime 能管理多种感知和表达通道。

**本节小结**：多模态让 Agent 更接近真实软件和真实环境；小模型让这些能力更容易进入真实项目；但系统仍然需要在运行时治理、安全、成本、延迟和评估上建立清晰边界。

## 二、多模态能力成熟度地图

可以把当前多模态能力按成熟度分为三层。

### 2.1 已经比较成熟，可进入工程实践

| 能力 | 当前成熟度 | 典型用途 | Agent 中的价值 |
|------|------------|----------|----------------|
| 语音识别 ASR | 较成熟 | 会议转写、客服录音、字幕、语音输入 | 让 Agent 接收自然语音和音频文件 |
| 文本转语音 TTS | 较成熟 | 播报、客服、教育、无障碍、有声内容 | 让 Agent 以自然语音反馈 |
| 图像理解 | 较成熟 | 截图分析、图片问答、图表解释、票据识别 | 让 Agent 读取视觉上下文 |
| OCR / 文档视觉理解 | 较成熟 | PDF、表格、合同、发票、复杂版面解析 | 让 Agent 处理真实业务材料 |
| 图像生成与编辑 | 较成熟 | 设计草图、海报、产品图、素材生成、局部编辑 | 让 Agent 产出可视化 artifact |
| 短视频生成 | 可用但仍需审核 | 文生视频、图生视频、广告素材、短片分镜 | 让 Agent 参与内容创作流程 |

这些能力已经可以作为工具或 Skill 接入 Agent，但仍然需要 schema、trace、审核和成本控制。

### 2.2 快速发展，适合实验和受控应用

| 能力 | 当前成熟度 | 主要挑战 |
|------|------------|----------|
| 实时语音 Agent | 快速成熟 | 低延迟、打断、噪音、口音、工具调用同步 |
| 实时语音翻译 | 快速成熟 | 同传延迟、专有名词、说话人保持、语气保留 |
| 视频理解 | 快速成熟 | 长视频上下文、时间定位、音画联合理解 |
| 语音情感与语气控制 | 快速成熟 | 一致性、可控性、滥用风险 |
| 音视频联合生成 | 快速成熟 | 声画同步、角色一致性、物理一致性 |
| 视觉操作 / computer use | 快速成熟 | 屏幕 prompt injection、误点击、权限隔离 |

这些能力适合做“Agent Runtime 扩展实验”，不适合在没有 guardrails 的情况下直接进入高风险业务。

### 2.3 仍不稳定，不应过度依赖

| 能力 | 问题 |
|------|------|
| 长视频全局推理 | 容易遗漏细节，时间线和因果关系可能不稳 |
| 完全自动视觉操作 | 页面误读、误点击、提示注入和环境不可控 |
| 复杂视频生成 | 长时一致性、人物一致性、物理逻辑仍不稳定 |
| 无监管声音克隆 | 涉及身份伪造和授权问题 |
| 生成内容版权判定 | 来源、相似性和授权边界仍难自动判断 |
| 多模态事实性判断 | 图像/视频中的幻觉更难被用户识别 |

这些方向可以研究，但必须配合人工审核、用途限制和明确的 blocked / needs_human 终态。

### 2.4 小模型已经可以承担部分项目级能力

小模型和专用模型的进展很快。它们的意义不是替代最强的大模型，而是让 Agent 可以在更多地方部署更便宜、更快、更可控的局部能力。

从项目角度看，小模型不只包括 VLM，也包括纯语言、编码、ASR、TTS 和全模态模型。它们在 Agent Runtime 中的位置不同：

| 能力线 | 代表模型 / 系列 | 适合放在 Agent 中的位置 | 实践价值 |
|--------|-----------------|--------------------------|----------|
| 纯语言小模型 | Qwen3.5-0.8B/2B/4B、Gemma 4 E2B/E4B、Phi-4-mini、MiniCPM3-4B、SmolLM3、Jan-Nano、MiniMind | 轻量 planner、router、摘要器、低风险对话层 | 端侧运行、快速响应、低成本批处理 |
| 编码小模型 | mini-coder-4b、Jan-Code-4B、mini-swe-1.7B、TinyCodeLM、MiniCoderX | Agent 工作流里的 worker 子模型 | 处理 scope 明确的代码生成、编辑、重构、调试子任务 |
| ASR / 听写模型 | Qwen3-ASR-0.6B/1.7B、GLM-ASR-Nano、Voxtral-Mini-4B-Realtime、MiMo-V2.5-ASR、StepAudio 2.5 ASR、Whisper Tiny | 语音输入前端、离线转写、实时听写 | 把语音入口从云 API 变成可本地/边缘部署的能力 |
| TTS / 说话模型 | Voxtral-4B-TTS、VibeVoice-Realtime、CosyVoice2、Pocket TTS、MOSS-TTS-Nano、TinyTTS | Agent 表达层、播报层、实时语音回复 | 低延迟、低成本、可离线的语音输出 |
| VLM / 图像理解模型 | Moondream、SmolVLM/SmolVLM2、Phi-4-multimodal、MiniMind-V、nanoVLM、Qwen3.5-4B 多模态版 | 截图、图片、文档页、UI 画面理解 | 低成本视觉感知和结构化视觉 artifact |
| Omni / 全模态模型 | MiniCPM-o 4.5、Phi-4-multimodal、Qwen-Omni / Qwen3.5-Omni | 看、听、说、想一体化实验 | 验证实时多模态 Agent，但 runtime 复杂度最高 |

这个清单应该被当成“滚动观察表”，因为 2026 年小模型更新速度很快，不宜固化成一次性的排行榜。进入工程前必须重新核对官方模型卡、license、量化方案、部署栈和本地评测结果。

在 VLM 和多模态方向，代表性模型包括：

| 模型 / 系列 | 典型规模 | 主要能力 | 适合放在 Agent 中的位置 |
|-------------|----------|----------|--------------------------|
| Qwen3-VL | 2B / 4B / 8B / 32B / MoE | 图像、视频、OCR、视觉 grounding、长上下文、多模态推理 | 当前优先观察对象；适合截图、文档、GUI、短视频理解 |
| Qwen2.5-VL | 3B / 7B / 32B / 72B | 图像理解、文档理解、视频理解、视觉定位 | 成熟度较高；适合票据/表格解析、图文问答、视觉预处理 |
| Qwen2.5-Omni / Qwen3-Omni | 7B 或 MoE | 文本、图像、音频、视频输入，文本/语音输出 | 适合研究 omni-modal Agent，但工程复杂度高于纯 VLM |
| Kimi-VL-A3B | 16B 总参数，约 2.8B/3B 激活 | 多模态推理、长上下文、OCR、长文档、长视频、视觉 grounding | 适合研究小激活参数 MoE 在 Agent 场景的性价比 |
| MiniCPM-V / MiniCPM-o | 8B-9B 左右 | 图像、视频、语音和多模态实时交互探索 | 本地视觉理解、离线视频理解、边缘端多模态原型 |
| InternVL3 / InternVL3.5 | 1B / 2B / 4B / 8B / 14B / MoE | 通用 VLM、多模态推理、视觉问答、文档/图表理解 | 适合和 Qwen、MiniCPM 做本地模型对照评测 |
| GLM-4.1V / GLM-4.5V / GLM-4.6V | 9B/10B 到更大规模 | 多模态推理、视频理解、长文档理解 | 适合研究 thinking-style VLM 和中文生态模型 |
| Ovis2.5 | 2B / 9B 等 | 原生分辨率视觉感知、多模态推理 | 适合资源受限环境下的视觉推理评测 |
| Gemma 3 / Gemma 3n | 轻量到中等规模 | 图像、文本，Gemma 3n 面向音频/视频和端侧部署 | 端侧多模态实验、隐私敏感场景的本地预处理 |
| SmolVLM2 | 256M / 500M / 2.2B | 图像和视频理解 | 轻量级视觉分类、短视频摘要、低成本批处理 |
| Moondream | 500M 起 | 轻量视觉问答、检测、指向和计数 | 摄像头/截图快速理解、低延迟视觉工具 |
| Florence-2 | 数亿参数级视觉模型 | caption、OCR、目标检测、分割等视觉任务 | 结构化视觉工具，而不是通用对话模型 |
| Phi-3.5/4 Vision、Llama 3.2 Vision、Molmo、LLaVA-OneVision | 4B-15B 常见 | 图像理解、图表/科学问题、视觉问答 | 适合作为国际开源/开放权重基线 |

可以进一步按用途分组，而不是只按模型名比较：

| 用途 | 优先观察模型 | 为什么 |
|------|--------------|--------|
| 截图/GUI 理解 | Qwen3-VL、Qwen2.5-VL、Kimi-VL、Moondream | 需要 grounding、OCR、界面元素理解和低延迟 |
| 文档/OCR/表格 | Qwen3-VL、Qwen2.5-VL、Kimi-VL、GLM-4.1V、Florence-2 | 需要版面理解、文字准确性和结构化输出 |
| 短视频理解 | Qwen3-VL、MiniCPM-V、InternVL3.5、SmolVLM2 | 需要抽帧、时间戳、事件摘要和成本控制 |
| 实时/端侧多模态 | Gemma 3n、MiniCPM-o、Moondream、SmolVLM2 | 需要低延迟、低显存、隐私和离线能力 |
| 多模态推理 | Qwen3-VL Thinking、Kimi-VL、GLM-4.1V、InternVL3.5 | 需要更强的链式推理、数学/图表/复杂视觉判断 |
| 专用视觉工具 | Florence-2、OCR、检测、分割模型 | 任务边界清楚，适合做稳定 Skill |

这说明项目中可以采用“大小模型协作”：

```text
小模型：路由、摘要、ASR、TTS、OCR、截图理解、低风险批处理
编码小模型：明确 scope 的代码编辑、测试修复、局部重构
VLM 小模型：图片/文档/短视频的初步感知和结构化
Omni 小模型：实时多模态交互原型和端侧实验
大模型：任务规划、复杂综合判断、最终解释、异常仲裁
```

对 Agent Runtime 来说，这比单纯接入一个最强模型更有实践价值：

- 成本更可控，适合频繁调用的感知任务。
- 延迟更低，适合交互式 UI、语音前处理和截图理解。
- 隐私边界更清楚，部分媒体可以在本地或私有环境处理。
- 评估更容易，因为小模型常常承担单一、可验证的任务。
- 降级策略更自然，大模型不可用时仍能保留基础感知能力。

但小模型也需要明确限制：

- 不适合作为高风险决策的唯一依据。
- 不应默认相信其 OCR、定位和计数结果。
- 对复杂跨页文档、长视频、细粒度医学/法律/安全判断仍需更强模型或人工复核。
- 必须记录模型版本、量化方式、输入分辨率、抽帧策略和失败样例。

**本节小结**：多模态小模型已经值得在项目 E 中实际使用，尤其适合作为 Runtime 的可插拔 Skill；但它们应该被设计成“可评估的专用能力”，而不是被包装成无所不能的小 Agent。

## 三、主要能力方向

### 3.1 语音理解：从“转文字”到“实时对话状态”

语音理解不只是 ASR。对 Agent 来说，语音输入至少包含三层信息：

| 层次 | 内容 | Agent 需要记录什么 |
|------|------|--------------------|
| 文字内容 | 用户说了什么 | transcript、置信度、时间戳 |
| 对话边界 | 什么时候开始说、什么时候停顿、什么时候打断 | turn、VAD event、interrupt event |
| 声学线索 | 语速、语气、情绪、噪音、口音 | audio metadata、quality signal |

OpenAI Realtime 文档将实时能力分成 voice agents、live translation、transcription 和 speech generation，并强调 voice-agent session 会管理会话状态、工具调用和事件流。Google Gemini Live API 也把实时音视频交互、VAD、工具调用、session management 放在核心能力中。

对 Agent Runtime 的启发：

- 语音输入不能只保存最终 transcript。
- 应保存每个 speech turn 的开始、结束、打断和转写版本。
- 工具调用需要与语音轮次关联，否则复盘时不知道哪个语音意图触发了哪个动作。
- 实时系统必须把延迟作为一等指标。

推荐结构：

```text
AudioTurn
  id
  started_at
  ended_at
  transcript_partial[]
  transcript_final
  vad_events[]
  speaker_id?
  language?
  audio_quality
  linked_tool_calls[]
```

### 3.2 语音生成：从 TTS 到“可打断、可控、可追踪”的表达通道

TTS 已经比较成熟，ElevenLabs、OpenAI、百度智能云、MiniMax 等都提供语音合成能力。新的趋势是：

- 更自然的语音。
- 多语言和方言。
- 情绪、语气、语速控制。
- 低延迟流式输出。
- 语音克隆或音色设计。
- 与 Agent 对话状态结合。

但语音输出比文本输出更难治理：

- 用户听到后不容易逐字复核。
- 播报错误可能造成更强信任感。
- 声音克隆涉及身份授权。
- 语气、情绪可能改变用户判断。
- 实时语音更容易发生“说出去才发现错了”的问题。

对 Agent Runtime 的启发：

- 语音输出也应有 artifact。
- 对关键业务信息，先生成文本确认，再生成语音。
- 高风险播报需要 human approval。
- 语音文件、voice id、prompt、参数都应进入 trace。

推荐结构：

```text
SpeechOutputArtifact
  text_source
  voice_id
  style
  speed
  language
  audio_uri
  generated_at
  approved_by?
```

### 3.3 图像理解：从图片问答到“视觉证据”

图像理解已经适合进入很多 Agent 场景：

- 截图分析。
- UI 状态识别。
- 图表解释。
- 合同/票据/证件识别。
- 复杂文档版面理解。
- 工业巡检图片初筛。
- 医疗/法律等高风险领域辅助分析。

Claude Vision 文档明确提醒图片质量、文字可读性、图片放置顺序和 token 成本；百度 Qianfan-VL 也强调 OCR、文档解析、图表理解、复杂表格解析等企业场景。

对 Agent Runtime 的启发：

- 图像输入应先变成结构化视觉 artifact。
- 下游 Agent 不应直接依赖“我看到了什么”的长文本描述。
- 对关键判断，应保存 crop、OCR、坐标、置信度、引用区域。

推荐结构：

```text
ImageUnderstandingArtifact
  image_uri
  summary
  detected_text[]
  detected_objects[]
  regions[]
  chart_data?
  confidence
  model
```

### 3.4 视频理解：时间轴成为新的上下文

视频理解和图片理解不同，核心难点是时间。

Google Gemini 文档显示，模型可以处理视频，完成描述、分段、信息抽取、视频问答，并能引用视频中的具体时间戳。Qwen-Omni 系列也强调音频、视频和文本的统一理解。

对 Agent 来说，视频不是一个大文件，而应该被拆成：

- 片段。
- 时间戳。
- 关键帧。
- 音频转写。
- 事件。
- 场景切换。
- 视觉证据。
- 音画同步关系。

推荐结构：

```text
VideoUnderstandingArtifact
  video_uri
  duration
  transcript_segments[]
  keyframes[]
  scene_segments[]
  events[]
  referenced_timestamps[]
  summary
```

适合实验的任务：

- 会议视频摘要。
- 操作教程视频结构化。
- 课程视频生成测验题。
- 短视频内容审核初筛。
- 监控片段异常摘要。

不适合直接自动化的任务：

- 无人值守安全决策。
- 法律证据判断。
- 医疗诊断。
- 需要精确动作识别的高风险场景。

### 3.5 图像生成与编辑：从创作工具到结构化产物生成

图像生成已经从“生成一张好看的图”发展到更工程化的能力：

- 文生图。
- 图生图。
- 多轮图像编辑。
- 局部编辑 / inpainting。
- 多参考图合成。
- 产品 mockup。
- 保持人物、logo、风格一致性。
- 生成图像和文本交织的内容。

OpenAI 的图像文档已经支持生成、编辑、多轮编辑、参考图；Google Gemini 图像生成文档也强调 conversational editing、添加/删除元素、风格迁移、多图组合和细节保持。

对 Agent Runtime 的启发：

- 图像生成应视为工具调用，而不是普通文本输出。
- 每次生成都要记录 prompt、reference images、seed/参数、模型、输出文件、审核结果。
- 生成图像通常需要版本管理。
- 高风险图像需要人工审批。

推荐结构：

```text
ImageGenerationArtifact
  prompt
  revised_prompt?
  reference_images[]
  model
  parameters
  output_images[]
  moderation_result
  provenance_metadata?
  version
```

### 3.6 视频生成：从“生成短片”到异步生产流水线

视频生成正在快速成熟。Google Veo 3 / 3.1 支持带音频的视频输出；阿里云百炼的万相视频生成支持文本、图像、音频输入和声画同步；MiniMax 视频生成支持文生视频、图生视频、首尾帧生成视频和主体参考视频；腾讯混元生视频提供视频生成和视频处理 API。

视频生成的工程特征很明显：

- 多数是异步任务。
- 需要任务 ID。
- 需要轮询状态。
- 需要下载文件。
- 需要存储中间和最终产物。
- 需要内容审核。
- 需要成本估算。
- 需要版本和重试管理。

这和普通 LLM 调用完全不同。它更像一个 workflow：

```text
脚本 -> 分镜 -> 参考图 -> 视频生成任务 -> 状态轮询 -> 下载 -> 审核 -> 交付
```

推荐结构：

```text
VideoGenerationJob
  job_id
  prompt
  mode: text_to_video | image_to_video | reference_to_video
  inputs[]
  model
  status
  created_at
  completed_at
  output_video_uri
  moderation_result
  cost_estimate
```

## 四、国内外代表平台与服务

### 4.1 国际平台

| 平台 | 多模态能力 | 对 Agent 的意义 |
|------|------------|----------------|
| OpenAI | Realtime voice agents、live translation、streaming transcription、speech generation、image generation/editing、vision input | 适合研究“实时语音 Agent + 工具调用 + 多模态输入”的 runtime |
| Google Gemini / Veo / Imagen | Live API、视频理解、图像生成、Veo 视频生成、工具调用 | 适合研究“实时音视频交互 + 视频理解/生成”的全链路 |
| Anthropic Claude | 视觉理解、computer use、屏幕操作风险提示 | 适合研究视觉 Agent 和屏幕操作的安全边界 |
| ElevenLabs | TTS、STT、voice cloning、conversational agents、generative audio | 适合研究语音 Agent 的表达层和声音资产治理 |

### 4.2 国内平台

| 平台 | 多模态能力 | 对 Agent 的意义 |
|------|------------|----------------|
| 阿里云百炼 / Qwen / 万相 | Qwen-Omni 文本、图像、音频、视频输入，文本和语音流式输出；万相视频生成支持文本、图像、音频输入和声画同步 | 适合研究全模态理解、语音输出和视频生成 workflow |
| MiniMax | 文本、语音、视频、图像、音乐和文件管理；MCP 支持语音合成、音色克隆、视频生成、音乐生成等 | 适合研究多模态生成工具如何通过 MCP 进入 Agent |
| 腾讯混元 | 图像生成、图像处理、视频生成和视频处理 API | 适合研究云 API 型视觉生成工具接入 |
| 百度千帆 / Qianfan-VL | OCR、文档解析、图表理解、复杂表格解析、语音合成、数字人口型视频生成 | 适合研究企业文档视觉理解和语音合成 |
| 科大讯飞星辰 Agent | 语音、数字人、工作流、多源模型接入和多渠道发布 | 适合研究语音/数字人 Agent 产品化 |
| 火山引擎 / Coze / Seedance | Agent 平台、工作流、插件、视频生成 API、AgentOps | 适合研究多模态内容生产 Agent 与低代码平台结合 |

### 4.3 开源与小模型生态

除了云平台，开源和小模型生态已经足够重要，应该单独纳入项目 E 的实验范围。

| 方向 | 代表模型 / 项目 | 适合验证的问题 |
|------|-----------------|----------------|
| 新一代通用 VLM | Qwen3-VL、Kimi-VL、InternVL3.5、GLM-4.1V、Ovis2.5 | 小参数或小激活参数模型是否已经足够完成复杂视觉推理 |
| 成熟视觉语言小模型 | Qwen2.5-VL 3B/7B、MiniCPM-V、Gemma 3、Gemma 3n、SmolVLM2、Moondream | 小模型是否足够完成截图、票据、图表、短视频等感知任务 |
| Omni-modal 小模型 | Qwen-Omni、MiniCPM-o、Gemma 3n | 语音、图像、视频输入是否能进入同一 Agent runtime |
| 专用视觉基础模型 | Florence-2、OCR/检测/分割模型 | 是否可以把视觉任务拆成更稳定的专用 Skill |
| 端侧和私有部署 | Gemma 3n、MiniCPM、Moondream、量化 VLM | 是否可以把敏感媒体留在本地或内网 |
| 组合式视觉流水线 | OCR + detector + VLM + validator | 是否比单模型端到端更稳定、更便宜、更可评估 |

这个生态对 Agent 的意义很直接：Runtime 不必把所有多模态输入都送给昂贵大模型。更合理的是先由小模型完成感知、抽取、筛选和初步结构化，再把高价值、低噪声的 artifact 交给更强模型做综合推理。

### 4.4 共同趋势

这些平台虽然产品形态不同，但趋势很一致：

```text
单一模型 API -> 多模态能力 API -> Agent 工具生态 -> AgentOps / Runtime / Governance
```

具体表现为：

- 语音不再只是 TTS/ASR，而是实时语音 Agent。
- 视觉不再只是图片问答，而是文档、视频、屏幕和操作环境理解。
- 图像/视频生成不再只是创作工具，而是异步内容生产流水线。
- MCP、插件、工作流、trace、eval 开始成为多模态能力的接入方式。
- 平台正在从“模型调用”转向“多模态 Agent 应用开发与治理”。

## 五、多模态对 Agent Runtime 的影响

### 5.1 Context Engineering 变复杂

文本上下文可以截断、摘要、检索。多模态上下文还需要：

- 音频切片。
- 视频抽帧。
- 图像压缩。
- OCR。
- 时间戳。
- 文件引用。
- 媒体存储。
- 多模态摘要。
- 重要片段索引。

推荐原则：

```text
不要把大媒体文件直接塞给 Agent。
先把媒体转成结构化 artifact，再让 Agent 推理。
```

### 5.2 Artifact Protocol 必须扩展

项目 E 的 artifact 不能只支持文本和 JSON。至少要支持：

| Artifact | 用途 |
|----------|------|
| TranscriptArtifact | 语音/视频转写 |
| ImageUnderstandingArtifact | 图片理解结果 |
| VideoUnderstandingArtifact | 视频理解结果 |
| SpeechOutputArtifact | 语音生成结果 |
| ImageGenerationArtifact | 图像生成结果 |
| VideoGenerationJob | 视频生成异步任务 |
| MediaModerationReport | 媒体安全检查 |
| ProvenanceRecord | 来源、版权、水印、生成模型信息 |

### 5.3 Tool Governance 的风险等级需要升级

多模态工具风险更高：

| 工具 | 风险 | 策略 |
|------|------|------|
| ASR | 误识别导致错误指令 | 保存音频和 transcript，关键动作复核 |
| TTS | 错误内容被自然语音放大信任 | 高风险内容先文本确认 |
| 视觉理解 | 图像误读、OCR 错误 | 保存证据区域和置信度 |
| 摄像头 | 隐私、环境泄露 | 明确授权、最小采集、可见提示 |
| 屏幕读取 | 敏感信息泄露 | 屏幕范围控制、敏感区域遮挡 |
| computer use | 误操作、prompt injection | 沙箱、审批、操作级权限 |
| 图像生成 | 肖像、版权、误导内容 | 审核、来源记录、用途限制 |
| 视频生成 | 深度伪造、版权、误导传播 | 人工审批、水印、发布限制 |
| 声音克隆 | 身份伪造 | 授权证明、禁止默认开放 |

### 5.4 Trace 要能回放多模态过程

多模态 trace 不只是日志。它应能回答：

- 用户说了什么，原始音频是什么。
- Agent 听成了什么。
- 哪个图像区域支撑了判断。
- 哪个视频时间戳支撑了结论。
- 哪个 prompt 生成了图片或视频。
- 哪次生成失败或被审核拦截。
- 哪个工具因为风险进入 needs_human。

推荐事件模型：

```text
MediaInputReceived
MediaPreprocessed
TranscriptCreated
VisionArtifactCreated
GenerationJobCreated
GenerationJobCompleted
MediaModerationCompleted
MediaOutputDelivered
HumanApprovalRequested
HumanApprovalCompleted
```

### 5.5 Evaluation 需要多维指标

文本 eval 不够用。多模态需要更多指标：

| 能力 | 指标 |
|------|------|
| ASR | WER、专有名词正确率、延迟、说话人识别 |
| TTS | 自然度、可懂度、情绪一致性、延迟 |
| 语音 Agent | 首包延迟、打断响应、任务完成率、工具调用准确率 |
| 图像理解 | OCR 准确率、区域定位、图表解析准确率、幻觉率 |
| 视频理解 | 时间戳准确率、片段召回、事件识别、摘要忠实度 |
| 图像生成 | 指令遵循、局部编辑保持度、文字渲染、品牌一致性 |
| 视频生成 | 运动一致性、人物一致性、声画同步、物理合理性 |
| 多模态安全 | prompt injection 拦截率、误报率、深伪风险识别 |

### 5.6 成本和延迟控制变成核心问题

多模态调用成本通常高于文本：

- 图像按像素、token 或输出规格计费。
- 语音按音频时长、字符或 token 计费。
- 视频按秒数、分辨率、模型等级计费。
- 实时会话按持续连接和音频 token 计费。
- 生成任务失败、重试和审核也会产生成本。

项目 E 的 BudgetPolicy 应扩展：

```text
max_audio_seconds
max_video_seconds
max_image_count
max_generation_jobs
max_realtime_session_seconds
max_media_storage_mb
max_media_cost
```

## 六、方法论：不要把多模态当成“多接几个 API”

### 6.1 先感知，再推理，再行动

多模态 Agent 应采用三段式：

```text
Perception -> Reasoning -> Action
```

其中 Perception 不是直接让 LLM 看文件，而是生成结构化感知产物：

```text
音频 -> transcript + speaker + timestamp
图片 -> OCR + objects + regions + summary
视频 -> transcript + keyframes + scenes + timestamps
屏幕 -> UI tree / screenshot regions / actionable elements
```

这样做的好处：

- 可复盘。
- 可缓存。
- 可校验。
- 可替换模型。
- 可让下游 Agent 使用稳定输入。

### 6.2 生成内容必须进入审批和版本

图像、视频、声音都不应直接作为最终结果发布。推荐：

```text
Generate -> Moderate -> Review -> Version -> Deliver
```

至少应保存：

- prompt。
- reference。
- model。
- parameters。
- output。
- moderation。
- reviewer。
- published version。

### 6.3 多模态工具默认不是低风险工具

读取图片、转写语音看起来像只读操作，但仍可能泄露隐私或触发错误决策。生成视频、克隆声音、操作屏幕更应默认为高风险。

推荐分级：

| 风险级别 | 示例 | 策略 |
|----------|------|------|
| read_low | 用户上传公开图片摘要 | 允许，记录 trace |
| read_sensitive | 合同、证件、会议录音、屏幕截图 | 用户授权，敏感信息遮挡 |
| generate_draft | 草稿图、草稿音频、内部视频 | 允许，必须标记草稿 |
| generate_publishable | 可对外发布的图像/视频/声音 | 人工审批 |
| identity_sensitive | 人脸、声音克隆、数字人 | 默认禁止或强授权 |
| action_sensitive | computer use、真实系统操作 | 沙箱和逐步确认 |

### 6.4 多模态 Agent 更需要 Human-in-the-loop

多模态输出更容易被用户当成真实证据：

- 图片看起来真实。
- 语音听起来可信。
- 视频有强叙事性。
- 数字人增加信任感。

因此人工介入点应前置：

- 发布前。
- 外部发送前。
- 生成肖像或声音前。
- 操作真实系统前。
- 低置信度视觉判断前。

## 七、对项目 E 的启发与实践路线

多模态不应让项目 E 变成大而全的平台。更合理的方式是：在 Agent Runtime & Governance Lab 中新增一个可选的 Multimodal Track。

### 7.1 项目 E 的定位补充

原项目 E 可以增加一个判断：

```text
Agent Runtime 不只管理文本推理，也要管理媒体输入、媒体输出和媒体工具。
```

因此，Runtime 八层模型需要扩展：

| Runtime 层 | 多模态补充 |
|------------|------------|
| Task Contract | 输入/输出模态、媒体权限、发布范围 |
| Context Engineering | 音视频切片、图像压缩、OCR、抽帧、媒体摘要 |
| Artifact Protocol | transcript、keyframe、OCR、media generation job |
| Tool Governance | 摄像头、麦克风、屏幕、生成工具、声音克隆权限 |
| Execution Runtime | 流式会话、异步媒体任务、轮询、取消、重试 |
| Safety Runtime | 深伪、版权、肖像、声音、隐私、prompt injection |
| Observability | 多模态 trace、媒体引用、时间戳、成本、延迟 |
| Evaluation Loop | WER、图像 grounding、视频时间戳、声画同步、人工审核 |

项目 E 还应该加入一个模型分层原则：

```text
高频、低风险、可验证的感知任务：优先小模型或专用模型
需要综合推理、计划和解释的任务：使用更强的通用模型
涉及发布、权限、财务、安全、法务的任务：进入人工审核或高等级 guardrail
```

这样可以避免两个极端：

- 所有多模态任务都调用最强模型，导致成本和延迟过高。
- 过度迷信小模型，把不稳定能力用于高风险决策。

更好的实践是让每个模型都有明确的 `capability contract`：它处理什么输入、输出什么 artifact、置信度如何表达、失败时如何降级、哪些结果必须交给人或更强模型复核。

### 7.2 最小实验 1：图片/文档理解 Agent

目标：让 Agent 接收一张截图、票据、表格或文档页，生成结构化 artifact。

流程：

```text
image -> small VLM/OCR/detector -> ImageUnderstandingArtifact -> validator -> summary
```

验收标准：

- 保存原图路径。
- 保存 OCR 结果。
- 保存结构化字段。
- 保存模型和耗时。
- 记录使用的是小模型、专用模型还是云端大模型。
- 输出可复盘 trace。

价值：

- 低风险。
- 容易验证。
- 和企业知识库、文档处理场景高度相关。
- 可以直接验证小模型是否已经足够承担项目级视觉感知任务。

### 7.3 最小实验 2：语音输入到 Agent

目标：用户上传一段短音频，Agent 转写、理解、生成结构化任务。

流程：

```text
audio -> ASR -> TranscriptArtifact -> TaskContract -> Agent step
```

验收标准：

- 保存音频文件引用。
- 保存 transcript。
- 保存语言、时长、延迟。
- 关键字段可人工修正。

价值：

- 为实时语音 Agent 做准备。
- 先从离线音频开始，避免 WebRTC 复杂度。

### 7.4 最小实验 3：视频摘要与时间戳引用

目标：上传短视频，Agent 输出摘要、关键事件、时间戳和后续任务建议。

流程：

```text
video -> transcript/keyframes -> small video VLM -> VideoUnderstandingArtifact -> report
```

验收标准：

- 支持 1-3 分钟短视频。
- 输出关键片段时间戳。
- 输出摘要和问题列表。
- trace 中记录处理耗时和成本。

价值：

- 直接验证多模态 context engineering。
- 对调研、课程、会议、演示视频有实际价值。
- 可以评估“抽帧 + 小模型 + 结构化校验”是否比直接调用大模型更稳定。

### 7.5 最小实验 4：图像生成作为受控工具

目标：Agent 根据结构化 brief 生成一张内部草稿图，并进入人工审核。

流程：

```text
CreativeBrief -> image generation tool -> ImageGenerationArtifact -> moderation -> approval
```

验收标准：

- prompt 和 revised prompt 可追踪。
- 输出文件可版本化。
- 未审批前状态为 draft。
- 审批后才能标记 deliverable。

价值：

- 练习生成型工具的权限和版本治理。
- 不把生成结果直接当最终答案。

### 7.6 最小实验 5：实时语音 Agent 只做对照研究

实时语音 Agent 很有价值，但不建议作为第一阶段实现。原因：

- WebRTC / WebSocket / SIP 复杂度高。
- 低延迟调试成本高。
- VAD、打断和音频播放状态容易制造大量边界问题。
- 工具调用与实时对话同步需要更强 runtime。

建议先做文档研究和原型对照，等前面 artifact、trace、tool governance 稳定后再进入。

## 八、风险与治理清单

### 8.1 隐私风险

| 风险 | 示例 | 治理方式 |
|------|------|----------|
| 语音隐私 | 会议录音、客服录音 | 明示授权、最小保存、可删除 |
| 图像隐私 | 证件、合同、屏幕截图 | 脱敏、遮挡、访问控制 |
| 视频隐私 | 监控、课堂、医疗场景 | 场景授权、用途限制 |
| 生物特征 | 人脸、声音 | 强授权、默认禁止克隆 |

### 8.2 安全风险

| 风险 | 示例 | 治理方式 |
|------|------|----------|
| 多模态 prompt injection | 图片/网页/视频中写着“忽略之前指令” | 感知层隔离、工具前确认 |
| 误识别触发动作 | ASR 把语音误转成危险命令 | 高风险动作复述确认 |
| computer use 误操作 | 点击错误按钮、提交错误表单 | 沙箱、逐步审批 |
| 深度伪造 | 克隆声音、生成仿真人像视频 | 禁止默认开放、发布审核 |

### 8.3 质量风险

| 风险 | 示例 | 治理方式 |
|------|------|----------|
| 视觉幻觉 | 图片中不存在的对象被识别出来 | 区域证据、置信度、人工复核 |
| 视频时间错位 | 引用错误时间戳 | 时间戳 eval |
| 图像文字错误 | 海报、图表文字扭曲 | OCR 回检 |
| 声画不同步 | 口型和音频不匹配 | 同步评分、人工审核 |
| 品牌不一致 | 生成图误改 logo 或人物 | reference lock、版本比较 |

### 8.4 法务与合规风险

多模态生成比文本更容易触碰版权和肖像权：

- 训练数据来源不透明。
- 参考图授权不清。
- 人脸相似度过高。
- 声音克隆缺少授权。
- 生成视频可能被误认为真实记录。
- 对外发布需要标识或水印。

项目 E 不需要解决所有法务问题，但需要设计字段：

```text
source_license
consent_record
provenance_metadata
watermark_status
publish_scope
reviewer
```

## 九、结论

多模态能力已经足够成熟，值得进入 Agent 学习和实践，但进入方式应该克制。

推荐判断：

```text
短期：先做离线图片、音频、短视频 artifact 化。
中期：把图像生成和语音生成作为受控工具接入。
后期：再研究实时语音、实时视觉和 computer use。
```

最重要的不是追逐最新模型，而是建立多模态 runtime 思维：

- 媒体输入先结构化。
- 媒体输出先审核。
- 多模态工具先分级。
- 大模型、小模型和专用模型分层使用。
- 所有过程进 trace。
- 成本和延迟显式计量。
- 生成内容进入版本治理。
- 高风险动作进入 human-in-the-loop。

对项目 E 来说，多模态方向最有价值的产出不是一个炫酷 demo，而是一套可复用的多模态 Agent Runtime 设计经验。

小模型能力成熟后，项目 E 的实践价值反而更高：它可以研究“如何把多个有限但可用的模型组织成可靠系统”，而不是只研究“如何调用一个最强 API”。这更接近真实工程中的成本、延迟、隐私和治理约束。

## 参考资料

### OpenAI

- [OpenAI：Advancing voice intelligence with new models in the API](https://openai.com/index/advancing-voice-intelligence-with-new-models-in-the-api/)
- [OpenAI Realtime and audio 文档](https://developers.openai.com/api/docs/guides/realtime)
- [OpenAI Realtime API 文档](https://platform.openai.com/docs/guides/realtime)
- [OpenAI Image generation 文档](https://developers.openai.com/api/docs/guides/image-generation)
- [OpenAI：Image generation API](https://openai.com/index/image-generation-api/)

### Google

- [Gemini Live API overview](https://ai.google.dev/gemini-api/docs/live-api)
- [Gemini Live API capabilities guide](https://ai.google.dev/gemini-api/docs/live-api/capabilities)
- [Gemini Video understanding](https://ai.google.dev/gemini-api/docs/video-understanding)
- [Veo 3.1 in Gemini API](https://ai.google.dev/gemini-api/docs/video)
- [Gemini Image generation](https://ai.google.dev/gemini-api/docs/image-generation)
- [Gemma 3n model overview](https://ai.google.dev/gemma/docs/gemma-3n)
- [Gemma 3 model overview](https://ai.google.dev/gemma/docs/core)

### Anthropic

- [Claude Vision](https://docs.claude.com/en/docs/build-with-claude/vision)
- [Claude Computer use tool](https://platform.claude.com/docs/en/agents-and-tools/tool-use/computer-use-tool)

### 语音与生成平台

- [ElevenLabs Documentation](https://elevenlabs.io/docs/overview/intro/)
- [MiniMax API 接口概览](https://platform.minimaxi.com/docs/api-reference/api-overview)
- [MiniMax 视频生成](https://platform.minimaxi.com/docs/guides/video-generation)

### 开源与小模型

- [Qwen3.5-0.8B on Hugging Face](https://huggingface.co/Qwen/Qwen3.5-0.8B)
- [Qwen3-ASR-0.6B on Hugging Face](https://huggingface.co/Qwen/Qwen3-ASR-0.6B)
- [Qwen3-ASR Technical Report](https://arxiv.org/abs/2601.21337)
- [Qwen3-VL 官方仓库](https://github.com/QwenLM/Qwen3-VL)
- [Qwen2.5-VL 官方博客](https://qwenlm.github.io/blog/qwen2.5-vl/)
- [Kimi-VL 官方仓库](https://github.com/MoonshotAI/Kimi-VL)
- [MiniCPM-V 官方仓库](https://github.com/OpenBMB/MiniCPM-V)
- [InternVL3.5 官方博客](https://internvl.github.io/blog/2025-08-26-InternVL-3.5/)
- [GLM-V 官方仓库](https://github.com/THUDM/GLM-4.1V-Thinking)
- [Ovis2.5 Technical Report](https://arxiv.org/abs/2508.11737)
- [SmolVLM2：Bringing Video Understanding to Every Device](https://huggingface.co/blog/smolvlm2)
- [Moondream Docs](https://docs.moondream.ai/)
- [Moondream Models](https://moondream.ai/p/models)
- [Microsoft Florence-2 on Hugging Face](https://huggingface.co/microsoft/Florence-2-base)
- [Llama 3.2 11B Vision on Hugging Face](https://huggingface.co/meta-llama/Llama-3.2-11B-Vision-Instruct)
- [SmolLM3-3B on Hugging Face](https://huggingface.co/HuggingFaceTB/SmolLM3-3B)
- [Jan-Nano Technical Report](https://arxiv.org/abs/2506.22760)
- [Jan-Code-4B on Hugging Face](https://huggingface.co/janhq/Jan-code-4b)
- [TinyCodeLM-150M on Hugging Face](https://huggingface.co/upiter/TinyCodeLM-150M)
- [Voxtral Mini Transcribe Realtime](https://docs.mistral.ai/models/voxtral-mini-transcribe-realtime-26-02)
- [VibeVoice-Realtime-0.5B on Hugging Face](https://huggingface.co/microsoft/VibeVoice-Realtime-0.5B)
- [CosyVoice2](https://funaudiollm.github.io/cosyvoice2/)
- [Pocket TTS](https://kyutai.org/tts)
- [MOSS-TTS-Nano](https://github.com/OpenMOSS/MOSS-TTS-Nano)
- [TinyTTS](https://github.com/tronghieuit/tiny-tts)

### 国内多模态平台

- [Qwen2.5-Omni 官方博客](https://qwenlm.github.io/blog/qwen2.5-omni/)
- [阿里云百炼视频生成](https://www.alibabacloud.com/help/zh/model-studio/use-video-generation)
- [腾讯混元生视频](https://cloud.tencent.com/document/product/1616/107786)
- [腾讯混元生图 API 概览](https://cloud.tencent.com/document/product/1668/88077)
- [百度 Qianfan-VL](https://baidubce.github.io/Qianfan-VL/)
- [百度智能云语音合成](https://cloud.baidu.com/doc/qianfan-docs/s/sm8pqtkt3)
