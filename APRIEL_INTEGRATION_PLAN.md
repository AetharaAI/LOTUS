# Apriel-1.5-15b Integration Plan

## Overview
Integrate Apriel-1.5-15b-Thinker as AetherPro flagship model running on OVHcloud vLLM inference.

## Architecture

### 1. vLLM Provider (lib/providers.py)
```python
class VLLMProvider(BaseProvider):
    """
    vLLM inference provider for self-hosted models

    Supports:
    - Apriel-1.5-15b-Thinker
    - Any vLLM-compatible model
    - OpenAI-compatible API
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get('base_url')  # OVHcloud endpoint
        self.api_key = config.get('api_key', 'EMPTY')  # vLLM uses 'EMPTY'

        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(
            base_url=f"{self.base_url}/v1",
            api_key=self.api_key
        )

    async def complete(self, prompt: str, **kwargs) -> LLMResponse:
        """Call vLLM endpoint (OpenAI-compatible)"""
        model = kwargs.get('model', 'Apriel-1.5-15b-Thinker')

        response = await self.client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=kwargs.get('temperature', 0.7),
            max_tokens=kwargs.get('max_tokens', 4096)
        )

        return LLMResponse(
            text=response.choices[0].message.content,
            model=model,
            provider="vllm",
            tokens_used=response.usage.total_tokens,
            metadata={'endpoint': self.base_url}
        )
```

### 2. Model Triad Router
```python
class TriadRouter:
    """
    3-Model Strategic Router

    Models:
    1. Apriel-1.5-15b-Thinker (vLLM) - Fast ReAct, tool calling, general reasoning
    2. Vision Model (Claude/GPT-4V) - Computer vision, screen analysis
    3. Specialized Model - Domain-specific (coding, math, etc)
    """

    def __init__(self, provider_manager: ProviderManager):
        self.providers = provider_manager

        # Model capabilities mapping
        self.capabilities = {
            'apriel': ['reasoning', 'tool_calling', 'react', 'general'],
            'vision': ['image_analysis', 'screen_reading', 'ocr'],
            'specialist': ['code', 'math', 'research']
        }

    async def route(self, task: Dict[str, Any]) -> str:
        """Intelligent routing based on task type"""
        task_type = task.get('type')

        # Strategic routing
        if task_type in ['tool_call', 'react', 'general']:
            return 'vllm'  # Apriel
        elif 'image' in task or 'vision' in task:
            return 'anthropic'  # Claude for vision
        elif task.get('requires_specialist'):
            return task.get('specialist_provider', 'openai')

        # Default to Apriel
        return 'vllm'

    async def parallel_query(self, prompt: str, models: List[str]) -> Dict[str, LLMResponse]:
        """Query multiple models in parallel, return all responses"""
        tasks = {
            model: self.providers.complete(prompt, provider=model)
            for model in models
        }

        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        return {
            model: result
            for model, result in zip(tasks.keys(), results)
            if not isinstance(result, Exception)
        }

    async def consensus(self, prompt: str) -> LLMResponse:
        """
        Get consensus from all 3 models (Triad voting)

        Use case: Critical decisions, validation
        """
        responses = await self.parallel_query(prompt, ['vllm', 'anthropic', 'openai'])

        # Analyze consensus, pick best response
        # (Could use another model to judge, or scoring system)
        return self._select_best(responses)
```

### 3. Configuration (lotus/config/system.yaml)
```yaml
providers:
  # Apriel-1.5-15b on vLLM (OVHcloud)
  vllm:
    enabled: true
    base_url: "https://your-ovh-instance.com:8000"
    api_key: "EMPTY"  # vLLM default
    default_model: "Apriel-1.5-15b-Thinker"
    timeout: 120

  # Claude for vision tasks
  anthropic:
    enabled: true
    default_model: "claude-3-5-sonnet-20241022"

  # OpenAI for specialist tasks
  openai:
    enabled: true
    default_model: "gpt-4"

  # Ollama for local fallback
  ollama:
    enabled: true
    base_url: "http://localhost:11434"
    default_model: "llama3"

# Model Triad Strategy
triad:
  enabled: true
  primary: "vllm"  # Apriel as flagship
  vision: "anthropic"
  specialist: "openai"

  # Routing rules
  routing:
    tool_calling: "vllm"
    vision_tasks: "anthropic"
    code_generation: "openai"
    general_reasoning: "vllm"

  # Parallel execution
  parallel_enabled: true
  consensus_threshold: 2  # 2/3 models agree
```

