# Prospecting Agent - Conversation Flow Architecture

This document describes the enhanced conversation flow integration with the ProspectingSession class and improved CLI experience.

## Architecture Overview

The prospecting system uses a multi-layer architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────────┐
│                       USER (CLI)                                │
│  - Interactive query loop                                       │
│  - Session commands (history, summary)                           │
│  - Clarification responses                                       │
└─────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│               PROSPECTING SESSION (session.py)                  │
│  - Maintains conversation state                                 │
│  - Tracks query history and results                             │
│  - Manages clarification flow                                   │
│  - Accumulates session statistics                               │
└─────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│              PROSPECTING ORCHESTRATOR                           │
│  1. Planner Agent (analyzes query, creates plan)                │
│  2. Approval Handler (gets user approval)                       │
│  3. Executor Agent (executes plan)                              │
│  4. Sufficiency Checker (validates results)                     │
│  5. Reporter Agent (generates report)                           │
└─────────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│                    DATA SOURCES                                 │
│  - Orbis, Companies House, Crunchbase, etc.                     │
│  - (Using mock responses for testing)                           │
└─────────────────────────────────────────────────────────────────┘
```

## Key Components

### 1. ProspectingSession (`src/session.py`)

The main session manager that coordinates a multi-query conversation.

**Responsibilities:**
- Maintain conversation state across multiple queries
- Track query history with full workflow details
- Accumulate statistics across the session
- Handle clarification flow
- Store current results for reference

**Key Methods:**
```python
# Main workflow
await session.process_query(user_query: str) -> Dict[str, Any]

# Clarification handling
await session.clarify_and_retry(response: str) -> Dict[str, Any]

# State inspection
session.get_session_summary() -> Dict[str, Any]
session.get_query_history() -> List[Dict[str, Any]]
```

**QueryHistory Model:**
```python
@dataclass
class QueryHistory:
    query: str                          # The user's query
    timestamp: datetime                 # When query was made
    plan: Optional[Dict]                # Planner's execution plan
    execution_results: Optional[Dict]   # Data from executor
    sufficiency_result: Optional[Dict]  # Sufficiency evaluation
    report: Optional[str]               # Generated report
    clarifications: List[Dict]          # Clarification Q&A history
    status: str                         # Workflow status
```

### 2. CLIFormatter (`src/session.py`)

Provides color-formatted output with consistent styling for the CLI.

**Features:**
- ANSI color codes (green for success, red for errors, etc.)
- Structured headers, sections, and status indicators
- Progress indicators for multi-step operations
- Complete result formatting

**Usage:**
```python
print(CLIFormatter.header("TITLE"))           # Cyan boxed header
print(CLIFormatter.section("Section"))        # Blue section title
print(CLIFormatter.success("Operation OK"))   # Green checkmark
print(CLIFormatter.error("Failed"))           # Red X
print(CLIFormatter.warning("Caution"))        # Yellow warning
print(CLIFormatter.info("FYI"))               # Cyan info
```

### 3. CLIApprovalHandler (`src/cli.py`)

Interactive CLI-based approval handler for plan review.

**Workflow:**
1. Displays plan reasoning and steps
2. Shows estimated data sources and planner confidence
3. Prompts user for approval decision
4. Handles revisions with feedback collection

## Conversation Flow

### Normal Query Flow

```
User enters query
    ↓
[Session.process_query()]
    ↓
[Orchestrator.run()]
    ├─→ Planner: Analyzes query → ExecutionPlan
    ├─→ Check: Does plan need clarification?
    │   ├─→ YES: Return clarification to user
    │   └─→ NO: Continue
    ├─→ Approval Handler: Show plan summary
    ├─→ Check: User approved?
    │   ├─→ REJECTED: Return to user
    │   ├─→ MODIFY: Update and repeat
    │   └─→ APPROVED: Continue
    ├─→ Executor: Run approved plan → Results
    ├─→ Sufficiency Checker: Validate results
    └─→ Check: Sufficient data?
        ├─→ SUFFICIENT: Reporter generates report
        ├─→ INSUFFICIENT: Return gaps to user
        └─→ CLARIFICATION_NEEDED: Ask user for refinement
    ↓
