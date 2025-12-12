# Prospecting Agent Architecture Flow

## Complete System Flow Diagram

```mermaid
flowchart TD
    Start([User Query]) --> Orchestrator{Orchestrator}

    Orchestrator --> |Step 1| Planner[Planner Agent<br/>Sonnet 4.5 + Extended Thinking]

    Planner --> |Creates| Plan[Execution Plan]

    Plan --> Clarify{Needs<br/>Clarification?}

    Clarify -->|Yes| ClarifyReturn[Return Clarification Request<br/>to User]
    ClarifyReturn --> End1([Wait for User Response])

    Clarify -->|No| ApprovalLoop[Approval Loop Start]

    ApprovalLoop --> Summarizer[Summarizer Agent<br/>Haiku 4.5]

    Summarizer --> |Generates| Summary[Human-Friendly Summary]

    Summary --> UserApproval{User Approval<br/>Decision}

    UserApproval -->|Approved| Execute[Execute Plan]
    UserApproval -->|Rejected| End2([Workflow Terminated])
    UserApproval -->|Needs Revision| Revise[Planner.revise_plan]

    Revise --> |Creates new plan| Summary

    Execute --> Executor[Executor Agent<br/>Haiku 4.5]

    Executor --> |For each step| Tools[Data Source Tools]

    Tools --> Orbis[(Orbis API)]
    Tools --> Crunchbase[(Crunchbase API)]
    Tools --> PitchBook[(PitchBook API)]
    Tools --> CompaniesHouse[(Companies House API)]
    Tools --> WealthX[(Wealth-X API)]
    Tools --> WealthMonitor[(Wealth Monitor API)]
    Tools --> DNB[(D&B API)]
    Tools --> SerpAPI[(SerpAPI)]
    Tools --> CRM[(Internal CRM)]

    Orbis --> Results[Aggregated Results]
    Crunchbase --> Results
    PitchBook --> Results
    CompaniesHouse --> Results
    WealthX --> Results
    WealthMonitor --> Results
    DNB --> Results
    SerpAPI --> Results
    CRM --> Results

    Results --> Future1[Sufficiency Checker<br/>Sonnet 4.5 + Extended Thinking<br/>FUTURE]

    Future1 --> Check{Results<br/>Sufficient?}

    Check -->|Yes| Reporter[Report Generator<br/>Sonnet 4.5<br/>FUTURE]
    Check -->|No - Need Clarification| ClarifyReturn
    Check -->|No - Retry Needed| Execute

    Reporter --> FinalReport[Final Markdown Report]
    FinalReport --> End3([Return to User])

    style Orchestrator fill:#e1f5ff,stroke:#333,stroke-width:3px
    style Planner fill:#fff4e6,stroke:#333,stroke-width:2px
    style Summarizer fill:#fff4e6,stroke:#333,stroke-width:2px
    style Executor fill:#fff4e6,stroke:#333,stroke-width:2px
    style Future1 fill:#f0f0f0,stroke:#999,stroke-width:2px,stroke-dasharray: 5 5
    style Reporter fill:#f0f0f0,stroke:#999,stroke-width:2px,stroke-dasharray: 5 5
    style ApprovalLoop fill:#e8f5e9,stroke:#333,stroke-width:2px
    style UserApproval fill:#fff9c4,stroke:#333,stroke-width:3px
    style Tools fill:#fce4ec,stroke:#333,stroke-width:2px
    style Results fill:#e3f2fd,stroke:#333,stroke-width:2px
```

## Component Breakdown

### 1. Entry Point
- **User Query**: Natural language prospecting question
- **Orchestrator**: Main coordinator that manages the entire workflow

### 2. Planning Phase (Planner Agent)
- **Model**: Claude Sonnet 4.5 with Extended Thinking
- **Input**: User query
- **Output**: Structured ExecutionPlan with steps, data sources, parameters
- **Clarification**: If query is ambiguous, returns clarification questions

### 3. Approval Loop ⟲
This is a **critical iterative loop** that ensures user control:

1. **Summarizer Agent** converts technical plan to human-friendly summary
2. **User Decision** has 3 options:
   - ✅ **Approved** → Proceed to execution
   - ❌ **Rejected** → Terminate workflow
   - 🔄 **Needs Revision** → Loop back to Planner for revision

The loop continues until approval or rejection.

### 4. Execution Phase (Executor Agent)
- **Model**: Claude Haiku 4.5 (fast, cost-efficient)
- **Process**: Executes plan steps sequentially
- **Tools**: Calls various data source APIs based on plan
- **Output**: AggregatedResults with all data

### 5. Data Source Tools Layer
Nine different APIs that can be queried:
- **Orbis**: Corporate structures, financials, directors
- **Crunchbase**: Funding rounds, startups
- **PitchBook**: PE/VC deals, valuations
- **Companies House**: UK company filings, PSCs
- **Wealth-X**: UHNW profiles, wealth data
- **Wealth Monitor**: UK-specific wealth data
- **D&B**: Credit risk, firmographics
- **SerpAPI**: News and web search
- **Internal CRM**: Client exclusion check

### 6. Future Components (Not Yet Implemented)

