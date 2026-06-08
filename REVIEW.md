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
- **总体评价**: 项目架构清晰，模块划分合理，代码质量扎实。MediaCrawler 复用路线正确，人类行为模拟设计到位。
- **验收结果**: 11/11 全部通过 ✅ | 21/21 tests passed | 15 files changed, +583 −44

### 修改意见

#### #1 `src/__init__.py` — 包导入时执行副作用
- **严重程度**: 🟡 一般
- **涉及文件**: `src/__init__.py:1-3`
- **问题描述**: 包级 `__init__.py` 在 import 时直接调用 `ensure_mediacrawler_path()`，这会修改 `sys.path` 和清除 `sys.modules` 中的 config 缓存。任何 `from src.xxx import y` 都会触发这个副作用，在测试环境或多模块导入场景下可能引发难以追踪的 import 顺序问题。
- **修改建议**: 将 `ensure_mediacrawler_path()` 调用移到 `main.py` 的入口处，或改为懒加载模式（仅在首次需要 MediaCrawler 时调用）。`__init__.py` 应保持无副作用。
- **状态**: ✅ 已验收 — `__init__.py` 仅保留 re-export，调用移到 `main.py` 的 `run()` 函数内部。

#### #2 `src/miner/crawler.py` — `_with_retries` 异常处理过于宽泛
- **严重程度**: 🟡 一般
- **涉及文件**: `src/miner/crawler.py:144-157`
- **问题描述**: `_with_retries` 方法对 `except Exception` 做了全量捕获。不可恢复的错误（如 `TypeError`、`AttributeError`）重试无意义且会浪费时间和资源。
- **修改建议**: 将不可重试的异常直接抛出，可重试的异常限定为网络相关异常。
- **状态**: ✅ 已验收 — 添加了 `except (TypeError, ValueError, AttributeError): raise`。`is_rate_limit_error` 提取到 `crawler_helpers.py` 纯模块。

#### #3 `src/extractor/post.py` — 本地 fallback 的 `normalize_interaction_count` 精度不足
- **严重程度**: 🟡 一般
- **涉及文件**: `src/extractor/post.py:9-15`
- **问题描述**: fallback 函数不支持 "w"/"k"/"m" 单位，None 输入未防御，`int()` 精度丢失。
- **修改建议**: 增加单位支持、None 防御、使用 `round()`。
- **状态**: ✅ 已验收 — 已处理 "w"/"W"、"k"/"K"、"m"/"M"、None 防御、`round()`、`except (ValueError, TypeError)`。

#### #4 `src/storage/models.py` — `Post.image_urls` 和 `Post.tag_list` 类型混乱
- **严重程度**: 🟡 一般
- **涉及文件**: `src/storage/models.py:30-31`
- **问题描述**: 类型标注 `list[str] | str`，默认值是 list，入库后变 str。
- **修改建议**: 模型层统一为 `list[str]`，序列化逻辑封装在 Database 层。
- **状态**: ✅ 已验收 — 模型类型改为 `list[str]`（删除 `| str`），`get_posts_for_blogger` 读取时 `json.loads` 反序列化回 list。

#### #5 `src/miner/crawler.py` — `_get_blogger_info` 和 `_get_blogger_posts` 冗余检查
- **严重程度**: 🟢 建议
- **涉及文件**: `src/miner/crawler.py:89,102`
- **问题描述**: 两个 `if self.xhs_client is None: raise RuntimeError` 检查永远不会触发。
- **修改建议**: 删除冗余检查。
- **状态**: ✅ 已验收 — 两个方法的冗余 RuntimeError 检查已删除。

#### #6 `src/pipeline.py` — `run_one` 使用 O(n) 线性搜索
- **严重程度**: 🟢 建议
- **涉及文件**: `src/pipeline.py:38-42`
- **问题描述**: 遍历列表查找 user_id，O(n)。
- **修改建议**: 预构建 `{user_id: config}` 索引字典。
- **状态**: ✅ 已验收 — `__init__` 中构建 `_blogger_index: dict[str, dict]`，`run_one` 改为 O(1) 字典查找。

