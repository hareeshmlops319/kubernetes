# 14. Performance Optimization: Networking and Multi-Node (RDMA, NCCL)


Multi-node training performance is often limited by the network, not the GPUs.

## 14.1 GPUDirect RDMA

GPUDirect RDMA lets the NIC read and write GPU memory directly, bypassing host memory and CPU copies.

**Stack:** NVIDIA Network Operator (MOFED/DOCA drivers, RDMA shared device plugin or SR-IOV, Multus, IPAM) plus the GPU Operator with RDMA enabled.

```bash
helm upgrade gpu-operator nvidia/gpu-operator -n gpu-operator --reuse-values \
  --set driver.rdma.enabled=true \
  --set driver.rdma.useHostMofed=false   # true if MOFED is installed on host
```

Recent setups can use **DMA-BUF** instead of `nvidia-peermem` (open kernel modules plus a recent kernel), which needs no extra kernel module.

**Pod with a secondary RDMA network:**

```yaml
metadata:
  annotations:
    k8s.v1.cni.cncf.io/networks: rdma-net-ipam
spec:
  containers:
    - name: trainer
      securityContext:
        capabilities:
          add: ["IPC_LOCK"]          # required for RDMA memory registration
      resources:
        limits:
          nvidia.com/gpu: 8
          rdma/rdma_shared_device_a: 1   # or nvidia.com/<sriov-resource>: 8
```

## 14.2 NCCL tuning

NCCL handles collectives (all-reduce, all-gather) for PyTorch DDP/FSDP, Megatron, DeepSpeed, and others.

```yaml
env:
  - name: NCCL_DEBUG
    value: INFO                  # verify transport: look for "NET/IB" and "GDRDMA"
  - name: NCCL_IB_HCA
    value: mlx5                  # which HCAs to use
  - name: NCCL_SOCKET_IFNAME
    value: eth0                  # bootstrap interface (not the RDMA one)
  - name: NCCL_NET_GDR_LEVEL
    value: PHB                   # allow GPUDirect RDMA up to this topology distance
  - name: NCCL_IB_GID_INDEX
    value: "3"                   # RoCEv2 typically
  - name: NCCL_CROSS_NIC
    value: "0"
  # Cloud specifics: AWS EFA uses aws-ofi-nccl plugin; GCP uses gIB / TCPXO plugins
```

**Validate with nccl-tests** before blaming the model code:

```bash
mpirun -np 16 -H node1:8,node2:8 \
  /opt/nccl-tests/build/all_reduce_perf -b 8 -e 8G -f 2 -g 1
```

Compare `busbw` against the theoretical number. For example, on 8×400 Gb/s NDR per node, expect roughly 350–380 GB/s bus bandwidth for large messages on well-tuned clusters. Numbers far below that point to configuration problems (GDR disabled, wrong HCA, PCIe topology, ACS).

## 14.3 Distributed training operators

| Tool | Use |
|---|---|
| **Kubeflow Trainer** (TrainJob, formerly Training Operator PyTorchJob) | PyTorch, DeepSpeed, JAX distributed jobs |
| **JobSet** | Generic multi-template distributed jobs (TPU/GPU) |
| **MPI Operator** | Horovod, MPI, nccl-tests |
| **KubeRay** | Ray Train, Ray Serve |
| **LeaderWorkerSet (LWS)** | Multi-node inference (for example vLLM/SGLang with tensor plus pipeline parallelism across nodes) |
