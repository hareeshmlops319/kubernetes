# 12. Performance Optimization: Node and Hardware Level


## 12.1 Persistence mode

Without persistence mode, the driver tears down GPU state when the last client exits, which adds seconds of latency to every pod start. The operator's driver container runs `nvidia-persistenced`, so this is on by default. Verify it:

```bash
kubectl exec -n gpu-operator ds/nvidia-driver-daemonset -- nvidia-smi -q | grep -i persistence
```

## 12.2 Clocks and power

```bash
# Inspect throttling
nvidia-smi -q -d PERFORMANCE,CLOCK,POWER

# Lock graphics clocks for consistent latency (inference / benchmarking)
nvidia-smi -lgc <min>,<max>
nvidia-smi -rgc                 # reset

# Power cap (perf/watt optimization; often -10–20% power costs only a few % perf)
nvidia-smi -pl <watts>
```

- **For throughput or cost per token:** Try power capping. Many workloads are memory bound and lose little performance at lower power.
- **For latency-critical inference:** Lock the clocks to avoid ramp-up jitter.
- Apply these settings with a privileged DaemonSet or a node-tuning tool so they survive reboots. Use them carefully and document them.

## 12.3 Cooling and throttling

Check `DCGM_FI_DEV_CLOCK_THROTTLE_REASONS`. Constant `HW_SLOWDOWN`, `HW_THERMAL`, or `SW_THERMAL` events point to datacenter cooling or airflow problems. No software tuning fixes those.

## 12.4 ECC

Keep ECC **enabled** in production. Silent data corruption is far worse than the ~5–10% memory capacity and bandwidth cost on older GPUs. HBM GPUs have ECC with negligible overhead.

## 12.5 Topology awareness (PCIe, NVLink, NUMA)

```bash
nvidia-smi topo -m
```

```
        GPU0  GPU1  GPU2  GPU3  NIC0  CPU Affinity  NUMA Affinity
GPU0     X    NV18  NV18  NV18  PXB   0-55          0
GPU1    NV18   X    NV18  NV18  PXB   0-55          0
...
```

| Code | Meaning | Performance |
|---|---|---|
| `NV#` | NVLink (# of links) | Best |
| `PIX` | Same PCIe switch | Good |
| `PXB` | Multiple PCIe switches | OK |
| `PHB` | Through the CPU host bridge | Worse |
| `NODE` | Across PCIe host bridges within a NUMA node | Worse |
| `SYS` | Across NUMA nodes (QPI/UPI/xGMI) | Worst |

Goals:

- Multi-GPU jobs should get GPUs connected by **NVLink/NVSwitch**, or at least on the same PCIe switch.
- CPU threads and memory should be on the **same NUMA node** as the GPU.
- The RDMA NIC should be on the **same PCIe switch** as its GPU (`PIX`/`PXB`) for GPUDirect RDMA.

The NVIDIA device plugin prefers allocating topology-aligned GPU sets when a container asks for multiple GPUs. On NVSwitch systems (DGX/HGX) all GPUs are equal, so this matters mostly on PCIe servers.

## 12.6 Fabric Manager (NVSwitch systems)

HGX/DGX A100, H100, H200, and B200 systems with NVSwitch **require Fabric Manager**. The operator's driver container runs it automatically on these systems. If CUDA reports `system not yet initialized` (error 802), Fabric Manager isn't running or its version doesn't match the driver.

## 12.7 OS-level tuning

- **CPU governor:** Set to `performance`.
- **Transparent hugepages:** Settings vary by workload. Many ML stacks prefer `madvise`.
- **IOMMU:** Use `iommu=pt` (passthrough) for bare-metal performance with RDMA.
- **PCIe ACS:** Disable ACS on PCIe switches (or set it up correctly) for GPUDirect P2P/RDMA. Otherwise traffic goes through the root complex.
- **Kernel:** Use an LTS kernel that the driver branch supports.