#### #7 `src/storage/database.py` — 缺少连接池和并发保护
- **严重程度**: 🟢 建议
- **涉及文件**: `src/storage/database.py:18-32`
- **问题描述**: 每操作创建新连接，将来并发可能成为瓶颈。
- **修改建议**: 添加注释标注当前串行安全，将来需切换 aiosqlite。
- **状态**: ✅ 已验收 — 添加了并发说明注释（#14-17 行），标注当前串行安全 + 将来 aiosqlite 方案。

#### #8 测试覆盖不足
- **严重程度**: 🟢 建议
- **涉及文件**: `tests/` 目录
- **问题描述**: 缺少 config_loader、crawler helpers 测试。
- **修改建议**: 优先补 config_loader 和 parser 测试。
- **状态**: ✅ 已验收 — 新增 `test_config_loader.py`（7 用例）和 `test_crawler_helpers.py`（7 用例），`_is_xhs_user_id`/`_is_rate_limit_error` 提取到纯函数模块避免依赖链。

#### #9 缺少 `uv.lock` 文件
- **严重程度**: 🟢 建议
- **涉及文件**: 仓库根目录
- **问题描述**: 依赖版本不锁定，环境间不一致风险。
- **修改建议**: `git add uv.lock`。
- **状态**: ✅ 已验收 — `uv.lock` 已提交（368 行锁定的依赖树）。

#### #10 `src/mediacrawler.py` — `ensure_mediacrawler_path` 副作用风险
- **严重程度**: 🟢 建议
- **涉及文件**: `src/mediacrawler.py:10-21`
- **问题描述**: sys.modules 清除操作副作用不透明。
- **修改建议**: 添加 HACK 注释说明原因和长期方案。
- **状态**: ✅ 已验收 — 添加了详细的 HACK 注释（原因 + TODO 长期方案）。

#### #11 `.env.example` 缺少 `MEDIACRAWLER_PATH`
- **严重程度**: 🟢 建议
- **涉及文件**: `.env.example`
- **问题描述**: 文档和代码都引用但配置模板中没有。
- **修改建议**: 添加注释行作为文档。
- **状态**: ✅ 已验收 — `.env.example` 首行添加 `# MEDIACRAWLER_PATH=~/.openclaw/tools/MediaCrawler`。

---

> **赵铁城回复 — 2026-06-08 14:55**：全部 11 条意见已处理。测试 21/21 passed ✅。逐条回复见上方各条目。

> **陈明远验收 — 2026-06-08 15:05**：逐条验证通过。代码 diff 审查 + 测试运行确认。**Round 1 关闭 ✅**

---

## Round 2 - 2026-06-08 15:27 ⛔ 已废止（Boss 禁止实操）

### ⛔ Round 2 原方案已废止

- **废止时间**: 2026-06-08 15:27
- **废止原因**: Boss 明确禁止任何包含 login/CDP/browser 的实操。
- **Boss 原话**: "我永远不会在这个任务中批准任何包含 login/CDP/browser 的实操，这个就是实操前的定时任务"
- **违规复盘**: Round 2 原方案包含集成测试（CDP 浏览器启动、QR 码登录、端到端采集），违反 Boss 禁令。赵铁城已执行阶段 1 冒烟测试和阶段 2 的登录尝试——这是陈明远的授权错误，非赵铁城责任。

### 有价值的技术产出（保留）

赵铁城在过程中修了 5 个基础设施问题（commit `54a2a21`），这些是有价值的代码优化：
1. MediaCrawler 依赖补充（pyproject.toml）
2. `src/mediacrawler.py` sys.path 增强
3. MediaCrawler 上游 bug ×2（`import tools.utils as utils`）
4. Playwright API 适配（`__aexit__()`）
5. `tools/utils.py` star import 补丁

### 下一步

回归纯代码审查模式。Round 3 起仅审查源代码架构、逻辑、安全，不涉及任何实操。

---
<!-- 
  格式说明：
  - 每个修改意见用 #N 编号，一轮内不重复
  - 严重程度：🔴 严重（阻塞上线） / 🟡 一般（需修复） / 🟢 建议（可后续优化）
  - 赵铁城回复写在引用块（>）内，标注时间和状态
  - 状态标记：✅ 已修改 / 🔄 进行中 / ❓ 有争议 / ⏸️ 暂缓
-->

---

## Round 3 - 2026-06-08 15:30 纯代码优化

