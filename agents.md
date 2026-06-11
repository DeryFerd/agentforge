# AgentForge — Agent Behavior & Execution Model

> **Version:** 1.0
> **Status:** Draft
> **Last Updated:** June 2026

---

## 1. Overview: What Are Agents in AgentForge?

In AgentForge, **agents** are the fundamental execution units. Each agent is a specialized, configurable AI component that performs a specific task within a workflow. Agents are not standalone processes — they are orchestrated by the AgentForge runtime, which manages their lifecycle, context, tool access, and communication.

Agents in AgentForge are:
- **Configurable** — Users define system prompts, model selection, tool bindings, and output schemas via the visual editor
- **Stateless by default** — Each invocation receives fresh context from the workflow state; agents don't retain memory between runs unless explicitly configured
- **Bounded** — Each agent can only call tools explicitly assigned to it; no agent can access the platform's internal systems
- **Observable** — Every LLM call, tool invocation, and decision is traced and logged

---

## 2. Node Types & Agent Behaviors

### 2.1 Agent Node

The primary node type. Wraps an LLM call with configurable behavior.

**Configuration:**
```yaml
agent_node:
  name: "Summarizer"
  description: "Summarizes customer feedback into key themes"
  model:
    provider: "openai"          # openai | anthropic | google
    model_id: "gpt-4o"          # specific model
    temperature: 0.3
    max_tokens: 2000
  system_prompt: |
    You are a customer feedback analyst. Summarize the provided
    feedback into 3-5 key themes with sentiment indicators.
    Output must be valid JSON matching the specified schema.
  tools:                         # MCP tools available to this agent
    - server: "web-search"
      tool: "search"
    - server: "database"
      tool: "query"
  output_schema:                 # Expected output structure
    type: object
    properties:
      themes:
        type: array
        items:
          type: object
          properties:
            theme: { type: string }
            sentiment: { type: string, enum: [positive, negative, neutral] }
            evidence: { type: string }
      summary: { type: string }
  timeout_seconds: 60
  retry_policy:
    max_retries: 2
    backoff: exponential
    retryable_errors: ["rate_limit", "timeout", "service_unavailable"]
```

**Execution Behavior:**
1. **Context Assembly:** The runtime constructs the LLM context:
   - System prompt (from config)
   - Workflow global context (filtered to relevant fields only)
   - Upstream node outputs (from connected edges in the DAG)
   - Available tool descriptions (from MCP registry)
2. **LLM Call:** Sends the assembled context to the configured model
3. **Tool Loop:** If the LLM requests a tool call:
   - Validate the tool is in the agent's allowed list
   - Execute the tool via MCP client
   - Feed the result back to the LLM
   - Repeat until the LLM produces a final answer (no more tool calls)
4. **Output Validation:** Parse the final response against the output schema
   - If valid → emit success event with structured output
   - If invalid → retry (up to max_retries) or emit failure
5. **Telemetry:** Record tokens used, latency, cost, and full trace

**Anti-Hallucination Measures:**
- System prompt always includes: "Only use information provided in the context. If insufficient, say so explicitly."
- Output schema enforcement prevents free-form hallucination
- Evaluator nodes downstream can cross-check agent outputs

---

### 2.2 Tool Node

Calls an external tool directly (no LLM reasoning involved).

**Configuration:**
```yaml
tool_node:
  name: "Fetch User Data"
  description: "Retrieves user profile from database"
  tool:
    server: "database"
    tool: "query"
  input_mapping:                 # Map workflow state to tool parameters
    sql: "SELECT * FROM users WHERE id = {{workflow.input.user_id}}"
    database: "production"
  output_mapping:                # Map tool result to workflow state
    user_data: "{{result.rows[0]}}"
  timeout_seconds: 30
```

**Execution Behavior:**
1. **Input Resolution:** Resolve template variables from workflow state
2. **Validation:** Validate resolved parameters against tool's input schema
3. **Execution:** Call the MCP server's tool with resolved parameters
4. **Output Mapping:** Map the tool result into the workflow state using output_mapping
5. **Error Handling:** If tool call fails, apply retry policy or fail the node

---

### 2.3 Router Node

Conditional branching — routes execution to different downstream paths based on logic.

**Configuration:**
```yaml
router_node:
  name: "Intent Router"
  description: "Routes based on customer intent"
  routing_mode: "conditional"    # conditional | llm_based | parallel_fanout
  conditions:
    - name: "billing"
      expression: "{{upstream.classifier.output.intent}} == 'billing'"
      target: "billing_agent"
    - name: "technical"
      expression: "{{upstream.classifier.output.intent}} == 'technical'"
      target: "tech_support_agent"
    - name: "default"
      expression: "true"         # fallback
      target: "general_agent"
```

