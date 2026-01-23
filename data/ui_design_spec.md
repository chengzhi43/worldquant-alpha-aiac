# Alpha-GPT 2.0: Web UI & UX Design Specification

**Version**: 2.0  
**Date**: 2026-01-24  
**Philosophy**: Human-AI Symbiosis + RD-Agent Trace Transparency

---

## 1. Design System & Aesthetics

### 1.1 Theme: "Future FinTech"

- **Mode**: Dark mode default
- **Primary Colors**:
  - Background: `#0a0e17` (Deep Navy)
  - Surface: `#131a2b` (Card Background)
  - Border: `rgba(255, 255, 255, 0.1)`
- **Accent Colors**:
  - Cyan `#00d4ff`: AI activity, Trace steps
  - Green `#00ff88`: Profit, Success
  - Red `#ff4757`: Risk, Failure
  - Amber `#ffb700`: Warning, Pending
- **Typography**:
  - Font: Inter, SF Pro (Fallback: system-ui)
  - Code: JetBrains Mono

### 1.2 Visual Style

- **Glassmorphism**: Cards with `backdrop-filter: blur(12px)`
- **Gradients**: Subtle cyan-to-purple for headers
- **Animations**: Smooth slide-in, fade transitions (200ms)
- **Real-time**: Streaming text for LLM thoughts (typewriter effect)

---

## 2. Page Architecture

### 2.1 Dashboard (控制中心)

**Layout**: 3-column responsive grid

```
┌─────────────────────────────────────────────────────────┐
│ [Header] AIAC 2.0 - Alpha Mining Factory       [⚙️] [👤] │
├─────────────┬─────────────────────────┬─────────────────┤
│  Daily Goal │  Current Task Status    │  System Health  │
│  [◐ 2/4]   │  Mining: USA/TOP3000    │  BRAIN: ✅      │
│             │  Dataset: news_sent...  │  LLM: ✅        │
├─────────────┴─────────────────────────┴─────────────────┤
│ ┌─────────────────────────────────────────────────────┐ │
│ │ Live Activity Feed (SSE)                            │ │
│ │ [10:24:01] Mining Agent analyzing dataset...        │ │
│ │ [10:24:15] Simulation #1024 completed: Sharpe 1.8 ✅│ │
│ │ [10:24:30] Feedback Loop triggered                  │ │
│ └─────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────┤
│ ┌───────────────────────┐  ┌──────────────────────────┐ │
│ │ Today's KPIs          │  │ Top 10 Alpha PnL Chart   │ │
│ │ Sims: 45  Rate: 78%   │  │ [Recharts Line Graph]    │ │
│ │ Avg Sharpe: 1.62      │  │                          │ │
│ └───────────────────────┘  └──────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

**Components**:
- `DailyGoalRing`: Circular progress, animated fill
- `TaskStatusCard`: Current region/dataset, elapsed time
- `LiveFeed`: SSE-powered, max 100 entries, color-coded
- `KPICards`: Animated counters
- `PnLChart`: Recharts LineChart with tooltips

---

### 2.2 Task Management (任务控制)

**Two Views**: List View | Detail (Trace) View

#### 2.2.1 Task List View

```
┌─────────────────────────────────────────────────────────┐
│ [+ Create Task]              [Filter: All ▾] [Sort ▾]   │
├─────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────┐ │
│ │ Task #1024                                    ▶️ Run │ │
│ │ Region: USA | Universe: TOP3000 | Mode: Auto       │ │
│ │ Progress: ████████░░ 80% | Alphas: 3               │ │
│ │ Started: 2026-01-24 10:00 | ETA: 15 min            │ │
│ └─────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ Task #1023                                   ✅ Done │ │
│ │ ...                                                 │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

#### 2.2.2 Task Creation Wizard

**Step 1**: Basic Config
- Task Name (auto-generated suggestion)
- Region: USA / CHN / ASI / EUR / GLB
- Universe: TOP3000 / TOP500 / MINVOL1M

**Step 2**: Mining Strategy
- `Auto-Explore` (Hierarchical RAG)
- `Specific Datasets` (Multi-select)

**Step 3**: Agent Mode
- `Autonomous`: Fully automatic
- `Interactive`: Pause at each step for approval

**Step 4**: Review & Launch

#### 2.2.3 Task Detail View (Trace Visualization - 核心)

```
┌─────────────────────────────────────────────────────────┐
│ Task #1024: USA Momentum Alphas              [⏸️][⏹️]   │
├─────────────┬───────────────────────────────┬───────────┤
│  Task Info  │      Trace Timeline (Center)  │ Candidates│
│             │                               │           │
│ Region: USA │  ┌─[Step 1: RAG Query]────┐   │ ┌───────┐ │
│ Universe:   │  │ Query: "momentum"      │   │ │Alpha1 │ │
│ TOP3000     │  │ Retrieved: 3 docs      │   │ │Sharpe │ │
│             │  │ ✅ Success (120ms)     │   │ │1.82 ✅│ │
│ Progress:   │  └────────────────────────┘   │ └───────┘ │
│ ████░░ 60%  │         │                     │ ┌───────┐ │
│             │         ▼                     │ │Alpha2 │ │
│ Alphas: 2   │  ┌─[Step 2: Hypothesis]───┐   │ │Simula-│ │
│             │  │ "价量背离捕捉反转"      │   │ │ting...│ │
│ [Intervene] │  │ CoT: 价格上涨但成交量下 │   │ └───────┘ │
│             │  │ 降表明动能减弱...       │   │           │
│             │  │ ✅ Success (850ms)     │   │           │
│             │  └────────────────────────┘   │           │
│             │         │                     │           │
│             │         ▼                     │           │
│             │  ┌─[Step 3: Code Gen]─────┐   │           │
│             │  │ ```                    │   │           │
│             │  │ ts_rank(close/         │   │           │
│             │  │   ts_mean(close,20),10)│   │           │
│             │  │ ```                    │   │           │
│             │  │ ✅ Success (320ms)     │   │           │
│             │  └────────────────────────┘   │           │
└─────────────┴───────────────────────────────┴───────────┘
```