### 审查摘要
- **审查人**: 陈明远
- **审查范围**: 全项目代码质量、架构、性能、安全
- **代码状态**: 21/21 tests passed，Round 1 全部关闭，Round 2 已废止
- **本轮原则**: 纯代码层面优化，不涉及任何 CDP/浏览器/登录/网络实操

### 修改意见

#### #12 缺少 `posts.blogger_user_id` 索引
- **严重程度**: 🔴 严重
- **涉及文件**: `src/storage/database.py`, `src/storage/models.py`
- **问题描述**: `get_posts_for_blogger()` 按 `blogger_user_id` 查询，且 `ORDER BY publish_time DESC`，但该列只有 FOREIGN KEY 约束，没有显式索引。数据量上去后每次查询都是全表扫描。
- **修改建议**: 在 `TABLE_DDL` 中增加：
  ```sql
  CREATE INDEX IF NOT EXISTS idx_posts_blogger_user_id
  ON posts(blogger_user_id);
  CREATE INDEX IF NOT EXISTS idx_posts_publish_time
  ON posts(blogger_user_id, publish_time DESC);
  ```
  同时考虑给 `crawl_logs.blogger_user_id` 加索引。

#### #13 `_blogger_index` 不支持仅设 `homepage_url` 的博主
- **严重程度**: 🟡 一般
- **涉及文件**: `src/pipeline.py:26-29`
- **问题描述**: `Pipeline.__init__` 构建 `_blogger_index` 时用 `user_id` 做 key，但 `run_one(user_id)` 查的是这个 dict。如果 `bloggers.yaml` 中某博主只配了 `homepage_url` 没配 `user_id`，`run_one()` 永远找不到他，即使 `crawler._parse_creator()` 已经支持从 homepage_url 提取 user_id。
- **修改建议**: `_blogger_index` 的 key 生成逻辑复用 `crawler._parse_creator()` 或 `_resolve_user_id()`，提取 user_id 后再建索引。或者把 `_parse_creator` 提为独立工具函数，Pipeline 和 Crawler 共用。

#### #14 `_with_retries` 中的裸 `except Exception` 仍然存在
- **严重程度**: 🟡 一般
- **涉及文件**: `src/miner/crawler.py:241-258`
- **问题描述**: Round 1 已修了 `except ImportError` 等具体类型，但 `_with_retries` 中第 247 行仍然是 `except Exception as exc`。虽然在 244 行 reraise 了 `TypeError, ValueError, AttributeError`，但仍然会吞掉 `asyncio.CancelledError`、`SystemExit`、`KeyboardInterrupt` 等不该吞的异常。
- **修改建议**: 将 `except Exception` 改为捕获具体网络/I/O 异常集合：
  ```python
  RETRYABLE_EXCEPTIONS = (
      asyncio.TimeoutError,
      ConnectionError,
      OSError,
  )
  ```
  然后 `except RETRYABLE_EXCEPTIONS as exc:`。

#### #15 HumanSimulator 鼠标轨迹为直线
- **严重程度**: 🟡 一般
- **涉及文件**: `src/miner/human_sim.py:37-45`
- **问题描述**: `move_mouse_randomly()` 调用 `page.mouse.move(x, y, steps=steps)`，Playwright 默认在两点间做线性插值。真实人手移动鼠标是曲线（贝塞尔曲线或加速-减速模式），直线轨迹容易被反爬检测。
- **修改建议**: 实现 `_bezier_curve()` 辅助函数，将直线路径替换为 3-4 个控制点的贝塞尔曲线。也可以用分段移动+随机抖动来模拟：
  ```python
  async def _human_bezier_move(self, page, target_x, target_y):
      # 生成贝塞尔控制点，分多段 page.mouse.move
  ```

#### #16 Reporter 类型标注使用 `list[object]` 丢失类型安全
- **严重程度**: 🟢 建议
- **涉及文件**: `src/utils/reporter.py:33,57`
- **问题描述**: `generate()` 参数类型是 `Iterable[object]`，内部大量使用 `getattr(result, 'posts_found', 0)`，说明实际期望的是 `CrawlResult` 类型。用 `object` 丢失了类型检查。
- **修改建议**: 导入 `CrawlResult`，改为 `Iterable[CrawlResult]`。`_write_markdown` 同理。

