# <div align="center">JM-Cosmos</div>

<div align="center"><em>全能型 JM 漫画下载与管理工具</em></div>

<br>
<div align="center">
  <a href="#更新日志"><img src="https://img.shields.io/badge/VERSION-v2.0.0-E91E63?style=for-the-badge" alt="Version"></a>
  <a href="https://github.com/GEMILUXVII/astrbot_plugin_jm_cosmos/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-AGPL--3.0-009688?style=for-the-badge" alt="License"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/PYTHON-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"></a>
  <a href="https://github.com/AstrBotDevs/AstrBot"><img src="https://img.shields.io/badge/AstrBot-Compatible-00BFA5?style=for-the-badge&logo=robot&logoColor=white" alt="AstrBot Compatible"></a>
</div>

<div align="center">
  <a href="https://pypi.org/project/jmcomic/"><img src="https://img.shields.io/badge/JMCOMIC-≥2.5.0-9C27B0?style=for-the-badge" alt="JMComic"></a>
  <a href="https://github.com/botuniverse/onebot-11"><img src="https://img.shields.io/badge/OneBotv11-AIOCQHTTP-FF5722?style=for-the-badge&logo=qq&logoColor=white" alt="OneBot v11 Support"></a>
  <a href="https://github.com/GEMILUXVII/astrbot_plugin_jm_cosmos"><img src="https://img.shields.io/badge/UPDATED-2025.12.26-2196F3?style=for-the-badge" alt="Updated"></a>
</div>

## 介绍

JM-Cosmos 是一个基于 AstrBot 开发的 JM 漫画下载插件，支持漫画搜索、预览、下载、打包与 QQ 发送。

**v2.0.0 是完全重构的版本**，采用模块化架构设计，代码更清晰、更易维护，并新增了多项实用功能。

## 功能特性

### 核心功能

- **漫画搜索** - 通过关键词搜索 JM 漫画
- **漫画详情** - 查看漫画信息、标签、作者等
- **本子下载** - 下载完整本子（/jm）或单章节（/jmc）
- **自动打包** - 下载完成后自动打包为 ZIP 或 PDF
- **加密保护** - 支持为 ZIP/PDF 设置密码加密
- **自动发送** - 打包后自动发送文件到聊天

### 高级功能

- **代理支持** - 支持 HTTP/SOCKS5 代理
- **权限控制** - 可选的管理员权限和群组白名单
- **自动清理** - 发送后自动删除本地文件
- **封面预览** - 下载前展示漫画封面和详情
- **调试模式** - 详细日志输出便于问题排查

## 安装方法

### 1. 下载插件

将插件下载到 AstrBot 的插件目录 `data/plugins/`

### 2. 安装依赖

```bash
cd data/plugins/jm_cosmos2
pip install -r requirements.txt
```

**必须安装的依赖：**

| 依赖 | 用途 |
|-----|------|
| `jmcomic>=2.5.0` | JM 漫画下载核心库 |
| `pymupdf>=1.23.0` | PDF 打包支持 |
| `pyzipper>=0.3.6` | 加密 ZIP 支持 |

> **注意**：如果不安装 `pyzipper`，ZIP 文件将**无法加密**！

### 3. 重启 AstrBot

确保插件被正确加载。

### 4. 配置插件

在 AstrBot 管理面板的「插件配置」中设置选项。

## 命令列表

| 命令 | 说明 | 示例 |
|------|------|------|
| `/jm <ID>` | 下载指定 ID 的本子 | `/jm 123456` |
| `/jmc <ID>` | 下载指定 ID 的章节 | `/jmc 789012` |
| `/jms <关键词>` | 搜索漫画 | `/jms 标签名` |
| `/jmi <ID>` | 查看本子详情 | `/jmi 123456` |
| `/jmhelp` | 查看帮助信息 | `/jmhelp` |

## 配置说明