**Routing Modes:**

| Mode | Behavior |
|---|---|
| **Conditional** | Evaluates expressions against upstream outputs; first match wins |
| **LLM-Based** | Sends context to an LLM that selects the branch (for ambiguous cases) |
| **Parallel Fan-Out** | Activates ALL downstream branches simultaneously; results merged at fan-in |

**Execution Behavior:**
1. Receive input from upstream node
2. Evaluate routing conditions (or call LLM for llm_based mode)
3. Select target branch(es)
4. Emit routing event (which branch was selected and why)
5. Pass input to selected downstream node(s)

---

### 2.4 Evaluator Node

Quality gate — checks if upstream agent output meets defined criteria.

**Configuration:**
```yaml
evaluator_node:
  name: "Quality Check"
  description: "Validates summary quality before delivery"
  evaluation_mode: "llm_judge"   # schema_only | llm_judge | custom_function
  criteria:
    - name: "completeness"
      description: "All key themes from input are addressed in the summary"
      weight: 0.4
    - name: "accuracy"
      description: "Summary claims are supported by the provided evidence"
      weight: 0.3
    - name: "conciseness"
      description: "Summary is under 200 words"
      weight: 0.3
  passing_threshold: 0.7         # weighted score must exceed this
  on_fail: "retry_upstream"      # retry_upstream | fail | fallback_branch
  judge_model:
    provider: "anthropic"
    model_id: "claude-sonnet-4-20250514"
```

**Evaluation Modes:**

| Mode | Behavior |
|---|---|
| **Schema Only** | Validates output matches the JSON schema (no LLM call) |
| **LLM-as-Judge** | Sends output + criteria to a separate LLM that scores quality |
| **Custom Function** | Runs user-defined Python validation logic |

**Execution Behavior:**
1. Receive the output from the upstream node being evaluated
2. Run evaluation based on mode:
   - Schema: JSON schema validation
   - LLM Judge: Construct evaluation prompt with criteria → call judge model → parse scores
   - Custom: Execute user function in sandboxed environment
3. Calculate weighted score
4. Decision:
   - Score >= threshold → pass, forward output downstream
   - Score < threshold → apply `on_fail` action:
     - `retry_upstream`: re-execute the upstream node (max N times)
     - `fail`: mark workflow as failed
     - `fallback_branch`: route to an alternative path
5. Emit evaluation event with scores, reasoning, and decision

---

### 2.5 Human-in-the-Loop (HITL) Node

Pauses execution for human review or input.

**Configuration:**
```yaml
hitl_node:
  name: "Manager Approval"
  description: "Requires manager approval before sending response"
  approval_mode: "approve_reject"   # approve_reject | provide_input | edit_output
  notification:
    channels: ["email", "slack"]
    recipients: ["manager@company.com"]
    message: "Workflow '{{workflow.name}}' requires your approval at step '{{node.name}}'"
  timeout_hours: 24
  on_timeout: "escalate"            # escalate | auto_approve | auto_reject
  escalation_recipients: ["director@company.com"]
  display:                           # What to show the reviewer
    show: ["upstream.agent.output", "workflow.input", "cost_so_far"]
    actions:
      - label: "Approve"
        value: "approved"
      - label: "Reject with Feedback"
        value: "rejected"
        requires_input: true         # reviewer must provide reason
```

**Approval Modes:**

| Mode | Behavior |
|---|---|
| **Approve/Reject** | Binary decision; rejection can trigger retry or fail |
| **Provide Input** | Human provides data that replaces or augments the workflow state |
| **Edit Output** | Human can modify the upstream agent's output before it continues |

**Execution Behavior:**
1. Workflow execution pauses at this node
2. Node emits `execution_paused` event with review payload
3. Notification sent to configured recipients (email, Slack, webhook)
4. Dashboard shows "Awaiting Approval" status with review interface
5. Reviewer takes action via:
   - Web UI (click approve/reject, optionally provide feedback)
   - API endpoint (`POST /executions/{run_id}/nodes/{node_id}/respond`)
6. On response:
   - Approved → resume execution from next node
   - Rejected → apply configured action (retry, fail, reroute)
   - Timeout → apply timeout action (escalate, auto-approve, auto-reject)
7. Emit `execution_resumed` event with human's decision and any input

---

### 2.6 Input / Output Nodes

Define the workflow's interface with the outside world.

