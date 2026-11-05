# iMES 设备洞察 Agent —— 基础框架

面向**制造业设备运维**的对话式分析助手基础框架。架构参考课件源码 `imooc-mas`（DDD 分层多智能体系统），并按你的《iMES 设备洞察 Agent 总体技术方案》做了**制造业领域适配**。使用 **uv** 管理 Python 工程。

> 定位：**查现状 → 看趋势 → 找原因 → 问对策** 的闭环。班组长 / 设备工程师用自然语言即可完成设备洞察。

---

## 一、架构

| 本框架实现 |
| --- | --- |
| 项目初始化 / 通用模块（数据源、统一响应、日志跨域） | `core/config.py` 动态配置、`interfaces/errors` 统一异常、`infrastructure/logging` 日志 |
| MCP 协议 | `core/config.py` 的 `MCPConfig`（预留扩展位）、`domain/services/tools` 工具协议 |
| LLM 模块（可动态配置 + 后台运行） `domain/external/llm.py` 协议 + `infrastructure/external/llm`（OpenAI/DeepSeek 与 Mock 两种实现）、`application/services/agent_service.py` 后台任务运行器 |
| Agent 模块 | `domain/services/agents`（BaseAgent ReAct 循环 + EquipmentInsightAgent）、事件流（ToolEvent/MessageEvent/DoneEvent） |
| 沙箱模块（思路预留） | 工具协议可挂载沙箱执行，基础框架先用进程内工具集 | |

DDD 分层结构：

```
ims_equipment_agent/                 # 即课件中的 api/ 根
├── pyproject.toml                   # uv 工程管理
├── config.yaml                      # 业务配置（agent/llm/mcp/data_source）
├── .env.example                     # 环境变量样例
├── core/
│   └── config.py                    # Settings + AppConfig（LLMConfig/AgentConfig/MCPConfig）
└── app/
    ├── main.py                      # FastAPI 入口 + 生命周期 + CORS + 异常
    ├── domain/                      # 领域层（不依赖具体实现）
    │   ├── external/                # LLM / JSONParser 协议
    │   ├── models/                  # event / message / memory / tool_result
    │   ├── repositories/            # IMemoryRepository / IUnitOfWork
    │   └── services/
    │       ├── agents/              # BaseAgent（ReAct）+ react（设备洞察Agent）
    │       ├── tools/               # tool 装饰器 + BaseTool + 5 类工具
    │       └── analysis/            # Theil-Sen + Bootstrap 稳健趋势
    ├── infrastructure/              # 基础设施层（协议的具体实现）
    │   ├── external/llm/            # OpenAILLM(DeepSeek) + MockLLM
    │   ├── external/json_parser/    # DefaultJSONParser(json-repair)
    │   ├── logging/                 # setup_logging
    │   ├── repositories/            # InMemoryMemoryRepository
    │   └── data/                    # 内置样本数据（设备/报警/时序/知识库）
    ├── application/                 # 应用层
    │   ├── errors/                  # 统一异常
    │   └── services/agent_service.py# AgentTaskRunner（后台运行）+ AgentService（会话管理）
    └── interfaces/                  # 接口层
        ├── endpoints/               # chat(对话/SSE) + status(状态)
        ├── schemas/                 # 请求/响应模型
        ├── errors/                  # 异常处理器
        └── service_dependencies.py  # 依赖注入
```

---

## 二、内置的 5 类设备运维工具（工具设计）

| 工具集 | 工具 | 说明 |
| --- | --- | --- |
| `equipment` | `query_equipment` / `query_alarm_log` | 查设备主数据（型号/控制限）、查报警日志 |
| `trend` | `analyze_trend` | Theil-Sen 斜率 + Bootstrap 95% 置信区间（方案第5章核心算法） |
| `prediction` | `predict_failure` / `explain` | 故障概率预测 + SHAP 风格可解释性 |
| `knowledge` | `search_knowledge` | SOP / 历史案例检索（关键词 + 机型过滤） |
| `workorder` | `create_workorder` / `query_workorder` | 创建设备维修工单（落地可执行动作） |

