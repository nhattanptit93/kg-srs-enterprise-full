# KG-SRS Enterprise — Design Overview

Hệ multi-agent trên **LangGraph** chuyển một **Raw Requirement Document (RD)** thành **SRS (Software Requirements Specification)** đạt chuẩn chất lượng, thông qua một chuỗi agent chuyên trách có khả năng **self-healing** (tự phát hiện lỗi và quay lui để sửa) với **loop limit** để tránh lặp vô hạn.

---

## 1. Mục tiêu

- **Input:** Raw RD viết trong [input.md](input.md) (hoặc file khác truyền qua CLI).
- **Output:** tài liệu SRS đã được verify, có `score >= 8`, in ra stdout.
- **Guarantee:** nếu SRS chưa đạt chất lượng, workflow **tự động** quay lại đúng bước gây lỗi thay vì sửa thủ công — dựa vào `issue_type` do verifier phân loại. Tối đa **3 vòng loop** (MAX_ITERATIONS).
- **Learning:** lưu lại bài học (lessons) vào vector memory (FAISS) để các lần chạy sau tận dụng.

---

## 2. Kiến trúc tổng quan

```
┌─────────────────────────────────────────────────────────────────┐
│                        input.md (Raw RD)                        │
│            user viết requirement thô vào đây                    │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                         main.py (entry)                         │
│     load_dotenv() → load_input() → build_app() → invoke         │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                  controller/workflow.py                         │
│     LangGraph StateGraph + conditional routing + loop cap       │
└─────────────────────────────────────────────────────────────────┘
                               │
          ┌────────────────────┼────────────────────┐
          ▼                    ▼                    ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ Pipeline Agents  │  │   core/state.py  │  │   core/llm.py    │
│ (8 modules)      │  │   AgentState     │  │ Anthropic SDK    │
└──────────────────┘  └──────────────────┘  └──────────────────┘
                                                     │
                                            ┌────────┴────────┐
                                            ▼                 ▼
                                  ┌──────────────────┐   skills (.md)
                                  │ core/memory.py   │
                                  │ FAISS + MiniLM   │
                                  └──────────────────┘
```

**Thành phần chính:**

| Layer | File | Vai trò |
|---|---|---|
| Input | [input.md](input.md) | Raw RD — điểm nhập liệu duy nhất cho user |
| Entry | [main.py](main.py) | Nạp env, đọc RD từ file, build graph, invoke, in output |
| Controller | [controller/workflow.py](controller/workflow.py) | Định nghĩa graph LangGraph, node, edge, routing + loop cap |
| State | [core/state.py](core/state.py) | Schema `AgentState` chạy xuyên suốt workflow |
| LLM | [core/llm.py](core/llm.py) | Anthropic SDK + prompt caching + `load_skill()` |
| Memory | [core/memory.py](core/memory.py) | `VectorMemory` embed + FAISS, persist `memory.json` |

### 2.1 Chi tiết Workflow của các Agent (Data Flow)

Hệ thống sử dụng mô hình tuần tự. Ở mỗi bước, Agent sẽ đọc các trường cần thiết từ `AgentState` (Input), thực hiện công việc (nhờ LLM), và ghi kết quả mới vào `AgentState` (Output) để truyền cho Agent tiếp theo.

```text
(1) Raw Requirement ──> [ state["input"] ]
                             │
                             ▼
┌────────────────────────────────────────────────────────┐
│ 1. INTERVIEW AGENT                                     │
│ Đọc: state["input"]                                    │
│ Phân tích yêu cầu thô, đặt câu hỏi & nhận câu trả lời. │
│ Ghi: state["answers"]                                  │
└────────────────────────────────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────┐
│ 2. STRUCTURING AGENT                                   │
│ Đọc: state["input"], state["answers"]                  │
│ Tổng hợp ý tưởng và câu trả lời thành Use Case.        │
│ Ghi: state["usecase"]                                  │
└────────────────────────────────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────┐
│ 3. GRAPH AGENT                                         │
│ Đọc: state["usecase"]                                  │
│ Chuyển Use Case thành Knowledge Graph (JSON).          │
│ Ghi: state["graph"]                                    │
└────────────────────────────────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────┐
│ 4. SRS AGENT                                           │
│ Đọc: state["graph"]                                    │
│ Viết tài liệu Đặc tả Yêu cầu Phần mềm (SRS) hoàn chỉnh.│
│ Ghi: state["srs"]                                      │
└────────────────────────────────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────┐
│ 5. VERIFICATION AGENT                                  │
│ Đọc: state["srs"]                                      │
│ Đánh giá chất lượng SRS (chấm điểm 0-10 & loại lỗi).   │
│ Ghi: state["qa"], state["score"], state["issue_type"]  │
└────────────────────────────────────────────────────────┘
                             │
            ┌────────────────┴────────────────┐
            │ Controller kiểm tra "score"     │
            ▼                                 ▼
    [ score < 8 ]                     [ score >= 8 ]
            │                                 │
┌────────────────────────┐                    │
│ 6. REFINE AGENT        │                    │
│ Đọc: srs, qa           │                    │
│ Sửa lỗi Consistency.   │                    │
│ Ghi: srs (ghi đè)      │                    │
└────────────────────────┘                    │
     (Vòng lặp lại)                           ▼
                                ┌────────────────────────┐
                                │ 7. DIAGRAM AGENT       │
                                │ Đọc: srs               │
                                │ Sinh state/flow/sequence│
                                │ Mermaid + drawio       │
                                │ Embed vào current_srs  │
                                └────────────────────────┘
                                             │
                                             ▼
                                ┌────────────────────────┐
                                │ 8. MEMORIZE AGENT      │
                                │ Đọc: toàn bộ State     │
                                │ Lưu bài học vào FAISS. │
                                └────────────────────────┘
                                             │
                                             ▼
                             [ OUTPUT SAU CÙNG CỦA HỆ THỐNG ]
                    Tài liệu SRS hoàn chỉnh tại workspace/current_srs.md
                    Diagram artifacts tại workspace/diagrams/ (.mmd + .drawio)
                    Điểm chất lượng (state["score"]) & Số vòng lặp đã chạy
```

