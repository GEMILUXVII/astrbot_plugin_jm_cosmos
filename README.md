# <div align="center">🪐 JM-Cosmos</div>

<div align="center"><em>全能型 JM 漫画下载与管理工具</em></div>

<br>
<div align="center">
  <a href="#更新日志"><img src="https://img.shields.io/badge/VERSION-v1.1.0-E91E63?style=for-the-badge" alt="Version"></a>
  <a href="https://github.com/GEMILUXVII/astrbot_plugin_jm_cosmos/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-AGPL--3.0-009688?style=for-the-badge" alt="License"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/PYTHON-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"></a>
  <a href="https://github.com/AstrBotDevs/AstrBot"><img src="https://img.shields.io/badge/AstrBot-Compatible-00BFA5?style=for-the-badge&logo=robot&logoColor=white" alt="AstrBot Compatible"></a>
</div>

<div align="center">
  <a href="https://pypi.org/project/jmcomic/"><img src="https://img.shields.io/badge/JMCOMIC-≥2.5.39-9C27B0?style=for-the-badge" alt="JMComic"></a>
  <a href="https://github.com/botuniverse/onebot-11"><img src="https://img.shields.io/badge/OneBotv11-AIOCQHTTP-FF5722?style=for-the-badge&logo=qq&logoColor=white" alt="OneBot v11 Support"></a>
  <a href="https://github.com/GEMILUXVII/astrbot_plugin_jm_cosmos"><img src="https://img.shields.io/badge/UPDATED-2025.09.20-2196F3?style=for-the-badge" alt="Updated"></a>
</div>

## ◎ 介绍

JM-Cosmos 是一个基于 AstrBot 开发的 JM 漫画下载插件，支持漫画搜索、预览、下载、PDF 转换与 QQ 发送

## ◎ 功能特性

### 核心功能

- 通过 ID 下载 JM 漫画并转换为 PDF
- 支持发送漫画前几页图片预览
- 支持搜索漫画、作者作品
- 支持获取漫画排行榜和随机推荐

### 高级功能

- 自动测试和更新可用域名
- 提供详细的 PDF 文件信息和诊断
- 可配置代理、Cookie 和线程数
- 智能适配各种命名格式的漫画目录
- 强大的错误处理和故障恢复能力
- 自动处理域名失效问题
- 线程池和内存优化
- 支持多种搜索格式和批量显示

## ◎ 安装方法

1. **下载插件**: 下载本插件到 AstrBot 的插件目录
2. **安装依赖**: 在终端中执行以下命令:
   ```bash
   pip install -r requirements.txt
   ```
3. **重启 AstrBot**: 确保插件被加载
4. **配置插件**: 所有配置可在 AstrBot 管理面板的"插件配置"中进行设置
5. **更新域名**: 使用以下命令更新可用域名:
   ```bash
   /jmdomain update
   ```

## ◎ 命令列表

### 基础命令

- `/jm [ID]` - 下载漫画为 PDF 并发送
- `/jmimg [ID] [页数]` - 发送漫画前几页图片预览
- `/jminfo [ID]` - 查看漫画信息
- `/jmpdf [ID]` - 检查 PDF 文件信息
- `/jmhelp` - 查看帮助信息

### 搜索功能

- `/jmsearch [关键词] [序号]` - 搜索漫画
- `/jmauthor [作者] [数量]` - 搜索作者作品（显示前 N 部或详细信息）
- `/jmrecommend` - 随机推荐漫画

### 配置命令

- `/jmconfig proxy [代理URL]` - 设置代理 URL
- `/jmconfig noproxy` - 清除代理设置
- `/jmconfig cookie [AVS Cookie]` - 设置登录 Cookie
- `/jmconfig threads [数量]` - 设置最大下载线程数
- `/jmconfig domain [域名]` - 添加 JM 漫画域名
- `/jmconfig debug [on/off]` - 开启/关闭调试模式
- `/jmconfig cover [on/off]` - 控制是否显示封面图片

### 域名管理

- `/jmdomain list` - 显示当前配置的域名
- `/jmdomain test` - 测试所有域名并显示结果
- `/jmdomain update` - 测试并自动更新可用域名

## ◎ 使用示例

### 下载与发送漫画

```
/jm 123456
```

### 获取漫画预览

```
/jmimg 123456 5
```

获取漫画前 5 页预览

### 搜索漫画

```
/jmsearch 关键词 1
```

搜索并获取第 1 个结果

### 搜索作者作品

```
/jmauthor そらもち 3
```

显示作者前 3 部作品列表

```
/jmauthor そらもち 1
```

显示作者第 1 部作品的详细信息（包含封面）

### 设置 HTTP 代理

```
/jmconfig proxy http://127.0.0.1:7890
```

### 更新可用域名

```
/jmdomain update
```

## ◎ 配置说明

插件使用 AstrBot 的官方配置系统，配置存储在 `data/config/astrbot_plugin_jm_cosmos_config.json` 中。

- **域名列表** (`domain_list`): JM 漫画域名列表
- **代理设置** (`proxy`): HTTP 代理，如 http://127.0.0.1:7890
- **登录凭证** (`avs_cookie`): 登录 Cookie
- **线程控制** (`max_threads`): 最大下载线程数
- **调试选项** (`debug_mode`): 调试模式开关

您可以通过 AstrBot 管理面板的"插件配置"页面轻松修改所有设置，也可以使用 `/jmconfig` 命令进行修改。

## ◎ 文件结构

### 核心文件