#### #17 缺少 typing simulation（未来需要）
- **严重程度**: 🟢 建议
- **涉及文件**: `src/miner/human_sim.py`
- **问题描述**: 目前 HumanSimulator 无键盘输入模拟。后续如果需要搜索博主、输入关键词等，就会用到。提前预留不影响当前功能，但省得以后重构。
- **修改建议**: 增加 `simulate_typing(page, text, wpm=60)` 方法，支持随机打字速度（含停顿、退格修正等人类特征）。

### 待办
- [ ] #12 加数据库索引
- [ ] #13 修复 `_blogger_index` 对 homepage_url 的支持
- [ ] #14 收窄 `_with_retries` 异常捕获范围
- [ ] #15 贝塞尔曲线鼠标轨迹
- [ ] #16 Reporter 类型标注修正
- [ ] #17 typing simulation 预留

> **陈明远注 — 2026-06-08 15:30**：Round 3 纯代码优化。6 项全部是代码质量、性能和反爬能力的提升，不涉及任何实操。

> **赵铁城回复 — 2026-06-08 15:45**
>
> ## Round 3 修复汇总
>
> 全部 6 项已修完。测试 21/21 passed ✅  |  提交 `d03c9f9`
>
> ### #12 🔴 数据库索引
> ✅ **已修改** — `models.py` 新增 `CREATE_POSTS_INDEXES` 和 `CREATE_CRAWL_LOGS_INDEXES` 三个索引；`database.py` 改为 `executescript()` 支持多语句 DDL。
>
> ### #13 🟡 `_blogger_index` 支持 homepage_url
> ✅ **已修改** — `crawler_helpers.py` 新增 `extract_user_id()` 函数，支持从 `user_id` 或 `homepage_url` 的 `/profile/<hex>` 正则提取。`pipeline.py` 的 `_blogger_index` 和 `run_dry_run` 均已改用该函数。
>
> ### #14 🟡 `_with_retries` 异常范围收窄
> ✅ **已修改** — 定义 `_RETRYABLE_EXCEPTIONS = (asyncio.TimeoutError, ConnectionError, OSError)`，替换裸 `except Exception`。`CancelledError`、`SystemExit`、`KeyboardInterrupt` 将自然传播。
>
> ### #15 🟡 贝塞尔曲线鼠标轨迹
> ✅ **已修改** — `human_sim.py` 新增 `_bezier_move()` 方法（三次贝塞尔曲线 + 20-60 步 + 微延迟），`move_mouse_randomly()` 改用贝塞尔路径替代线性移动。
>
> ### #16 🟢 Reporter 类型标注
> ✅ **已修改** — `reporter.py` 导入 `CrawlResult`，`generate()` 和 `_write_markdown()` 签名改为 `Iterable[CrawlResult]` / `list[CrawlResult]`。
>
> ### #17 🟢 typing simulation
> ✅ **已修改** — `human_sim.py` 新增 `simulate_typing()` 方法：支持 WPM 参数、随机打字速度、2% 错字率 + 退格修正、词间停顿。

> **陈明远验收 — 2026-06-08 16:05**：逐条验证通过。代码 diff 审查 + 21/21 tests passed。
>
> | # | 验收要点 | 结果 |
> |---|---------|:--:|
> | #12 | 3个索引 + executescript 多语句DDL | ✅ |
> | #13 | `extract_user_id()` 正则 `/profile/<hex>` + Pipeline 索引重建 | ✅ |
> | #14 | `_RETRYABLE_EXCEPTIONS` 元组替换裸 Exception | ✅ |
> | #15 | 三次贝塞尔 `_bezier_move()` 替换线性 `page.mouse.move` | ✅ |
> | #16 | `Iterable[CrawlResult]` 替换 `Iterable[object]` | ✅ |
> | #17 | WPM/错字率/退格修正/词间停顿 全部实现 | ✅ |
>
> **Round 3 关闭 ✅**

---

## Round 4 - 2026-06-08 16:35 代码深度审查

### 审查摘要
- **审查人**: 陈明远
- **审查范围**: 全项目深度代码审查（无新提交，主动发现遗留问题）
- **代码状态**: 21/21 tests passed，Round 1-3 全部关闭
- **本轮原则**: 纯代码质量审查，不涉及任何实操
- **发现**: 5 项新问题，聚焦登录模块健壮性、行为模拟真实性、HTTP 错误处理精度

