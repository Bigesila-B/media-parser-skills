---
name: "media-parser"
description: "解析社交平台链接（B站/抖音/TikTok/快手/微博/小红书等10个平台），提取视频/图片直链并下载到本地。当用户发送包含社交平台链接的消息、或要求解析/下载某个链接的视频时调用。"
---

# 流媒体平台链接解析与下载

## 功能概述

自动识别用户消息中的社交平台链接，解析提取视频/图片直链，并下载媒体文件到本地。支持 10 个平台：B站、抖音、TikTok、快手、微博、小红书、闲鱼、今日头条、小黑盒、Twitter/X。

## 何时调用

当用户消息中出现以下任一情况时调用本技能：
- 用户直接发送了一个社交平台链接（如 `https://www.bilibili.com/video/BV...`）
- 用户发送了一段包含链接的文本（如抖音分享文案 `https://v.douyin.com/xxx 复制此链接...`）
- 用户明确要求"解析""下载""提取"某个链接的视频或图片

## 支持的链接格式

| 平台 | 链接示例 |
|------|---------|
| B站 | `b23.tv/xxx`、`bilibili.com/video/BV...`、`bilibili.com/video/av...`、`bilibili.com/bangumi/play/ep...`、`bilibili.com/opus/...`、`t.bilibili.com/...` |
| 抖音 | `v.douyin.com/xxx`、`douyin.com/video/...`、`douyin.com/note/...`、`douyin.com/slides/...` |
| TikTok | `vm.tiktok.com/xxx`、`vt.tiktok.com/xxx`、`tiktok.com/@.../video/...`、`tiktok.com/@.../photo/...` |
| 快手 | `v.kuaishou.com/xxx`、`kuaishou.com/...`、`gifshow.com/...`、`chenzhongtech.com/...` |
| 微博 | `weibo.com/...`、`m.weibo.cn/detail/...`、`weibo.cn/status/...`、`video.weibo.com/show?fid=...` |
| 小红书 | `xhslink.com/xxx`、`xiaohongshu.com/explore/...`、`xiaohongshu.com/discovery/item/...` |
| 闲鱼 | `m.tb.cn/xxx`、`goofish.com/item?id=...`、`h5.m.goofish.com/item?id=...` |
| 今日头条 | `m.toutiao.com/is/xxx`、`toutiao.com/article/...`、`toutiao.com/video/...`、`toutiao.com/w/...` |
| 小黑盒 | `xiaoheihe.cn/app/topic/game/...`、`xiaoheihe.cn/app/bbs/link/...` |
| Twitter/X | `twitter.com/.../status/...`、`x.com/.../status/...` |

## 使用方法

### 基本命令

脚本位于工作区 `astrbot_plugin_media_parser/media_parser_cli.py`，使用 Python 运行：

```bash
# 解析并下载媒体（默认行为）
python astrbot_plugin_media_parser/media_parser_cli.py "包含链接的文本"

# 仅解析提取直链和元数据，不下载文件
python astrbot_plugin_media_parser/media_parser_cli.py "包含链接的文本" --no-download

# 使用代理（TikTok/Twitter 等海外平台需要）
python astrbot_plugin_media_parser/media_parser_cli.py "链接" --proxy http://127.0.0.1:7897

# 指定下载目录
python astrbot_plugin_media_parser/media_parser_cli.py "链接" --output-dir D:/downloads

# 格式化 JSON 输出（便于阅读）
python astrbot_plugin_media_parser/media_parser_cli.py "链接" --pretty

# 从文件读取
python astrbot_plugin_media_parser/media_parser_cli.py -f input.txt --pretty

# 从 stdin 读取
echo "链接文本" | python astrbot_plugin_media_parser/media_parser_cli.py
```

### 参数说明

| 参数 | 说明 |
|------|------|
| `text` | 位置参数，包含链接的文本 |
| `-f / --file` | 从文件读取文本 |
| `--proxy` | 代理地址，格式 `http://host:port` |
| `--output-dir` | 媒体文件缓存目录（默认插件目录下 `cache/`） |
| `--no-download` | 仅解析不下载 |
| `--pretty` | 格式化 JSON 输出 |
| `--debug` | 启用调试日志 |

## 输出格式

脚本输出 JSON 到 stdout，结构如下：