**Input Node:**
```yaml
input_node:
  name: "Workflow Input"
  schema:
    type: object
    required: ["query", "user_id"]
    properties:
      query: { type: string, description: "User's question" }
      user_id: { type: string, description: "Authenticated user ID" }
      context: { type: object, description: "Optional additional context" }
```

**Output Node:**
```yaml
output_node:
  name: "Workflow Output"
  mapping:
    response: "{{upstream.summarizer.output.summary}}"
    metadata:
      sources_used: "{{upstream.researcher.output.sources}}"
      confidence: "{{upstream.evaluator.output.score}}"
      cost_usd: "{{execution.cost_usd}}"
```

---

## 3. Workflow Execution Model

### 3.1 Compilation Phase

When a user clicks "Run" (or API trigger fires):

```
1. Load workflow DAG JSON from database
2. Validate DAG structure:
   - No cycles (must be a valid DAG)
   - All nodes connected (no orphaned nodes)
   - All required node configurations present
   - Edge source/target node IDs valid
   - Input/output schema compatibility across connected nodes
3. Compile to LangGraph StateGraph:
   - Define WorkflowState schema (union of all node outputs + global context)
   - Register each node as a LangGraph node function
   - Register edges (conditional edges for Router nodes, fan-out for parallel)
   - Set entry point (Input node) and exit point (Output node)
4. Produce compiled graph (CompiledGraph)
5. Create execution record in database (status: "queued")
6. Enqueue execution job to Redis
```

### 3.2 Execution Phase

```
Worker picks up job from Redis queue:

1. Load compiled graph + execution record
2. Initialize WorkflowState with input data
3. Begin graph execution:

   FOR each node in execution order:
     a. Emit "node_started" event (WebSocket → frontend)
     b. Assemble node input:
        - Collect outputs from upstream nodes (following edges)
        - Apply input_mapping transformations
     c. Execute node (based on type — see Section 2)
     d. Store node output in WorkflowState
     e. Record execution_node in database (status, I/O, tokens, cost)
     f. Emit "node_completed" or "node_failed" event
     g. If HITL node → emit "execution_paused", wait for response
     h. If Router node → determine next node(s) based on routing logic
     i. If parallel branches → fan-out execution, wait for all to complete

4. Collect final outputs from Output node
5. Update execution record (status: "completed" or "failed")
6. Emit "execution_completed" event
7. Persist final state to PostgreSQL (checkpoint)
```

### 3.3 Execution Modes

| Mode | Description | Use Case |
|---|---|---|
| **Full Run** | Execute entire workflow from Input to Output | Normal operation |
| **Step Mode** | Execute one node at a time, pausing between each | Debugging |
| **Resume** | Continue from a paused HITL node | After human approval |
| **Partial Retry** | Re-execute from a specific node using checkpointed state | After fixing a failed node |
| **Dry Run** | Validate workflow structure without executing any nodes | Pre-deployment check |

### 3.4 State Management

**State Flow:**
```
Input Node → produces initial state
  → Agent Node A → appends output_a to state
    → Agent Node B → appends output_b to state
      → Router Node → reads state, selects branch
        → Agent Node C (branch 1) → appends output_c
        → Tool Node D (branch 2) → appends output_d
          → Evaluator Node → reads state, scores output
            → Output Node → reads state, maps to final output
```

**State Isolation:**
- Each execution run has its own isolated state
- Nodes can only read outputs from their direct upstream connections (not all nodes)
- Global context is a shared namespace for cross-cutting data (e.g., user_id, session info)

**Checkpointing:**
- LangGraph automatically checkpoints after each node execution
- Checkpoints stored in PostgreSQL
- Enables: crash recovery, partial retry, execution replay

---

## 4. Agent Communication Patterns

### 4.1 Sequential Pipeline (Default)

```
Agent A → Agent B → Agent C → Output
```
- Agent B receives Agent A's output as input
- Each agent runs only after its upstream completes
- Best for: linear processing chains (extract → analyze → summarize)

### 4.2 Parallel Fan-Out / Fan-In

```
         ┌→ Agent B ─┐
Agent A →├→ Agent C ─┤→ Agent E (merger)
         └→ Agent D ─┘
```
- Router node triggers parallel execution of B, C, D
- All three run concurrently
- Agent E waits for all three to complete, then merges results
- Best for: independent analyses that need to be combined

### 4.3 Hierarchical (Planner + Workers)

