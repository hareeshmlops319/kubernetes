# 2. What the GPU Operator Is and Why You Need It


The **NVIDIA GPU Operator** is a Kubernetes operator. It uses the operator pattern (a CRD plus a controller) to manage the full NVIDIA software stack on GPU nodes as **containers**. It is driven by a single custom resource, `ClusterPolicy` (plus an optional `NVIDIADriver` CR).

**Benefits:**

- **Immutable, uniform nodes:** You can use a stock OS image without baking drivers into it. The driver runs as a container.
- **Declarative:** The whole GPU stack is versioned in Helm values or a `ClusterPolicy`.
- **Automatic node onboarding:** When a GPU node joins, the operator detects it through NFD labels and deploys the stack.
- **Managed upgrades:** Rolling driver upgrades with cordon, drain, and validation.
- **Built-in observability:** DCGM exporter metrics are ready for Prometheus.
- **Advanced features:** MIG management, time-slicing, MPS, vGPU, GPUDirect RDMA, GPUDirect Storage, Kata/confidential containers.
