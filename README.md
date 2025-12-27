<div align="center">
  <img src="logo.png" alt="AstrBot JM-Cosmos II Plugin Logo" width="160" />
</div>

# <div align="center">JM-Cosmos II</div>

<div align="center">
  <strong>全能型 JM 漫画下载与管理工具</strong>
</div>

<br>
<div align="center">
  <a href="CHANGELOG.md"><img src="https://img.shields.io/badge/VERSION-v2.5.1-E91E63?style=for-the-badge" alt="Version"></a>
  <a href="https://github.com/GEMILUXVII/astrbot_plugin_jm_cosmos/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-AGPL--3.0-009688?style=for-the-badge" alt="License"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/PYTHON-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"></a>
  <a href="https://github.com/AstrBotDevs/AstrBot"><img src="https://img.shields.io/badge/AstrBot-Compatible-00BFA5?style=for-the-badge&logo=robot&logoColor=white" alt="AstrBot Compatible"></a>
</div>

<div align="center">
  <a href="https://pypi.org/project/jmcomic/"><img src="https://img.shields.io/badge/JMCOMIC-≥2.5.0-9C27B0?style=for-the-badge" alt="JMComic"></a>
  <a href="https://github.com/botuniverse/onebot-11"><img src="https://img.shields.io/badge/OneBotv11-AIOCQHTTP-FF5722?style=for-the-badge&logo=qq&logoColor=white" alt="OneBot v11 Support"></a>
  <a href="https://github.com/GEMILUXVII/astrbot_plugin_jm_cosmos"><img src="https://img.shields.io/badge/UPDATED-2025.12.27-2196F3?style=for-the-badge" alt="Updated"></a>
</div>

## 介绍

JM-Cosmos II 是一个基于 AstrBot 开发的 JM 漫画下载插件，支持漫画搜索、预览、下载、打包与 QQ 发送。

**v2.0.0 是完全重构的版本**，采用模块化架构设计，代码更清晰、更易维护，并新增了多项实用功能。

> [!CAUTION]
> **从 v1.x 升级到 v2.x 的用户请注意：**
> - v2.x 与 v1.x **不兼容**，配置项和命令均有变更
> - 升级前请**删除旧插件目录**，然后安装新版本
> - 升级后需在管理面板**重新配置所有选项**
> - 部分命令已移除（`/jmimg`, `/jmpdf`, `/jmconfig`, `/jmdomain`, `/jmauthor`, `/jmrecommend`）

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

| 依赖              | 用途              |
| ----------------- | ----------------- |
| `jmcomic>=2.6.10` | JM 漫画下载核心库 |
| `pymupdf>=1.23.0` | PDF 打包支持      |
| `pyzipper>=0.3.6` | 加密 ZIP 支持     |

> [!WARNING]
> 如果不安装 `pyzipper`，默认可发送 zip 文件，但 ZIP 文件将**无法加密**！

### 3. 重启 AstrBot

确保插件被正确加载。

### 4. 配置插件

在 AstrBot 管理面板的「插件配置」中设置选项。

## 命令列表

### 下载命令

#### `/jm <ID>`
下载指定 ID 的完整本子。

```
/jm 123456
```

- 下载完成后自动打包并发送
- 若开启 `send_cover_preview`，下载前会显示封面预览

---

#### `/jmc <本子ID> <章节序号>`
下载指定本子的指定章节。

```
/jmc 123456 3   # 下载本子 123456 的第 3 章
```

---

### 搜索与浏览

#### `/jms <关键词>`
搜索漫画。

```
/jms 标签名
/jms 作者名
```

---

#### `/jmi <ID>`
查看本子详情（标题、作者、标签、章节数等）。

```
/jmi 123456
```

- 若开启 `send_cover_preview`，会同时显示封面图片

---

#### `/jmrank [类型] [页码]`
查看排行榜。

| 参数     | 可选值         | 默认值 |
| -------- | -------------- | ------ |
| 类型     | `week` `month` | `week` |
| 页码     | 正整数         | `1`    |

```
/jmrank              # 查看周排行榜第1页
/jmrank week         # 查看周排行榜第1页
/jmrank month 2      # 查看月排行榜第2页
```

---

#### `/jmrec [分类] [排序] [时间] [页码]`
推荐浏览 - 按分类、排序、时间浏览漫画。

| 参数     | 可选值                                                                 | 默认值 |
| -------- | ---------------------------------------------------------------------- | ------ |
| 分类     | `all` `doujin` `single` `short` `hanman` `meiman` `3d` `cosplay` `another` | `all`  |
| 排序     | `hot`(热门) `new`(最新) `pic`(图多) `like`(点赞)                        | `hot`  |
| 时间     | `day`(今日) `week`(本周) `month`(本月) `all`(全部)                       | `week` |
| 页码     | 正整数                                                                 | `1`    |

```
/jmrec                  # 本周全分类热门（默认推荐）
/jmrec hanman           # 本周韩漫热门
/jmrec all hot day      # 今日全分类热门
/jmrec doujin new week  # 本周同人最新
/jmrec 3d hot month 2   # 本月3D热门第2页
/jmrec help             # 查看详细帮助
```

> **提示**：参数顺序灵活，智能识别。例如 `/jmrec 2 hanman` 和 `/jmrec hanman 2` 效果相同。

---

### 账号功能

#### `/jmlogin <用户名> <密码>`
登录 JM 账号。

```
/jmlogin myuser mypassword
```

> **提示**：建议在管理面板中配置账号密码以实现自动登录

