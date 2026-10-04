# 11. Monitoring and Observability (DCGM)


You can't optimize what you don't measure. The **DCGM exporter** is the foundation.

## 11.1 Wire it into Prometheus

With kube-prometheus-stack installed:

```bash
helm upgrade gpu-operator nvidia/gpu-operator -n gpu-operator --reuse-values \
  --set dcgmExporter.serviceMonitor.enabled=true
```

If Prometheus selects ServiceMonitors by label, add `dcgmExporter.serviceMonitor.additionalLabels.release=<prometheus-release>`.

Import the official **NVIDIA DCGM Exporter Grafana dashboard** (Grafana ID **12239**).

## 11.2 The metrics that actually matter

| Metric | What it tells you | Watch for |
|---|---|---|
| `DCGM_FI_DEV_GPU_UTIL` | % of time **any** kernel was running | A **coarse** metric. 100% can still mean poor use of the hardware |
| `DCGM_FI_PROF_GR_ENGINE_ACTIVE` | Graphics/compute engine active ratio | A more accurate version of "busy" |
| `DCGM_FI_PROF_SM_ACTIVE` | Fraction of SMs with at least one warp resident | Low = kernels too small or poor parallelism |
| `DCGM_FI_PROF_SM_OCCUPANCY` | Warps resident relative to the maximum | Low = register or shared memory pressure, small blocks |
| `DCGM_FI_PROF_PIPE_TENSOR_ACTIVE` | Tensor Core usage | Near 0 on DL training = not using mixed precision |
| `DCGM_FI_PROF_DRAM_ACTIVE` | Memory bandwidth usage | High = memory bound |
| `DCGM_FI_DEV_FB_USED` / `FB_FREE` | VRAM usage | Over-provisioned GPUs, OOM risk |
| `DCGM_FI_PROF_PCIE_TX/RX_BYTES` | Host-device transfer | High = data loading bottleneck |
| `DCGM_FI_PROF_NVLINK_TX/RX_BYTES` | GPU-to-GPU traffic | Collective communication health |
| `DCGM_FI_DEV_POWER_USAGE` | Watts | Power capping, efficiency |
| `DCGM_FI_DEV_GPU_TEMP`, `DCGM_FI_DEV_MEMORY_TEMP` | Temperature | Thermal throttling |
| `DCGM_FI_DEV_CLOCK_THROTTLE_REASONS` (or `CLOCKS_EVENT_REASONS`) | Why clocks dropped | Power, thermal, or sync boost |
| `DCGM_FI_DEV_XID_ERRORS` | Last XID error code | Hardware or driver faults |
| `DCGM_FI_DEV_ECC_DBE_VOL_TOTAL` | Double-bit ECC errors | Failing memory, so retire the GPU |
| `DCGM_FI_DEV_ROW_REMAP_FAILURE` | Row remapping failed | Needs RMA |

> **`GPU_UTIL` lies.** A tiny kernel running nonstop shows 100% utilization while using 1 of 132 SMs. Use **SM_ACTIVE**, **SM_OCCUPANCY**, and **PIPE_TENSOR_ACTIVE** to judge real efficiency.

## 11.3 Enabling profiling metrics

The `DCGM_FI_PROF_*` metrics may not be in the default CSV. Provide a custom metrics file:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: dcgm-metrics
  namespace: gpu-operator