[Update session state]
[Return result to CLI]
```

### Clarification Flow

When the system needs more information:

```
User enters initial query
    ↓
[Planner or Sufficiency Checker needs clarification]
    ↓
[Display clarification question]
    ↓
User provides response
    ↓
[Session.clarify_and_retry()]
    ↓
[Orchestrator runs with enhanced query]
    ↓
[Return results or ask more questions]
```

## Usage Examples

### Basic Query

```
💬 Enter your query (or 'quit', 'session', 'history'):
> Find UK tech companies that raised Series B in 2024

[Processing...]

✓ Sufficient data collected

► Execution Summary
  Steps executed: 7
  ✓ 7 succeeded
  Records found: 45
  Companies: 12
  Individuals: 23
  Execution time: 8500ms
  Sources: crunchbase, pitchbook, companies_house, orbis

► Report
[Full prospecting report...]
```

### With Clarification

```
💬 Enter your query (or 'quit', 'session', 'history'):
> Find wealthy individuals in London

──────────────────────────────────────────────────────────
CLARIFICATION NEEDED
──────────────────────────────────────────────────────────

What is your minimum net worth threshold?

Options:
  1. £10 million
  2. £50 million
  3. £100 million+
  4. Any wealth level

Your choice: 2

[Processing with clarification...]

✓ Sufficient data collected
[Report...]
```

### Insufficient Results

```
💬 Enter your query:
> Find female founders in healthcare

⚠ INSUFFICIENT DATA

Reason: Limited healthcare sector data in available sources

Identified gaps:
  • Healthcare company database limited
  • Founder biographical data sparse

What would you like to do?
  1. Refine your query and try again
  2. View the partial results we gathered
  3. Go back to main menu

Choose (1-3): 1

Enter your refined query:
> Find female founders in technology sector

[Retry with refined query...]
```

### Session Commands

```
💬 Enter your query (or 'quit', 'session', 'history'):
> session

──────────────────────────────────────────────────────────
SESSION SUMMARY
──────────────────────────────────────────────────────────

Session ID: 2024-12-15T11:30:45.123456
Total queries: 3
Successful: ✓ 2
Failed: ✗ 1

Data collected:
  Records: 156
  Companies: 34
  Individuals: 67
  Total execution time: 18500ms
```

## State Management

### QueryHistory Tracking

Each query in the session maintains complete state:

```python
# Access previous query
query = session.query_history[-1]

print(f"Query: {query.query}")
print(f"Status: {query.status}")  # e.g., "sufficient", "insufficient"
print(f"Found {len(query.plan['steps'])} steps in plan")
print(f"Clarifications asked: {len(query.clarifications)}")
```

### Session Statistics

The session accumulates metrics:

```python
summary = session.get_session_summary()

# Overall metrics
print(f"Total queries: {summary['total_queries']}")
print(f"Success rate: {summary['successful_queries'] / summary['total_queries']:.0%}")

# Data metrics
print(f"Total records: {summary['total_records_found']}")
print(f"Companies found: {summary['unique_companies']}")
print(f"Individuals found: {summary['unique_individuals']}")

# Performance
print(f"Avg query time: {summary['total_execution_time_ms'] / summary['total_queries']}ms")
```

## Error Handling & Edge Cases

### 1. Empty Results

```
⚠ INSUFFICIENT DATA

Reason: No companies found matching your criteria

Identified gaps:
  • No matches in Crunchbase for specified criteria
  • Companies House search returned no results

Suggestion: Try broadening your search criteria or using different keywords
```

### 2. All Results Filtered (Existing Clients)

```
⚠ INSUFFICIENT DATA

Reason: All identified companies are existing clients

Identified gaps:
  • Found 23 matching companies, but all are current clients
  • No new prospect opportunities identified

Would you like to:
  1. View the matching companies anyway
  2. Modify your search criteria
  3. Return to main menu
```

### 3. API Failures

```
⚠ PARTIAL DATA

✓ Succeeded: 5 steps
✗ Failed: 2 steps
  - Pitchbook connection timeout
  - Crunchbase rate limit exceeded

Partial results available. You can:
  1. View the partial data collected
  2. Retry the failed steps
  3. Refine your query
```

### 4. Network Interruption

```
⚠ Interrupted

