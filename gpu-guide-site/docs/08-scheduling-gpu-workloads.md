# 8. Scheduling GPU Workloads


## 8.1 Requesting GPUs

```yaml
resources:
  limits:
    nvidia.com/gpu: 2      # GPUs go in limits; requests default to limits
```

Rules:

- GPUs are **integers** under the device plugin. There are no fractional GPUs unless you use sharing (Section 9).
- GPUs are **not overcommitted**. Each allocated GPU is exclusive to the container unless sharing is configured.
- If you specify both, `requests` must equal `limits` for extended resources.

## 8.2 Steering pods to the right GPU

```yaml
spec:
  nodeSelector:
    nvidia.com/gpu.product: NVIDIA-A100-SXM4-80GB
  # or with affinity for flexibility:
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
          - matchExpressions:
              - key: nvidia.com/gpu.memory
                operator: Gt
                values: ["40000"]
```

## 8.3 Keeping non-GPU pods off GPU nodes

Taint the GPU nodes:

```bash
kubectl taint nodes <gpu-node> nvidia.com/gpu=present:NoSchedule
```

GPU pods then tolerate the taint:

```yaml
tolerations:
  - key: nvidia.com/gpu
    operator: Exists
    effect: NoSchedule
```

> **Tip:** Enable the **`ExtendedResourceToleration`** admission plugin on the API server. It automatically adds the toleration to any pod that requests `nvidia.com/gpu`.

## 8.4 Avoid this common mistake

**Don't** set `NVIDIA_VISIBLE_DEVICES=all` in images or pod specs to get around the scheduler. The pod would see every GPU on the node, including GPUs allocated to other pods. The device plugin sets this variable (or CDI devices) correctly. Recent toolkit versions ignore the env var from unprivileged containers when `accept-nvidia-visible-devices-envvar-when-unprivileged=false` is configured, which is the recommended hardening.