**Trace Step Component**:
- Collapsible card per step
- Status indicator: ✅ Success | ❌ Failed | ⏳ Running | ⏸️ Paused
- Timing badge
- Input/Output toggle
- For failed steps: Show Diff with self-correction

**Intervention Modal** (when Interactive mode or Pause clicked):
- Options: Continue | Skip Dataset | Adjust Prompt | Abort

---

### 2.3 Alpha Lab (Alpha 实验室)

**Layout**: Master-Detail

```
┌─────────────────────────────────────────────────────────┐
│ [Filter: All ▾] [Region ▾] [Quality ▾]   [Search 🔍]    │
├──────────────────────┬──────────────────────────────────┤
│  Alpha List          │      Alpha Detail               │
│                      │                                  │
│ ┌──────────────────┐ │  Expression:                     │
│ │ #A1024           │ │  ┌────────────────────────────┐  │
│ │ ✅ PASS | 1.82   │ │  │ ts_rank(close /            │  │
│ │ USA | momentum   │ │  │   ts_mean(close, 20), 10)  │  │
│ └──────────────────┘ │  │ - ts_rank(volume /         │  │
│ ┌──────────────────┐ │  │   ts_mean(volume, 20), 10) │  │
│ │ #A1023           │ │  └────────────────────────────┘  │
│ │ ❌ LOW_SHARPE    │ │                                  │
│ │ CHN | reversal   │ │  Hypothesis:                     │
│ └──────────────────┘ │  "价量背离：价格动量与成交量动    │
│ ...                  │  量相对排名差异，捕捉价量分歧"    │
│                      │                                  │
│                      │  ┌─── Metrics ───────────────┐   │
│                      │  │ Sharpe   Returns  Turnover│   │
│                      │  │  1.82    12.3%     0.45   │   │
│                      │  └───────────────────────────┘   │
│                      │                                  │
│                      │  [📈 PnL Chart]                  │
│                      │  [Cumulative Returns Line]       │
│                      │                                  │
│                      │  ─── Human Feedback ───          │
│                      │  [👍 Like]  [👎 Dislike]         │
│                      │  Comment: [________________]     │
│                      │  [Submit Feedback]               │
└──────────────────────┴──────────────────────────────────┘
```

**PnL Chart** (TradingView style):
- X: Date | Y: Cumulative Return
- Benchmark overlay (optional)
- Hover tooltip with exact values
- Zoom/pan enabled

---

### 2.4 Config Center (配置中心)

**Tabs**: Quality | Operators | Datasets | Knowledge

#### 2.4.1 Quality Thresholds

| Metric | Min | Max | Current |
|--------|-----|-----|---------|
| Sharpe | 0 | 5 | `1.5` |
| Turnover | 0 | 2 | `0.7` |
| Fitness | 0 | 1 | `0.6` |

Slider components with live preview

#### 2.4.2 Operator Preferences

```
┌─────────────────────────────────────────┐
│ Operator        Usage   Success   Status│
├─────────────────────────────────────────┤
│ ts_rank         234     78%       [✅]  │
│ ts_corr         189     82%       [✅]  │
│ ts_product       45     12%       [❌]  │
│ grouped_zscore   67     65%       [✅]  │
└─────────────────────────────────────────┘
```

Toggle to BAN/ACTIVATE operators

#### 2.4.3 Knowledge Base Viewer

- List of `SUCCESS_PATTERN` / `FAILURE_PITFALL` entries
- Edit/Delete capabilities
- Add custom rule

---

## 3. Component Library

| Component | Description | Library |
|-----------|-------------|---------|
| `TraceTimeline` | Vertical step visualization | Custom |
| `ExpressionEditor` | Monaco-based code view | Monaco Editor |
| `PnLChart` | Interactive returns chart | Recharts |
| `LiveFeed` | SSE real-time log | Custom + EventSource |
| `GoalRing` | Circular progress | Ant Design Progress |
| `FeedbackModal` | Thumbs + Comment | Ant Design Modal |
| `KPICard` | Animated stat card | Custom |

---

## 4. Responsive Breakpoints

| Breakpoint | Width | Layout |
|------------|-------|--------|
| Desktop | ≥1200px | 3-column |
| Tablet | 768-1199px | 2-column |
| Mobile | <768px | 1-column (limited features) |

---

## 5. State Management

- **Server State**: React Query (TanStack Query)
  - Auto-refetch for task status
  - SSE integration for live feed
- **UI State**: Zustand
  - Current task selection
  - Filter/sort preferences
  - Modal visibility

---

## 6. Accessibility

- WCAG 2.1 AA compliance
- Keyboard navigation for all interactions
- Screen reader labels for icons
- Sufficient color contrast (4.5:1 minimum)
