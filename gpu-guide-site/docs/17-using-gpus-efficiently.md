# 17. Using GPUs Efficiently: Utilization, Quotas, Autoscaling, Cost


Studies of real clusters often find **average GPU utilization below 30–40%**. Here's how to do better.

## 17.1 The waste taxonomy

| Waste type | Cause | Fix |
|---|---|---|
| **Idle allocated** | Notebooks or dev pods holding GPUs overnight | Idle culling, TTLs, time-slicing for dev |
| **Oversized allocation** | Small model on a big GPU | MIG, MPS, time-slicing, smaller GPU types |
| **Fragmentation** | Free GPUs spread across nodes | Bin-packing, defragmentation, gang scheduling |
| **Under-utilized while running** | Data loading, CPU bottleneck, no mixed precision | Sections 13–16 |
| **Queue starvation** | Static per-team allocations | Fair-share quotas with borrowing (Kueue / KAI) |
| **Overprovisioned capacity** | Fixed node pools sized for peak | Autoscaling, spot/preemptible capacity |
| **Slow startup** | Image pulls, model loading, driver install | Pre-pull, caching, precompiled drivers |

## 17.2 Quotas and fair sharing with Kueue

```yaml
apiVersion: kueue.x-k8s.io/v1beta1
kind: ResourceFlavor
metadata:
  name: h100
spec:
  nodeLabels:
    nvidia.com/gpu.product: NVIDIA-H100-80GB-HBM3
---
apiVersion: kueue.x-k8s.io/v1beta1
kind: ClusterQueue
metadata:
  name: team-a
spec:
  cohort: research          # queues in a cohort can borrow idle quota from each other
  namespaceSelector: {}
  preemption:
    reclaimWithinCohort: Any
    withinClusterQueue: LowerPriority
  resourceGroups:
    - coveredResources: ["cpu", "memory", "nvidia.com/gpu"]
      flavors:
        - name: h100
          resources:
            - name: cpu
              nominalQuota: 512
            - name: memory
              nominalQuota: 4Ti
            - name: nvidia.com/gpu
              nominalQuota: 32
              borrowingLimit: 32     # may borrow up to 32 idle GPUs from the cohort
---
apiVersion: kueue.x-k8s.io/v1beta1
kind: LocalQueue
metadata:
  name: team-a-queue
  namespace: team-a
spec:
  clusterQueue: team-a
```

Jobs opt in with the label `kueue.x-k8s.io/queue-name: team-a-queue`.

**Why this matters:** Guaranteed quotas plus **borrowing** keep idle GPUs working. When the owner team needs its quota back, borrowed workloads are preempted.

## 17.3 Priority and preemption

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: inference-prod
value: 100000
---
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: training-preemptible
value: 1000
preemptionPolicy: PreemptLowerPriority
```

The pattern: production inference > scheduled training > opportunistic or batch jobs. Opportunistic jobs **must checkpoint often** so preemption is cheap.

## 17.4 Autoscaling

**Node autoscaling:**

- **Cluster Autoscaler:** Use separate GPU node groups, and allow scale-to-zero (on some clouds this needs node group tags like `k8s.io/cluster-autoscaler/node-template/resources/nvidia.com/gpu`).
- **Karpenter:** NodePools with GPU instance families, `consolidationPolicy: WhenEmptyOrUnderutilized`, and GPU taints.
- Scale-up takes several minutes (VM boot, driver, image pull). Precompiled drivers, driver-included AMIs, and image caching cut this down.

**Pod autoscaling for inference (KEDA on DCGM or engine metrics):**

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: llm-server
spec:
  scaleTargetRef:
    name: llm-server
  minReplicaCount: 1
  maxReplicaCount: 10
  triggers:
    - type: prometheus
      metadata:
        serverAddress: http://prometheus.monitoring:9090
        # Prefer queue depth / latency over GPU util for LLM serving
        query: sum(vllm:num_requests_waiting{model_name="llama"})
        threshold: "10"
```

> For LLM serving, scale on **request queue depth, KV-cache usage, or time-to-first-token**, not on `GPU_UTIL`. GPU utilization is nearly always high when a model is loaded and serving.

## 17.5 Idle detection and culling

- JupyterHub `jupyterhub-idle-culler`, or Kubeflow Notebooks culling.
- A custom controller or CronJob that finds pods with `avg_over_time(DCGM_FI_DEV_GPU_UTIL[2h]) < 5` and notifies or scales down.
- `activeDeadlineSeconds` and `ttlSecondsAfterFinished` on Jobs.

## 17.6 Cost levers

| Lever | Typical savings |
|---|---|
| Spot/preemptible GPUs for checkpointed training and batch inference | 50–90% |
| Right-sizing GPU type (L4/L40S vs H100 for inference) | 2–5× cost per token for small models |
| MIG or MPS for small models | 2–7× density |
| Quantization (FP8/INT4) | 2–4× throughput per GPU |
| Reserved/committed capacity for baseline load, plus on-demand or spot for bursts | 30–60% |
| Scale-to-zero for dev and infrequent endpoints | Up to 100% of idle cost |
| Chargeback dashboards (per-namespace GPU-hours) | Behavioral. Teams release what they don't use |

## 17.7 A maturity model

| Level | Practices |
|---|---|
| **1. Basic** | GPU Operator installed, whole-GPU allocation, `GPU_UTIL` dashboard |
| **2. Managed** | Taints, node pools per GPU type, Prometheus alerts, time-slicing for dev |
| **3. Efficient** | MIG/MPS for inference, Kueue quotas with borrowing, bin-packing, idle culling, autoscaling |
| **4. Optimized** | Profiling metrics per job, NUMA/CPU pinning, GPUDirect RDMA, topology-aware gang scheduling, FP8, optimized serving engines |
| **5. Advanced** | DRA with attribute-based allocation, ComputeDomains, disaggregated inference, automated chargeback, SLO-driven autoscaling |
