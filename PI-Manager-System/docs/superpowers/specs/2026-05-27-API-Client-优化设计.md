# API Client 基础设施优化设计

> **日期：** 2026-05-27
> **状态：** 已批准
> **目标：** 优化前后端通信基础设施，改进日志输出和会话管理

---

## 1. 概述

### 1.1 背景

当前 `ApiClient` 存在以下问题：
- 使用 `print()` 调试输出，不适合生产环境
- 缺少会话健康检查和断线重连机制
- 统一超时设置导致大文件下载可能超时

### 1.2 目标

1. 使用 `logging` 模块替代 `print()`，支持控制台和文件双输出
2. 添加会话健康检查和断线重连机制
3. 实现动态超时计算，支持大文件下载

### 1.3 范围

| 文件 | 操作 |
|:---|:---|
| `client/api/logging_config.py` | 新增 |
| `client/api/client.py` | 修改 |
| `client/main.py` | 修改（可选集成） |

---

## 2. 设计方案

### 2.1 日志配置模块

**文件：** `client/api/logging_config.py`（新增）

**核心功能：**
- 创建统一的 logger 实例
- 支持控制台 + 滚动文件输出
- 日志文件大小限制（10MB），保留 5 个备份

**配置参数：**

| 参数 | 值 | 说明 |
|:---|:---|:---|
| LOG_DIR | `{项目根目录}/logs/` | 日志文件目录 |
| LOG_LEVEL | DEBUG | 开发环境使用 DEBUG |
| LOG_FORMAT | `%(asctime)s [%(levelname)s] %(name)s: %(message)s` | 日志格式 |
| MAX_BYTES | 10MB | 单个日志文件最大大小 |
| BACKUP_COUNT | 5 | 保留的备份文件数量 |

**接口设计：**

```python
def setup_logger(name: str = None) -> logging.Logger:
    """
    创建配置好的 logger

    Args:
        name: logger 名称，默认使用模块名

    Returns:
        配置好的 Logger 实例
    """
```

### 2.2 ApiClient 改造

**文件：** `client/api/client.py`（修改）

#### 2.2.1 日志集成

```python
from .logging_config import setup_logger

class ApiClient:
    def __init__(self, base_url: str = None):
        # ... 现有代码 ...
        self._logger = setup_logger("ApiClient")
```

**日志级别使用规范：**

| 级别 | 使用场景 |
|:---|:---|
| DEBUG | 请求参数、响应状态、详细数据流 |
| INFO | 重要操作确认、成功状态 |
| WARNING | 非关键问题、配置异常 |
| ERROR | 请求失败、异常情况 |

#### 2.2.2 动态超时计算

**设计原则：**
- 默认超时 10 秒（保持向后兼容）
- 根据响应大小自动延长超时时间
- 大文件下载（>1MB）自动调整超时

**实现逻辑：**

```python
DEFAULT_TIMEOUT = 10  # 默认超时（秒）
LARGE_RESPONSE_THRESHOLD = 1024 * 1024  # 1MB 阈值

def _calculate_timeout(self, response: requests.Response = None) -> int:
    """根据响应大小动态计算超时时间"""
    timeout = DEFAULT_TIMEOUT

    if response is not None:
        content_length = response.headers.get("Content-Length")
        if content_length:
            try:
                size = int(content_length)
                if size > LARGE_RESPONSE_THRESHOLD:
                    # 大文件：每 100KB 额外增加 1 秒，最少 30 秒
                    timeout = max(30, size // (100 * 1024))
            except ValueError:
                pass

    return timeout
```

#### 2.2.3 会话健康检查

**接口设计：**

```python
def is_alive(self) -> bool:
    """
    检查 API 连接是否正常

    Returns:
        True: 连接正常
        False: 连接异常
    """
    try:
        response = self.session.get(self.base_url, timeout=5)
        return response.status_code < 500
    except Exception:
        return False

def refresh_session(self):
    """
    刷新会话（断线重连）

    重新创建 session 对象，
    并重新应用已有的配置（db_config 等）
    """
    self._logger.info("刷新 API 会话...")
    self.session = self._create_session()
    if self.db_config:
        self.set_db_config(self.db_config)
    self._logger.info("API 会话已刷新")
```

---

## 3. 数据流

### 3.1 日志输出流程