```json
{
  "success": true,
  "total_links": 1,
  "results": [
    {
      "platform": "bilibili",
      "url": "原始链接",
      "title": "标题",
      "author": "作者",
      "desc": "简介",
      "timestamp": "发布时间",
      "duration": "时长信息",
      "videos": [
        {
          "direct_url": "视频直链URL",
          "file_path": "下载到本地的文件路径（未下载时为null）",
          "size_mb": 12.5,
          "mode": "local|direct|skip|not_downloaded",
          "status": "success|skipped|not_downloaded",
          "skip_reason": "跳过原因（成功时为null）",
          "headers": "下载直链所需的请求头（direct/skip/not_downloaded 模式下提供，含 Referer、User-Agent 等）"
        }
      ],
      "images": [
        {
          "direct_url": "图片直链URL",
          "file_path": "本地文件路径",
          "mode": "local|skip|not_downloaded",
          "status": "success|skipped|not_downloaded",
          "skip_reason": null,
          "headers": "下载直链所需的请求头"
        }
      ],
      "error": null
    }
  ],
  "summary": {
    "total_links": 1,
    "successful_parses": 1,
    "failed_parses": 0,
    "total_videos": 1,
    "total_images": 0,
    "downloaded_videos": 1,
    "downloaded_images": 0,
    "failed_downloads": 0
  },
  "supported_platforms": ["bilibili", "douyin", ...]
}
```

### mode 字段含义

- `local`：媒体已下载到本地，`file_path` 有值
- `direct`：媒体使用直链发送（缓存不可用时的普通视频降级），需配合 `headers` 下载
- `skip`：媒体被跳过，查看 `skip_reason` 了解原因
- `not_downloaded`：使用了 `--no-download`，仅提取直链未下载，需配合 `headers` 下载

### headers 字段

当 `mode` 为 `direct`、`skip` 或 `not_downloaded` 时，输出中会包含 `headers` 字段（含 `Referer`、`User-Agent` 等）。如果需要自行下载直链，必须携带这些请求头，否则部分平台（如 B站、微博）的 CDN 会返回 403 Forbidden。

## 执行后的操作指南

1. **解析成功 + 下载成功**：向用户展示标题、作者、简介等元数据，告知下载的文件路径
2. **解析成功 + 部分跳过**：展示成功部分，说明跳过原因（如"缓存目录不可用""视频过大""403 访问被拒绝"）
3. **解析失败**：告知用户解析失败，展示 `error` 字段中的错误信息
4. **未找到链接**：`total_links` 为 0，告知用户未在文本中检测到支持的社交平台链接

## 平台特性与注意事项

### 代理需求

- **TikTok**：受地区风控影响明显，通常需要 `--proxy`
- **Twitter/X**：图片和视频 CDN 大多需要代理环境
- **小黑盒**：视频下载速度不佳时建议启用代理
- **B站**：国内可直连，无需代理

### 下载限制

- 图片始终下载到本地缓存后才能使用（不支持直链发送图片）
- B站高画质（1080P+/4K）需要配置 Cookie，当前脚本默认无 Cookie，解析普通画质
- 微博视频必须携带 referer 下载，会强制缓存
- DASH 音视频流（B站 Cookie 模式）和 M3U8 分片需要 ffmpeg 合并

### 环境依赖

- Python 3.10+
- `aiohttp`、`cryptography` 库
- `ffmpeg`（用于 DASH/M3U8 合并、图片格式转换、视频封面截取）

## 示例场景

### 场景 1：用户发送抖音链接

用户消息：`看看这个视频 https://v.douyin.com/iRNBho5y/`

执行：
```bash
python astrbot_plugin_media_parser/media_parser_cli.py "看看这个视频 https://v.douyin.com/iRNBho5y/" --pretty
```

### 场景 2：用户发送包含多个链接的文本

用户消息：`这两个视频不错 https://www.bilibili.com/video/BV1xx 和 https://v.douyin.com/yyy`

执行：
```bash
python astrbot_plugin_media_parser/media_parser_cli.py "这两个视频不错 https://www.bilibili.com/video/BV1xx 和 https://v.douyin.com/yyy" --pretty
```

### 场景 3：用户要解析 Twitter 链接（需代理）

用户消息：`帮我下载这个 https://x.com/user/status/123`

执行：
```bash
python astrbot_plugin_media_parser/media_parser_cli.py "帮我下载这个 https://x.com/user/status/123" --proxy http://127.0.0.1:7897 --pretty
```

### 场景 4：仅提取直链不下载

用户消息：`只要视频直链就行 https://www.bilibili.com/video/BV1xx`

执行：
```bash
python astrbot_plugin_media_parser/media_parser_cli.py "只要视频直链就行 https://www.bilibili.com/video/BV1xx" --no-download --pretty
```
