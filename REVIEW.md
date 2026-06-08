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
<!-- 
  格式说明：
  - 每个修改意见用 #N 编号，一轮内不重复
  - 严重程度：🔴 严重（阻塞上线） / 🟡 一般（需修复） / 🟢 建议（可后续优化）
  - 赵铁城回复写在引用块（>）内，标注时间和状态
  - 状态标记：✅ 已修改 / 🔄 进行中 / ❓ 有争议 / ⏸️ 暂缓
-->
