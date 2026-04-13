# Rehearsal 上传链路修复总结

这份文档总结了本轮 `rehearsal` 上传预演相关的全部修复，重点说明 Celery/Windows 环境下为什么会出问题、怎么一步步定位、以及最终落地了哪些修复。

## 1. 本轮修复覆盖了什么

主要修了五类问题：

1. 上传型预演的数据模型、上传接口、文件处理链路
2. 上传页处理完成后，讲稿生成、TTS、播放器复用接入
3. Windows + Celery worker 导致上传任务卡住、`processing` 不推进
4. `start_dev.py` 启动方式和单独启动行为不一致
5. 上传预演重新进入播放后字幕丢失、图片首屏加载慢或空白

## 2. 先修好的基础链路

### 2.1 上传型预演的基础能力

先补了上传型预演的数据字段和接口能力：

- `backend/app/models/rehearsal.py`
- `backend/app/schemas/rehearsal.py`
- `backend/app/services/rehearsal_upload_service.py`
- `backend/app/services/rehearsal_file_processing_service.py`
- `backend/app/services/rehearsal_upload_generation_service.py`

能力范围包括：

- 支持 `PDF / PPT / PPTX` 上传
- 文件大小上限 `50MB`
- 文件页数上限 `30 页`
- 原文件上传到 OSS
- `PPT / PPTX -> PDF` 转换
- PDF 拆页
- 页图渲染
- 页文本解析
- 空白页 / 封底页识别
- 页级状态汇总到 session 状态
- 讲稿生成
- TTS 音频生成
- 上传页复用现有播放器

### 2.2 处理状态模型

上传型预演使用这套状态：

- session 级：`processing / partial / ready / failed`
- scene 级：`pending / generating / ready / fallback / skipped / failed`

其中：

- `ready` 表示页面正常解析，可正常播放
- `fallback` 表示页图有了，但文本或讲稿链路部分失败，仍然允许播放
- `skipped` 表示空白页或封底页，进入跳过

## 3. 第一批关键 bug 修复

### 3.1 AsyncSession.added 导致真实环境崩溃

问题：

- `backend/app/services/rehearsal_file_processing_service.py` 早期版本用了 `db.added`
- 真实 `AsyncSession` 没有这个属性
- 结果是上传处理一到第一页就抛 `AttributeError`
- 后台任务直接走失败分支，会话被标成失败

修复：

- 去掉对 `AsyncSession.added` 的依赖
- 改成只在对象是新对象、且 `db.add` 可用时补注册

### 3.2 成功页面没有标记成 ready

问题：

- 正常解析成功的上传页，`scene_status` 还停留在 `pending`
- 后续 `generate_upload_session_narration()` 只处理 `ready / fallback`
- 所以正常页根本不进入讲稿生成
- 整个 session 也会一直停在 `processing`

修复：

- 正常解析成功且非 `skipped` 的页面显式标记为 `ready`

### 3.3 上传进度页到播放器的场景映射不完整

问题：

- 从上传进度页直接进入播放时，前端有一段手写映射
- 这段逻辑只看 `slide_content / actions`
- 但上传页经常只有 `page_image_url / page_text / script_text / audio_url`
- 结果就是从进度页进去时出现空白页或没有讲稿

修复：

- 抽出统一映射模块 `teacher-platform/src/stores/rehearsalSceneMapping.js`
- `teacher-platform/src/stores/rehearsal.js`
- `teacher-platform/src/views/rehearsal/RehearsalNew.vue`

统一规则：

- 没有 `slide_content` 时，用 `page_image_url` 合成页图 slide
- 没有 `actions` 时，用 `script_text / page_text` 合成 `speech action`
- 有 `audio_url` 时自动映射到 `persistent_audio_url`

## 4. 数据库和运行环境问题

### 4.1 `/api/v1/rehearsal/sessions` 返回 500

现象：

