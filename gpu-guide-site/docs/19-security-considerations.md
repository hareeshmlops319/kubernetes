# 19. Security Considerations


- **Privileged components:** The operator's DaemonSets are privileged by design. Isolate the `gpu-operator` namespace and restrict who can modify `ClusterPolicy`.
- **Don't run workloads as privileged** just to "make GPUs work". The device plugin and CDI handle device access.
- **Block `NVIDIA_VISIBLE_DEVICES` abuse:** Configure the toolkit so unprivileged containers can't request GPUs via env vars (CDI or volume-mount device-list strategy: `devicePlugin.env: DEVICE_LIST_STRATEGY=volume-mounts` or CDI).
- **Multi-tenancy:** Time-slicing and MPS give **no security isolation**. Use MIG, separate GPUs, or confidential computing for untrusted tenants.
- **Confidential Computing:** Hopper and Blackwell support GPU confidential computing (CC mode) with Kata Containers and confidential VMs. The operator supports it via `ccManager`.
- **Keep the NVIDIA Container Toolkit patched.** There have been container escape CVEs (for example CVE-2024-0132 and CVE-2025-23266). Track NVIDIA security bulletins.
- **Supply chain:** Pull from `nvcr.io`, mirror to a trusted registry, verify signatures where available, and pin image digests.
- **Network policies:** Restrict access to the DCGM exporter's port 9400 and to the operator's metrics.
