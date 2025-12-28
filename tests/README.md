# 测试模块

## 目录结构

```
tests/
├── unit/                # 单元测试
└── integration/         # 集成测试
```

## 快速开始

```bash
# 安装依赖
pip install pytest pytest-asyncio jmcomic

# 运行单元测试
pytest tests/unit/ -v

# 运行集成测试
pytest tests/integration/ -v

# 运行所有测试
pytest tests/ -v
```

## 配置

复制 `.env.example` 为 `.env`，填写测试账号：

```env
JM_TEST_USERNAME=your_username
JM_TEST_PASSWORD=your_password
```