- 前端看起来像“课程都没了”
- 实际数据库数据还在
- 但 `/api/v1/rehearsal/sessions` 返回 `500`

根因：

- 代码已经开始读取新增列：
  - `source`
  - `original_file_url`
  - `original_file_name`
  - `converted_pdf_url`
  - `total_pages`
  - `page_image_url`
  - `script_text`
  - `audio_url`
- 但本地数据库还停留在旧 Alembic 版本
- ORM 查询时直接读到不存在的列，所以接口 500

修复：

- 跑数据库迁移到 `20260412_rehearsal_upload_fields`

### 4.2 上传时报 `No module named 'PyPDF2'`

现象：

- 上传时页数检测报错：`文件页数检测失败: No module named 'PyPDF2'`

根因：

- 页数检测逻辑优先用 `fitz`
- 没有 `fitz` 时 fallback 到 `PyPDF2`
- 当前运行环境里缺少 `PyPDF2`

修复：

- 安装 `PyPDF2==3.0.1`

## 5. Celery / Windows 修复过程

这一段是整个问题里最关键的部分。

### 5.1 最开始的现象

上传文件后：

- session 可以创建成功
- 数据库里 `rehearsal_sessions.status` 一直停在 `processing`
- `total_scenes=0` 或 scene 不继续推进
- 页面一直转圈

同时，Celery worker 终端里出现过这类错误：

- `ValueError('not enough values to unpack (expected 3, got 0)')`
- 栈在 `celery.app.trace.fast_trace_task`

### 5.2 第一层根因：Windows 上 prefork 不稳定

这是当时和 PPT 生成问题相同的一层：

- Celery 默认 worker pool 是 `prefork`
- 在 Windows 上这套经常不稳定
- 任务一旦进 worker，就可能在 trace 层直接炸掉

所以第一轮修复做了：

- `backend/app/celery.py`
- `backend/start_dev.py`

具体是：

- Windows 下默认把 worker pool 切成 `solo`
- 并把并发降成 `1`

也就是：

- `worker_pool='solo'`
- `worker_concurrency=1`
- 启动命令显式补 `--pool=solo --concurrency=1`

### 5.3 第二层根因：上传任务名冲突

光改 `solo` 还不够，因为上传链路还有任务名冲突：

- 旧的 `backend/app/tasks.py`
- 新的 `backend/app/rehearsal_tasks.py`

都曾使用过同名任务：

- `app.tasks.process_rehearsal_upload_session`

这会导致：

- worker 收到上传任务后，可能跑到旧任务实现
- 或者任务路由、日志、问题定位全部混乱

修复：

- 把上传任务名改成唯一的：
  - `app.rehearsal_tasks.process_rehearsal_upload_session`

这一步是为了让 worker、dispatcher、日志、路由全部指向同一条上传处理实现。

### 5.4 为什么只改 solo 还不够

这里和 PPT 的区别最重要。

#### PPT 那边为什么只改 solo 就够

PPT 当时的核心问题是：

- 任务已经成功派发到了 Celery worker
- 只是 worker 在 Windows 上用 `prefork` 不稳定

所以：

- 改成 `solo`
- worker 就能正常执行

#### rehearsal 这边为什么不够

`rehearsal` 后来又额外接了“本地子进程兜底”：

- Windows 下不强依赖 Celery worker
- 派发失败时，本地再起一个 Python 子进程直接跑上传处理

但这条兜底链第一版用了：

- `asyncio.create_subprocess_exec(...)`

而你当前 Windows 环境里，这一步会直接：

- 抛 `NotImplementedError`

所以实际情况变成：

1. Celery 这条路在 Windows 上有问题
2. 本地兜底子进程这条路也起不来

结果就是：

- session 创建成功
- 但后台处理根本没有真正进入执行

### 5.5 rehearsal 兜底模式是怎么做的

参考了 PPT 那套 dispatcher 思路，补了两个文件：

- `backend/app/rehearsal_task_dispatcher.py`
- `backend/app/rehearsal_task_runner.py`