---

## 3. Graph Flow

```mermaid
flowchart TD
    START([START]) --> interview
    interview --> struct
    struct --> graph
    graph --> srs
    srs --> verify
    verify -->|score >= 8| diagram
    verify -->|iterations >= 3| diagram
    verify -->|issue_type = LOGIC| graph
    verify -->|issue_type = MISSING| interview
    verify -->|else - CONSISTENCY, ...| refine
    refine --> verify
    diagram --> memorize
    memorize --> END([END])

    classDef agent fill:#e8f1ff,stroke:#4a7bd4,color:#000
    class interview,struct,graph,srs,verify,refine,diagram,memorize agent
```

**Đường đi chính (happy path):**
`interview → struct → graph → srs → verify → END`

**Các vòng self-healing (khi `score < SCORE_THRESHOLD` và `iterations < MAX_ITERATIONS`):**
- `LOGIC` → nhảy về **graph** (sai logic quan hệ giữa các thực thể, vẽ lại graph, sau đó build lại srs)
- `MISSING` → nhảy về **interview** (thiếu thông tin, hỏi thêm user, sau đó build lại toàn bộ)
- `CONSISTENCY` / khác → vào **refine** rồi vòng lại **verify** (tinh chỉnh trực tiếp trên SRS, không cần build lại graph)

**Loop guard:** biến `iterations` tăng mỗi lần `verify` chạy. Khi `iterations >= MAX_ITERATIONS (=3)`, router ép về END dù score chưa đạt — tránh lặp vô hạn.