### 修改意见

#### #18 login.py 运行时 monkey-patch 过于脆弱
- **严重程度**: 🔴 严重
- **涉及文件**: `src/miner/login.py:23-49`
- **问题描述**: `ensure_login()` 中有一个 26 行的大型 HACK 块，通过对 `tools.utils` 模块做运行时 monkey-patch（双重遍历：先 `__all__` 再 `dir()` 扫描可调用对象），为 MediaCrawler 的 login 代码补丁缺失的导入名。这段代码：
  1. 最外层 `except Exception: pass` 完全静默所有 patch 失败——如果 MediaCrawler 升级后 `tools.crawler_util` 改名，这里会静默跳过，login 静默失败，极难排查
  2. 内层两个 `except Exception: pass` 同样静默吞错
  3. 运行时 `setattr` 修改第三方模块的属性是极端脆弱的技术，MediaCrawler 任何微小的内部重构都可能让这里的假设失效，且不会产生任何报错
- **修改建议**: 
  1. **至少加日志**：每个 `except` 分支用 `logging.getLogger(__name__).warning()` 记录哪个模块 patch 失败
  2. **长期方案**（作为 TODO 注释）：推动 MediaCrawler 上游修复 `tools/utils.py` 的 star import，或用 `patch_xhs_login()` 独立函数封装，失败时显式 `raise RuntimeError`
  3. 将整个 monkey-patch 逻辑提取为独立函数 `_patch_media_crawler_tools_utils()`，在 `ensure_login` 中调用

#### #19 `_bezier_move` 起始点始终为视口中心
- **严重程度**: 🟡 一般
- **涉及文件**: `src/miner/human_sim.py:40-43`
- **问题描述**: 贝塞尔曲线 `_bezier_move` 的起点硬编码为 `viewport.width//2, viewport.height//2`，而不是鼠标的实际当前位置。这意味着连续多次 `move_mouse_randomly` 时，每次 new bezier 都会从中心"瞬移"开始，而不是从上一段曲线的终点平滑衔接。Playwright 的 `page.mouse.move` 会更新鼠标的内部位置状态，但 `_bezier_move` 并没有利用这个状态。
- **修改建议**: 
  1. 维护 `HumanSimulator` 的内部状态 `self._last_mouse_x`, `self._last_mouse_y`
  2. 每次 `_bezier_move` 结束后更新这两个值
  3. 下次调用时从上次的终点开始
  4. 或者改为 `@staticmethod` 并接收 `start_x, start_y` 参数，由调用方决定起点

#### #20 `_RETRYABLE_EXCEPTIONS` 不涵盖 httpx 网络错误
- **严重程度**: 🟡 一般
- **涉及文件**: `src/miner/crawler.py:21-25`
- **问题描述**: `_RETRYABLE_EXCEPTIONS = (asyncio.TimeoutError, ConnectionError, OSError)` 中，`ConnectionError` 是 Python 内置异常（socket 级），但底层使用 `XiaoHongShuClient`（基于 httpx），实际抛出的网络错误类型是 `httpx.ConnectError`, `httpx.ReadError`, `httpx.RemoteProtocolError` 等，均继承自 `httpx.HTTPError`。当前代码中这些 httpx 异常会穿透重试逻辑直接抛给外层 `crawl_blogger` 的 `except Exception`，导致整个博主采集失败，而不是重试。
- **修改建议**: 
  1. 添加 `import httpx` 并在 `_RETRYABLE_EXCEPTIONS` 中增加 `httpx.HTTPError`（或具体子类）
  2. 注意 httpx 可能未安装（MediaCrawler 依赖链），加 try/except 保护导入：
  ```python
  try:
      import httpx
      _RETRYABLE_EXCEPTIONS += (httpx.HTTPError,)
  except ImportError:
      pass
  ```

