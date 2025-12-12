# Strands SDK Implementation Assessment

## Executive Summary

This document assesses the prospecting agent implementation against the AWS Strands SDK documentation and best practices. The implementation is generally well-structured but has several areas that need improvement to align with Strands best practices.

## Assessment Date
2025-12-12

## Key Findings

### ✅ What's Working Well

1. **Model Configuration**
   - Correctly using EU inference profiles for cross-region access
   - Proper model IDs: `eu.anthropic.claude-sonnet-4-5-20250929-v1:0` (planner/reporter) and `eu.anthropic.claude-haiku-4-5-20251001-v1:0` (executor)
   - Appropriate model selection (Sonnet for complex planning, Haiku for fast classification)

2. **Agent Architecture**
   - Multi-agent pattern with specialized agents (Planner, Executor, Sufficiency Checker, Reporter)
   - Clear separation of concerns
   - Good use of async/await patterns

3. **LLM-based Intent Detection**
   - Successfully migrated from keyword-based to LLM-based intent classification
   - Uses lightweight Haiku model for fast, cost-effective classification
   - Proper error handling with fallback to AMBIGUOUS

## ⚠️ Critical Issues

### 1. **Missing Extended Thinking Configuration**

**Issue**: The CLAUDE.md spec calls for extended thinking, but it's not implemented in the planner.