职责划分：

- `rehearsal_task_dispatcher.py`
  - 决定是走 Celery 还是走本地子进程
- `rehearsal_task_runner.py`
  - 作为单独 Python 进程入口，直接执行上传任务

上传入口：

- `backend/app/services/rehearsal_upload_service.py`

不再直接 `.delay()`，而是统一走 dispatcher。

### 5.6 本地兜底第一版为什么失败

第一版本地兜底用了：

- `asyncio.create_subprocess_exec(...)`

你提供的日志已经明确说明：

- `POST /api/v1/rehearsal/upload` 成功
- 但日志出现 `Failed to spawn rehearsal local task subprocess`
- 根因是 `asyncio.create_subprocess_exec(...)` 抛 `NotImplementedError`

说明问题不是“处理慢”，而是：

- 连兜底子进程都没创建出来

### 5.7 最终兜底修复

最终把本地兜底改成同步子进程启动：

- `subprocess.Popen(...)`

落点：

- `backend/app/rehearsal_task_dispatcher.py`

这一步的意义：

- 不再依赖当前事件循环对子进程能力的支持
- 避开 Windows 下 `asyncio.create_subprocess_exec` 的兼容问题

最终 dispatcher 策略变成：

#### Windows

- `rehearsal` 上传任务默认直接走本地子进程兜底

#### 非 Windows

- 先尝试 Celery
- 派发失败再 fallback 到本地子进程

### 5.8 `start_dev.py` 为什么也要修

后面又发现一个更隐蔽的问题：

- 你分开开两个终端时，上传能工作
- 但用 `python start_dev.py` 启动时，上传更容易失败

根因不是 Celery 配置本身，而是 `start_dev.py` 的子进程管理方式：

- FastAPI 和 Celery 都被 `stdout=PIPE / stderr=STDOUT` 接管
- 但脚本本身没有持续消费这些输出
- 开发态日志一多，就有机会把子进程输出管道堵住
- 结果表现成启动方式不同、行为不同

修复：

- `backend/start_dev.py`

具体改动：

- 去掉对子进程输出的 `PIPE` 捕获
- 让 FastAPI / Celery 直接继承当前终端输出
- 新增 `build_child_process_env()`
- 设置 `PYTHONUNBUFFERED=1`

所以现在：

- `python start_dev.py` 启动时
- FastAPI 和 Celery 都直接在当前终端打印日志
- 不再因为开发脚本的管道阻塞把服务拖死

### 5.9 最终 Celery 相关的稳定方案

现在 `rehearsal` 这条链路是双保险：

#### 第一层

- Celery 在 Windows 下使用 `solo`

#### 第二层

- `rehearsal` 上传任务在 Windows 下默认走本地子进程兜底

#### 第三层

- `start_dev.py` 不再用会堵塞的 `PIPE`

所以最终目标不是“只修 Celery”，而是把这三层都补完整：

1. worker 执行模型修正
2. 上传任务派发路径去歧义
3. Windows 本地兜底可用
4. 开发启动脚本不再制造假故障

## 6. 前端播放相关修复

### 6.1 上传成功后跳转时序

问题：

- 上传成功后，前端先清文件，再跳转
- 如果跳转链路失败，用户就会看到“文件没了，但还停在原页面”

修复：

- `teacher-platform/src/views/rehearsal/RehearsalLab.vue`

改成：

- 先 `await router.push(...)`
- 跳转成功后再清本地文件选择态

### 6.2 重新进入播放后字幕不显示

问题：

- 播放页的字幕组件只依赖 `store.currentSubtitle`
- 但重新进入播放时，字幕通常还没被 `speech action` 再次触发
- 所以底部文案可能是空的

修复：

- `teacher-platform/src/stores/rehearsalSceneMapping.js`
- `teacher-platform/src/views/rehearsal/RehearsalPlay.vue`
- `teacher-platform/src/stores/rehearsal.js`

