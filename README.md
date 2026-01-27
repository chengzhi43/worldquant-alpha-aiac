# AIAC 2.0 - Alpha-GPT Mining System

<div align="center">

![Version](https://img.shields.io/badge/version-2.0.0-blue)
![Python](https://img.shields.io/badge/python-3.10+-green)
![React](https://img.shields.io/badge/react-18.x-61DAFB)
![License](https://img.shields.io/badge/license-MIT-yellow)

**Human-AI Collaborative Alpha Mining Platform**  
*基于 Alpha-GPT 范式 + RD-Agent CoSTEER 反馈闘环*

[English](#features) | [中文](#功能特性)

</div>

---

## 🌟 Overview

AIAC 2.0 是一个基于 **Alpha-GPT** 理念的智能 Alpha 挖掘系统，融合了 **RD-Agent** 的 CoSTEER 反馈闘环机制，实现：

- 🎯 **每日稳定产出 3-4 个合格 Alpha**
- 🔄 **持续多样性探索**（跨区域、跨数据集）
- 👁️ **全链路 Trace 可视化**（RD-Agent 风格）
- 🧠 **知识库自演进**（成功模式 + 失败教训）
- 🤝 **人机协作**（Human-in-the-Loop 干预）

---

## 📋 Features

### 核心功能

| 模块 | 功能 | 状态 |
|------|------|------|
| **Dashboard** | 每日目标进度、KPI 卡片、实时活动流 | ✅ |
| **Task Management** | 任务创建、启动/暂停、Trace 时间线 | ✅ |
| **Alpha Lab** | Alpha 列表、详情、人工反馈、**Brain 同步** | ✅ |
| **Config Center** | 质量门槛、算子偏好、知识库管理 | ✅ |
| **Mining Agent** | Hierarchical RAG + LLM 生成 | ✅ |
| **Feedback Loop** | CoSTEER 双循环（自修正 + 知识演进） | ✅ |

### 技术架构

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React + Vite)              │
│  Dashboard | Tasks | Alpha Lab | Config | Data Mgmt     │
└─────────────────────────────────────────────────────────┘
                            │ REST API + SSE
┌─────────────────────────────────────────────────────────┐
│                    Backend (FastAPI)                    │
│  ┌─────────────────────────────────────────────────┐    │
│  │              Agent Hub (LangGraph)               │    │
│  │  Mining | Strategy | Feedback | Field Screener  │    │
│  └─────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────┐    │
│  │            Core Services                         │    │
│  │  Knowledge Base | Prompt Engine | BRAIN Adapter │    │
│  │  Credentials | Mining Service | Evolution        │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
                            │
         ┌─────────────────┴─────────────────┐
         │                                   │
┌───────────────────┐       ┌───────────────────┐
│   PostgreSQL     │       │   Redis + Celery  │
│   (SQLAlchemy)   │       │   (异步任务)       │
└───────────────────┘       └───────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL 14+
- Redis 7+ (用于 Celery 异步任务)
- WorldQuant BRAIN 账号

### 方法一：一键启动 (推荐)

**Windows:**
```bash
# 双击运行或命令行执行
start.bat
```

**Linux/macOS:**
```bash
chmod +x start.sh
./start.sh
```

启动脚本会自动：
1. 检查并创建 `.env` 配置文件
2. 可选安装依赖
3. 可选初始化/重置数据库
4. 启动 Backend、Frontend 和 Celery Worker

### 方法二：手动启动

#### 1. Clone & Setup

```bash
git clone https://github.com/your-repo/worldquant-alpha-aiac.git
cd worldquant-alpha-aiac

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend && npm install && cd ..
```

#### 2. Configure Environment

复制并编辑 `.env` 文件:

```bash
cp .env.example .env
```

```env
# Database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password_here
POSTGRES_SERVER=localhost
POSTGRES_PORT=5433
POSTGRES_DB=alpha_gpt

# Redis (for Celery and SSE)
REDIS_URL=redis://localhost:6379/0

# WorldQuant BRAIN Platform
BRAIN_EMAIL=your_email@example.com
BRAIN_PASSWORD=your_brain_password

# LLM Configuration (OpenAI Compatible)
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_BASE_URL=https://api.deepseek.com/v1
OPENAI_MODEL=deepseek-chat

# Mining Defaults (optional)
DEFAULT_REGION=USA
DEFAULT_UNIVERSE=TOP3000
DEFAULT_DAILY_GOAL=4

# Quality Thresholds (optional)
SHARPE_MIN=1.5
TURNOVER_MAX=0.7
FITNESS_MIN=0.6
MAX_CORRELATION=0.7
```

#### 3. Initialize Database

数据库和表结构会自动创建，无需手动操作：

- **数据库**: 由 `init_database.py` 自动创建（首次运行时）
- **表结构**: 由 SQLAlchemy 在应用启动时自动创建

只需确保 PostgreSQL 服务正在运行且 `.env` 中的凭证配置正确即可。

```bash
# 可选：手动创建数据库（如果自动创建失败）
python backend/migrations/init_database.py
```

#### 4. Start Services

**Terminal 1 - Backend:**
```bash
uvicorn backend.main:app --reload --port 8001
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

**Terminal 3 - Celery Worker (可选，用于后台任务):**
```bash
celery -A backend.celery_app worker --loglevel=info --pool=solo
```

**Access:**
- Frontend: http://localhost:5174
- API Docs: http://localhost:8001/docs
- API: http://localhost:8001/api/v1

---

## 📁 Project Structure

```
worldquant-alpha-aiac/
├── backend/
│   ├── main.py                 # FastAPI 应用入口
│   ├── config.py               # 配置管理
│   ├── database.py             # 数据库连接 + SQLAlchemy 自动迁移
│   ├── models.py               # SQLAlchemy 模型
│   ├── celery_app.py           # Celery 配置
│   ├── tasks.py                # Celery 任务定义
│   ├── routers/
│   │   ├── dashboard.py        # 统计 & Live Feed
│   │   ├── tasks.py            # 任务管理 & Trace
│   │   ├── alphas.py           # Alpha 管理 & 反馈
│   │   ├── knowledge.py        # 知识库管理
│   │   ├── mining.py           # 挖掘任务 API
│   │   ├── config.py           # 配置 API
│   │   ├── datasets.py         # 数据集 API
│   │   ├── operators.py        # 算子 API
│   │   └── analysis.py         # 分析 API
│   ├── services/
│   │   ├── mining_service.py   # 挖掘服务
│   │   ├── analysis_service.py # 分析服务
│   │   └── credentials_service.py # 凭证管理服务
│   ├── agents/
│   │   ├── agent_hub.py        # Agent 统一入口
│   │   ├── mining_agent.py     # 挖掘 Agent
│   │   ├── feedback_agent.py   # 反馈 Agent
│   │   ├── strategy_agent.py   # 策略 Agent
│   │   ├── field_screener.py   # 字段筛选器
│   │   ├── evolution_strategy.py # 进化策略
│   │   ├── prompts.py          # Prompt 模板
│   │   ├── graph/              # LangGraph 工作流
│   │   └── services/           # Agent 内部服务
│   ├── adapters/
│   │   ├── brain_adapter.py    # BRAIN API 封装
│   │   └── brain.py            # BRAIN 底层接口
│   └── migrations/
│       └── init_database.py    # 数据库初始化辅助脚本
├── frontend/
│   ├── Dockerfile              # 前端 Docker 镜像
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   ├── index.css           # 暗色主题
│   │   ├── components/
│   │   │   ├── AppSidebar.jsx
│   │   │   └── AppHeader.jsx
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx
│   │   │   ├── TaskManagement.jsx
│   │   │   ├── TaskDetail.jsx
│   │   │   ├── AlphaLab.jsx
│   │   │   ├── AlphaDetail.jsx
│   │   │   ├── ConfigCenter.jsx
│   │   │   └── DataManagement.jsx  # 数据管理
│   │   └── services/
│   │       └── api.js
│   ├── package.json
│   └── vite.config.js
├── data/                       # 设计文档
│   ├── 需求说明文档.md
│   ├── 详细设计说明文档.md
│   └── ui_design_spec.md
├── .env.example                # 环境变量模板
├── requirements.txt            # Python 依赖
├── docker-compose.yml          # Docker 编排配置
├── Dockerfile.backend          # 后端 Docker 镜像
├── start.bat                   # Windows 一键启动脚本
├── start.sh                    # Linux/macOS 一键启动脚本
└── README.md
```

---

## 🔧 API Reference

### Dashboard

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/stats/daily` | GET | 今日挖掘统计 |
| `/api/v1/stats/kpi` | GET | KPI 指标 |
| `/api/v1/stats/live-feed` | GET | SSE 实时活动流 |

### Tasks

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/tasks` | GET | 任务列表 |
| `/api/v1/tasks` | POST | 创建任务 |
| `/api/v1/tasks/{id}` | GET | 任务详情 (含 Trace) |
| `/api/v1/tasks/{id}/trace` | GET | 完整 Trace 时间线 |
| `/api/v1/tasks/{id}/start` | POST | 启动任务 |
| `/api/v1/tasks/{id}/intervene` | POST | 人工干预 (暂停/跳过/调整) |

### Alphas

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/alphas` | GET | Alpha 列表 |
| `/api/v1/alphas/sync` | POST | 同步 Brain 平台 Alpha |
| `/api/v1/alphas/{id}` | GET | Alpha 详情 |
| `/api/v1/alphas/{id}/feedback` | POST | 提交人工反馈 |

### Knowledge

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/knowledge` | GET | 知识库条目 |
| `/api/v1/knowledge/success-patterns` | GET | 成功模式 |
| `/api/v1/knowledge/failure-pitfalls` | GET | 失败教训 |

---

## 🐳 Docker Deployment

Docker 方式适合生产环境部署，包含完整的服务编排。

### 服务组件

| 服务 | 端口 | 说明 |
|------|------|------|
| `db` | 5433:5432 | PostgreSQL 数据库 |
| `redis` | 6379:6379 | Redis (Celery & SSE) |
| `backend` | 8000:8000 | FastAPI 后端 |
| `frontend` | 3000:3000 | React 前端 |
| `celery-worker` | - | Celery 工作进程 |
| `celery-beat` | - | Celery 定时任务 |

### 使用方法

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env 填入你的配置

# 2. 构建并启动所有服务
docker-compose up -d

# 3. 查看日志
docker-compose logs -f

# 4. 查看特定服务日志
docker-compose logs -f backend

# 5. 停止所有服务
docker-compose down

# 6. 停止并删除数据卷（清空数据）
docker-compose down -v
```

### Docker 访问地址

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## 📊 Key Concepts

### Trace Visualization (RD-Agent Style)

每个挖掘任务的步骤完全透明，对应 `TraceStepType` 枚举：

```
Step 1: RAG_QUERY     → 检索知识库成功模式
Step 2: HYPOTHESIS    → 生成投资假设
Step 3: CODE_GEN      → 生成 Alpha 表达式
Step 4: VALIDATE      → 语法校验
Step 5: SIMULATE      → BRAIN 平台模拟
Step 6: SELF_CORRECT  → 失败时自我修正（可选）
Step 7: EVALUATE      → 质量评估（Sharpe/Turnover/Fitness）
```

### Evolution Loop (进化循环)

Mining Agent 支持多轮进化挖掘：

```
Round 1: 初始策略 → 生成 Alpha → 分析结果 → 策略演进
Round 2: 新策略 → 字段过滤 → 生成 Alpha → 分析结果 → 策略演进
Round N: 累积学习 → 达到目标或最大迭代
```

关键组件：
- **EvolutionStrategy**: 控制字段偏好、算子选择
- **RoundResult**: 记录每轮成功/失败统计
- **FeedbackAgent**: 从失败中学习优化策略

### CoSTEER Feedback Loop

**短循环** (单 Alpha 内):
```
生成 → 模拟 → 失败 → SELF_CORRECT → 重试（最多3次）
```

**长循环** (跨任务):
```
失败样本 → FeedbackAgent 聚类归因 → 更新 KnowledgeEntry → 优化 Prompt
```

### Knowledge Base (知识库)

知识库类型（`KnowledgeEntryType`）：
- **SUCCESS_PATTERN**: 成功的 Alpha 模式
- **FAILURE_PITFALL**: 失败教训
- **FIELD_BLACKLIST**: 问题字段黑名单
- **OPERATOR_STAT**: 算子使用统计

### Human-in-the-Loop

- 任意步骤可暂停/调整（`AgentMode.INTERACTIVE`）
- 👍/👎 反馈直接影响知识库（`HumanFeedback`）
- Alpha 优化候选自动识别

---

## 📈 Roadmap

### 已完成 ✅

- [x] **Phase 1**: 基础骨架 (Backend + Frontend + DB + SQLAlchemy 自动迁移)
- [x] **Phase 2**: Trace 可视化 + Mining Agent 核心
- [x] **Phase 3**: Brain 平台同步与集成 (Datasets, Operators, Fields, Alphas)
- [x] **Phase 4**: Celery 异步任务队列 (Mining, Sync, Feedback 定时任务)
- [x] **Phase 5**: 多区域支持 (USA, CHN, ASI, EUR 等)
- [x] **Phase 6**: LangGraph 工作流 + Evolution Strategy
- [x] **Phase 7**: Knowledge Base 知识库系统

### 进行中 🔄

- [ ] **Phase 8**: 高级分析仪表盘 (PnL 曲线, 区域对比)
- [ ] **Phase 9**: Alpha 优化链 (Chain-of-Alpha)

### 规划中 📋

- [ ] **Phase 10**: 多任务并行挖掘调度
- [ ] **Phase 11**: 模板库扩展 + RL 策略学习
- [ ] **Phase 12**: 生产环境部署优化 (监控, 日志, 告警)

---

## 🤝 Contributing

欢迎贡献！请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。

---

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- [Alpha-GPT Paper](https://arxiv.org/abs/xxxx) - Human-AI Interaction Paradigm
- [RD-Agent](https://github.com/microsoft/RD-Agent) - CoSTEER Feedback Loop
- [WorldQuant BRAIN](https://platform.worldquantbrain.com) - Alpha Simulation Platform

---

<div align="center">

**Built with ❤️ for Quantitative Research**

</div>
