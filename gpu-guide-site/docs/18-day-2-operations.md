# 18. Day-2 Operations: Upgrades, Health, Reliability


## 18.1 Upgrading the GPU Operator

```bash
# 1. Read release notes; CRDs are NOT upgraded by helm automatically
kubectl apply -f https://raw.githubusercontent.com/NVIDIA/gpu-operator/<version>/deployments/gpu-operator/crds/nvidia.com_clusterpolicies.yaml
kubectl apply -f https://raw.githubusercontent.com/NVIDIA/gpu-operator/<version>/deployments/gpu-operator/crds/nvidia.com_nvidiadrivers.yaml

# 2. Upgrade the release
helm upgrade gpu-operator nvidia/gpu-operator -n gpu-operator \
  --version=<new-version> -f values-prod.yaml
```

(Check whether your version ships CRD-upgrade hooks. Recent charts include an upgrade-CRD job.)

## 18.2 Driver upgrades

When you change `driver.version`, the **upgrade controller** rolls through the nodes:

```
upgrade-required → cordon → wait-for-jobs → pod-deletion → drain
  → pod-restart (new driver) → validation → uncordon → upgrade-done
```

Track progress:

```bash
kubectl get nodes -L nvidia.com/gpu-driver-upgrade-state
```

Best practices:

- Use `maxParallelUpgrades` and `maxUnavailable` to protect capacity.
- Use `waitForCompletion.podSelector` to let training jobs finish.
- Test on a canary node pool first (the `NVIDIADriver` CRD makes this easy).
- Stay on an NVIDIA **production branch (PB)** or **LTSB** driver for stability.

## 18.3 GPU health management

- **DCGM diagnostics:** `dcgmi diag -r 1` (quick), `-r 3` (long, run in maintenance windows).
- **XID errors:** Check `dmesg | grep -i xid` on the node.

| XID | Meaning | Action |
|---|---|---|
| 13, 31, 43 | Application fault (illegal memory access, page fault) | Usually an application bug |
| 45 | Preemptive cleanup | Often follows another error |
| 48 | Double-bit ECC error | Drain, reset the GPU, RMA if it repeats |
| 63, 64 | ECC page retirement / row remap | Reset when idle. Check remap failure |
| 74 | NVLink error | Check hardware and cables, reset |
| 79 | GPU fell off the bus | Hardware/PCIe/power. Drain node, RMA |
| 92 | High single-bit ECC rate | Monitor, plan replacement |
| 94, 95 | Contained / uncontained ECC error | 95: reset the GPU. 94: the application is affected |

- **Automated remediation:** Node Problem Detector with GPU custom plugins, or NVIDIA's **NVSentinel** (GPU fault detection and remediation for Kubernetes) and similar tools. They taint or cordon unhealthy GPU nodes automatically.
- **Device plugin health:** The device plugin marks GPUs unhealthy on critical XIDs, which removes them from allocatable resources. Configure XIDs to skip with `DP_DISABLE_HEALTHCHECKS` if you need to (rarely).

## 18.4 Backup and GitOps

Keep the Helm values, the `ClusterPolicy`, sharing ConfigMaps, MIG configs, Kueue objects, and scheduler configs in Git. Manage them with Argo CD or Flux. Because GPU nodes are stateless with the operator, you can always rebuild them from Git.
