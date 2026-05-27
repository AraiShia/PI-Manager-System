# API Client 基础设施优化实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 优化 ApiClient，使用 logging 替代 print，添加会话健康检查和动态超时

**架构：** 新增日志配置模块，修改 ApiClient 集成日志和健康检查功能

**技术栈：** Python logging, requests, PySide6

---

## 文件结构

| 文件 | 操作 | 职责 |
|:---|:---|:---|
| `client/api/logging_config.py` | 新增 | 日志配置模块 |
| `client/api/client.py` | 修改 | 集成日志、健康检查、动态超时 |

---

## 任务 1：创建日志配置模块

**文件：**
- 创建：`client/api/logging_config.py`

- [ ] **步骤 1：创建日志配置文件**

```python
import logging
import os
from logging.handlers import RotatingFileHandler

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

- [ ] **步骤 2：Commit**

```bash
git add client/api/logging_config.py
git commit -m "feat: 添加日志配置模块"
```

---

## 任务 2：修改 ApiClient - 基础改造

**文件：**
- 修改：`client/api/client.py`

- [ ] **步骤 1：添加导入和 logger 初始化**

在 `client/api/client.py` 文件顶部添加导入：

```python
from .logging_config import setup_logger
```

在 `ApiClient.__init__` 方法中添加：

```python
def __init__(self, base_url: str = None):
    self.base_url = (base_url or Config.API_BASE_URL).rstrip("/")
    self.session = self._create_session()
    self.db_config = None
    self._logger = setup_logger("ApiClient")
```

- [ ] **步骤 2：Commit**

```bash
git add client/api/client.py
git commit -m "feat: ApiClient 添加 logger 初始化"
```

---

## 任务 3：替换 get 方法中的 print

**文件：**
- 修改：`client/api/client.py:47-78`

- [ ] **步骤 1：修改 get 方法**

找到 `def get` 方法（约第 47 行），替换为：

```python
def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
    url = self._build_url(endpoint)
    self._logger.debug(f"GET request: {endpoint}, params: {params}")
    try:
        response = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)
        self._logger.debug(f"GET response status: {response.status_code}")
        response.raise_for_status()
        result = response.json()
        self._logger.debug(f"GET response: {len(result) if isinstance(result, list) else 'dict'} items")
        return result
    except Exception as e:
        self._logger.error(f"GET request failed: {str(e)}")
        raise
```

- [ ] **步骤 2：Commit**

```bash
git add client/api/client.py
git commit -m "refactor: get 方法 print 替换为 logger"
```

---

## 任务 4：替换 post 方法中的 print

**文件：**
- 修改：`client/api/client.py:80-120`

- [ ] **步骤 1：修改 post 方法**

找到 `def post` 方法（约第 80 行），替换为：

```python
def post(self, endpoint: str, data: Dict[str, Any] = None, files: Dict = None) -> Dict[str, Any]:
    url = self._build_url(endpoint)
    self._logger.debug(f"POST request: {endpoint}")

    if files:
        import requests as req
        if self.token:
            headers = {"Authorization": f"Bearer {self.token}"}
        else:
            headers = {}

        response = req.post(url, files=files, headers=headers, timeout=60)
    else:
        response = self.session.post(url, json=data, timeout=REQUEST_TIMEOUT)

    self._logger.debug(f"POST response status: {response.status_code}")
    try:
        response.raise_for_status()
        result = response.json()
        self._logger.debug(f"POST response: OK")
        return result
    except Exception as e:
        self._logger.error(f"POST request failed: {str(e)}")
        raise
