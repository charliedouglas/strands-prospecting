# Quick Start: Enhanced Prospecting Agent

## Running the Agent

```bash
python -m src.main
```

## What's New

### 1. Session-Based Conversation

The agent now maintains conversation state across multiple queries:

```
Query 1 → Process → Results → Store in session
Query 2 → Process → Results → Store in session
Query 3 → Use previous context if needed → Results
```

### 2. Interactive Commands

```
> session    # Show session summary and statistics
> history    # Show all queries in this session
> quit       # Exit the program
```

### 3. Enhanced Error Recovery

The agent now offers choices when things don't go as expected:

- **Insufficient Data**: Refine query, view partial results, or try again
- **Clarification Needed**: Answer follow-up questions with retry
- **API Failures**: Continue with partial results or retry

### 4. Beautiful CLI Output

Color-coded output with clear structure:

```
✓ Success messages (green)
✗ Error messages (red)
⚠ Warnings (yellow)
ℹ Information (cyan)
```

## Core Workflow

```
1. User enters prospecting query
   ↓
2. Planner analyzes and creates execution plan
   ↓
3. User approves or requests modifications
   ↓
4. Executor gathers data from multiple sources
   ↓
5. Sufficiency checker validates results
   ↓
6. Report generated or clarification requested
   ↓
7. Results stored in session
   ↓
8. User can enter next query or use commands
```

## Example Interactions

### Normal Query

```
💬 Enter your query (or 'quit', 'session', 'history'):
> Find UK tech companies with Series B funding

✓ Sufficient data collected

► Execution Summary
  Steps executed: 7
  ✓ 7 succeeded
  Companies found: 12
  Individuals found: 23
  Execution time: 8500ms

► Report
[Detailed prospecting report...]
```

### With Clarification

```
💬 Enter your query:
> Find wealthy individuals in London

❓ Clarification Needed

What is your minimum net worth threshold?

Options:
  1. £10 million
  2. £50 million
  3. £100 million+
  4. Any amount

Your choice: 2

[Processing with clarification...]

✓ Results found
```

### Insufficient Results

```
💬 Enter your query:
> Find renewable energy companies

⚠ Insufficient Data

What would you like to do?
  1. Refine your query and try again
  2. View the partial results we gathered
  3. Go back to main menu

Choose (1-3): 1

Enter your refined query:
> Find renewable energy companies with recent funding
```

### Session Summary

```
💬 Enter your query:
> session

► SESSION SUMMARY

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

## Key Features

### ✓ Multi-Query Sessions

- Process multiple related queries in one session
- Results and context preserved across queries
- Accumulate statistics across all queries

### ✓ Smart Clarification

- Agent asks for clarification when query is ambiguous
- Multiple choice options when appropriate
- Free text input for flexible responses
- Automatic retry with clarified intent

### ✓ Comprehensive State Management

- Every query tracked with full workflow history
- Clarification attempts recorded
- Execution timing tracked
- Source-by-source results available

### ✓ Helpful Error Handling

- Partial results when some APIs fail
- Options for next steps on insufficient data
- Graceful recovery from interruptions
- Descriptive error messages

### ✓ Professional CLI Output

- Color-coded status indicators
- Structured sections and summaries
- Progress indicators for long operations
- Consistent formatting throughout

## File Structure

### New Files

- **`src/session.py`**: ProspectingSession class and CLIFormatter
- **`src/cli.py`**: CLIApprovalHandler for interactive approval

### Modified Files

- **`src/main.py`**: Updated to use ProspectingSession with enhanced commands

### Documentation

- **`CONVERSATION_FLOW.md`**: Detailed architecture and examples
- **`IMPLEMENTATION_SUMMARY.md`**: Technical implementation details
- **`QUICK_START.md`**: This file

## Common Scenarios

### Scenario 1: Research a Specific Company

```
> Find everything about ACME Technologies - ownership, financials, directors

[Plan created]
[Execution]
[Results returned with full profile]

> Next query or 'quit'
```

### Scenario 2: Find Similar Companies

```
> Find UK tech companies similar to ACME Technologies