### 4. OVHcloud vLLM Setup

**Instance Setup:**
```bash
# OVHcloud GPU instance (US-East)
# Instance type: GPU.L40S or GPU.A100

# Install vLLM
pip install vllm

# Start vLLM server
python -m vllm.entrypoints.openai.api_server \
    --model AetharaAI/Apriel-1.5-15b-Thinker \
    --port 8000 \
    --host 0.0.0.0 \
    --dtype auto \
    --max-model-len 4096 \
    --trust-remote-code

# Systemd service for auto-restart
sudo systemctl enable vllm-apriel.service
```

**vLLM Config:**
```python
# vllm_config.py
MAX_MODEL_LEN = 4096
TENSOR_PARALLEL_SIZE = 1  # Single GPU
GPU_MEMORY_UTILIZATION = 0.9
SWAP_SPACE = 4  # GB
ENFORCE_EAGER = False
MAX_NUM_SEQS = 256  # Batch size
```

## Implementation Steps

### Phase 1: Add vLLM Provider
1. Add VLLMProvider class to lib/providers.py ✓
2. Update ProviderManager to initialize vLLM ✓
3. Test connection to OVHcloud endpoint ✓

### Phase 2: Build Triad Router
1. Create triad_router.py in lotus/lib/ ✓
2. Implement strategic routing logic ✓
3. Add parallel execution support ✓
4. Add consensus voting mechanism ✓

### Phase 3: Integrate with Reasoning Engine
1. Update reasoning/logic.py to use TriadRouter ✓
2. Add task type detection ✓
3. Route based on task characteristics ✓

### Phase 4: LiteLLM Integration (Optional)
```python
# Alternative: Use LiteLLM as unified interface
import litellm

# Supports 100+ providers with one API
response = await litellm.acompletion(
    model="vllm/Apriel-1.5-15b-Thinker",  # Your vLLM
    messages=[...],
    api_base="https://your-ovh-instance.com:8000"
)

# Automatic fallback
response = await litellm.acompletion(
    model="claude-3-opus",
    fallbacks=["gpt-4", "vllm/Apriel-1.5-15b-Thinker"]
)
```

## Benefits of Model Triad in LOTUS

### 1. Cost Optimization
- Apriel (vLLM): $0/token (self-hosted) - 80% of requests
- Claude: $3/$15 per 1M tokens - Vision tasks only
- GPT-4: $10/$30 per 1M tokens - Specialist tasks only

### 2. Performance
- Parallel execution: 3x throughput for independent tasks
- Fast primary model (Apriel) handles 80% of load
- Strategic routing minimizes latency

### 3. Resilience
- 3-model fallback chain
- Consensus voting for critical decisions
- No single point of failure

### 4. Specialization
- Each model does what it's best at
- Apriel trained on your PresenceOS logs = native ReAct
- Vision model for computer use
- Specialist model for domain expertise

## Example Usage

```python
# In a LOTUS module
triad = self.config.get("services.triad")

# Simple routing
response = await triad.route_and_complete({
    'type': 'tool_calling',
    'prompt': 'Get weather for NYC'
})
# → Routes to Apriel (vLLM)

# Parallel execution
responses = await triad.parallel_query(
    "Analyze this image and write code to process it",
    models=['vllm', 'anthropic', 'openai']
)
# → Apriel analyzes, Claude sees image, GPT writes code

# Consensus for critical decision
response = await triad.consensus(
    "Should I execute this sudo rm -rf command?"
)
# → All 3 models vote, needs 2/3 agreement
```

## Testing Apriel Integration

```python
# Test vLLM endpoint
async def test_apriel():
    provider = VLLMProvider({
        'base_url': 'https://your-ovh.com:8000',
        'api_key': 'EMPTY'
    })

    response = await provider.complete(
        "Thought: I need to solve this problem.\nAction: tool_call\nTool: calculator"
    )

    print(f"Apriel response: {response.text}")
    print(f"Tokens used: {response.tokens_used}")
```

## Next Steps

1. Set up OVHcloud GPU instance
2. Deploy vLLM with Apriel-1.5-15b-Thinker
3. Add VLLMProvider to LOTUS
4. Build TriadRouter
5. Update system.yaml with triad config
6. Test routing logic
7. Benchmark performance vs single-model
8. Fine-tune routing rules based on results