```
Planner Agent → [Worker 1, Worker 2, Worker 3] → Synthesizer Agent
```
- Planner agent receives the task and decides how to decompose it
- Dynamically creates worker assignments (not static in the DAG)
- Workers execute their assignments
- Synthesizer combines worker outputs
- Best for: complex, open-ended tasks where decomposition isn't known upfront

**Implementation in AgentForge:**
- Planner is an Agent Node with a special "decompose" tool
- The tool dynamically adds worker nodes to the execution graph
- This is the most advanced pattern, available via the "Dynamic Planner" template

### 4.4 Competitive (Generate + Evaluate)

```
         ┌→ Agent B (approach 1) ─┐
Agent A →├→ Agent C (approach 2) ─┤→ Evaluator → Output
         └→ Agent D (approach 3) ─┘
```
- Multiple agents independently solve the same problem
- Evaluator picks the best result (or combines the best elements)
- Best for: code generation, creative writing, optimization tasks

### 4.5 Feedback Loop (Retry with Refinement)

```
Agent A → Evaluator → (fail) → Agent A (with feedback) → Evaluator → (pass) → Output
```
- Agent A produces output
- Evaluator checks quality; if insufficient, sends feedback back
- Agent A re-runs with feedback appended to context
- Loop continues until quality threshold met or max iterations reached
- Best for: tasks requiring iterative refinement

---

## 5. Agent Template System

### 5.1 Template Structure

Each template is a self-contained package:

```yaml
# template.yaml
name: "customer-feedback-analyzer"
version: "1.2.0"
description: "Analyzes customer feedback and extracts actionable themes"
author: "agentforge-community"
license: "MIT"
category: "analysis"
tags: ["nlp", "sentiment", "feedback"]

agent_config:
  model:
    provider: "openai"
    model_id: "gpt-4o-mini"       # cost-efficient default
    temperature: 0.2
  system_prompt: |
    You are a customer feedback analyst. Your task is to:
    1. Identify recurring themes in the feedback
    2. Classify sentiment for each theme (positive/negative/neutral)
    3. Extract specific quotes as evidence
    4. Prioritize themes by frequency and severity

    Output JSON matching the specified schema.
    Only use information provided in the feedback.
  tools:
    - server: "web-search"        # optional, user can disable
      tool: "search"
      required: false

input_schema:
  type: object
  required: ["feedback_text"]
  properties:
    feedback_text: { type: string }
    source: { type: string }
    date_range: { type: string }

output_schema:
  type: object
  properties:
    themes:
      type: array
      items:
        type: object
        properties:
          theme: { type: string }
          sentiment: { type: string }
          evidence: { type: array, items: { type: string } }
          priority: { type: string, enum: [high, medium, low] }
    executive_summary: { type: string }
    total_feedback_analyzed: { type: integer }

customizable_params:
  - path: "agent_config.model.temperature"
    label: "Creativity Level"
    type: "number"
    min: 0
    max: 1
    default: 0.2
  - path: "agent_config.model.model_id"
    label: "Model"
    type: "select"
    options: ["gpt-4o", "gpt-4o-mini", "claude-sonnet-4-20250514"]
    default: "gpt-4o-mini"
```

### 5.2 Template Lifecycle

```
Draft → Submitted → Under Review → Published → Deprecated
```

| Stage | Description |
|---|---|
| **Draft** | User is configuring the template locally |
| **Submitted** | User submits to the registry for review |
| **Under Review** | Automated tests run (schema validation, execution test, security scan) |
| **Published** | Template available in marketplace for all users |
| **Deprecated** | Template superseded by newer version; still usable but hidden from search |

### 5.3 Built-in Templates (MVP)

| Template | Description | Category |
|---|---|---|
| `text-summarizer` | Summarizes long text into key points | General |
| `intent-classifier` | Classifies user intent from text input | Classification |
| `data-extractor` | Extracts structured data from unstructured text | Extraction |
| `translator` | Translates text between languages | General |
| `sentiment-analyzer` | Analyzes sentiment with confidence scores | Analysis |
| `code-generator` | Generates code from natural language descriptions | Development |
| `content-writer` | Generates blog posts, emails, or social media content | Content |
| `qa-answerer` | Answers questions based on provided context (RAG) | Q&A |
| `router-basic` | Routes input based on keyword matching | Routing |
| `json-validator` | Validates and fixes JSON output from other agents | Quality |

---

## 6. MCP Tool Integration

### 6.1 How Tools Work

Agents call external tools through the **Model Context Protocol (MCP)**. The flow:

```
Agent needs data → LLM decides to call tool
  → Node Executor intercepts tool call
  → Looks up MCP server in registry
  → Establishes MCP connection (stdio or SSE transport)
  → Calls tool with LLM-provided parameters
  → Receives structured result
  → Feeds result back to LLM as tool output
  → LLM continues reasoning with new data
```

