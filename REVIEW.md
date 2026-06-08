# 🔍 代码审查记录

> 本文档是陈明远（CTO）与赵铁城（后端工程师）之间的代码审查协作文件。
> 每次审查为一轮（Round），陈明远写修改意见，赵铁城回复修改结果并推送。
>
> **协作流程**：
> 1. 陈明远拉取最新代码，审查后在本文件写入修改意见 → `git commit && git push`
> 2. 赵铁城拉取最新代码，逐条阅读意见，修改代码后在对应条目下回复 → `git commit && git push`
> 3. 陈明远拉取验证，确认修复后标记 ✅ → 进入下一轮

---

## Round 1 - 2026-06-08 14:30

### 审查摘要
- **审查人**: 陈明远
- **审查范围**: 全项目首次详细审查，覆盖 24 个源文件（src/、config/、tests/、scripts/）
- **总体评价**: 项目架构清晰，模块划分合理，代码质量扎实。MediaCrawler 复用路线正确，人类行为模拟设计到位。以下意见按严重程度排序，优先处理 🔴🟡。

### 修改意见

#### #1 `src/__init__.py` — 包导入时执行副作用
- **严重程度**: 🟡 一般
- **涉及文件**: `src/__init__.py:1-3`
- **问题描述**: 包级 `__init__.py` 在 import 时直接调用 `ensure_mediacrawler_path()`，这会修改 `sys.path` 和清除 `sys.modules` 中的 config 缓存。任何 `from src.xxx import y` 都会触发这个副作用，在测试环境或多模块导入场景下可能引发难以追踪的 import 顺序问题。
- **修改建议**: 将 `ensure_mediacrawler_path()` 调用移到 `main.py` 的入口处，或改为懒加载模式（仅在首次需要 MediaCrawler 时调用）。`__init__.py` 应保持无副作用。

#### #2 `src/miner/crawler.py` — `_with_retries` 异常处理过于宽泛
- **严重程度**: 🟡 一般
- **涉及文件**: `src/miner/crawler.py:144-157`
- **问题描述**: `_with_retries` 方法对 `except Exception` 做了全量捕获。如果遇到 `asyncio.CancelledError`（Python 3.9+ 它不再是 Exception 的子类，但仍有类似问题）或不可恢复的错误（如 `TypeError`、`AttributeError`），重试无意义且会浪费时间和资源。
- **修改建议**: 
  - 将不可重试的异常（`TypeError`、`ValueError`、`AttributeError`）直接抛出，不做重试
  - 可重试的异常限定为网络相关异常：`httpx.HTTPError`、`TimeoutError`、`ConnectionError`
  - 保留限流检测逻辑（已做得很好）

#### #3 `src/extractor/post.py` — 本地 fallback 的 `normalize_interaction_count` 精度不足
- **严重程度**: 🟡 一般
- **涉及文件**: `src/extractor/post.py:9-15`
- **问题描述**: 当 MediaCrawler 的 `tools.crawler_util` 不可用时，fallback 函数只处理了 `"2.2万"` 格式和纯数字，但没有处理：
  - 小写 `"w"` 缩写（如 `"2.2w"`）
  - K/M 缩写（如 `"1.2k"`）
  - 空字符串 `""` 已处理（返回 0），但 `None` 未处理
  - 小数点后多位的 `"2.23万"` 精度丢失（`int(2.23*10000)` = 22300 而非更精确处理）
- **修改建议**: 
  - 增加 `"w"`、`"k"`、`"m"` 单位的处理
  - 对 `None` 输入做防御
  - 考虑直接用 `round(float(value) * 10000)` 而非 `int()`，保留更精确的整数

#### #4 `src/storage/models.py` — `Post.image_urls` 和 `Post.tag_list` 类型混乱
- **严重程度**: 🟡 一般
- **涉及文件**: `src/storage/models.py:30-31`
- **问题描述**: 两个字段的类型标注为 `list[str] | str`，默认值是 `list`，但在 database.py 中入库时转为 JSON 字符串，出库时却保持字符串格式。这导致同一个 `Post` 对象在不同生命周期中字段类型不一致（创建时是 list，入库后变 str）。
- **修改建议**: 
  - 模型层统一为 `list[str]`，默认值 `field(default_factory=list)`
  - 序列化/反序列化逻辑全部封装在 `Database` 层（`upsert_post` 写入时序列化，查询方法中反序列化）
  - 删除类型标注中的 `| str`