[Clarification]
> In terms of funding size, revenue, or employee count? (Funding)

[Execution]
[Results returned]

> session   # View stats
> history   # See all queries
```

### Scenario 3: Explore Individuals

```
> Find UHNWIs in London with tech wealth interests

[Execution with adequate data]
[Report generated]

> Find female tech founders in London   # Follow-up query
[Execution]
[Results]
```

## Tips & Tricks

### Use the Session Commands

```
# After several queries, check your progress
> session

# See what you've already searched
> history

# Then continue with new queries
```

### Refine Ambiguous Queries

If the agent asks for clarification, be specific:

```
BAD:  > Find investors
GOOD: > Find UK venture capital firms investing in fintech

BAD:  > Find wealthy people
GOOD: > Find individuals with £50M+ net worth in London
```

### Learn from Partial Results

If results are insufficient, view what was found:

```
> (Choose option 2: View partial results)
```

Then refine your query based on what's available.

### Use History for Context

Reference previous queries:

```
> history   # See what you searched

# Use those companies/individuals in your next query
> Find investors in the same portfolio companies
```

## Troubleshooting

### Issue: "Please enter a query"

**Solution**: Don't leave the input blank. Type a prospecting query.

### Issue: "Workflow cancelled by user"

**Solution**: You selected "reject" during plan approval. Resubmit your query.

### Issue: All results are existing clients

**Solution**:
1. View the results to see what matched
2. Refine your criteria to exclude those industries/stages
3. Try a different search angle

### Issue: Interrupted by Ctrl+C

**Solution**: Your session is still active. Type a new query or `quit`.

## Advanced Usage

### Batch Processing

To process multiple queries:

```python
from src.session import ProspectingSession
from src.cli import CLIApprovalHandler
from src.config import Settings
import asyncio

async def batch_queries():
    session = ProspectingSession(Settings(), CLIApprovalHandler())

    queries = [
        "Find Series B funded UK tech companies",
        "Find female founders in fintech",
        "Find venture capital with UK focus"
    ]

    for query in queries:
        result = await session.process_query(query)
        print(f"Status: {result['status']}")

    # View aggregated results
    summary = session.get_session_summary()
    print(f"Total companies found: {summary['unique_companies']}")

asyncio.run(batch_queries())
```

### Custom Processing

```python
from src.session import ProspectingSession

session = ProspectingSession(settings, approval_handler)
result = await session.process_query("Your query")

# Access full history
for query_entry in session.query_history:
    print(f"Query: {query_entry.query}")
    print(f"Status: {query_entry.status}")
    print(f"Records found: {len(query_entry.execution_results)}")
```

## Performance Expectations

- **First Query**: 5-15 seconds (includes model initialization)
- **Subsequent Queries**: 3-10 seconds (model reused)
- **Clarification Retry**: 2-5 seconds (same plan, focused data)
- **Report Generation**: 1-3 seconds (formatting)

## What's Happening Under the Hood

1. **Planner Agent** (Claude Sonnet 4.5 + Extended Thinking)
   - Analyzes your query
   - Determines which data sources to use
   - Creates structured execution plan

2. **Approval Handler** (Interactive CLI)
   - Shows you the plan
   - Gets your approval (or feedback for revisions)

3. **Executor Agent** (Claude Haiku 4.5)
   - Follows the approved plan step-by-step
   - Calls mock data source APIs
   - Aggregates results

4. **Sufficiency Checker** (Claude Sonnet 4.5 + Extended Thinking)
   - Validates if data adequately answers your query
   - Identifies gaps if needed
   - Suggests next steps

5. **Report Generator** (Claude Sonnet 4.5)
   - Formats results into professional report
   - Highlights key insights
   - Provides actionable intelligence

## Next Steps

- Read `CONVERSATION_FLOW.md` for detailed architecture
- Check `IMPLEMENTATION_SUMMARY.md` for technical details
- Run `python -m src.main` to try it out!

## Support

For issues or questions:
1. Check the documentation files
2. Review the inline code comments
3. Check your environment variables (.env file)
4. Verify you have AWS credentials configured

Happy prospecting! 🚀