Your progress has been saved. You can:
  1. Retry the current query
  2. View previous results
  3. Start a new query
```

## CLI Output Features

### Color Coding

- **Green** (✓): Successful operations
- **Red** (✗): Failures and errors
- **Yellow** (⚠): Warnings and cautions
- **Cyan** (ℹ): Information and headers
- **Dim**: Secondary information and progress

### Progress Indicators

```
[1/5] Analyzing query...        # Initial planning
[2/5] Planning execution...     # Planner running
[3/5] Executing plan...         # Executor running
[4/5] Validating results...     # Sufficiency checking
[5/5] Generating report...      # Report generation
```

### Session Header

```
═══════════════════════════════════════════════════════════════
PROSPECTING AGENT
═══════════════════════════════════════════════════════════════
Region: eu-west-2
Extended Thinking: Enabled
Mock APIs: Enabled

Commands:
  • Type your query and press Enter to start prospecting
  • Type 'session' to see session summary
  • Type 'history' to see query history
  • Type 'quit' or 'exit' to leave
```

## Session Lifecycle

### Initialization

```python
from src.config import Settings
from src.session import ProspectingSession
from src.cli import CLIApprovalHandler

settings = Settings()
approval_handler = CLIApprovalHandler()
session = ProspectingSession(settings, approval_handler)
```

### Query Processing

```python
# Single query with full workflow
result = await session.process_query("Your prospecting query")

# Handle clarification
if result.get("status") == "clarification_needed":
    user_response = input("Please provide more information: ")
    refined_result = await session.clarify_and_retry(user_response)
```

### Session Inspection

```python
# View history anytime
history = session.get_query_history()

# Get aggregated statistics
stats = session.get_session_summary()

# Access last query results
if session.query_history:
    last_query = session.query_history[-1]
    print(f"Previous: {last_query.query}")
```

### Cleanup

```python
# Session automatically manages resources
# Just let it go out of scope or explicitly close if needed
del session
```

## Extending the Session

### Custom Clarification Logic

```python
# Override in a subclass
class CustomSession(ProspectingSession):
    async def clarify_and_retry(self, response: str):
        # Add custom processing
        enhanced_response = self._parse_response(response)
        return await super().clarify_and_retry(enhanced_response)
```

### Custom Metrics

```python
# Extend SessionStats
@dataclass
class CustomStats(SessionStats):
    average_relevance_score: float = 0.0
    user_satisfaction: float = 0.0
```

### Custom CLI Formatting

```python
# Extend CLIFormatter
class CustomFormatter(CLIFormatter):
    @staticmethod
    def header(text: str) -> str:
        # Custom styling
        return f"*** {text} ***"
```

## Performance Considerations

1. **Session Memory**: Each query stores full history. Clear old queries if sessions run long.
2. **Concurrent Sessions**: Create separate ProspectingSession instances for parallel queries.
3. **Result Caching**: `current_results` stores last result; manually cache if needed.
4. **Statistics**: Accumulated stats are in-memory; persist to database for production.

## Integration with Existing Code

The ProspectingSession is built on top of ProspectingOrchestrator, maintaining backward compatibility:

```python
# Old way (still works)
from src.orchestrator import ProspectingOrchestrator
orchestrator = ProspectingOrchestrator(settings, approval_handler)
result = await orchestrator.run(query)

# New way (recommended)
from src.session import ProspectingSession
session = ProspectingSession(settings, approval_handler)
result = await session.process_query(query)
```

## Testing

The conversation flow can be tested with:

```bash
# Run the CLI
python -m src.main

# In the CLI, test different scenarios:
# 1. Normal query
# 2. Query needing clarification
# 3. Query with insufficient results
# 4. Session commands (history, summary)
# 5. Error handling (Ctrl+C, quit)
```

## Future Enhancements

1. **Session Persistence**: Save/load session state from disk or database
2. **Follow-up Queries**: Automatically use previous context for related queries
3. **Result Deduplication**: Merge duplicate entities across queries
4. **Export Functionality**: Export session results in multiple formats
5. **Multi-user Sessions**: Support collaborative prospecting workflows
6. **Advanced Analytics**: Track success rates, common queries, performance patterns