#### #5 `src/miner/crawler.py` — `_get_blogger_info` 和 `_get_blogger_posts` 冗余检查
- **严重程度**: 🟢 建议
- **涉及文件**: `src/miner/crawler.py:89,102`
- **问题描述**: 两个方法在开头都检查 `if self.xhs_client is None: raise RuntimeError`。但这两个方法只在 `crawl_blogger` 中 `_ensure_client()` 之后调用，这个检查永远不会触发。冗余代码增加维护负担。
- **修改建议**: 删除这两个 `RuntimeError` 检查，或改为 `assert self.xhs_client is not None`（开发期断言）。

#### #6 `src/pipeline.py` — `run_one` 使用 O(n) 线性搜索
- **严重程度**: 🟢 建议
- **涉及文件**: `src/pipeline.py:38-42`
- **问题描述**: 通过遍历 `bloggers_config["bloggers"]` 列表查找指定 user_id。当前配置只有1个博主没影响，但如果博主列表扩展到几十上百个，每次 `run_one` 都是 O(n)。
- **修改建议**: 在 `__init__` 中预构建 `{user_id: config}` 的索引字典，`run_one` 直接 O(1) 查找。

#### #7 `src/storage/database.py` — 缺少连接池和并发保护
- **严重程度**: 🟢 建议
- **涉及文件**: `src/storage/database.py:18-32`
- **问题描述**: 每次操作都创建新的 SQLite 连接（`:memory:` 除外）。SQLite 在多线程下默认是串行化的，但如果将来引入 asyncio 并发（多个 blogger 同时采集），单连接可能成为瓶颈。
- **修改建议**: 
  - 当前阶段可以不改，因为爬虫是单 blogger 串行
  - 在代码注释中标注：如果将来改为并发采集，需要切换到 `aiosqlite` 或连接池模式

#### #8 测试覆盖不足
- **严重程度**: 🟢 建议
- **涉及文件**: `tests/` 目录
- **问题描述**: 现有 4 个测试文件覆盖了模型创建、CRUD 操作、数据提取和延时模拟。缺少：
  - `config_loader` 测试（YAML 解析、Settings 加载、校验逻辑）
  - `pipeline` 集成测试（dry-run 流程、错误处理路径）
  - `crawler` 的 `_parse_creator` 测试（各种 URL 格式、user_id 格式）
  - `_is_rate_limit_error` 测试（中文/英文限流消息）
- **修改建议**: 优先补 `config_loader` 和 `_parse_creator` 的测试，这两块是用户输入的入口，容易出边界问题。

#### #9 缺少 `uv.lock` 文件
- **严重程度**: 🟢 建议
- **涉及文件**: 仓库根目录
- **问题描述**: `uv.lock` 未被 git 追踪。虽然 `.gitignore` 没有排除它，但实际没有提交。这会导致不同环境安装的依赖版本不一致，可能出现"我这边能跑你那边不行"的问题。
- **修改建议**: `uv sync` 生成 `uv.lock` 后 `git add uv.lock && git commit`。

#### #10 `src/mediacrawler.py` — `ensure_mediacrawler_path` 副作用风险
- **严重程度**: 🟢 建议
- **涉及文件**: `src/mediacrawler.py:10-21`
- **问题描述**: 函数除了 `sys.path.insert` 外，还遍历 `sys.modules` 清除名为 `config` 的缓存模块。这是为了防止 MediaCrawler 和自己的 `config/` 目录冲突，但副作用范围不透明——如果其他模块恰好也有 `config` 包，会被误删。
- **修改建议**: 加一个注释说明这个 hack 的原因和影响范围。长期方案是让 MediaCrawler 使用命名空间包或重命名其 config 模块。

#### #11 `.env.example` 缺少 `MEDIACRAWLER_PATH`
- **严重程度**: 🟢 建议
- **涉及文件**: `.env.example`
- **问题描述**: README 和 `mediacrawler.py` 都提到 `MEDIACRAWLER_PATH` 环境变量，但 `.env.example` 中没有这个字段。新用户可能不知道有这个配置项。
- **修改建议**: 在 `.env.example` 中添加 `# MEDIACRAWLER_PATH=~/.openclaw/tools/MediaCrawler`（注释掉，作为文档）。

---

> ⏳ 待赵铁城逐条回复

---
<!-- 
  格式说明：
  - 每个修改意见用 #N 编号，一轮内不重复
  - 严重程度：🔴 严重（阻塞上线） / 🟡 一般（需修复） / 🟢 建议（可后续优化）
  - 赵铁城回复写在引用块（>）内，标注时间和状态
  - 状态标记：✅ 已修改 / 🔄 进行中 / ❓ 有争议 / ⏸️ 暂缓
-->
