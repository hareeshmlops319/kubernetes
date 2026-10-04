# 16. Performance Optimization: Application Level


The biggest gains usually come from the workload itself.

## 16.1 Training

| Technique | Gain | Notes |
|---|---|---|
| **Mixed precision (BF16/FP16)** | 2–3× vs FP32 | Uses Tensor Cores. Check `PIPE_TENSOR_ACTIVE` |
| **FP8 (Hopper/Blackwell)** | Up to ~1.5–2× over BF16 | Transformer Engine. FP4/MXFP formats on Blackwell |
| **`torch.compile`** | 1.2–2× | Kernel fusion, fewer launches |
| **FlashAttention / SDPA** | Large for attention | Memory and speed |
| **Larger batch size** to fill VRAM | Higher utilization | Use gradient accumulation if memory bound |
| **Activation checkpointing** | Fits bigger models/batches | Trades compute for memory |
| **FSDP / ZeRO / tensor/pipeline parallel** | Scale beyond one GPU's memory | Megatron-Core, DeepSpeed, NeMo |
| **CUDA Graphs** | Reduces CPU launch overhead | Good for small, static-shaped steps |
| **Overlap comm/compute** | Hides NCCL time | Bucketed DDP, FSDP prefetch |
| **Fused optimizers** (`fused=True` AdamW, Apex) | 5–15% | Fewer kernels |

## 16.2 Inference

| Technique | Notes |
|---|---|
| **Optimized serving engines** | **vLLM**, **SGLang**, **TensorRT-LLM**, **NVIDIA Dynamo**, **Triton Inference Server**, **NVIDIA NIM** |
| **Continuous/in-flight batching** | Large throughput gain over static batching |
| **PagedAttention / KV-cache management** | Higher concurrency per GPU |
| **Quantization** (FP8, INT8, INT4 AWQ/GPTQ, NVFP4) | Smaller footprint, higher throughput, often fits on a cheaper GPU or MIG slice |
| **Speculative decoding** | Lower latency |
| **Disaggregated prefill/decode** | Dynamo, llm-d. Scales prefill and decode pools separately |
| **KV-cache-aware routing** | Gateway API Inference Extension, Dynamo router. Reuses the prefix cache |
| **TensorRT / ONNX Runtime with TRT EP** | For CV and classic DL models |
| **Dynamic batching in Triton** | `max_queue_delay_microseconds` tuned to the latency SLO |
| **Right-size the GPU** | A 7B INT4 model doesn't need an H100. L4, a MIG slice, or time-slicing may do |

## 16.3 Profiling tools

- **Nsight Systems** (`nsys`): timeline of CPU, GPU, NCCL, and data loading. Finds idle gaps.
- **Nsight Compute** (`ncu`): per-kernel analysis.
- **PyTorch Profiler** with TensorBoard.
- **DCGM profiling metrics** for continuous fleet-level monitoring (Section 11).

Run Nsight Systems in a pod:

```bash
nsys profile -o /results/profile --trace=cuda,nvtx,osrt,cudnn,cublas \
  --duration=60 python train.py
```

(Profiling counters may require `NVreg_RestrictProfilingToAdminUsers=0` in the driver module parameters, set through the driver's `kernelModuleConfig` ConfigMap, or the `SYS_ADMIN` capability.)
