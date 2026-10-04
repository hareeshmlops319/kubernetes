# 23. Further Reading


- GPU Operator docs: https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/
- GPU Operator source: https://github.com/NVIDIA/gpu-operator
- NVIDIA device plugin: https://github.com/NVIDIA/k8s-device-plugin
- NVIDIA DRA driver for GPUs: https://github.com/NVIDIA/k8s-dra-driver-gpu
- NVIDIA Container Toolkit: https://github.com/NVIDIA/nvidia-container-toolkit
- DCGM exporter: https://github.com/NVIDIA/dcgm-exporter
- MIG user guide: https://docs.nvidia.com/datacenter/tesla/mig-user-guide/
- MIG parted (MIG manager config format): https://github.com/NVIDIA/mig-parted
- NVIDIA Network Operator: https://docs.nvidia.com/networking/display/kubernetes
- NCCL docs and env vars: https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/env.html
- nccl-tests: https://github.com/NVIDIA/nccl-tests
- KAI Scheduler: https://github.com/NVIDIA/KAI-Scheduler
- Kueue: https://kueue.sigs.k8s.io/
- Kubernetes DRA: https://kubernetes.io/docs/concepts/scheduling-eviction/dynamic-resource-allocation/
- Kubernetes device plugins: https://kubernetes.io/docs/concepts/extend-kubernetes/compute-storage-net/device-plugins/
- Kubernetes Topology Manager: https://kubernetes.io/docs/tasks/administer-cluster/topology-manager/
- XID errors catalog: https://docs.nvidia.com/deploy/xid-errors/
- Grafana DCGM dashboard: https://grafana.com/grafana/dashboards/12239

---

*Values, profile names, and metric names differ between GPU models, operator versions, and cloud providers. Check them against your environment's documentation and test changes on a canary node pool before rolling them out to the fleet.*