#### Sufficiency Checker
- **Model**: Claude Sonnet 4.5 with Extended Thinking
- **Purpose**: Evaluate if results answer the original query
- **Outputs**:
  - ✅ **Sufficient** → Generate report
  - 🔄 **Retry Needed** → Re-execute with different parameters
  - ❓ **Clarification Needed** → Ask user for more details

#### Report Generator
- **Model**: Claude Sonnet 4.5
- **Purpose**: Create formatted markdown report
- **Output**: Professional prospect dossier

## Key Architectural Patterns

### 1. Human-in-the-Loop
The approval loop ensures users:
- Understand what data will be queried
- Can modify the approach before execution
- Maintain control over expensive API calls

### 2. Agent Specialization
Different models for different tasks:
- **Sonnet 4.5** (reasoning-heavy): Planning, sufficiency checking, reporting
- **Haiku 4.5** (fast execution): Summarizing, executing API calls

### 3. Iterative Refinement
Multiple feedback loops:
- **Planning Loop**: Clarification if query unclear
- **Approval Loop**: User can request plan revisions
- **Execution Loop**: (Future) Retry if results insufficient

### 4. Separation of Concerns
Each agent has a single responsibility:
- Planner → Strategy
- Summarizer → Communication
- Executor → Execution
- Sufficiency → Quality control
- Reporter → Presentation

## Data Flow Example

**Query**: "Find UK tech companies that raised Series B in last 12 months"

```
1. User Query
   ↓
2. Planner Agent
   → Creates plan: [Crunchbase search] → [PitchBook cross-ref] → [Companies House directors] → [CRM check]
   ↓
3. Approval Loop
   → Summarizer: "I'll search Crunchbase for Series B rounds in UK (last 12mo), verify with PitchBook..."
   → User: "Approved ✅"
   ↓
4. Executor Agent
   → Step 1: Crunchbase API (found 23 companies)
   → Step 2: PitchBook API (cross-referenced, found 18 matches)
   → Step 3: Companies House (got directors for 18 companies)
   → Step 4: CRM (excluded 2 existing clients)
   ↓
5. Sufficiency Checker (Future)
   → Evaluates: 16 unique prospects with funding + director data
   → Decision: SUFFICIENT ✅
   ↓
6. Report Generator (Future)
   → Creates markdown report with prospect profiles
   ↓
7. Return to User
```

## Current Implementation Status

| Component | Status | Model |
|-----------|--------|-------|
| Orchestrator | ✅ Implemented | N/A |
| Planner Agent | ✅ Implemented | Sonnet 4.5 + Extended Thinking |
| Summarizer Agent | ✅ Implemented | Haiku 4.5 |
| Executor Agent | ✅ Implemented | Haiku 4.5 |
| Data Source Tools | ✅ Implemented (mocked) | N/A |
| Approval Handler | ✅ Implemented | N/A |
| Sufficiency Checker | ⏳ TODO | Sonnet 4.5 + Extended Thinking |
| Report Generator | ⏳ TODO | Sonnet 4.5 |

## Loop Details

### Approval Loop Detailed Flow

```mermaid
sequenceDiagram
    participant User
    participant Orchestrator
    participant Planner
    participant Summarizer
    participant ApprovalHandler

    User->>Orchestrator: Submit Query
    Orchestrator->>Planner: create_plan(query)
    Planner->>Orchestrator: ExecutionPlan

    loop Approval Loop (until approved/rejected)
        Orchestrator->>Summarizer: summarize_plan(plan, query)
        Summarizer->>Orchestrator: Human-friendly summary
        Orchestrator->>ApprovalHandler: request_approval(summary)
        ApprovalHandler->>User: Show summary + request decision
        User->>ApprovalHandler: Decision (approve/reject/revise)

        alt User Approves
            ApprovalHandler->>Orchestrator: APPROVED
            Orchestrator->>Orchestrator: Exit loop
        else User Rejects
            ApprovalHandler->>Orchestrator: REJECTED
            Orchestrator->>User: WorkflowRejectedError
        else User Requests Revision
            ApprovalHandler->>Orchestrator: NEEDS_REVISION + feedback
            Orchestrator->>Planner: revise_plan(plan, feedback, query)
            Planner->>Orchestrator: Revised ExecutionPlan
            Note over Orchestrator: Loop continues with revised plan
        end
    end

    Orchestrator->>User: Proceed to execution
```

### Execution Loop (Per-Step)

```mermaid
sequenceDiagram
    participant Executor
    participant Tool
    participant API
    participant Results

    loop For each step in plan
        Executor->>Tool: Execute step with params
        Tool->>API: API request

        alt API Success
            API->>Tool: Data
            Tool->>Results: Add SearchResult (success=true)
        else API Failure
            API->>Tool: Error
            Tool->>Results: Add SearchResult (success=false, error)
        end

        Note over Executor: Continue to next step
    end

    Executor->>Results: Return AggregatedResults
```

## Configuration Points

Key settings in [config.py](src/config.py):

```python
# Model selection
planner_model: str = "eu.anthropic.claude-sonnet-4-5-20250514-v1:0"
executor_model: str = "eu.anthropic.claude-haiku-4-5-20250514-v1:0"

# Extended thinking (for Planner)
enable_extended_thinking: bool = True
thinking_budget_tokens: int = 10000

# Execution
mock_apis: bool = True  # Use mocks vs real APIs
api_timeout_seconds: int = 30
max_retries: int = 2
```
