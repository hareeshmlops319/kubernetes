# 20. Troubleshooting Playbook


## 20.1 First commands

```bash
kubectl get pods -n gpu-operator -o wide
kubectl get clusterpolicies.nvidia.com -o yaml | yq '.items[0].status'
kubectl describe node <node> | grep -A10 -i 'allocatable\|nvidia'
kubectl logs -n gpu-operator deploy/gpu-operator
kubectl logs -n gpu-operator ds/nvidia-driver-daemonset -c nvidia-driver-ctr
kubectl logs -n gpu-operator ds/nvidia-operator-validator -c driver-validation
kubectl logs -n gpu-operator ds/nvidia-device-plugin-daemonset
# On the node
ls /run/nvidia/validations/
dmesg | grep -iE 'nvidia|nvrm|xid'
```

## 20.2 Common issues

| Symptom | Likely cause | Fix |
|---|---|---|
| No operator pods on a GPU node | NFD didn't label the node (`pci-10de.present`) | Check NFD worker pods. Check for duplicate NFD installs |
| Driver pod `CrashLoopBackOff`, "Could not resolve Linux kernel version" | Kernel headers unavailable for this kernel | Update the OS repos, use a supported kernel, or use precompiled drivers |
| Driver fails, "Key was rejected by service" | Secure Boot blocks unsigned modules | Disable Secure Boot or use signed/precompiled drivers |
| Driver fails, "nouveau" in use | Nouveau loaded | Blacklist nouveau and reboot |
| Driver pod hangs, "Unable to load nvidia module: already in use" | Host driver is pre-installed | `driver.enabled=false` |
| Toolkit OK but pods fail with `could not select device driver "" with capabilities: [[gpu]]` | Runtime not configured, or the wrong containerd config path | Check `toolkit.env` CONTAINERD_CONFIG/SOCKET for your distro. Restart containerd |
| `nvidia.com/gpu: 0` allocatable | Device plugin not registered, all GPUs unhealthy, or MIG mixed strategy hiding GPUs | Device plugin logs. `nvidia-smi`. Check MIG strategy |
| Pod `Pending: Insufficient nvidia.com/gpu` | Real shortage, or fragmentation | Bin-packing, autoscaling, check taints and tolerations |
| `TopologyAffinityError` | Topology Manager can't align NUMA | Use `restricted`/`best-effort`, or fewer GPUs per pod |
| CUDA error 802 `system not yet initialized` | Fabric Manager not running (NVSwitch systems) | Check the fabric manager in driver pod logs. Match versions |
| CUDA error 804 / "forward compatibility" | Container CUDA newer than the driver | Upgrade the driver or use an older CUDA image |
| `Failed to initialize NVML: Unknown Error` after a while | cgroup driver/systemd reload removed device access (cgroup v2 + runc) | Use CDI, update the toolkit, or use the systemd cgroup driver consistently |
| `mig.config.state=failed` | GPU in use, or MIG enable needs a reset | Drain workloads, check MIG manager logs, reboot if needed |
| DCGM exporter shows no `PROF_` metrics | Profiling metrics not in CSV, or not supported (some GPUs, vGPU) | Custom CSV (Section 11.3) |
| Two pods see the same GPU unexpectedly | Time-slicing on, or `NVIDIA_VISIBLE_DEVICES=all` in the image | Check sharing config. Harden env var handling |
| `Bus error` in PyTorch DataLoader | `/dev/shm` too small | Memory-backed emptyDir (Section 13.2) |
| NCCL slow, logs show `NET/Socket` | RDMA not used | Network Operator, `IPC_LOCK`, `NCCL_IB_HCA`, GDR settings |

## 20.3 Uninstalling cleanly

```bash
helm uninstall gpu-operator -n gpu-operator
kubectl delete crd clusterpolicies.nvidia.com nvidiadrivers.nvidia.com
# Driver modules stay loaded until reboot; reboot GPU nodes for a clean state
```