```
ApiClient 请求
    ↓
setup_logger 获取 logger
    ↓
logger.debug/info/warning/error
    ↓
├── ConsoleHandler → 控制台输出
└── RotatingFileHandler → logs/api_client.log
```

### 3.2 断线重连流程

```
请求失败 (ConnectionError/TimeoutError)
    ↓
is_alive() 检查
    ↓ (返回 False)
refresh_session() 重连
    ↓
重试请求
```

### 3.3 动态超时流程

```
发送请求
    ↓
检查响应 Content-Length
    ↓
size > 1MB ?
    ├── 是 → timeout = max(30, size / 100KB)
    └── 否 → timeout = 10s
    ↓
继续处理响应
```

---

## 4. 文件变更

### 4.1 新增文件

**`client/api/logging_config.py`**

```python
import logging
import os
from logging.handlers import RotatingFileHandler

# 配置常量
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

LOG_LEVEL = logging.DEBUG
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
MAX_BYTES = 10 * 1024 * 1024  # 10MB
BACKUP_COUNT = 5


def setup_logger(name: str = None) -> logging.Logger:
    """创建配置好的 logger"""
    logger = logging.getLogger(name or __name__)
    logger.setLevel(LOG_LEVEL)

    if logger.handlers:
        return logger

    # 控制台 Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(LOG_LEVEL)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(console_handler)

    # 文件 Handler（滚动日志）
    file_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, "api_client.log"),
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8"
    )
    file_handler.setLevel(LOG_LEVEL)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(file_handler)

    return logger
```

### 4.2 修改文件

**`client/api/client.py`**

| 修改内容 | 位置 |
|:---|:---|
| 添加 `from .logging_config import setup_logger` | 导入部分 |
| `self._logger = setup_logger("ApiClient")` | `__init__` |
| 替换所有 `print()` 为 `self._logger.debug/error/info` | 各方法 |
| 添加 `_calculate_timeout()` 方法 | 新增方法 |
| 添加 `is_alive()` 方法 | 新增方法 |
| 添加 `refresh_session()` 方法 | 新增方法 |

---

## 5. 测试计划

### 5.1 单元测试

| 测试项 | 验证点 |
|:---|:---|
| 日志配置 | logger 正确创建，handler 不重复 |
| 日志输出 | 控制台和文件同时输出 |
| 日志滚动 | 超过 10MB 自动创建新文件 |
| 动态超时 | 大文件响应超时时间正确计算 |
| 健康检查 | 连接正常/异常时返回值正确 |
| 断线重连 | refresh_session 正确重建 session |

### 5.2 集成测试

| 测试项 | 验证点 |
|:---|:---|
| 正常请求 | 日志正确记录请求和响应 |
| 异常处理 | 错误日志正确输出，包含堆栈信息 |
| 大文件下载 | 超时时间足够完成下载 |

---

## 6. 风险与注意事项

### 6.1 已知风险

1. **日志文件占用空间** - 滚动日志最多占用 60MB（10MB × 5 备份）
2. **生产环境日志级别** - 需要在部署时调整为 INFO 或 WARNING

### 6.2 注意事项

1. 不要在日志中输出敏感信息（如密码、Token）
2. 生产部署前修改 `LOG_LEVEL` 为 `INFO`
3. 定期清理 `logs/` 目录中的旧日志

---

## 7. 后续优化（暂不实施）

以下功能作为可选优化点，记录但不纳入本次实施：

| 功能 | 说明 | 优先级 |
|:---|:---|:---|
| 数据库连接池 | 为迁移 MySQL/PostgreSQL 预留 | P3 |
| 服务端认证 | 移除数据库密码传递 | P2 |
| 健康检查端点 | 后端添加 `/health` 接口 | P3 |

---

## 8. 验收标准

- [ ] `client/api/logging_config.py` 创建完成
- [ ] `ApiClient` 中所有 `print()` 替换为 `logger`
- [ ] 日志同时输出到控制台和 `logs/api_client.log`
- [ ] 添加 `is_alive()` 方法并正确检测连接状态
- [ ] 添加 `refresh_session()` 方法并正确重建 session
- [ ] 添加 `_calculate_timeout()` 方法并正确计算超时
- [ ] 日志文件超过 10MB 时自动滚动
- [ ] 本地测试通过：无报错、日志正常输出