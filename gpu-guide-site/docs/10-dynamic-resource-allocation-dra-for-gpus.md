# 10. Dynamic Resource Allocation (DRA) for GPUs


DRA (`resource.k8s.io/v1`, GA in Kubernetes 1.34) replaces "count of opaque devices" with **claims over devices that have attributes**. NVIDIA provides the **NVIDIA DRA Driver for GPUs** (`k8s-dra-driver-gpu`), which the GPU Operator can deploy alongside or instead of the device plugin.

## 10.1 What DRA adds

- Select GPUs by **attributes** using CEL, for example memory ≥ 40Gi, a specific architecture, or a driver version.
- **Shared claims:** Multiple pods or containers can reference the same `ResourceClaim`, so they share one GPU explicitly.
- **Dynamic MIG** and partitioning without pre-labeling nodes (driver feature, check maturity).
- **ComputeDomains** for multi-node NVLink (GB200 NVL72): IMEX channels are managed for you.
- **Admin access** and device health status reporting.

## 10.2 Example

```yaml
apiVersion: resource.k8s.io/v1
kind: ResourceClaimTemplate
metadata:
  name: big-gpu
spec:
  spec:
    devices:
      requests:
        - name: gpu
          exactly:
            deviceClassName: gpu.nvidia.com
            selectors:
              - cel:
                  expression: |
                    device.capacity['gpu.nvidia.com'].memory.compareTo(quantity('40Gi')) >= 0
---
apiVersion: v1
kind: Pod
metadata:
  name: dra-gpu-pod
spec:
  resourceClaims:
    - name: gpu
      resourceClaimTemplateName: big-gpu
  containers:
    - name: app
      image: nvcr.io/nvidia/cuda:12.6.0-base-ubuntu22.04
      command: ["nvidia-smi", "-L"]
      resources:
        claims:
          - name: gpu
```

## 10.3 Two containers sharing one GPU

```yaml
apiVersion: resource.k8s.io/v1
kind: ResourceClaim
metadata:
  name: shared-gpu
spec:
  devices:
    requests:
      - name: gpu
        exactly:
          deviceClassName: gpu.nvidia.com
---
# Pods A and B both reference resourceClaimName: shared-gpu
spec:
  resourceClaims:
    - name: gpu
      resourceClaimName: shared-gpu
```

> **Device plugin or DRA?** Use the device plugin today for simple, stable fleets. Adopt DRA when you need attribute-based selection, explicit sharing, or GB200 ComputeDomains. Don't advertise the same GPUs through both on the same node.