data:
  dcgm-metrics.csv: |
    DCGM_FI_DEV_GPU_UTIL,           gauge, GPU utilization (%)
    DCGM_FI_DEV_FB_USED,            gauge, Framebuffer used (MiB)
    DCGM_FI_DEV_FB_FREE,            gauge, Framebuffer free (MiB)
    DCGM_FI_DEV_POWER_USAGE,        gauge, Power (W)
    DCGM_FI_DEV_GPU_TEMP,           gauge, GPU temperature (C)
    DCGM_FI_DEV_SM_CLOCK,           gauge, SM clock (MHz)
    DCGM_FI_DEV_XID_ERRORS,         gauge, Last XID error
    DCGM_FI_DEV_ECC_DBE_VOL_TOTAL,  counter, Volatile DBE errors
    DCGM_FI_PROF_GR_ENGINE_ACTIVE,  gauge, Graphics engine active ratio
    DCGM_FI_PROF_SM_ACTIVE,         gauge, SM active ratio
    DCGM_FI_PROF_SM_OCCUPANCY,      gauge, SM occupancy ratio
    DCGM_FI_PROF_PIPE_TENSOR_ACTIVE,gauge, Tensor pipe active ratio
    DCGM_FI_PROF_DRAM_ACTIVE,       gauge, DRAM active ratio
    DCGM_FI_PROF_PCIE_TX_BYTES,     gauge, PCIe TX bytes/s
    DCGM_FI_PROF_PCIE_RX_BYTES,     gauge, PCIe RX bytes/s
    DCGM_FI_PROF_NVLINK_TX_BYTES,   gauge, NVLink TX bytes/s
    DCGM_FI_PROF_NVLINK_RX_BYTES,   gauge, NVLink RX bytes/s
```

```bash
kubectl apply -f dcgm-metrics.yaml
helm upgrade gpu-operator nvidia/gpu-operator -n gpu-operator --reuse-values \
  --set dcgmExporter.config.name=dcgm-metrics
```

## 11.4 Per-pod attribution

The DCGM exporter maps GPUs to pods via the kubelet pod-resources API, adding `pod`, `namespace`, and `container` labels. This enables per-team dashboards and chargeback. For MIG, metrics carry `GPU_I_PROFILE` and `GPU_I_ID` labels.

## 11.5 Useful PromQL

```promql
# Average real SM activity per namespace
avg by (namespace) (DCGM_FI_PROF_SM_ACTIVE{namespace!=""})

# Idle allocated GPUs (allocated to a pod but <5% busy for 1h) -> waste
avg_over_time(DCGM_FI_DEV_GPU_UTIL{pod!=""}[1h]) < 5

# Memory headroom per GPU (%)
100 * DCGM_FI_DEV_FB_USED / (DCGM_FI_DEV_FB_USED + DCGM_FI_DEV_FB_FREE)

# Tensor Core usage on training jobs
avg by (pod) (DCGM_FI_PROF_PIPE_TENSOR_ACTIVE{namespace="training"})

# Cluster-wide allocation ratio (needs kube-state-metrics)
sum(kube_pod_container_resource_requests{resource="nvidia_com_gpu"})
  / sum(kube_node_status_allocatable{resource="nvidia_com_gpu"})
```

## 11.6 Alerts to have

```yaml
groups:
  - name: gpu.rules
    rules:
      - alert: GPUXidError
        expr: DCGM_FI_DEV_XID_ERRORS > 0
        for: 1m
        labels: {severity: critical}
        annotations:
          summary: "XID {{ $value }} on {{ $labels.Hostname }} GPU {{ $labels.gpu }}"
      - alert: GPUDoubleBitECC
        expr: increase(DCGM_FI_DEV_ECC_DBE_VOL_TOTAL[10m]) > 0
        labels: {severity: critical}
      - alert: GPUHighTemp
        expr: DCGM_FI_DEV_GPU_TEMP > 85
        for: 5m
        labels: {severity: warning}
      - alert: GPUAllocatedButIdle
        expr: avg_over_time(DCGM_FI_DEV_GPU_UTIL{pod!=""}[2h]) < 5
        labels: {severity: info}
        annotations:
          summary: "Pod {{ $labels.namespace }}/{{ $labels.pod }} holds a GPU but is idle"
      - alert: GPUOperatorNotReady
        expr: gpu_operator_reconciliation_status == 0
        for: 15m
        labels: {severity: warning}
```
