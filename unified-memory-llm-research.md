# Apple Silicon Unified Memory for Local LLM Inference — Research Summary

## 1. How Unified Memory Enables Large Models

### The Core Architecture
Apple Silicon uses a **unified memory architecture (UMA)** where CPU, GPU, and Neural Engine share the same memory pool. Unlike discrete NVIDIA GPUs with fixed VRAM (e.g., 24GB on RTX 4090), Apple Silicon can allocate up to ~75% of total unified memory to the GPU dynamically.

**Key insight:** A 128GB Mac Studio can allocate ~96GB to GPU, enough to run 70B+ parameter models entirely in memory — something no single consumer NVIDIA GPU can do (RTX 4090 tops out at 24GB VRAM).

### Memory Limits by Mac Configuration
| Mac Config | Total RAM | Max GPU Allocation (~75%) | Largest Practical Model |
|---|---|---|---|
| 16GB (M4 base) | 16GB | ~12GB | 7B Q4, some 13B Q3 |
| 24GB | 24GB | ~18GB | 13B Q4-Q5 |
| 32GB | 32GB | ~24GB | 70B Q3_K_S (with kernel tweak) |
| 48GB | 48GB | ~36GB | 70B Q4_K_M comfortably |
| 64GB | 64GB | ~48GB | 70B Q4-Q5 with large context |
| 96GB (M3 Ultra) | 96GB | ~72GB | 70B Q6-Q8, 120B+ Q3-Q4 |
| 128GB | 128GB | ~96GB | 70B full precision, 120B+ Q4 |
| 192GB (M2 Ultra) | 192GB | ~144GB | 120B+ models comfortably |
| 256GB (M3 Ultra) | 256GB | ~192GB | Even larger MoE models |

### Bypassing the Default GPU Limit
By default, macOS limits GPU memory to ~75% of unified memory. Community found workaround:
```bash
sudo sysctl iogpu.wired_limit_mb=57344  # Set GPU limit to 56GB on 64GB Mac
```
This allows a 32GB Mac to run 70B Q3_K_S models on GPU (28GB model). See: https://github.com/ggerganov/llama.cpp/discussions/2182

---

## 2. Memory Bandwidth: The Real Bottleneck

LLM **inference is memory-bandwidth bound**, not compute bound. The model weights must be streamed from memory to the compute units every token. This means tokens/second is directly proportional to memory bandwidth.

### Memory Bandwidth Comparison
| Chip | Memory Bandwidth | Notes |
|---|---|---|
| M1 / M2 / M3 (base) | ~68 GB/s | Entry-level, slowest for LLMs |
| M1 Pro / M2 Pro / M3 Pro | ~200 GB/s | Good mid-range |
| M1 Max / M2 Max / M3 Max | ~400 GB/s | Serious LLM territory |
| M4 Max | ~546 GB/s | Best single-chip Mac option |
| M1 Ultra / M2 Ultra | ~800 GB/s | Dual-die, fastest Macs |
| **RTX 4090** | **~1,004 GB/s** | ~2x faster than M4 Max |
| **RTX 3090** | **~936 GB/s** | Still faster than any single Mac chip |
| **A100 80GB** | **~2,039 GB/s** | Datacenter, ~$12K+ |

### What This Means in Practice
- **RTX 4090 is roughly 2x faster** than M4 Max for pure inference speed (tok/s)
- But RTX 4090 **can only fit ~24GB models** (Q4 70B requires ~40GB)
- To run 70B on NVIDIA, you need: 2× RTX 3090/4090 ($2-4K) or A100 ($12K+)
- A single M4 Max 128GB ($4,499-5,999) can run 70B Q4-Q6 with one machine, one power supply, silent operation

---

## 3. Real-World Benchmarks (from Community + SiliconBench)