Logic routing nằm ở hàm `route()` trong [controller/workflow.py:14-25](controller/workflow.py#L14-L25).

---

## 4. Mô tả từng Agent

### 4.1 Interview — [agents/interview/agent.py](agents/interview/agent.py)
- **Việc:** Đặt câu hỏi làm rõ yêu cầu. Nạp prompt từ [SKILLS.md](agents/interview/SKILLS.md), truy hồi lessons từ `VectorMemory`, gọi LLM sinh câu hỏi.
- **Input state:** `input`
- **Output state:** `answers`
- **3 chế độ hoạt động:**
  1. Nếu `state["answers"]` đã có sẵn → skip (dùng cho preset programmatic).
  2. Nếu `stdin` là TTY → `input()` block, user gõ câu trả lời.
  3. Nếu không phải TTY (IDE run, CI) → LLM tự sinh câu trả lời plausible để pipeline không treo.

### 4.2 Structuring — [agents/structuring/agent.py](agents/structuring/agent.py)
- **Việc:** Tổng hợp RD + câu trả lời phỏng vấn thành mô tả **Use Case** có cấu trúc.
- **Input state:** `input`, `answers`
- **Output state:** `usecase`

### 4.3 Graph — [agents/graph/agent.py](agents/graph/agent.py)
- **Việc:** Chuyển Use Case thành **Knowledge Graph** dạng JSON (thực thể + quan hệ). Đây là bước trừu tượng hóa logic nghiệp vụ.
- **Input state:** `usecase`
- **Output state:** `graph`
- **Là điểm quay lui** khi verifier báo `LOGIC`.

### 4.4 SRS — [agents/srs/agent.py](agents/srs/agent.py)
- **Việc:** Từ graph JSON, sinh tài liệu SRS hoàn chỉnh (functional, non-functional, flows, …). Có truy hồi lessons từ `VectorMemory` để học từ lần chạy trước.
- **Input state:** `graph` (+ lessons)
- **Output state:** `srs`

### 4.5 Verification — [agents/verification/agent.py](agents/verification/agent.py)
- **Việc:** Chấm điểm SRS, phân loại lỗi. LLM được yêu cầu trả về `Score` và `IssueType`; agent parse 2 giá trị này. Đồng thời bump `iterations`.
- **Input state:** `srs`
- **Output state:** `qa`, `score`, `issue_type`, `iterations`
- **Gatekeeper** của toàn workflow — quyết định end hay loop back.

### 4.6 Refine — [agents/refine/agent.py](agents/refine/agent.py)
- **Việc:** Viết lại SRS dựa vào feedback trong `qa`. Dùng cho lỗi nhẹ (CONSISTENCY) mà không cần đi lại từ graph. Sử dụng **MCP Tools** để chỉnh sửa SRS.
- **Input state:** `srs`, `qa`
- **Output state:** `srs` (ghi đè)

### 4.7 Diagram — [agents/diagram/agent.py](agents/diagram/agent.py)
- **Việc:** Đọc SRS đã verified, sinh ra 3 nhóm biểu đồ (State Machines / Business Flows / System Sequences) ở định dạng **Mermaid** (`.mmd`) và **drawio** (`.drawio`). Mermaid blocks được embed vào `workspace/current_srs.md` ở Appendix F.
- **Input state:** `srs`, `srs_path`
- **Output state:** `diagram_paths` (list các file đã ghi), `diagram_coverage` (báo cáo coverage)
- **Output disk:**
  - `workspace/diagrams/state_machines.mmd` + `workspace/diagrams/state_machines/*.drawio`
  - `workspace/diagrams/flows.mmd` + `workspace/diagrams/flows/*.drawio`
  - `workspace/diagrams/sequences.mmd` + `workspace/diagrams/sequences/*.drawio`
  - `workspace/diagrams/coverage.json`

### 4.8 Memorize — [agents/memorize/agent.py](agents/memorize/agent.py)
- **Việc:** Đọc toàn bộ trạng thái và ghi các bài học/kinh nghiệm (lesson learned) vào VectorMemory (FAISS) để tận dụng cho các lần chạy sau.
- **Input state:** Toàn bộ `AgentState`.
- **Output:** Ghi xuống file `memory.json`.

---

## 5. State Schema

Định nghĩa tại [core/state.py](core/state.py). Trạng thái được **merge dần** qua từng node:

| Field | Tạo bởi | Ý nghĩa |
|---|---|---|
| `input` | main.py (từ input.md) | RD thô |
| `answers` | interview | Câu trả lời của user (hoặc auto-generated) |
| `usecase` | struct | Use case có cấu trúc |
| `graph` | graph | Knowledge graph JSON |
| `srs` | srs / refine | Tài liệu SRS |
| `qa` | verify | Nhận xét chất lượng của verifier |
| `score` | verify | Điểm chất lượng (0–10) |
| `issue_type` | verify | `LOGIC` / `MISSING` / `CONSISTENCY` / … |
| `iterations` | verify | Số vòng verify đã chạy (dùng cho loop cap) |

---

## 6. Memory, LLM & Tooling

### Vector Memory — [core/memory.py](core/memory.py)
- Embedding: `sentence-transformers/all-MiniLM-L6-v2` (384 chiều).
- Index: `faiss.IndexFlatL2`.
- Persist: JSON (`memory.json`) — chỉ lưu **text**, không lưu vector (rebuild khi load).
- Dùng ở: **interview** (tìm bài học khi đặt câu hỏi), **srs** (tham khảo khi viết).

### LLM Layer — [core/llm.py](core/llm.py)
- **Anthropic official SDK** (`anthropic.Anthropic`) — không dùng raw HTTP nữa.
- **Model:** `claude-opus-4-7` (biến `MODEL`).
- **Prompt caching:** system prompt được đánh dấu `cache_control: {"type": "ephemeral"}` để Anthropic cache prefix; chỉ bill phần user message thay đổi. Telemetry in `cache_read` / `cache_write` sau mỗi call.
- **Lưu ý:** để cache thực sự hit, system prompt phải ≥ 4096 tokens. Các SYSTEM hiện tại < 100 tokens nên `cache_read` sẽ là 0 cho đến khi SKILLS.md được mở rộng.
- `load_skill(path)` đọc prompt từ file `.md`.
- API key từ env var `ANTHROPIC_API_KEY` (nạp qua `.env` trong `main.py`).

### MCP Server (Model Context Protocol) — [core/mcp_server.py](core/mcp_server.py)
- **Công nghệ:** Sử dụng package `mcp` (`FastMCP`) để cung cấp các Filesystem Tools an toàn cho LLM.
- **Vai trò:** Tối ưu hóa Context Window Token. Thay vì đưa toàn bộ file SRS dài hàng nghìn dòng vào prompt (gây tốn kém và dễ lặp vô hạn), hệ thống lưu SRS vật lý xuống đĩa (`workspace/current_srs.md`) và cấp cho LLM các công cụ "phẫu thuật" (Surgical Patching):
  - `list_srs_sections()`: Xem mục lục cấu trúc file.
  - `get_srs_section(header)`: Lấy chi tiết nội dung của một mục.
  - `update_srs_section(header, new_content)`: Cập nhật riêng rẽ từng phần.
- **Hoạt động:** Hàm `call_llm_with_mcp()` sẽ spawn server qua giao thức Stdio (Standard I/O). Khi `refine` agent nhận được phản hồi lỗi `qa`, nó tự động dùng MCP tool để xem và sửa đúng chỗ bị lỗi.