接入真实 LLM（DeepSeek）后，`EquipmentInsightAgent` 会按意图自主选择并串联这些工具，输出自然语言结论。

---

## 三、运行方式（uv）

```bash
# 1. 进入工程根目录（即含 pyproject.toml 的目录）
cd ims_equipment_agent

# 2. 安装依赖（uv 自动创建虚拟环境）
uv sync

# 3. 启动服务（默认 mock 模式，无需 API Key 即可演示）
uv run uvicorn app.main:app --reload --port 8000
```

> 后端 API 文档：`http://localhost:8000/docs`。

### 前端（Next.js）
前端工程位于 `ui/`（Next.js 16 + React 19 + TypeScript + Tailwind 4 + Radix/shadcn 风格组件），
通过 `POST /api/chat/stream` 的 SSE 流实时展示「工具调用过程 + 最终结论」，并支持多轮对话（复用 `session_id`）。

```bash
# 另开终端，进入前端目录
cd ui
npm install        # 首次安装依赖
npm run dev        # 开发服务器，默认 http://localhost:3000
# 或生产构建： npm run build && npm run start
```

> 前端通过环境变量 `NEXT_PUBLIC_API_BASE_URL` 连接后端，默认 `http://localhost:8000/api`（见 `ui/.env.local`）；
> 生产构建可改为 `/api` 由 Nginx 反向代理。后端已开启 CORS，开发环境可直接跨端口调用。
>
> 目录结构（`ui/`）：
> ```
> ui/src/
> ├── app/                # 页面（layout.tsx 顶栏 + page.tsx 对话页）
> ├── components/
> │   ├── ui/             # shadcn 风格基础组件（button/card/input/textarea/badge/avatar/scroll-area/separator）
> │   ├── tool-use/       # 工具调用可视化卡片（calling/called 状态、入参与返回）
> │   └── status-pill.tsx # 顶栏 LLM 状态指示
> ├── hooks/use-chat.ts   # 管理对话轮次与流式事件
> └── lib/api/            # 类型定义 / 配置 / SSE 客户端 / 状态接口
> ```

### 两种 LLM 模式
- **Mock 模式（默认）**：`config.yaml` 中 `llm.api_key` 留空即自动回退，用关键词意图识别驱动 ReAct 循环，便于本地演示/单测。
- **真实模式（DeepSeek）**：复制 `.env.example` 为 `.env`，填入 `LLM_API_KEY`，`llm.provider=openai`，重启即可。

---

## 四、接口示例

```bash
# 1) 状态
curl http://localhost:8000/api/status

# 2) 对话（SSE 流式，提交即输出）
curl -N -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message":"1号邦定机最近温度是不是在上升？会不会出问题？"}'

# 也可：先 POST /api/chat 拿到 session_id，再 GET /api/chat/stream/{session_id} 拉取
```

事件流类型：`tool`(调用中/已调用) → `message`(最终回答) → `done`。

---

## 五、如何扩展（对照方案落地）

1. **替换真实数据源**：在 `app/infrastructure/data/` 增加数据库/时序库实现，或把工具改为调用真实 MES / 数仓接口（保持返回 `ToolResult`）。
2. **接入 MCP**：参考第6章，新增 `app/domain/services/tools/mcp.py` 实现 `BaseTool`，在 `AgentService._tools` 注册；`MCPConfig` 已预留。
3. **持久化记忆**：把 `InMemoryMemoryRepository` 换成 Postgres/Redis 实现（`IMemoryRepository` 接口不变）。
4. **接入故障预测模型**：用 LightGBM + 真实 SHAP 替换 `prediction.py` 中的演示式评分（见方案第5章 ADR）。
5. **多 Agent 协作**：参考第2章，新增 `PlannerAgent`，由 `AgentService` 编排多个 `BaseAgent`。

---

## 六、技术栈

FastAPI · Uvicorn · OpenAI SDK（兼容 DeepSeek）· Pydantic / pydantic-settings · NumPy（Theil-Sen）· json-repair · uv
