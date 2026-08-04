<div align="center">

# 流媒体链接解析下载技能（media-parser-skill）

_✨ 解析社交平台链接，提取视频/图片直链并下载到本地 ✨_

[![License](https://img.shields.io/badge/License-AGPLv3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0.html)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platforms](https://img.shields.io/badge/Platforms-10-orange.svg)](#-支持的平台)

</div>

---

## 📖 项目简介

`media-parser-skill` 是一个用于**识别媒体链接并下载视频/图片**的开源技能包，由两部分组成：

| 目录 | 说明 |
|------|------|
| `media-parser/` | **AI 技能定义**（SKILL.md）：供 AI Agent（如 TRAE）识别人工智能场景下用户发送的社交平台链接，自动解析、下载并优先发送原文件 |
| `astrbot_plugin_media_parser/` | **AstrBot 插件**（v6.3.1）：完整实现，支持解析、下载、翻译、打包发送等全部能力，可独立部署到 AstrBot 机器人 |

技能基于 AstrBot 插件能力封装，将「解析链接 → 提取直链 → 下载原文件 → 优先发送 `.mp4`/原图」的工作流固化，开箱即用。

## 🎯 核心特性

- ✅ 支持 **10 个平台**：B站、抖音、TikTok、快手、微博、小红书、闲鱼、今日头条、小黑盒、Twitter/X
- ✅ 自动识别消息中的平台链接（含短链、分享文案、小程序卡片）
- ✅ 提取视频/图片**直链**并下载到本地缓存
- ✅ **优先发送下载的原文件**（视频 `.mp4`、图片原图），非直链替代
- ✅ 支持 `--no-download` 仅提取直链模式，配合请求头可自行下载
- ✅ 并发下载、Range 加速、DASH/M3U8 合并（需 ffmpeg）
- ✅ 可选大模型翻译标题与正文、消息集合打包发送（插件模式）
- ✅ 可选 B站 Cookie 解锁高画质 + 管理员协助自动续期（插件模式）

## 📺 支持的平台

| 平台 | 支持的链接类型 | 能力 |
|------|--------------|------|
| **B站** | `b23.tv`、`bilibili.com/video/BV/av`、番剧、动态、小程序卡片 | 视频 / 图片 / 文本 |
| **抖音** | `v.douyin.com`、`douyin.com/video/note/slides` | 视频 / 图片 / 文本 |
| **TikTok** | `vm/vt.tiktok.com`、`tiktok.com/@../video/photo` | 视频 / 图片 / 文本 |
| **快手** | `v.kuaishou.com`、`kuaishou.com`、`gifshow.com`、`chenzhongtech.com` | 视频 / 图片 / 文本 |
| **微博** | `weibo.com`、`m.weibo.cn/detail`、`weibo.cn/status`、`video.weibo.com` | 视频 / 图片 / 文本 |
| **小红书** | `xhslink.com`、`xiaohongshu.com/explore`、`discovery/item` | 视频 / 图片 / 文本 |
| **闲鱼** | `m.tb.cn`、`goofish.com/item`、`h5.m.goofish.com/item` | 视频 / 图片 / 文本 |
| **今日头条** | `m.toutiao.com/is`、`toutiao.com/article/video/w` | 视频 / 图片 / 文本 |
| **小黑盒** | `xiaoheihe.cn/app/topic/game`、`xiaoheihe.cn/app/bbs/link` | 视频 / 图片 / 文本 |
| **Twitter/X** | `twitter.com/../status`、`x.com/../status` | 视频 / 图片 / 文本 |

## 🚀 快速开始

### 方式一：作为 AI 技能使用（TRAE / Agent）

1. 将 `media-parser/SKILL.md` 配置为技能定义；
2. 将 `astrbot_plugin_media_parser/` 放入工作区；
3. 用户发送包含平台链接的消息时，Agent 自动调用：

```bash
# 解析并下载媒体（默认行为，下载成功后优先发送原文件）
python astrbot_plugin_media_parser/media_parser_cli.py "包含链接的文本"

# 仅解析提取直链和元数据，不下载
python astrbot_plugin_media_parser/media_parser_cli.py "链接" --no-download

# 使用代理（TikTok/Twitter 等海外平台需要）
python astrbot_plugin_media_parser/media_parser_cli.py "链接" --proxy http://127.0.0.1:7897

# 指定下载目录 / 格式化输出
python astrbot_plugin_media_parser/media_parser_cli.py "链接" --output-dir D:/downloads --pretty
```

### 方式二：作为 AstrBot 插件使用

1. 依赖库：AstrBot WebUI → 控制台 → 安装 `aiohttp`、`cryptography`
2. 插件：AstrBot WebUI → 插件市场搜索 `astrbot_plugin_media_parser` 安装，或将本仓库 `astrbot_plugin_media_parser/` 放入插件目录

## 🔧 环境依赖

- Python 3.10+
- `aiohttp`、`cryptography`
- `ffmpeg`（DASH/M3U8 合并、图片格式转换、视频封面截取）

## 📦 目录结构

```
media-parser-skill/
├── README.md                          # 本文档
├── LICENSE                            # AGPLv3 许可证
├── media-parser/
│   └── SKILL.md                       # AI 技能定义（触发条件、CLI 用法、执行指南）
└── astrbot_plugin_media_parser/       # AstrBot 插件完整实现
    ├── main.py                        # 插件入口（AstrBot Star）
    ├── media_parser_cli.py            # 非交互式 CLI，供 AI 技能调用
    ├── run_local.py                   # 本地运行入口
    ├── core/
    │   ├── parser/                    # 平台解析器（platform/ 下 10 个平台）
    │   ├── downloader/                # 下载管理（普通/DASH/M3U8/图片/Range）
    │   ├── translation/               # 大模型翻译
    │   ├── message_adapter/           # 消息节点构建与发送
    │   ├── storage/                   # 缓存与文件管理
    │   └── interaction/               # 交互（B站 Cookie 协助）
    └── docs/                          # 架构与解析器元数据文档
```

## 📤 输出格式

CLI 输出 JSON，核心字段：

```json
{
  "platform": "bilibili",
  "title": "视频标题",
  "author": "作者",
  "desc": "简介",
  "videos": [
    {
      "direct_url": "视频直链URL",
      "file_path": "下载到本地的文件路径",
      "size_mb": 3.94,
      "mode": "local | direct | skip | not_downloaded",
      "status": "success | skipped | not_downloaded",
      "headers": "下载直链所需的请求头"
    }
  ],
  "images": [],
  "error": null
}
```

**发送原文件优先级**：`mode: local` 表示已下载原文件，Agent 应优先直接发送 `file_path` 指向的 `.mp4`/原图文件给用户，并附一行元数据摘要（标题 | 作者 | 大小）。

## ⚠️ 注意事项

- **代理需求**：TikTok、Twitter/X、小黑盒受地区风控影响，建议 `--proxy`；B站国内可直连
- **B站画质**：高画质（1080P+/4K）需配置 Cookie，默认无 Cookie 解析普通画质
- **图片**：始终下载到本地缓存后发送
- **微博**：视频必须携带 referer 下载，会强制缓存
- **DASH/M3U8**：需要 ffmpeg 合并音视频流

## 🤝 贡献

欢迎提交 PR 以添加更多平台解析支持和新功能。

## 📄 许可证

[GNU Affero General Public License v3.0](LICENSE)

插件源码基于 [drdon1234/astrbot_plugin_media_parser](https://github.com/drdon1234/astrbot_plugin_media_parser) 打包封装。