- `main.py` - 插件入口点和命令注册
- `_conf_schema.json` - 配置模式定义（用于 AstrBot 管理面板显示）
- `requirements.txt` - 依赖库列表

### 数据目录

位于 `AstrBot/data/plugin_data/jm_cosmos/`:

- `downloads/` - 下载的漫画图片目录
- `pdfs/` - 生成的 PDF 文件目录
- `covers/` - 漫画封面缓存目录
- `logs/` - 日志文件目录

## ◎ 高级功能说明

### 三层下载回退机制

插件采用智能下载策略，确保最高成功率：

1. **直接客户端下载** - 使用配置的域名直接下载
2. **强制域名配置** - 强制使用特定域名重试
3. **原始方法回退** - 使用库默认方法作为最后保障

### 智能域名管理

- **自动域名切换** - 当主域名失效时自动尝试备用域名
- **域名持久化** - 更新的域名配置会自动保存
- **错误消息优化** - 显示实际尝试的域名而非默认域名

### 增强的作者搜索

- **智能搜索格式** - 自动选择最有效的搜索方式
- **批量结果显示** - 支持显示作者前 N 部作品列表
- **详细信息模式** - 请求 1 部作品时显示详细信息和封面

### 资源管理优化

- **线程池管理** - 智能控制下载线程数量
- **内存优化** - 改进的图片处理和缓存机制
- **错误恢复** - 强化的异常处理和重试逻辑

### PDF 诊断功能

`/jmpdf` 命令可以:

- 检测文件大小是否超过 QQ 限制
- 统计主目录和子目录中的所有图片
- 识别章节结构
- 在多种目录结构中查找图片
- 当目录存在但无图片时提供具体提示

## ◎ 常见问题

### 漫画无法下载或搜索失败

**可能原因:**

- 域名失效
- 网络问题
- 爬虫被识别

**解决方法:**

```
/jmdomain update
```

### 403 错误或 IP 被禁止访问

**可能原因:**

- IP 地区限制
- 爬虫被识别

**解决方法:**

```
/jmconfig proxy 你的代理地址
```

## ◎ 注意事项

- 本插件仅供学习交流使用
- 请勿将下载的内容用于商业用途
- 大量请求可能导致 IP 被封禁
- 请遵守当地法律法规

## ◎ 更新日志

#### **v1.1.0** (2025-09-20)

**◎ 重大功能更新**

- **全新三层下载回退机制** - 显著提高下载成功率

  - 直接客户端下载 → 强制域名配置 → 原始方法回退
  - 智能域名切换，自动处理失效域名
  - 增强的错误处理和重试逻辑

- **作者搜索功能大幅改进**

  - 支持显示作者前 N 部作品列表（如：`/jmauthor そらもち 3`）
  - 智能搜索格式选择，自动找到最有效的搜索方式
  - 优化搜索结果显示，提供更清晰的作品列表

- **资源管理全面优化**

  - 引入线程池管理，提供更好的并发控制
  - 优化内存使用，减少资源占用
  - 改进的客户端工厂模式，支持多域名管理

- **用户体验改善**

  - 更详细的调试信息和日志记录
  - 优化的进度提示和状态反馈

- **代码质量提升**
  - 大幅重构下载逻辑
  - 增强输入验证和异常处理
  - 添加更多调试工具和诊断功能

#### **v1.0.7** (2025-06-01)

- 新增配置项 `show_cover`，支持控制是否在漫画信息和搜索结果中显示封面图片

#### **v1.0.6** (2025-05-06)

- 更换文件发送方式，修复文件消息缺少参数问题

#### **v1.0.5** (2025-05-05)

- 迁移到 AstrBot 官方配置系统，支持在管理面板中配置
- 修复了 API 兼容性问题，使插件适配 AstrBot 最新版本
- 优化了资源管理，现在正确使用 AstrBot 推荐的数据目录
- 改进了错误处理和日志记录
- 添加了线程监控功能，帮助分析性能问题

#### **v1.0.4** (2025-05-05)

- 增加了智能目录识别功能，支持非标准命名的漫画目录
- 改进了图片统计逻辑，能正确统计主目录和子目录的图片
- 优化了`/jmpdf`命令，提供更详细的图片和章节信息
- 修复了部分漫画因目录命名问题无法使用`/jmimg`命令的问题

#### **v1.0.3** (2025-05-04)

- 增强了错误处理
- 添加了调试模式
- 添加了网站结构变化的适配
- 修复了 PDF 文件传输失败问题
- 新增图片预览功能和 PDF 文件诊断
- 新增域名测试与自动更新功能

#### **v1.0.2** (2025-05-03)

- 修复了 PDF 文件传输失败问题
- 新增图片预览功能和 PDF 文件诊断

#### **v1.0.1** (2025-05-02)

- 增强了错误处理
- 添加了调试模式
- 添加了网站结构变化的适配

#### **v1.0.0** (2025-05-01)

- 初始版本发布

## ◎ 许可协议

本插件采用 [GNU Affero General Public License v3.0 (AGPL-3.0)](https://www.gnu.org/licenses/agpl-3.0.html) 许可证。

## ◎ 致谢

本项目基于或参考了以下开源项目:

- [AstrBot](https://github.com/Soulter/AstrBot) - 机器人框架
- [JMComic-Crawler-Python](https://github.com/hect0x7/JMComic-Crawler-Python) - Python 爬虫
- [img2pdf](https://github.com/josch/img2pdf) - 图像转 PDF 工具