现在的策略：

- 优先显示 `store.currentSubtitle`
- 如果为空，就回退到当前页的讲稿文本
  - `speech action.text`
  - `scriptText`
  - `title`

这样即使重新进入播放、还没按下播放键，也不会出现底部文案完全消失。

### 6.3 播放快照恢复不正确

问题：

- 之前保存的 `actionIndex` 可能落到“当前 speech 已经自增后的下一个 action”
- 重新进入时，就会恢复到错误位置
- 上传页通常 action 很少，这个偏移会放大成“直接没字幕”

修复：

- `teacher-platform/src/stores/rehearsal.js`

增加了两层处理：

- 读取 session 时规范化 `sceneIndex / actionIndex`
- 保存播放快照时，如果当前处于播放中，则回退到当前 speech action 的索引

### 6.4 图片首次进入慢或不显示

问题：

- 上传页通常依赖 `page_image_url`
- 初次进入播放页时如果大图还没加载完，就会看起来像“没渲染出来”

修复：

- `teacher-platform/src/stores/rehearsalSceneMapping.js`
- `teacher-platform/src/stores/rehearsal.js`
- `teacher-platform/src/views/rehearsal/RehearsalPlay.vue`

新增：

- 当前页图片预热
- 后续几页图片预取

目标是减少：

- 首屏空白
- 首次进入切页慢
- 重新进入后第一张图慢

## 7. start_dev.py 现在能不能直接用

现在可以直接用，但前提是：

- 必须在 `conda base` 环境启动

建议方式：

```powershell
conda activate base
cd D:\Develop\Project\AIsystem\backend
python start_dev.py
```

原因：

- `start_dev.py` 会用当前 `sys.executable`
- 所以你从哪个 Python 环境启动，它就用哪个环境去拉起 FastAPI 和 Celery
- 只要你在 `base` 里启动，就不会再出现“API 一套解释器、worker 另一套解释器”的问题

## 8. 本轮还特意避免了什么

- 没有再改 `backend/app/tasks.py` 的中文编码
- 上传任务新逻辑放到了独立的 `backend/app/rehearsal_tasks.py`
- 本地兜底也放到了独立 dispatcher/runner 文件里

这是为了避免再碰你明确提醒过的 `tasks.py` 编码问题。

## 9. 这轮修复后验证过什么

跑过的验证包括：

- `pytest tests/test_rehearsal_processing_pipeline.py tests/test_rehearsal_task_dispatcher.py -q`
- `pytest tests/test_start_dev.py tests/test_start_dev_waits.py -q`
- `node src/stores/rehearsal.test.js`
- `npm run build`

通过结果：

- `rehearsal` 上传处理分发回归通过
- `start_dev.py` 启动参数和子进程管理回归通过
- 前端上传场景映射和字幕回退脚本通过
- 前端构建通过

保留的仅是已有警告：

- `pytest-asyncio` 的 fixture loop scope deprecation warning
- `lottie-web` 的 `eval` warning
- Vite 的大 chunk warning

## 10. 最终结论

这轮最核心的经验不是“把 Celery 改成 solo”这么简单，而是要分清三层问题：

1. Windows 上 Celery `prefork` 不稳定，所以 worker 要改 `solo`
2. 上传任务本身不能和旧任务重名，否则 worker/dispatcher 会混乱
3. Windows 本地兜底不能用 `asyncio.create_subprocess_exec`，要改成 `subprocess.Popen`
4. `start_dev.py` 不能把 FastAPI/Celery 输出接到无人消费的 `PIPE`，否则会制造额外假故障

PPT 那边当时只需要修第 1 层。

`rehearsal` 这次之所以更复杂，是因为它同时踩中了：

- worker 执行模型
- 任务命名冲突
- 本地兜底创建失败
- 开发启动脚本输出管道阻塞

所以最后必须把这几层一起修，上传链路才会真正稳定。
