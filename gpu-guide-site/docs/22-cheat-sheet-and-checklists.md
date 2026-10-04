# 22. Cheat Sheet and Checklists


## 22.1 Commands

```bash
# Install
helm install gpu-operator nvidia/gpu-operator -n gpu-operator --create-namespace

# Status
kubectl get clusterpolicy cluster-policy -o jsonpath='{.status.state}'
kubectl get nodes -L nvidia.com/gpu.product,nvidia.com/gpu.count,nvidia.com/mig.config.state

# GPU info
kubectl exec -n gpu-operator ds/nvidia-driver-daemonset -- nvidia-smi
kubectl exec -n gpu-operator ds/nvidia-driver-daemonset -- nvidia-smi topo -m
kubectl exec -n gpu-operator ds/nvidia-driver-daemonset -- nvidia-smi mig -lgip

# Time-slicing / MPS on
kubectl patch clusterpolicies.nvidia.com/cluster-policy --type merge \
  -p '{"spec":{"devicePlugin":{"config":{"name":"<cm>","default":"any"}}}}'

# MIG layout
kubectl label node <n> nvidia.com/mig.config=all-1g.10gb --overwrite

# Per-node sharing profile
kubectl label node <n> nvidia.com/device-plugin.config=<profile> --overwrite

# Metrics
kubectl port-forward -n gpu-operator svc/nvidia-dcgm-exporter 9400:9400
curl -s localhost:9400/metrics | grep DCGM_FI_DEV_GPU_UTIL

# Health
kubectl exec -n gpu-operator ds/nvidia-dcgm -- dcgmi diag -r 1
```

## 22.2 Production readiness checklist

**Setup**
- [ ] Operator chart and driver version pinned in Git
- [ ] Driver on a production branch. Open kernel modules on Hopper and newer
- [ ] CDI enabled
- [ ] `gpu-operator` namespace privileged. Other namespaces restricted
- [ ] GPU nodes tainted. `ExtendedResourceToleration` enabled
- [ ] Images mirrored (if air-gapped or rate-limited)

**Observability**
- [ ] DCGM exporter with profiling metrics, a ServiceMonitor, and a Grafana dashboard
- [ ] Alerts: XID, DBE ECC, temperature, operator not ready, idle allocated GPUs
- [ ] Per-namespace GPU-hours (chargeback/showback)

**Efficiency**
- [ ] Sharing strategy chosen per node pool (MIG/MPS/time-slicing/none)
- [ ] Kueue (or KAI/Volcano) quotas with borrowing and preemption
- [ ] Bin-packing scheduler profile for GPUs
- [ ] Node autoscaling (scale to zero where possible), and KEDA for inference
- [ ] Idle culling for notebooks. TTLs on Jobs

**Performance**
- [ ] `/dev/shm` sized for training pods
- [ ] CPU manager static plus Topology Manager for latency- or throughput-critical nodes
- [ ] GPUDirect RDMA verified with nccl-tests (multi-node)
- [ ] Mixed precision/FP8 in training. Optimized serving engines for inference
- [ ] Data pipeline verified to keep `SM_ACTIVE` high (Nsight Systems)
- [ ] Images and models cached on nodes

**Reliability**
- [ ] Driver upgrade policy with drain and `maxParallelUpgrades`
- [ ] Canary node pool for driver and operator upgrades
- [ ] Periodic DCGM diagnostics. Automated cordoning of unhealthy GPUs
- [ ] Training jobs checkpoint regularly (preemption- and failure-safe)
