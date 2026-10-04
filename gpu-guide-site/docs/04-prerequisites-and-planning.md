# 4. Prerequisites and Planning


## 4.1 Checklist

- [ ] **Supported GPU:** A data center GPU (A100, H100, H200, B200, GB200, L40S, L4, A10, T4, V100, and others). Consumer GeForce cards often work for development but are not officially supported.
- [ ] **Supported OS:** Ubuntu 20.04, 22.04, or 24.04, RHEL/Rocky 8.x or 9.x, Red Hat CoreOS (OpenShift). Check the support matrix for your operator version.
- [ ] **Kubernetes:** A version within the operator's supported range. Containerd 1.6+ or CRI-O.
- [ ] **No pre-installed driver** on the node, **or** set `driver.enabled=false` if one is already there.
- [ ] **Nouveau driver disabled.** The driver container handles this, but check if it fails.
- [ ] **Secure Boot:** Either disabled, or use precompiled/signed drivers. Unsigned kernel modules will not load under Secure Boot.
- [ ] **Kernel headers available.** The driver container needs matching headers, or use precompiled driver images.
- [ ] **Internet access** to `nvcr.io` and OS package repositories, **or** a mirrored registry for air-gapped setups.
- [ ] **Pod Security:** The `gpu-operator` namespace needs `privileged` pod security admission.
- [ ] **Helm 3** installed.

## 4.2 Decide up front

| Decision | Options | Guidance |
|---|---|---|
| Driver management | Operator-managed (container) vs. host-installed | Use operator-managed for uniform fleets. Use host-installed for managed clouds whose node images already have drivers (GKE COS, some EKS AMIs) |
| Driver type | Default (compiled on node), precompiled, open kernel modules | Use **open kernel modules** (`driver.kernelModuleType=open`) for Hopper, Blackwell, and newer. They are required on Blackwell |
| Runtime injection | Legacy runtime hook vs. **CDI** | Prefer CDI (`cdi.enabled=true`). It is cleaner and the future direction |
| Sharing | None, time-slicing, MPS, MIG, vGPU | See [Section 9](09-gpu-sharing.md) |
| Allocation API | Device plugin vs. DRA | Use the device plugin for simplicity. Use DRA for advanced selection and partitioning |
| Networking | Ethernet vs. InfiniBand/RoCE with GPUDirect RDMA | Multi-node training needs RDMA. Pair with the NVIDIA Network Operator |

## 4.3 Check the hardware first

```bash
# On the node
lspci | grep -i nvidia
uname -r
cat /etc/os-release
mokutil --sb-state          # Secure Boot status
lsmod | grep -E 'nouveau|nvidia'
```