**Current Code** ([planner.py:195-199](src/agents/planner.py#L195-L199)):
```python
agent = Agent(
    model=self.model,  # Just a string model ID
    system_prompt=PLANNER_SYSTEM_PROMPT,
    name="planner",
)
```

**Should Be**:
```python
from strands.models import BedrockModel

bedrock_model = BedrockModel(
    model_id=self.settings.planner_model,
    temperature=0.3,
    additional_request_fields={
        "thinking": {
            "type": "enabled",
            "budget_tokens": self.settings.thinking_budget_tokens  # 10000
        }
    }
)

agent = Agent(
    model=bedrock_model,
    system_prompt=PLANNER_SYSTEM_PROMPT,
    name="planner",
)
```

**Impact**:
- Missing the benefit of extended thinking for complex planning tasks
- Not following the architecture spec in CLAUDE.md
- Potentially lower quality plans for complex queries

**Reference**: [Bedrock Reasoning Support](https://strandsagents.com/latest/documentation/docs/user-guide/concepts/model-providers/amazon-bedrock/index.md#reasoning-support)

---

### 2. **Inefficient Agent Creation Pattern**

**Issue**: Creating new Agent instances on every invocation instead of reusing them.

**Current Code** ([planner.py:190-202](src/agents/planner.py#L190-L202)):
```python
for attempt in range(max_retries):
    try:
        # Creates a NEW agent for every retry
        agent = Agent(
            model=self.model,
            system_prompt=PLANNER_SYSTEM_PROMPT,
            name="planner",
        )
        response = await agent.invoke_async(prompt)
```

**Also in** ([planner.py:367-371](src/agents/planner.py#L367-L371)):
```python
# Creates a NEW agent for every intent classification
intent_agent = Agent(
    model=self.settings.executor_model,
    system_prompt="You are an intent classifier...",
    name="intent_classifier",
)
```

**Should Be**:
```python
class PlannerAgent:
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings()

        # Create the model instance once
        self.planner_model = BedrockModel(
            model_id=self.settings.planner_model,
            temperature=0.3,
            additional_request_fields={
                "thinking": {
                    "type": "enabled",
                    "budget_tokens": self.settings.thinking_budget_tokens
                }
            }
        )

        # Create agents once during initialization
        self.agent = Agent(
            model=self.planner_model,
            system_prompt=PLANNER_SYSTEM_PROMPT,
            name="planner",
        )

        self.intent_agent = Agent(
            model=self.settings.executor_model,
            system_prompt="You are an intent classifier...",
            name="intent_classifier",
        )

    async def create_plan(self, query: str) -> ExecutionPlan:
        # Reuse the same agent
        response = await self.agent.invoke_async(prompt)
```

**Impact**:
- Unnecessary overhead creating agents repeatedly
- Missing potential benefits from agent state/caching
- Inefficient resource usage

---

### 3. **Not Using BedrockModel for Configuration**

**Issue**: Passing model ID string instead of BedrockModel instance, losing fine-grained control.

**Current Code** ([planner.py:159](src/agents/planner.py#L159)):
```python
self.model = self.settings.planner_model  # Just a string
self.temperature = 0.3  # Stored but not used
self.max_tokens = 4000   # Stored but not used
```

**Should Be**:
```python
from strands.models import BedrockModel

self.model = BedrockModel(
    model_id=self.settings.planner_model,
    temperature=0.3,
    max_tokens=4000,
    additional_request_fields={
        "thinking": {
            "type": "enabled",
            "budget_tokens": self.settings.thinking_budget_tokens
        }
    }
)
```

**Impact**:
- Temperature and max_tokens settings are ignored
- Can't configure extended thinking
- Missing other BedrockModel features (caching, guardrails, etc.)

---

### 4. **Missing System Prompt Caching**

**Issue**: The system prompt is large and static but not cached, leading to unnecessary token costs.

**Current Implementation**: No caching at all.

**Recommended**:
```python
from strands.types.content import SystemContentBlock

# Create cacheable system prompt
system_content = [
    SystemContentBlock(text=PLANNER_SYSTEM_PROMPT),
    SystemContentBlock(cachePoint={"type": "default"})
]

agent = Agent(
    model=bedrock_model,
    system_prompt=system_content,  # Pass as SystemContentBlock array
    name="planner",
)
```

**Impact**:
- Higher token costs on every planning request
- Slower response times (no cache hits)
- Missing a key Strands optimization feature

**Reference**: [System Prompt Caching](https://strandsagents.com/latest/documentation/docs/user-guide/concepts/model-providers/amazon-bedrock/index.md#system-prompt-caching)

---

### 5. **Inconsistent Error Handling**

**Issue**: Different error handling strategies across methods.

**In create_plan** ([planner.py:210-220](src/agents/planner.py#L210-L220)):
```python
except (ValidationError, json.JSONDecodeError, ValueError) as e:
    last_error = e
    logger.warning(f"Attempt {attempt + 1} failed: {e}")
    # Has retry logic
```

**In analyze_query_intent** ([planner.py:388-391](src/agents/planner.py#L388-L391)):
```python
except Exception as e:  # Catches ALL exceptions
    logger.error(f"Error classifying intent: {e}")
    return QueryIntent.AMBIGUOUS  # Silent failure
```

**Should Be Consistent**:
```python
# Be specific about which exceptions to catch
except (ValidationError, ModelInvocationError) as e:
    logger.error(f"Error classifying intent: {e}")
    return QueryIntent.AMBIGUOUS
```

---

## 📊 Comparison with Strands Best Practices

### Agent Initialization

| Aspect | Current | Recommended | Status |
|--------|---------|-------------|--------|
| Model type | String ID | BedrockModel instance | ❌ |
| Agent reuse | Created per request | Created once | ❌ |
| Temperature | Stored but not used | Configured in model | ❌ |
| Max tokens | Stored but not used | Configured in model | ❌ |
| Extended thinking | Not configured | Via additional_request_fields | ❌ |

### Caching Strategy

| Aspect | Current | Recommended | Status |
|--------|---------|-------------|--------|
| System prompt | No caching | SystemContentBlock with cachePoint | ❌ |
| Tools | N/A (no tools) | cache_tools="default" | N/A |
| Messages | No caching | Not needed for stateless agents | ✅ |

### Response Handling

| Aspect | Current | Recommended | Status |
|--------|---------|-------------|--------|
| invoke_async | ✅ Used | ✅ Correct for async | ✅ |
| Response parsing | Manual JSON extraction | ✅ Works but fragile | ⚠️ |
| Error handling | Mixed approach | Consistent strategy | ⚠️ |

---

## 🎯 Recommended Changes (Priority Order)

### Priority 1: Enable Extended Thinking
```python
# src/agents/planner.py

def __init__(self, settings: Optional[Settings] = None):
    self.settings = settings or Settings()

    # Create BedrockModel with extended thinking
    self.planner_model = BedrockModel(
        model_id=self.settings.planner_model,
        temperature=0.3,
        max_tokens=4000,
        additional_request_fields={
            "thinking": {
                "type": "enabled",
                "budget_tokens": self.settings.thinking_budget_tokens
            }
        }
    )

    # Create agent once with cacheable system prompt
    system_content = [
        SystemContentBlock(text=PLANNER_SYSTEM_PROMPT),
        SystemContentBlock(cachePoint={"type": "default"})
    ]

    self.agent = Agent(
        model=self.planner_model,
        system_prompt=system_content,
        name="planner",
    )

    # Create intent classifier once
    self.intent_agent = Agent(
        model=self.settings.executor_model,
        system_prompt="You are an intent classifier for prospecting queries. Respond only with the intent category name.",
        name="intent_classifier",
    )

async def create_plan(self, query: str) -> ExecutionPlan:
    # Reuse self.agent instead of creating new one
    response = await self.agent.invoke_async(prompt)

async def analyze_query_intent(self, query: str) -> QueryIntent:
    # Reuse self.intent_agent instead of creating new one
    response = await self.intent_agent.invoke_async(intent_prompt)
```

### Priority 2: Add Import Statements
```python
# At top of planner.py
from strands.models import BedrockModel
from strands.types.content import SystemContentBlock
```

### Priority 3: Consistent Error Handling
```python
from botocore.exceptions import ClientError as BotocoreClientError

# In analyze_query_intent
try:
    response = await self.intent_agent.invoke_async(intent_prompt)
    # ... parsing logic ...
except (ValidationError, BotocoreClientError) as e:
    logger.error(f"Error classifying intent: {e}")
    return QueryIntent.AMBIGUOUS
```

### Priority 4: Update Config Documentation
```python
# src/config.py
class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Extended thinking (used for Planner and Sufficiency Checker)
    enable_extended_thinking: bool = True
    thinking_budget_tokens: int = 10000  # Minimum 1024, recommended 4096-10000
```

---

## 📈 Expected Improvements

### Performance
- **25-40% faster planning**: System prompt caching reduces input tokens on repeat calls
- **Lower latency**: Agent reuse eliminates initialization overhead
- **Better plan quality**: Extended thinking provides deeper reasoning

### Cost Optimization
- **60-80% reduction in input tokens**: After first request with prompt caching
- **Fewer retries**: Better initial plans from extended thinking
- **Lower error rates**: Proper model configuration

### Code Quality
- **Better separation of concerns**: Model config separate from agent logic
- **More maintainable**: Clear initialization vs. runtime phases
- **Easier testing**: Can mock BedrockModel instances

---

## 🔍 Additional Observations

### Missing Features (Not Critical, but Worth Considering)

1. **Guardrails**: Could add content filtering for prospecting queries
2. **Metrics Collection**: Not capturing cache metrics for monitoring
3. **Structured Output**: Could use for ExecutionPlan instead of manual JSON parsing
4. **Tool Caching**: Will be needed when Executor agent is implemented with tools

### Future Enhancements

1. **Multi-agent orchestration**: Consider using A2A protocol for agent communication
2. **Streaming responses**: For better UX in interactive scenarios
3. **Conversation history**: For multi-turn planning refinement
4. **Telemetry**: OpenTelemetry integration for observability

---

## 📚 References

- [Amazon Bedrock Model Provider](https://strandsagents.com/latest/documentation/docs/user-guide/concepts/model-providers/amazon-bedrock/)
- [Reasoning Support](https://strandsagents.com/latest/documentation/docs/user-guide/concepts/model-providers/amazon-bedrock/index.md#reasoning-support)
- [System Prompt Caching](https://strandsagents.com/latest/documentation/docs/user-guide/concepts/model-providers/amazon-bedrock/index.md#system-prompt-caching)
- [BedrockModel API Reference](https://strandsagents.com/latest/documentation/api-reference/models/#strands.models.bedrock)

---

## ✅ Action Items

- [ ] Refactor PlannerAgent to use BedrockModel with extended thinking
- [ ] Implement agent reuse pattern (create once, use many times)
- [ ] Add system prompt caching with SystemContentBlock
- [ ] Update imports to include BedrockModel and SystemContentBlock
- [ ] Standardize error handling across all methods
- [ ] Add metrics collection for cache performance
- [ ] Update tests to verify extended thinking is enabled
- [ ] Document new patterns in CLAUDE.md

---

## Conclusion

The implementation follows good async patterns and has a solid architecture, but is missing several key Strands SDK features that would significantly improve performance, cost-efficiency, and plan quality. The highest priority changes are:

1. **Enable extended thinking** for the planner (critical for complex queries)
2. **Implement agent reuse** (eliminates unnecessary overhead)
3. **Add system prompt caching** (60-80% token cost reduction)

These changes align the implementation with Strands best practices and the original CLAUDE.md specification.