所有配置可在 AstrBot 管理面板中修改：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `download_dir` | 漫画下载目录 | `./downloads` |
| `image_suffix` | 图片格式 (.jpg/.png/.webp) | `.jpg` |
| `client_type` | 客户端类型 (api/html) | `api` |
| `use_proxy` | 是否使用代理 | `false` |
| `proxy_url` | 代理服务器地址 | 空 |
| `pack_format` | 打包格式 (zip/pdf/none) | `zip` |
| `pack_password` | 打包密码（留空则不加密） | 空 |
| `auto_delete_after_send` | 发送后自动删除 | `true` |
| `send_cover_preview` | 发送封面预览 | `true` |
| `enabled_groups` | 启用的群列表（逗号分隔） | 空（全部启用） |
| `admin_only` | 仅管理员可用 | `false` |
| `admin_list` | 管理员用户 ID 列表 | 空 |
| `search_page_size` | 搜索结果数量 | `5` |
| `debug_mode` | 调试模式 | `false` |

## 文件结构

```
jm_cosmos2/
├── main.py              # 插件入口和命令注册
├── metadata.yaml        # 插件元数据
├── _conf_schema.json    # 配置模式定义
├── requirements.txt     # 依赖库列表
├── core/                # 核心模块
│   ├── __init__.py
│   ├── config.py        # 配置管理器
│   ├── downloader.py    # 下载管理器
│   └── packer.py        # 打包模块 (ZIP/PDF)
└── utils/               # 工具模块
    ├── __init__.py
    └── formatter.py     # 消息格式化器
```

## 常见问题

### Q: ZIP 文件没有加密？

**A:** 请确保已安装 `pyzipper` 库：
```bash
pip install pyzipper
```

### Q: 下载失败，提示 "not found client impl class"？

**A:** 请检查「客户端类型」配置，应为 `api` 或 `html`，不能是其他值。

### Q: 403 错误或 IP 被禁止访问？

**A:** 启用代理功能并配置代理地址：
```
use_proxy: true
proxy_url: http://127.0.0.1:7890
```

### Q: 如何只允许特定群使用？

**A:** 在「启用的群列表」中填写群号（逗号分隔），如：`123456789,987654321`

## 更新日志

查看完整更新日志：[CHANGELOG.md](./CHANGELOG.md)

**当前版本：v2.0.0** - 完全重构版本，采用模块化架构，新增加密打包、权限控制等功能。

## 注意事项

- 本插件仅供学习交流使用
- 请勿将下载的内容用于商业用途
- 大量请求可能导致 IP 被封禁
- 请遵守当地法律法规

## 贡献指南

欢迎提交 Pull Request 和 Issue。提交代码时请遵循以下提交消息规范：

### 提交类型

| 类型 | 说明 |
|------|------|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `docs` | 文档变更 |
| `style` | 代码格式调整（空格、分号等，不影响逻辑） |
| `refactor` | 代码重构（既非新功能也非 Bug 修复） |
| `perf` | 性能优化 |
| `test` | 添加或修正测试 |
| `chore` | 构建过程或辅助工具的变动 |
| `revert` | 回滚提交 |
| `ci` | CI/CD 相关变更 |
| `build` | 构建系统变更 |

### 提交格式

```
<类型>: <简短描述>

[可选的详细描述]
```

示例：
```
feat: 新增加密 ZIP 打包功能
fix: 修复客户端类型配置错误
docs: 更新 README 安装说明
```

## 许可证

[![](https://www.gnu.org/graphics/agplv3-155x51.png "AGPL v3 logo")](https://www.gnu.org/licenses/agpl-3.0.txt)

Copyright (C) 2025 GEMILUXVII

This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.


## 致谢

本项目基于或参考了以下开源项目:

- [AstrBot](https://github.com/Soulter/AstrBot) - 机器人框架
- [JMComic-Crawler-Python](https://github.com/hect0x7/JMComic-Crawler-Python) - JMComic 库
- [pyzipper](https://github.com/danifus/pyzipper) - 加密 ZIP 库
- [pymupdf](https://pymupdf.readthedocs.io/) - PDF 处理库