### Llama 3.3 70B Performance
| Machine | RAM | Quant | tok/s | Source |
|---|---|---|---|---|
| Mac Mini M4 Pro 64GB | 64GB | Q3_K_L | 3-3.5 | Reddit r/LocalLLaMA (Dec 2024) |
| Mac Mini M4 Pro 64GB | 64GB | Q4_K_M | ~5 | Reddit r/LocalLLaMA (Dec 2024) |
| Mac Studio M1 32GB | 32GB | Q3_K_S | 4 (gen) / 14 (prompt) | Reddit r/LocalLLaMA (Nov 2023) |
| Mac Studio M4 Max 64GB | 64GB | Q6 | ~8.2 | SiliconBench (estimated) |
| MacBook Pro M1 Max 64GB | 64GB | Q4 | ~8 | Medium blog (Nov 2023) |

### Smaller Models (for comparison)
| Machine | Model | Quant | tok/s | Source |
|---|---|---|---|---|
| Mac Mini M4 Pro 64GB | Llama 3.2 3B | Q4 (MLX) | 102-105 | Reddit (Dec 2024) |
| Mac Mini M4 Pro 64GB | Llama 3.2 3B | Q4_K_M (Ollama) | 70-80 | Reddit (Dec 2024) |
| Mac Studio M4 Max 64GB | Qwen 3 4B | 8-bit | ~143 | SiliconBench |
| Mac Studio M4 Max 64GB | Gemma 3 4B | 8-bit | ~100 | SiliconBench |

### MoE Models (Mixture of Experts)
Mixture of Experts models are particularly exciting for Macs because only a subset of parameters activate per token, meaning faster inference despite large total parameter counts:
- Qwen 3 30B-A3B: ~85 tok/s on M4 Max (MLX) — impressive for 30B-class
- Qwen3.5-35B-A3B: ~58 tok/s on M4 Max (MLX)

---

## 4. Quantization Strategies

### Recommended Quantization Levels
| Level | Quality | RAM for 70B | Best For |
|---|---|---|---|
| Q2/Q3 | Noticeable degradation | 28-35GB | Fitting big models on 32GB Macs |
| **Q4_K_M** | **Good general starting point** | ~40GB | **Sweet spot: 48GB+ Macs** |
| Q5_K_M | Better quality | ~50GB | 64GB+ Macs |
| Q6_K | Near-original quality | ~56GB | 64-96GB Macs |
| Q8_0 | Near-full-precision | ~75GB | 96-128GB Macs |

### Format Ecosystem
- **GGUF**: llama.cpp format, universal, used by Ollama, LM Studio
- **MLX**: Apple-optimized format (via MLX framework), often faster on Apple Silicon
- LM Studio now ships an MLX backend for faster inference (Oct 2024)

### Key Guidance from SiliconBench
> "Q4_K_M is the best general starting point — good quality-to-size ratio, runs fully on-GPU across all Apple Silicon chips. Q8_0 delivers near-full-precision quality but roughly doubles RAM requirements. IQ2 and IQ3 variants reach extreme compression but may show quality degradation on reasoning tasks. For most use cases: start at Q4_K_M, step up to Q6_K if RAM allows."

---

## 5. Software Stack

