# Apriel-1.5-15b-Thinker: Complete vLLM Configuration Guide

**Model:** Apriel-1.5-15b-Thinker (ServiceNow AI)  
**Engine:** vLLM 0.6.3+ (Docker: `vllm/vllm-openai:latest`)  
**Hardware:** NVIDIA L40S (48GB VRAM)  
**Date:** November 2025

---

## 📋 TABLE OF CONTENTS

1. [Current Configuration](#current-configuration)
2. [Core Model Arguments](#core-model-arguments)
3. [Performance Tuning](#performance-tuning)
4. [Memory Management](#memory-management)
5. [Tool Calling / Function Calling](#tool-calling-function-calling)
6. [Distributed Inference](#distributed-inference)
7. [Advanced Features](#advanced-features)
8. [Production Deployment](#production-deployment)
9. [Monitoring & Debugging](#monitoring-debugging)
10. [Optimization Recommendations](#optimization-recommendations)

---

## ✅ CURRENT CONFIGURATION

**Your current docker-compose.yml command:**

```yaml
command: >
  --model /app/model
  --dtype half
  --gpu-memory-utilization 0.90
  --max-model-len 16384
  --enforce-eager
  --served-model-name apriel-1.5-15b-thinker
  --api-key ${AETHER_API_KEY}
  --enable-auto-tool-choice
  --tool-call-parser hermes
```

**What each does:**
- `--model /app/model` - Path to model weights
- `--dtype half` - Use FP16 (half precision) for inference
- `--gpu-memory-utilization 0.90` - Use 90% of GPU VRAM
- `--max-model-len 16384` - Maximum context length (tokens)
- `--enforce-eager` - Disable CUDA graphs (required for some operations)
- `--served-model-name` - API model name
- `--api-key` - Authentication key
- `--enable-auto-tool-choice` - Enable function calling
- `--tool-call-parser hermes` - Use Hermes-style tool parsing

---

## 🎯 CORE MODEL ARGUMENTS

### Model Loading

```bash
--model <path_or_name>
# Path to local model or HuggingFace model ID
# Example: /app/model or meta-llama/Llama-3-8B

--tokenizer <path>
# Override tokenizer (if different from model)
# Default: Uses model's tokenizer

--revision <git_ref>
# Specific model version/branch
# Example: main, v1.0, commit hash

--tokenizer-mode <mode>
# Options: auto, slow, mistral
# 'mistral' for Mistral-based models (like Apriel)

--skip-tokenizer-init
# Skip tokenizer initialization
# Use when providing pre-tokenized inputs

--trust-remote-code
# Allow custom model code from HuggingFace
# ⚠️ Security risk - only use with trusted models

--code-revision <ref>
# Specific revision for custom code
```

---

## ⚡ PERFORMANCE TUNING

### Precision & Quantization

```bash
--dtype <type>
# Options: auto, half, float16, bfloat16, float, float32
# Current: half (FP16)
# Recommendation: Keep half for best speed/quality balance

--quantization <method>
# Options: awq, gptq, squeezellm, fp8, None
# Use for smaller memory footprint
# Example: --quantization awq

--kv-cache-dtype <type>
# KV cache precision
# Options: auto, fp8, fp8_e5m2, fp8_e4m3
# fp8 saves ~50% KV cache memory
# Example: --kv-cache-dtype fp8

--load-format <format>
# Options: auto, pt, safetensors, npcache, dummy
# Current: auto (safetensors preferred)
# 'npcache' for faster reloading
```

### Batch Processing

```bash
--max-num-batched-tokens <int>
# Maximum tokens per batch
# Default: Depends on model
# Higher = better throughput, more VRAM
# Example: --max-num-batched-tokens 8192

--max-num-seqs <int>
# Maximum concurrent sequences
# Default: 256
# Higher = more concurrent requests
# Example: --max-num-seqs 512

--max-seq-len-to-capture <int>
# For CUDA graphs (not used with --enforce-eager)
# Controls compiled sequence lengths

--max-paddings <int>
# Maximum padding tokens in batch
# Default: 512
```

### GPU Optimization

```bash
--gpu-memory-utilization <float>
# Fraction of GPU memory to use (0.0-1.0)
# Current: 0.90 (90%)
# Lower if OOM errors occur
# Higher for maximum throughput

--enforce-eager
# Disable CUDA graphs
# Current: ENABLED
# ✅ Keep enabled for Apriel (required for some features)
# ❌ Remove only if you need CUDA graph optimization

--disable-custom-all-reduce
# Disable custom kernels for distributed inference
# Use if encountering errors with multi-GPU

--enable-prefix-caching
# Cache common prompt prefixes
# Huge speedup for similar prompts
# Recommendation: ADD THIS FLAG
# Example: --enable-prefix-caching
```

---

## 💾 MEMORY MANAGEMENT

### Context Length

```bash
--max-model-len <int>
# Maximum sequence length (tokens)
# Current: 16384
# Apriel supports up to 131K context
# Trade-off: Longer = more VRAM usage
# Options for Apriel:
#   16384  - Current (low memory)
#   32768  - 2x context (moderate memory)
#   65536  - 4x context (high memory)
#   131072 - Full context (requires 48GB+ VRAM)

--max-log-probs <int>
# Maximum log probabilities to return
# Default: 20
# Lower saves bandwidth

--block-size <int>
# KV cache block size
# Default: 16
# Larger blocks = less memory overhead
```

### Swap & Offloading

```bash
--swap-space <int>
# CPU swap space in GB
# Default: 4
# Allows CPU offloading of KV cache
# Useful for long contexts
# Example: --swap-space 16

--cpu-offload-gb <int>
# Model weights to offload to CPU (GB)
# Use if VRAM is insufficient
# Performance hit, but enables larger models
```

---

## 🔧 TOOL CALLING / FUNCTION CALLING

### Current Setup (Enabled)

```bash
--enable-auto-tool-choice
# CRITICAL: Required for function calling
# Allows model to decide when to call tools

--tool-call-parser hermes
# Parser format for tool calls
# Options:
#   hermes   - Hermes/Mistral style (CURRENT - CORRECT FOR APRIEL)
#   mistral  - Pure Mistral style
#   llama3_json - Llama 3.1/3.2 style
#   llama4_pythonic - Llama 4 pythonic style
#   granite  - IBM Granite style
#   internlm - InternLM style
#   xlam     - xLAM style (flexible JSON)

--chat-template <path_or_name>
# Custom chat template for tool messages
# Optional for Hermes models (has built-in template)
# Use if you need custom tool formatting
# Example: --chat-template /app/templates/custom_tool_template.jinja

--tool-parser-plugin <path>
# Register custom tool parsers
# Advanced: for proprietary formats
```

### Tool Calling Examples

**Hermes Format (What Apriel uses):**
```xml
<tool_call>
{"name": "web_search", "arguments": {"query": "AI news"}}
</tool_call>
```

**Mistral Format:**
```json
[TOOL_CALLS] [{"name": "web_search", "arguments": {"query": "AI news"}}]
```

**Why Hermes for Apriel:**
- Apriel is based on Mistral/Hermes architecture
- Uses `<tool_call>` XML-style tags
- More reliable parallel tool calls
- Better structured output

---

## 🌐 DISTRIBUTED INFERENCE

### Multi-GPU

```bash
--tensor-parallel-size <int>
# Split model across GPUs (tensor parallelism)
# Default: 1 (single GPU)
# Example: --tensor-parallel-size 2
# Use when model doesn't fit on single GPU

--pipeline-parallel-size <int>
# Pipeline stages across GPUs
# Default: 1
# Example: --pipeline-parallel-size 2
# Use for very large models

--distributed-executor-backend <backend>
# Options: ray, mp (multiprocessing)
# Default: mp for local multi-GPU
# Use 'ray' for multi-node clusters

--disable-custom-all-reduce
# Use if multi-GPU synchronization issues occur
```

### For Your L40S Setup

**Single L40S-90 (48GB):**
```bash
# Current config is optimal
--tensor-parallel-size 1
```

**Future: 2x L40S Setup:**
```bash
--tensor-parallel-size 2
--gpu-memory-utilization 0.85  # Slightly lower for stability
```

---

## 🚀 ADVANCED FEATURES

### Chunked Prefill

```bash
--enable-chunked-prefill
# Process long prompts in chunks
# Reduces latency for first token
# Recommendation: ADD THIS

--max-num-batched-tokens <int>
# Works with chunked prefill
# Smaller values = lower latency, lower throughput
```

### Speculative Decoding

```bash
--speculative-model <model_path>
# Small "draft" model for speculation
# Example: --speculative-model /app/small-model
# Speeds up generation for compatible models

--num-speculative-tokens <int>
# Tokens to speculate ahead
# Default: 5
```

### LoRA Adapters

```bash
--enable-lora
# Enable LoRA adapter support

--max-loras <int>
# Maximum concurrent LoRA adapters
# Default: 1

--max-lora-rank <int>
# Maximum LoRA rank
# Default: 16

--lora-modules <name=path> [<name=path> ...]
# Load specific LoRA modules
# Example: --lora-modules sql=/app/lora/sql-expert
```

---

## 🏭 PRODUCTION DEPLOYMENT

### API Server

```bash
--host <ip>
# Bind address
# Default: 0.0.0.0
# Production: 127.0.0.1 (with nginx proxy)

--port <int>
# API port
# Default: 8000

--api-key <key>
# Authentication
# Current: ${AETHER_API_KEY}
# ⚠️ Keep secret!

--ssl-keyfile <path>
--ssl-certfile <path>
# SSL/TLS certificates
# Use nginx for SSL instead (recommended)

--root-path <path>
# URL prefix for API
# Example: --root-path /v1
```

### Logging & Monitoring

```bash
--disable-log-stats
# Disable periodic stats logging
# Use for production if logging overhead is high

--disable-log-requests
# Disable request logging
# Reduces log verbosity

--log-level <level>
# Options: debug, info, warning, error
# Default: info

--uvicorn-log-level <level>
# Web server log level
# Options: critical, error, warning, info, debug, trace
```

### Safety & Limits

```bash
--max-logprobs <int>
# Limit log probabilities returned
# Prevents abuse

--disable-frontend-multiprocessing
# Run API in same process as engine
# Use for debugging
# Production: Keep default (separate processes)

--served-model-name <name>
# Model name exposed in API
# Current: apriel-1.5-15b-thinker
```

---

## 📊 MONITORING & DEBUGGING

### Health Checks

```bash
# Built-in endpoints (always available):
# GET /health           - Health check
# GET /v1/models        - List models
# GET /metrics          - Prometheus metrics (if enabled)
```

### Performance Metrics

```bash
--disable-log-stats
# Controls periodic performance logging
# Default: Enabled (logs every 10s)
# Shows:
#   - Throughput (tokens/s)
#   - GPU utilization
#   - KV cache usage
#   - Queue status
```

### Debug Mode

```bash
# Environment variables (set in docker-compose):
VLLM_LOGGING_LEVEL=DEBUG
VLLM_TRACE_FUNCTION=1     # Trace function calls
CUDA_LAUNCH_BLOCKING=1    # Synchronous CUDA for debugging
```

---

## 🎯 OPTIMIZATION RECOMMENDATIONS

### For Apriel on L40S-90 (48GB)

**Current config is GOOD, but here's how to optimize further:**

### 1. **Enable Prefix Caching** (HIGHLY RECOMMENDED)
```yaml
command: >
  --model /app/model
  --dtype half
  --gpu-memory-utilization 0.90
  --max-model-len 16384
  --enforce-eager
  --served-model-name apriel-1.5-15b-thinker
  --api-key ${AETHER_API_KEY}
  --enable-auto-tool-choice
  --tool-call-parser hermes
  --enable-prefix-caching        # ADD THIS
```

**Benefit:** 3-10x faster for similar prompts (e.g., system prompts)

---

### 2. **Enable Chunked Prefill for Lower Latency**
```yaml
  --enable-chunked-prefill        # ADD THIS
  --max-num-batched-tokens 4096   # ADD THIS
```

**Benefit:** First token appears faster, better UX

---

### 3. **Increase Context Length (If Needed)**
```yaml
  --max-model-len 32768          # CHANGE from 16384
  --gpu-memory-utilization 0.85  # CHANGE from 0.90 (slightly lower)
```

**Benefit:** 2x context window for long conversations

---

### 4. **Add FP8 KV Cache (50% Memory Savings)**
```yaml
  --kv-cache-dtype fp8           # ADD THIS
```

**Benefit:** Frees up ~6GB VRAM for more concurrent users

---

### 5. **Optimize for High Throughput**
```yaml
  --max-num-seqs 512             # ADD THIS (from default 256)
  --max-num-batched-tokens 8192  # ADD THIS
```

**Benefit:** Handle 2x more concurrent requests

---

## 🔥 RECOMMENDED PRODUCTION CONFIG

**For high-performance, production Apriel deployment:**

```yaml
version: '3.8'
services:
  apriel-engine:
    image: vllm/vllm-openai:latest
    container_name: apriel_engine
    runtime: nvidia
    restart: always
    environment:
      - HUGGING_FACE_HUB_TOKEN=${HF_TOKEN}
      - VLLM_LOGGING_LEVEL=INFO
    volumes:
      - /home/ubuntu/Neuro-Symbiotic/models/apriel:/app/model
      - ~/.cache/huggingface:/root/.cache/huggingface 
    ports:
      - "127.0.0.1:8000:8000"
    ipc: host
    command: >
      --model /app/model
      --dtype half
      --gpu-memory-utilization 0.85
      --max-model-len 32768
      --enforce-eager
      --served-model-name apriel-1.5-15b-thinker
      --api-key ${AETHER_API_KEY}
      --enable-auto-tool-choice
      --tool-call-parser hermes
      --enable-prefix-caching
      --enable-chunked-prefill
      --max-num-batched-tokens 4096
      --max-num-seqs 512
      --kv-cache-dtype fp8
      --disable-log-requests
      --uvicorn-log-level warning
```

**Changes from your current config:**
1. ✅ Added `--enable-prefix-caching` - Faster repeated prompts
2. ✅ Added `--enable-chunked-prefill` - Lower first-token latency
3. ✅ Added `--max-num-batched-tokens 4096` - Optimal chunk size
4. ✅ Added `--max-num-seqs 512` - More concurrent users
5. ✅ Added `--kv-cache-dtype fp8` - 50% KV cache memory savings
6. ✅ Changed `--max-model-len 32768` - 2x context window
7. ✅ Changed `--gpu-memory-utilization 0.85` - Stability buffer
8. ✅ Added `--disable-log-requests` - Cleaner logs
9. ✅ Added `--uvicorn-log-level warning` - Less verbose

**Expected improvements:**
- 🚀 3-10x faster for repeated system prompts
- 🚀 30-50% lower first-token latency
- 🚀 2x concurrent request capacity
- 🚀 2x context window (16K → 32K tokens)
- 🚀 6GB freed VRAM (from FP8 KV cache)

---

## 📚 COMPLETE ARGUMENT REFERENCE

**For full docs, run:**
```bash
docker exec apriel_engine vllm serve --help
```

**Or check:**
- https://docs.vllm.ai/en/stable/
- https://docs.vllm.ai/en/stable/configuration/engine_args/
- https://docs.vllm.ai/en/stable/features/tool_calling/

---

## 🎓 TRAINING & FINE-TUNING

### Future: When Training Apriel

```bash
# vLLM doesn't do training - use these frameworks:
- PyTorch + HuggingFace Trainer
- Axolotl (fine-tuning framework)
- LLaMA Factory
- TRL (Transformer Reinforcement Learning)

# After training, deploy with vLLM
# vLLM is for INFERENCE only
```

### LoRA Fine-Tuning

```bash
# Train LoRA adapters
# Then deploy:
--enable-lora
--lora-modules domain_expert=/path/to/lora

# Dynamically load at runtime via API:
curl -X POST /v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "apriel-1.5-15b-thinker",
    "messages": [...],
    "lora_adapter": "domain_expert"
  }'
```

---

## 🐛 TROUBLESHOOTING

### OOM (Out of Memory)

```bash
# Reduce these:
--gpu-memory-utilization 0.75  # Lower from 0.90
--max-model-len 8192           # Reduce context
--max-num-seqs 256             # Fewer concurrent requests

# Or add:
--kv-cache-dtype fp8           # Use FP8 KV cache
--swap-space 16                # CPU offload
```

### Slow Performance

```bash
# Add these:
--enable-prefix-caching        # Cache common prompts
--max-num-batched-tokens 8192  # Larger batches
--kv-cache-dtype fp8           # Faster KV ops

# Remove if present:
--enforce-eager                # (Try removing for CUDA graphs)
```

### Tool Calling Not Working

```bash
# Ensure these are set:
--enable-auto-tool-choice      # REQUIRED
--tool-call-parser hermes      # REQUIRED for Apriel

# Check model supports it:
# Apriel does support tool calling
```

---

## 📈 BENCHMARKING

**Test your config:**

```bash
# Install benchmark tools
pip install vllm[bench]

# Benchmark latency
docker exec apriel_engine vllm bench latency \
  --model /app/model \
  --input-len 512 \
  --output-len 128

# Benchmark throughput
docker exec apriel_engine vllm bench throughput \
  --model /app/model \
  --input-len 512 \
  --output-len 128 \
  --num-prompts 100
```

---

## 🎯 QUICK REFERENCE

**Most Important Flags:**

| Flag | Purpose | Your Value | Optimal |
|------|---------|------------|---------|
| `--dtype` | Precision | `half` | ✅ Keep |
| `--gpu-memory-utilization` | VRAM % | `0.90` | `0.85` |
| `--max-model-len` | Context | `16384` | `32768` |
| `--enforce-eager` | CUDA graphs | `on` | ✅ Keep |
| `--enable-auto-tool-choice` | Tools | `on` | ✅ Keep |
| `--tool-call-parser` | Parser | `hermes` | ✅ Keep |
| `--enable-prefix-caching` | Speed | ❌ | ✅ **ADD** |
| `--kv-cache-dtype` | Memory | ❌ | ✅ **ADD fp8** |
| `--max-num-seqs` | Concurrent | default | ✅ **ADD 512** |

---

**END OF GUIDE**

*Last Updated: November 23, 2025*  
*vLLM Version: 0.6.3+*  
*Model: Apriel-1.5-15b-Thinker*