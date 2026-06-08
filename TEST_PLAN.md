# xhs-blogger-miner 真实测试方案

> 状态: 预设计，等待 Boss 实操放行
> 作者: 赵铁城 & 陈明远
> 更新: 2026-06-08

## 测试环境

| 项目 | 配置 |
|------|------|
| 目标博主 | 「一起自救」user_id=`5986da286a6a692eaf2a53a1` |
| 操作系统 | macOS arm64, Chrome 149 |
| CDP port | 9222 |
| 模式 | 先 non-headless（扫码建 session），后 headless（验证持久化） |
| 初始状态 | browser_data 已清空或过期，强制重新登录 |

## 测试矩阵

### T1 — 冒烟测试

| 项目 | 内容 |
|------|------|
| 前置条件 | `.env` 已配置 |
| 操作 | `uv run xhs-miner --dry-run --verbose` |
| 预期结果 | 0 错误，输出 "Dry-run complete" |
| 验收标准 | 无 import error，配置校验通过 |

### T2 — 登录验证

| 项目 | 内容 |
|------|------|
| 前置条件 | T1 通过，Chrome 未运行 |
| 操作 | `uv run xhs-miner --blogger <id> --no-headless --verbose` |
| 预期结果 | CDP 启动→导航→pong()=False→QR 码弹出 |
| 验收标准 | QR 码可见，等待扫码。扫码后 pong()=True |

### T3 — 最小采集 (max_count=1)

| 项目 | 内容 |
|------|------|
| 前置条件 | T2 扫码成功，session 有效 |
| 操作 | `max_count=1` (改 bloggers.yaml)，`uv run xhs-miner --blogger <id> --verbose` |
| 预期结果 | 1 个 post 采集，blogger info 更新 |
| 验收标准 | `posts` 表有 1 条记录，`crawl_log.status=success`，note_id 非空 |

### T4 — 分页采集 (max_count=50)

| 项目 | 内容 |
|------|------|
| 前置条件 | T3 通过 |
| 操作 | `max_count=50`，`uv run xhs-miner --blogger <id> --headless --verbose` |
| 预期结果 | 50 个 post，多页翻页，cursor 推进 |
| 验收标准 | `posts_found=50`，`has_more=true`，无重复 note_id |

### T5 — 限流退避

| 项目 | 内容 |
|------|------|
| 前置条件 | T4 通过，人为缩短 CRAWLER_MIN/MAX_SLEEP_SEC |
| 操作 | `CRAWLER_MIN_SLEEP_SEC=1 CRAWLER_MAX_SLEEP_SEC=2 max_count=100` |
| 预期结果 | 触发 429/461，日志含 RATE_LIMIT marker |
| 验收标准 | 指数退避日志可见，最终采集至少完成一部分 |

### T6 — 断点续采

| 项目 | 内容 |
|------|------|
| 前置条件 | T4 完成（50 posts 已入库） |
| 操作 | `uv run xhs-miner --blogger <id> --resume --verbose` |
| 预期结果 | 识别 50 个已采集 note_id，跳过全部 |
| 验收标准 | `posts_new=0`，`posts_found=50+新帖数`，无重复 INSERT |

### T7 — 中断恢复

| 项目 | 内容 |
|------|------|
| 前置条件 | T3 通过 |
| 操作 | 启动采集 max_count=20，采到一半 Ctrl+C，然后 `--resume` 重启 |
| 预期结果 | 第二次运行不重复采已有的，续采剩余的 |
| 验收标准 | `posts` 表最终 note_id 无重复，总数不超过 20 |

### T8 — 多格式导出

| 项目 | 内容 |
|------|------|
| 前置条件 | T3 通过 |
| 操作 | `--format csv` `--format json` `--format all` |
| 预期结果 | 3 个导出文件生成 |
| 验收标准 | CSV 可导入 Excel，JSON 有效，Markdown 可渲染 |

### T9 — 数据质量

| 项目 | 内容 |
|------|------|
| 前置条件 | 至少 1 条 post 已采集 |
| 操作 | `sqlite3 data/xhs_bloggers.db` 手工查验 |
| 验收标准 | 标题/content/interaction_count 无 null，image_urls 为 list，publish_time 为时间戳 |

### T10 — 错误处理

| 项目 | 内容 |
|------|------|
| 前置条件 | T1 通过 |
| 操作 | 测试无效 blogger ID: `--blogger zzzzzzzzzzzzzzzzzzzzzzzz` |
| 预期结果 | ValueError 提示 "Blogger not found in config" |
| 验收标准 | 错误信息清晰，进程正常退出，无 traceback |

## 验收清单

```
硬性标准（必须全部通过）：
☐ T1 冒烟测试 0错误
☐ T2 登录验证 pong()=True
☐ T3 最小采集 1 post 落库
☐ T4 分页采集 50 posts
☐ T6 断点续采 posts_new=0
☐ T10 错误处理 无 traceback

软性标准（尽量满足）：
☐ T5 限流退避生效
☐ T7 中断恢复无重复
☐ T8 多格式导出
☐ T9 数据质量验收
```

## 回滚方案

- XHS 返回封号/封 IP → 立即停止所有请求
- Chrome profile 损坏 → 删除 `browser_data/` 重建
- 数据污染 → 备份 `data/xhs_bloggers.db` 后可重建