```

- [ ] **步骤 2：Commit**

```bash
git add client/api/client.py
git commit -m "refactor: post 方法 print 替换为 logger"
```

---

## 任务 5：替换 put/patch/delete 方法中的 print

**文件：**
- 修改：`client/api/client.py`

- [ ] **步骤 1：修改 put 方法**

找到 `def put` 方法，替换为：

```python
def put(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
    url = self._build_url(endpoint)
    self._logger.debug(f"PUT request: {endpoint}")
    response = self.session.put(url, json=data, timeout=REQUEST_TIMEOUT)
    self._logger.debug(f"PUT response status: {response.status_code}")
    try:
        response.raise_for_status()
        result = response.json()
        self._logger.debug(f"PUT response: OK")
        return result
    except Exception as e:
        self._logger.error(f"PUT request failed: {str(e)}")
        raise
```

找到 `def patch` 方法，替换为：

```python
def patch(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    url = self._build_url(endpoint)
    self._logger.debug(f"PATCH request: {endpoint}")
    response = self.session.patch(url, json=data, timeout=REQUEST_TIMEOUT)
    self._logger.debug(f"PATCH response status: {response.status_code}")
    try:
        response.raise_for_status()
        result = response.json()
        self._logger.debug(f"PATCH response: OK")
        return result
    except Exception as e:
        self._logger.error(f"PATCH request failed: {str(e)}")
        raise
```

找到 `def delete` 方法，替换为：

```python
def delete(self, endpoint: str) -> Dict[str, Any]:
    url = self._build_url(endpoint)
    self._logger.debug(f"DELETE request: {endpoint}")
    response = self.session.delete(url, timeout=REQUEST_TIMEOUT)
    self._logger.debug(f"DELETE response status: {response.status_code}")
    if response.status_code >= 400:
        self._logger.warning(f"DELETE response body: {response.text}")
    try:
        response.raise_for_status()
        if response.content:
            result = response.json()
            self._logger.debug(f"DELETE response: {result}")
            return result
        return {}
    except Exception as e:
        self._logger.error(f"DELETE request failed: {str(e)}")
        raise
```

- [ ] **步骤 2：Commit**

```bash
git add client/api/client.py
git commit -m "refactor: put/patch/delete 方法 print 替换为 logger"
```

---

## 任务 6：添加动态超时方法

**文件：**
- 修改：`client/api/client.py`

- [ ] **步骤 1：在 ApiClient 类中添加超时常量和方法**

在 `REQUEST_TIMEOUT = 10` 之后添加：

```python
DEFAULT_TIMEOUT = 10
LARGE_RESPONSE_THRESHOLD = 1024 * 1024  # 1MB
```

在类中添加方法（在 `_build_url` 方法之前）：

```python
def _calculate_timeout(self, response: requests.Response = None) -> int:
    """根据响应大小动态计算超时时间"""
    timeout = DEFAULT_TIMEOUT

    if response is not None:
        content_length = response.headers.get("Content-Length")
        if content_length:
            try:
                size = int(content_length)
                if size > LARGE_RESPONSE_THRESHOLD:
                    timeout = max(30, size // (100 * 1024))
                    self._logger.debug(f"大文件响应 {size} bytes, 超时调整为 {timeout}s")
            except ValueError:
                pass

    return timeout
```

- [ ] **步骤 2：Commit**

```bash
git add client/api/client.py
git commit -m "feat: 添加动态超时计算方法"
```

---

## 任务 7：添加健康检查方法

**文件：**
- 修改：`client/api/client.py`

- [ ] **步骤 1：在 ApiClient 类中添加健康检查方法**

在 `_calculate_timeout` 方法之后添加：

```python
def is_alive(self) -> bool:
    """检查 API 连接是否正常"""
    try:
        response = self.session.get(self.base_url, timeout=5)
        return response.status_code < 500
    except Exception as e:
        self._logger.warning(f"健康检查失败: {str(e)}")
        return False

def refresh_session(self):
    """刷新会话（断线重连）"""
    self._logger.info("刷新 API 会话...")
    self.session = self._create_session()
    if self.db_config:
        self.set_db_config(self.db_config)
    self._logger.info("API 会话已刷新")
```

- [ ] **步骤 2：Commit**

```bash
git add client/api/client.py
git commit -m "feat: 添加会话健康检查方法"
```

---

## 任务 8：验证和测试

**文件：**
- 无文件变更

- [ ] **步骤 1：检查 logs 目录是否创建**

运行：检查 `client/logs` 目录是否存在

- [ ] **步骤 2：尝试运行客户端测试日志输出**

运行：启动客户端，访问产品管理 Tab

预期：控制台输出类似 `[DEBUG] ApiClient: GET request: /customer-products`

- [ ] **步骤 3：检查日志文件**

运行：查看 `client/logs/api_client.log` 内容

预期：包含请求和响应日志

- [ ] **步骤 4：Commit 测试结果**

```bash
git add -A
git commit -m "test: 验证日志和健康检查功能"
```

---

## 实施优先级

| 任务 | 优先级 | 说明 |
|:---:|:---:|:---|
| 1 | P1 | 日志配置模块 |
| 2 | P1 | 基础改造 |
| 3-5 | P1 | print 替换 |
| 6 | P2 | 动态超时 |
| 7 | P2 | 健康检查 |
| 8 | P3 | 验证测试 |

---

**计划已完成并保存到 `docs/superpowers/plans/2026-05-27-API-Client-优化实现.md`。**

**两种执行方式：**

**1. 子代理驱动（推荐）** - 每个任务调度一个新的子代理，任务间进行审查，快速迭代

**2. 内联执行** - 在当前会话中使用 executing-plans 执行任务，批量执行并设有检查点

**选哪种方式？**