### Runtimes (ranked by community preference)
1. **Ollama**: Easiest setup, `ollama run llama3.3:70b`, GGUF backend
2. **LM Studio**: GUI + CLI, supports both GGUF and MLX backends
3. **llama.cpp**: Maximum control, fastest for power users
4. **MLX (Apple's framework)**: Native Apple optimization, Python API

### The M4 Generation Upgrade Question
> "The M4 generation offers roughly 20–30% higher memory bandwidth than M3, which translates directly to higher tokens per second for memory-bandwidth-bound inference. If you are buying new hardware, M4 Max is the clear choice in its tier. If you already own an M3 Max, the throughput gain alone is unlikely to justify the upgrade cost — the RAM ceiling matters more." — SiliconBench

---

## 6. Mac Studio/Pro vs NVIDIA GPUs — Community Consensus

### Pros of Mac for Local LLMs
- **Run larger models**: 70B+ on a single machine vs needing multi-GPU on NVIDIA
- **Unified memory** = no CPU↔GPU data transfer bottleneck
- **Silent operation**: Only fan noise during 70B inference
- **Power efficiency**: ~40-80W vs 300-450W for equivalent GPU setups
- **No CUDA dependency hell**: Metal backend works out of the box
- **Portable**: MacBook Pro 128GB can run 70B models on the go
- **Cost-effective for large models**: Mac Studio 128GB ($4,499) vs A100 80GB ($12K+)

### Cons of Mac for Local LLMs
- **Slower per-token**: RTX 4090 is ~2x faster than M4 Max for models that fit
- **No training**: CUDA ecosystem dominates for training/fine-tuning
- **Bandwidth ceiling**: Even M4 Max at 546 GB/s is half of RTX 4090
- **Cost for small models**: If you only need 7B-13B, a used 3090 is cheaper

### Community Verdict (from r/LocalLLaMA)
- **"ELI5: Bandwidth is like a highway. Apple built more lanes in their consumer chips."**
- **"Best value for 70B+ models: Mac Studio. Best value for <30B models: used RTX 3090."**
- **"The advantages: User friendly. You don't build/procure different hardware parts to run 100B+ models. Portable. Quiet. Low power. Disadvantages: Slower than dedicated GPU. Software not there for training vs CUDA."**
- For running 24/7/365, Mac power savings alone save hundreds of dollars per year vs GPU rigs

### The DGX Spark Comparison (Oct 2025)
NVIDIA's DGX Spark (Grace CPU + Blackwell GPU, 128GB unified-ish) was reviewed:
> "You can get 2500 prefill with 4x 3090 and 90tps on 120B. This is literally 1/10th of the performance for more $. It's good for non-LLM tasks."

---

## 7. Practical Buying Guide (2026)

| Budget | Best Mac for LLMs | What You Can Run |
|---|---|---|
| $500-800 | Mac Mini M4 16-32GB | 7B-13B models well |
| $1,400-1,600 | Mac Mini M4 Pro 48GB | 70B Q4_K_M with context |
| $2,500-3,000 | MacBook Pro M4 Pro 48GB | Same as above, portable |
| $3,000-4,500 | Mac Studio M4 Max 64-128GB | 70B Q5-Q6, 120B+ Q3-Q4 |
| $7,500 | Mac Studio M3 Ultra 256GB | Run anything, future-proof |

### The ssd-llm Project
An interesting project (https://github.com/quantumnic/ssd-llm) enables running 70B+ models on Apple Silicon by using SSD as extended memory with intelligent layer streaming — potentially making even 16-32GB Macs usable for large models (at reduced speed).

---

## 8. Key Takeaways

1. **Unified memory is Apple Silicon's killer feature for local LLMs** — it lets you run models that simply cannot fit on any single consumer GPU
2. **Memory bandwidth is the bottleneck**, not compute — and Apple's bandwidth (546 GB/s on M4 Max) is competitive though behind NVIDIA (1 TB/s on RTX 4090)
3. **For 70B+ models, Mac is often the better value** — one machine, silent, efficient, no multi-GPU complexity
4. **For <30B models, used NVIDIA GPUs are often faster/cheaper**
5. **Q4_K_M quantization is the sweet spot** for quality-to-size ratio on Macs
6. **The gap is narrowing** — MLX framework and optimized runtimes keep improving Mac performance
7. **RAM matters more than GPU cores** — prioritize memory over extra GPU cores when buying

---

## Sources
- SiliconBench (siliconbench.radicchio.page) — Apple Silicon LLM benchmark database
- r/LocalLLaMA — Multiple community benchmark threads (2023-2025)
- llama.cpp GitHub Discussions #2182, #4167
- GitHub: XiongjieDai/GPU-Benchmarks-on-LLM-Inference
- GitHub: quantumnic/ssd-llm
- Medium: "Thoughts on Apple Silicon Performance for Local LLMs" (Nov 2023)
- Compute Market: "Mac Mini M4 for AI" (2026)
- SitePoint: "Running Local LLMs on Apple Silicon Mac" (March 2026)
