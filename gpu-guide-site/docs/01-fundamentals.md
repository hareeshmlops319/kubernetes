# 1. Fundamentals: GPUs in Kubernetes


## 1.1 How Kubernetes sees hardware

Kubernetes natively schedules only **CPU**, **memory**, **ephemeral storage**, and **hugepages**. It knows nothing about GPUs. GPUs reach Kubernetes through two mechanisms:

| Mechanism | Description | Status |
|---|---|---|
| **Device Plugin framework** | A DaemonSet registers an *extended resource* (for example `nvidia.com/gpu`) with the kubelet over gRPC. The kubelet advertises an integer count, and the device plugin decides which devices a container gets. | Stable, the most widely used |
| **Dynamic Resource Allocation (DRA)** | A richer API with `ResourceClaim`, `DeviceClass`, and `ResourceSlice`. It supports attribute-based selection, sharing, and partitioning. | GA in Kubernetes 1.34 (`resource.k8s.io/v1`) |

## 1.2 What a container needs to use a GPU

For a containerized process to run CUDA code, all of the following must be in place:

1. **The NVIDIA kernel driver** (`nvidia.ko`, `nvidia-uvm.ko`, `nvidia-modeset.ko`, and optionally `nvidia-peermem.ko`) loaded on the host.
2. **Device nodes** (`/dev/nvidia0`, `/dev/nvidiactl`, `/dev/nvidia-uvm`, and so on) exposed inside the container.
3. **User-space driver libraries** (`libcuda.so`, `libnvidia-ml.so`, and so on) that match the kernel driver version, mounted into the container.
4. **A container runtime hook or CDI spec** (NVIDIA Container Toolkit) that injects items 2 and 3.
5. **A scheduler-visible resource** (from the device plugin or DRA) so pods land on GPU nodes.
6. **The CUDA runtime and your application** inside the container image (for example `nvidia/cuda:12.x-runtime`).

> **Key idea:** The container image ships the **CUDA toolkit/runtime**. The host provides the **driver**. A newer driver supports older CUDA runtimes (backward compatibility). Forward compatibility, where an older driver runs a newer CUDA, is possible only on datacenter GPUs with the `cuda-compat` package.

## 1.3 The manual way (and why it hurts)

Without the operator, you would have to do the following on every GPU node:

- Install the driver package that matches the kernel, and rebuild it on every kernel update.
- Install and configure the NVIDIA Container Toolkit for containerd or CRI-O.
- Deploy the device plugin DaemonSet.
- Deploy DCGM and the DCGM exporter for metrics.
- Deploy Node Feature Discovery and GPU Feature Discovery for labels.
- Configure MIG by hand.
- Coordinate driver upgrades with node drains.

The GPU Operator automates all of this.
