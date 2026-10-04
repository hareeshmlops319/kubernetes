# 21. Reference Architectures


## 21.1 Small team / mixed dev cluster

- 2–4 GPU nodes (L4/L40S/A10), GPU Operator with defaults.
- Time-slicing (4 replicas) for notebooks. One node without sharing for training.
- JupyterHub with idle culling. Grafana dashboard 12239.

## 21.2 Enterprise inference platform

- Node pools: H100/H200 (large LLMs), L40S/L4 (small models), MIG-partitioned A100/H100 (`all-balanced`).
- Serving: vLLM/TensorRT-LLM/NIM behind Gateway API with the Inference Extension (KV-cache-aware routing).
- KEDA scaling on queue depth. Karpenter with a warm minimum.
- Priority classes: prod inference > batch inference.
- Model weights cached on local NVMe. Pre-pulled images.

## 21.3 Large-scale training cluster

- HGX H100/B200 nodes with NVSwitch, 8× 400G InfiniBand/RoCE per node.
- GPU Operator (open kernel modules, RDMA) plus Network Operator (SR-IOV or the shared RDMA device plugin).
- Kueue with Topology Aware Scheduling, or the KAI Scheduler, for gang scheduling and rack locality.
- Kubeflow Trainer/JobSet. A parallel filesystem with GDS. Async checkpointing.
- CPU manager static plus NUMA-aligned topology manager. 32–64 Gi `/dev/shm`.
- DCGM diagnostics in maintenance windows, automated XID remediation.
- GB200 NVL72: DRA driver with ComputeDomains for multi-node NVLink.
