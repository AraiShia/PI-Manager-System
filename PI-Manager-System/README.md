# PI订单管理系统

基于FastAPI + Vue3的PI订单管理系统，适用于公司NAS离线部署。

## 技术栈

### 后端
- Python 3.10+
- FastAPI 0.104+
- SQLAlchemy 2.0+
- SQLite（离线部署）

### 前端
- Vue 3.4+
- Vite 5.0+
- Element Plus
- Vue Router
- Pinia

## 项目结构

```
PI-Manager-System/
├── backend/                    # 后端代码
│   ├── app/                    # 应用核心
│   │   ├── __init__.py
│   │   └── database.py         # 数据库配置
│   ├── crud/                   # CRUD操作
│   ├── models/                 # SQLAlchemy模型
│   ├── routers/                # API路由
│   ├── schemas/                # Pydantic模式
│   ├── utils/                  # 工具函数
│   ├── main.py                 # 入口文件
│   └── requirements.txt        # 依赖
├── frontend/                   # 前端代码
│   ├── src/
│   │   ├── components/         # 公共组件
│   │   ├── views/              # 页面视图
│   │   ├── router/             # 路由配置
│   │   ├── utils/              # 工具函数
│   │   ├── main.js             # 入口文件
│   │   └── App.vue             # 根组件
│   ├── index.html
│   ├── vite.config.js          # Vite配置
│   └── package.json            # 依赖
└── data/                       # SQLite数据库目录
```

## 快速开始

### 后端启动

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 前端启动

```bash
cd frontend
npm install
npm run dev
```

### 访问地址

- 前端：http://localhost:5173
- API文档：http://localhost:8000/docs

## 核心模块

1. **产品管理** - 产品信息维护、OE号管理、包装体积计算
2. **客户管理** - 客户信息、收货地址、联系人管理
3. **供应商管理** - 供应商信息、供货周期、税率管理
4. **PI管理** - PI单创建、产品明细、付款条款配置
5. **采购管理** - 采购单生成、供应商报价对比
6. **出货管理** - 出货记录、装箱单、体积计算
7. **付款管理** - 收款记录、付款记录
8. **库存管理** - 库存预警、入库记录

## 特色功能

- 编号自动生成（PI号、PO号等）
- 价格历史追溯
- 包装体积自动计算
- 客户特殊要求自动带出
- 离线部署支持（SQLite）
