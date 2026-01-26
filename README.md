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
│  Dashboard | Tasks | Alpha Lab | Config Center          │
└─────────────────────────────────────────────────────────┘
                            │ REST API + SSE
┌─────────────────────────────────────────────────────────┐
│                    Backend (FastAPI)                    │
│  ┌─────────────────────────────────────────────────┐    │
│  │               Agent Hub                          │    │
│  │  Mining Agent | Analysis Agent | Feedback Agent │    │
│  └─────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────┐    │
│  │            Core Services                         │    │
│  │  Knowledge Base | Prompt Engine | BRAIN Adapter │    │
│  │  *Sync Service* | Task Scheduler                │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────┐
│                 PostgreSQL Database                     │
│  mining_tasks | trace_steps | alpha_base | knowledge    │
└─────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL 14+
- WorldQuant BRAIN 账号

### 1. Clone & Setup

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

### 2. Configure Environment

复制并编辑 `.env` 文件:

```bash
cp .env.example .env
```

```env
# Database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_DB=alpha_gpt

# Brain Platform
BRAIN_EMAIL=your_email@example.com
BRAIN_PASSWORD=your_brain_password

# LLM (OpenAI Compatible)
OPENAI_API_KEY=sk-xxxxxxxx
OPENAI_BASE_URL=https://api.deepseek.com/v1
OPENAI_MODEL=deepseek-chat
```

### 3. Initialize Database

```bash
# Create database
psql -U postgres -c "CREATE DATABASE alpha_gpt;"

# Run migrations
psql -U postgres -d alpha_gpt -f backend/migrations/001_initial_schema.sql
```

### 4. Start Services

**Terminal 1 - Backend:**
```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8001
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
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
│   ├── database.py             # 数据库连接
│   ├── models.py               # SQLAlchemy 模型
│   ├── routers/
│   │   ├── dashboard.py        # 统计 & Live Feed
│   │   ├── tasks.py            # 任务管理 & Trace
│   │   ├── alphas.py           # Alpha 管理 & 反馈
│   │   └── knowledge.py        # 知识库管理
│   ├── services/
│   │   ├── mining_service.py   # 挖掘服务
│   │   └── analysis_service.py # 分析服务
│   ├── agents/
│   │   ├── mining_agent.py     # Mining Agent
│   │   ├── feedback_agent.py   # Feedback Agent
│   │   └── prompts.py          # Prompt 模板
│   ├── adapters/
│   │   └── brain_adapter.py    # BRAIN API 封装
│   └── migrations/
│       └── 001_initial_schema.sql
├── frontend/
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
│   │   │   └── ConfigCenter.jsx
│   │   └── services/
│   │       └── api.js
│   ├── package.json
│   └── vite.config.js
├── data/
│   ├── 需求说明文档.md
│   ├── 详细设计说明文档.md
│   └── ui_design_spec.md
├── requirements.txt
├── docker-compose.yml
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

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

---

## 📊 Key Concepts

### Trace Visualization (RD-Agent Style)

每个挖掘任务的步骤完全透明：

```
Step 1: RAG_QUERY → 检索成功模式
Step 2: HYPOTHESIS → 生成投资假设
Step 3: CODE_GEN → 生成 Alpha 表达式
Step 4: VALIDATE → 语法校验
Step 5: SIMULATE → BRAIN 模拟
Step 6: EVALUATE → 质量评估
```

### CoSTEER Feedback Loop

**短循环** (单任务内):
```
生成 → 模拟 → 失败 → Self-Correction → 重试
```

**长循环** (跨任务):
```
失败样本 → 聚类归因 → 更新知识库 → 优化 Prompt
```

### Human-in-the-Loop

- 任意步骤可暂停/调整
- 👍/👎 反馈直接影响知识库
- 交互模式：每步确认

---

## 📈 Roadmap

- [x] Phase 1: 基础骨架 (Backend + Frontend + DB)
- [x] Phase 2: Trace 可视化 + Mining Agent 核心
- [x] Phase 3: Brain 平台同步与集成
- [ ] Phase 4: Celery 异步任务队列优化
- [ ] Phase 5: 多区域并行挖掘
- [ ] Phase 6: 高级分析仪表盘

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
