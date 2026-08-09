# v2.0.0 更新说明

> 发布时间：2026-08-09
>
> 本目录 `releases/v2.0.0/` 为媒体链接解析下载技能的**新版本**，发布方式为新增版本目录，**不覆盖**仓库根目录旧版文件。未列出的文件与根目录版本一致，升级方式见文末。

## 一、本次更新内容

### 1. 小红书 `xhslink.cn` 域名支持（Bug 修复）

**问题**：用户分享的小红书短链使用新域名 `xhslink.cn`，而解析器只识别 `xhslink.com`，导致链接完全未被识别（`total_links: 0`）。

**修复**（`core/parser/platform/xiaohongshu.py`）：
- `can_parse()` 增加 `xhslink.cn` 域名匹配
- `extract_links()` 的正则改为 `xhslink\.(?:com|cn)`
- `parse()` 短链展开逻辑同时支持 `xhslink.cn`

**验证**：`xhslink.cn/o/46iFnDBLZsQ` 解析成功并下载 3 张图片。

### 2. 抖音图文作品支持（Bug 修复）

**问题**：抖音图文作品（note 类型）同时带有一个封面视频字段时，解析器只按视频处理并尝试下载，而：
- 下载的 `playwm` 链接是失效畸形 URL（`video_id` 参数值本身是一个完整 URL），必然返回 404
- 真正的图片内容（如 11 张漫画图）被完全丢弃

**修复**（`core/parser/platform/douyin.py`）：
- 新增 `_is_malformed_playwm_url()`：过滤 `playwm/?video_id=<完整URL>` 这类失效链接
- `_extract_douyin_media_url_lists()`：不再因存在顶层 video 就提前返回，图文作品同时保留视频与图片

**验证**：抖音图文链接下载 11/11 张图片全部成功。

### 3. 图片格式转换 Pillow 后备（功能增强）

**问题**：环境未安装 ffmpeg 时，图片（如 webp）无法转换为 PNG，只能保留原格式。

**增强**（`core/downloader/handler/image.py`）：
- 新增 `_convert_image_with_pillow()`：ffmpeg 缺失时自动回退使用 Pillow 转换
- 转换在独立线程执行，不阻塞事件循环

**验证**：无 ffmpeg 环境下 11 张 webp 图片全部成功转为 PNG。

### 4. 图片下载 403 重试（功能增强）

**问题**：抖音等平台图片 CDN 偶发 403 风控，导致个别图片下载失败。

**增强**（`core/downloader/handler/base.py`）：
- `_is_retryable_exception()` 新增 `allow_image_403` 参数
- 图片下载遇 HTTP 403 时自动重试（视频 403 多为永久拒绝，不重试）

**验证**：实测一次 403 后自动重试成功，11/11 张图片全部下载。

### 5. 依赖清单更新

`requirements.txt` 增加 `Pillow`（图片格式转换后备方案）。

### 6. 技能文档更新（`media-parser/SKILL.md`）

- **发送原文件（优先执行）**：解析成功后优先将下载的 `.mp4` / 原图文件直接发送给用户，附一行元数据摘要，多个媒体全部发送
- **运行前环境检查（必做）**：调用脚本前检查 python / aiohttp / cryptography / Pillow / ffmpeg，缺失先安装再解析
- 小红书支持格式表补充 `xhslink.cn`

## 二、变更文件清单

| 文件 | 变更类型 |
|------|---------|
| `media-parser/SKILL.md` | 更新（发送原文件规则、环境检查、链接格式） |
| `astrbot_plugin_media_parser/requirements.txt` | 更新（增加 Pillow） |
| `astrbot_plugin_media_parser/core/parser/platform/xiaohongshu.py` | 修复（xhslink.cn） |
| `astrbot_plugin_media_parser/core/parser/platform/douyin.py` | 修复（图文作品 + 畸形链接过滤） |
| `astrbot_plugin_media_parser/core/downloader/handler/image.py` | 增强（Pillow 后备转换） |
| `astrbot_plugin_media_parser/core/downloader/handler/base.py` | 增强（图片 403 重试） |

## 三、升级方式

1. 复制仓库根目录旧版 `astrbot_plugin_media_parser/` 与 `media-parser/`
2. 用本目录 `releases/v2.0.0/` 下对应文件覆盖旧版同名文件
3. 执行 `pip install aiohttp cryptography Pillow` 安装依赖

## 四、已知限制

- 无 ffmpeg 时 DASH/M3U8 合并、视频封面截取不可用（图片转换已由 Pillow 兜底）
- B站高画质（1080P+/4K）需配置 Cookie，默认解析普通画质
- 海外平台（TikTok/Twitter/X/小黑盒）建议配合 `--proxy` 使用