---

#### `/jmlogout`
登出当前账号。

```
/jmlogout
```

---

#### `/jmstatus`
查看当前登录状态。

```
/jmstatus
```

---

#### `/jmfav [页码] [收藏夹ID]`
查看我的收藏（需要先登录）。

| 参数       | 说明                     | 默认值       |
| ---------- | ------------------------ | ------------ |
| 页码       | 收藏列表页码             | `1`          |
| 收藏夹ID   | 指定收藏夹，`0` 表示全部 | `0`          |

```
/jmfav               # 查看全部收藏第1页
/jmfav 2             # 查看全部收藏第2页
/jmfav 1 12345       # 查看收藏夹ID为12345的第1页
```

---

### 帮助

#### `/jmhelp`
显示帮助信息。

```
/jmhelp
```

## 配置说明

所有配置可在 AstrBot 管理面板中修改：

| 配置项                   | 说明                       | 默认值         |
| ------------------------ | -------------------------- | -------------- |
| `download_dir`           | 漫画下载目录               | `./downloads`  |
| `image_suffix`           | 图片格式 (.jpg/.png/.webp) | `.jpg`         |
| `client_type`            | 客户端类型 (api/html)      | `api`          |
| `use_proxy`              | 是否使用代理               | `false`        |
| `proxy_url`              | 代理服务器地址             | 空             |
| `pack_format`            | 打包格式 (zip/pdf/none)    | `zip`          |
| `pack_password`          | 打包密码（留空则不加密）   | 空             |
| `auto_delete_after_send` | 发送后自动删除             | `true`         |
| `send_cover_preview`     | 发送封面预览               | `true`         |
| `enabled_groups`         | 启用的群列表（逗号分隔）   | 空（全部启用） |
| `admin_only`             | 仅管理员可用               | `false`        |
| `admin_list`             | 管理员用户 ID 列表         | 空             |
| `search_page_size`       | 搜索结果数量               | `5`            |
| `debug_mode`             | 调试模式                   | `false`        |
| `jm_username`            | JM账号用户名               | 空（可选）     |
| `jm_password`            | JM账号密码                 | 空（可选）     |

> [!IMPORTANT]
> **关于登录持久化的重要说明**
> 
> - **在面板中配置账号密码**：插件重载/Bot重启后会**自动登录**，推荐使用此方式
> - **仅使用 `/jmlogin` 命令登录**：登录状态仅保存在内存中，插件重载后需要**重新登录**
> 
> 如需使用收藏夹等登录功能，建议在 AstrBot 管理面板中配置 `jm_username` 和 `jm_password`

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

### Q: Docker 部署时文件发送失败？

> [!IMPORTANT]
> **AstrBot 和 NapCat 分离部署时，必须配置共享卷才能发送文件！**

当 AstrBot 和 NapCat（或其他 OneBot 实现）部署在不同 Docker 容器中时，可能会遇到以下错误：

- `识别URL失败, uri= /AstrBot/data/plugin_data/jm_cosmos2/downloads/...`
- `文件消息缺少参数`

**原因**：两个容器的文件系统是隔离的，NapCat 无法访问 AstrBot 容器内的文件。

**解决方案**：在 NapCat 的 `docker-compose.yml` 中添加 volume 映射，使其能访问 AstrBot 的下载目录：

```yaml
services:
  napcat:
    volumes:
      - ./napcat-data:/app/data
      # 添加以下映射（路径根据实际情况调整）
      - /宿主机上的AstrBot数据目录/plugin_data/jm_cosmos2/downloads:/AstrBot/data/plugin_data/jm_cosmos2/downloads
```

**示例**：假设 AstrBot 的数据目录在宿主机的 `/root/AstrBot/data`：

```yaml
volumes:
  - /root/AstrBot/data/plugin_data/jm_cosmos2/downloads:/AstrBot/data/plugin_data/jm_cosmos2/downloads
```

> [!TIP]
> 修改后需要重建容器：`docker-compose down && docker-compose up -d`

## 更新日志

查看完整更新日志：[CHANGELOG.md](./CHANGELOG.md)

**当前版本：v2.5.1** - 修复 `/jmc` 章节下载功能。

## 注意事项

- 本插件仅供学习交流使用
- 请勿将下载的内容用于商业用途
- 大量请求可能导致 IP 被封禁
- 请遵守当地法律法规

## 贡献指南

欢迎提交 Pull Request 和 Issue。提交代码时请遵循以下提交消息规范：

### 提交类型

| 类型       | 说明                                     |
| ---------- | ---------------------------------------- |
| `feat`     | 新功能                                   |
| `fix`      | Bug 修复                                 |
| `docs`     | 文档变更                                 |
| `style`    | 代码格式调整（空格、分号等，不影响逻辑） |
| `refactor` | 代码重构（既非新功能也非 Bug 修复）      |
| `perf`     | 性能优化                                 |
| `test`     | 添加或修正测试                           |
| `chore`    | 构建过程或辅助工具的变动                 |
| `revert`   | 回滚提交                                 |
| `ci`       | CI/CD 相关变更                           |
| `build`    | 构建系统变更                             |

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

- [AstrBot](https://github.com/AstrBotDevs/AstrBot) - 机器人框架
- [JMComic-Crawler-Python](https://github.com/hect0x7/JMComic-Crawler-Python) - JMComic 库
- [pyzipper](https://github.com/danifus/pyzipper) - 加密 ZIP 库
- [pymupdf](https://pymupdf.readthedocs.io/) - PDF 处理库