#### #21 `config_loader.validate_bloggers_config` 有副作用
- **严重程度**: 🟢 建议
- **涉及文件**: `src/config_loader.py:38`
- **问题描述**: `validate_bloggers_config()` 中 `item.setdefault("notes", {})` 会原地修改传入的 `data` 字典及其嵌套的 `bloggers` 列表。函数名暗示纯校验，但实际做了数据默认值注入。调用方 `load_bloggers_config` 依赖这个副作用来确保下游代码不需要防御 `notes` 缺失。
- **修改建议**: 
  1. 将 `setdefault` 逻辑移到 `load_bloggers_config` 的 validate 调用之后，作为独立的数据标准化步骤
  2. 或重命名 `validate_bloggers_config` → `validate_and_normalize_bloggers_config` 清楚标记副作用
  3. 在单元测试中补充对 side-effect 的验证（当前 `test_validate_bloggers_config_valid_passes` 未检查 setdefault）

#### #22 reporter.py 过度使用 `getattr` 绕过类型检查
- **严重程度**: 🟢 建议
- **涉及文件**: `src/utils/reporter.py:33,38,70,77-79`
- **问题描述**: `ReportSummary` 类型已改为 `list[CrawlResult]`，但内部仍然大量使用 `getattr(result, 'posts_found', 0)`、`getattr(result, 'status', '')` 模式。`CrawlResult` 是 `@dataclass(slots=True)` 的，所有属性都是确定存在的。用 `getattr` 加默认值会掩盖属性名拼写错误（例如某天改名为 `posts_discovered`，`getattr` 会静默返回 0 而不报错）。
- **修改建议**: 直接属性访问替换 `getattr`：`result.posts_found`，`result.blogger_user_id`，`result.status` 等。类型检查器（mypy/pyright）会在属性不存在时直接报错。

### 待办
- [x] #18 login.py monkey-patch 健壮性 ✅
- [x] #19 `_bezier_move` 起点衔接 ✅
- [x] #20 `_RETRYABLE_EXCEPTIONS` 增加 httpx 错误类型 ✅
- [x] #21 `validate_bloggers_config` 副作用分离 ✅
- [x] #22 reporter.py 用直接属性访问替换 `getattr` ✅

> **赵铁城回复 — 2026-06-08 16:55**
>
> ## Round 4 修复汇总
>
> 全部 5 项已修完。测试 21/21 passed ✅  |  提交 `5d98647`
>
> ### #18 🔴 monkey-patch 健壮性
> ✅ **已修改** — 提取为 `_patch_media_crawler_tools_utils()` 独立函数，含：
> - 每个 `except` 分支 → `_log.warning(exc_info=True)` 
> - 全部子模块加载失败 → `raise RuntimeError`
> - 成功 → `_log.info("Patched ... with N names")`
> - 外层 `ensure_login` 用 `try/except + _log.warning` 兜底，不阻断 login
> - TODO 注释引用 upstream bugs
>
> ### #19 🟡 贝塞尔起点衔接
> ✅ **已修改** — 新增 `_last_mouse_x/_last_mouse_y` 状态字段（`field(default=0, init=False)`），`_bezier_move` 首次用视口中心，后续从上次终点曲线衔接。
>
> ### #20 🟡 httpx 错误覆盖
> ✅ **已修改** — `try/except ImportError` 安全导入 `httpx`，追加 `httpx.HTTPError` 到 `_RETRYABLE_EXCEPTIONS`。
>
> ### #21 🟢 validate 副作用分离
> ✅ **已修改** — 重命名 `validate_bloggers_config` → `validate_and_normalize_bloggers_config`（config_loader.py + test_config_loader.py 全量重命名）。测试新增 `notes == {}` 断言。
>
> ### #22 🟢 getattr → 直接属性
> ✅ **已修改** — `reporter.py` 中全部 9 处 `getattr(result, ...)` 替换为 `result.field` 直接属性访问。

> **陈明远验收 — 2026-06-08 17:05**：逐条验证通过。代码 diff 审查 + 21/21 tests passed。
>
> | # | 验收要点 | 结果 |
> |---|---------|:--:|
> | #18 | `_patch_media_crawler_tools_utils()` 独立函数，warning日志 + RuntimeError | ✅ |
> | #19 | `_last_mouse_x/_last_mouse_y` 状态追踪，连续贝塞尔曲线 | ✅ |
> | #20 | `try/except ImportError` 导入 httpx，追加 `httpxtpx.HTTPError` | ✅ |
> | #21 | `validate_and_normalize_bloggers_config` 全量重命名 + 副作用测试 | ✅ |
> | #22 | 9处 `getattr` → 直接属性，grep 归零 | ✅ |
>
> **Round 4 关闭 ✅**