### 6.2 MCP Server Registration

Users register MCP servers through the UI or API:

```json
{
  "name": "PostgreSQL Production",
  "transport": "stdio",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-postgres", "postgresql://..."],
  "capabilities": ["query", "list_tables", "describe_table"],
  "auth": {
    "type": "connection_string",
    "encrypted": true
  }
}
```

### 6.3 Tool Permissions

Each Agent Node has an **allowlist** of tools it can use:
- Configured at design time in the visual editor
- Enforced at runtime by the Node Executor
- If an agent tries to call an unlisted tool → execution fails with permission error
- This implements the **Principle of Least Privilege** for agent capabilities

---

## 7. Cost Model

### 7.1 Cost Calculation

Every agent node execution calculates cost:

```python
cost_usd = (tokens_input * model_price_per_input_token) +
           (tokens_output * model_price_per_output_token)
```

Model pricing is stored in a pricing table (updated regularly):

| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|---|---|---|
| gpt-4o | $2.50 | $10.00 |
| gpt-4o-mini | $0.15 | $0.60 |
| claude-sonnet-4-20250514 | $3.00 | $15.00 |
| gemini-2.0-flash | $0.10 | $0.40 |

### 7.2 Budget Controls

- **Per-run budget:** Maximum cost for a single workflow execution
- **Per-workflow budget:** Monthly spend limit for a workflow
- **Per-workspace budget:** Monthly spend limit for an entire workspace
- **Actions on budget breach:** Alert (email/Slack), pause execution, or block new runs

### 7.3 Cost Optimization Strategies (Built-In)

| Strategy | Description |
|---|---|
| **Model Routing** | Use cheaper models for simple tasks (classification, extraction), expensive for complex reasoning |
| **Context Trimming** | Only pass relevant state to each agent, not the entire workflow context |
| **Output Caching** | Cache identical tool call results within the same execution |
| **Token Budgets** | Set max_tokens per node to prevent runaway generation |

---

## 8. Error Handling & Recovery

### 8.1 Error Categories

| Category | Examples | Default Behavior |
|---|---|---|
| **Transient** | Rate limit, timeout, service unavailable | Retry with exponential backoff |
| **Validation** | Output doesn't match schema, invalid tool params | Retry with error feedback to LLM |
| **Permission** | Tool not in allowlist, RBAC violation | Fail node immediately, no retry |
| **Resource** | Budget exceeded, token limit hit | Pause workflow, notify owner |
| **Fatal** | Workflow config corrupted, LLM provider down | Fail workflow, alert admin |

### 8.2 Recovery Mechanisms

```
Node fails
  → Check retry policy
    → Retries remaining? → Yes → Wait (backoff) → Retry
                        → No → Check on_fail action
                          → retry_upstream → Re-run upstream node
                          → fallback_branch → Route to alternative path
                          → fail → Mark workflow as failed
                          → escalate → Notify + pause for human intervention
```

### 8.3 Execution Replay

Users can replay any past execution:
- Load checkpointed state from PostgreSQL
- Visualize the exact execution path taken
- Inspect input/output of every node
- "Fork" from any node: modify configuration and re-execute from that point
- Useful for debugging, auditing, and iterative improvement of workflows

---

## 9. Project Execution: How AgentForge Runs End-to-End

### From User Perspective:
```
1. User installs AgentForge: docker compose up
2. Opens browser → localhost:3000
3. Creates account → enters dashboard
4. Clicks "New Workflow" → DAG editor opens
5. Drags nodes onto canvas, configures each one
6. Connects nodes with edges
7. Clicks "Validate" → system checks for errors
8. Clicks "Run" → enters execution input data
9. Watches execution animate on the DAG canvas in real-time
10. Views results: output data, cost breakdown, execution timeline
11. Shares workflow API endpoint for programmatic access
```

### From System Perspective:
```
1. Frontend sends workflow DAG JSON + input data to API
2. API validates DAG, compiles to LangGraph StateGraph
3. Execution enqueued to Redis
4. Worker picks up job, initializes state, begins execution
5. Each node executes (LLM calls, tool calls, routing, evaluation)
6. Events emitted to Redis pub/sub → WebSocket relay → Frontend
7. State checkpointed to PostgreSQL after each node
8. Final output computed, execution record updated
9. Cost aggregated, telemetry exported to Langfuse
10. Result returned to API caller (sync) or available via execution endpoint
```
