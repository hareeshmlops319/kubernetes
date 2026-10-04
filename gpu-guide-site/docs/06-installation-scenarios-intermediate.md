# 6. Installation Scenarios (Intermediate)


## 6.1 A production-style `values.yaml`

```yaml
# values-prod.yaml
operator:
  defaultRuntime: containerd

nfd:
  enabled: true

driver:
  enabled: true
  version: "<driver-version>"        # pin it, e.g. a production branch (R550 / R570 / R580)
  kernelModuleType: auto              # auto | open | proprietary
  rdma:
    enabled: false                    # true for GPUDirect RDMA (with Network Operator)
  upgradePolicy:
    autoUpgrade: true
    maxParallelUpgrades: 1
    maxUnavailable: 25%
    drain:
      enable: true
      force: false
      deleteEmptyDir: true
      timeoutSeconds: 300
    podDeletion:
      force: false
      deleteEmptyDir: true
      timeoutSeconds: 300
    waitForCompletion:
      timeoutSeconds: 0
      podSelector: ""                 # e.g. "app=training" to wait for jobs to finish

toolkit:
  enabled: true

cdi:
  enabled: true
  default: false

devicePlugin:
  enabled: true
  config:
    name: ""                          # ConfigMap for time-slicing/MPS (Section 9)
    default: ""

mig:
  strategy: single                    # single | mixed

migManager:
  enabled: true

dcgm:
  enabled: true

dcgmExporter:
  enabled: true
  serviceMonitor:
    enabled: true                     # requires Prometheus Operator CRDs
    interval: 15s

gfd:
  enabled: true

validator:
  plugin:
    env:
      - name: WITH_WORKLOAD
        value: "false"

# Keep operator components off non-GPU nodes and tolerate GPU taints
daemonsets:
  tolerations:
    - key: nvidia.com/gpu
      operator: Exists
      effect: NoSchedule
  priorityClassName: system-node-critical
```

```bash
helm upgrade --install gpu-operator nvidia/gpu-operator \
  -n gpu-operator --version=<chart-version> -f values-prod.yaml --wait
```

## 6.2 Drivers already installed on the host

```bash
helm install gpu-operator nvidia/gpu-operator -n gpu-operator \
  --set driver.enabled=false
```

If the Container Toolkit is also pre-installed on the host, add `--set toolkit.enabled=false`.

## 6.3 Precompiled drivers (faster, Secure Boot friendly)

```bash
--set driver.usePrecompiled=true \
--set driver.version="<driver-branch, e.g. 550>"
```

Precompiled images exist only for specific kernel flavors (mainly Ubuntu). They skip on-node compilation, so nodes come up in seconds rather than minutes.

## 6.4 Per-node-pool drivers with the `NVIDIADriver` CRD

You can run different driver versions or types on different node pools, for example a stable branch on inference nodes and a new branch on training nodes.

```bash
helm install gpu-operator nvidia/gpu-operator -n gpu-operator \
  --set driver.nvidiaDriverCRD.enabled=true \
  --set driver.nvidiaDriverCRD.deployDefaultCR=false
```

```yaml
apiVersion: nvidia.com/v1alpha1
kind: NVIDIADriver
metadata:
  name: h100-training
spec:
  driverType: gpu
  kernelModuleType: open
  version: "<driver-version>"
  repository: nvcr.io/nvidia
  image: driver
  nodeSelector:
    nvidia.com/gpu.product: NVIDIA-H100-80GB-HBM3
---
apiVersion: nvidia.com/v1alpha1
kind: NVIDIADriver
metadata:
  name: l4-inference
spec:
  driverType: gpu
  version: "<other-driver-version>"
  repository: nvcr.io/nvidia
  image: driver
  nodeSelector:
    nvidia.com/gpu.product: NVIDIA-L4
```

> The node selectors of different `NVIDIADriver` CRs must not overlap.

## 6.5 Containerd variants (k3s, RKE2, MicroK8s)

These distributions keep containerd config in non-standard paths:

```yaml
toolkit:
  env:
    - name: CONTAINERD_CONFIG
      value: /var/lib/rancher/rke2/agent/etc/containerd/config.toml.tmpl   # RKE2
    - name: CONTAINERD_SOCKET
      value: /run/k3s/containerd/containerd.sock
    - name: CONTAINERD_RUNTIME_CLASS
      value: nvidia
    - name: CONTAINERD_SET_AS_DEFAULT
      value: "true"
```

For k3s the config is `/var/lib/rancher/k3s/agent/etc/containerd/config.toml.tmpl`. Recent operator versions also support containerd drop-in config files.

## 6.6 Managed clouds

| Platform | Notes |
|---|---|
| **AWS EKS** | EKS GPU AMIs (AL2023 NVIDIA, Bottlerocket NVIDIA) ship with drivers, so use `driver.enabled=false` and often `toolkit.enabled=false`. With a plain Ubuntu AMI, use the full operator |
| **GKE** | GKE can install drivers itself (`gpu-driver-version=latest` on the node pool). If you use the operator, set `driver.enabled=false` and `toolkit.enabled=false` and use GKE's device plugin, **or** create node pools with `gpu-driver-version=disabled` and Ubuntu images and let the operator manage everything. Don't mix the two approaches |
| **AKS** | Create GPU node pools with `--skip-gpu-driver-install` (or the equivalent option in current AKS), then install the full operator |
| **OpenShift** | Install NFD and the GPU Operator from OperatorHub. Drivers are built against RHCOS via the Driver Toolkit, and entitlement is not needed on modern OCP |

## 6.7 Air-gapped / disconnected clusters

1. Mirror all images (operator, driver for each OS and kernel, toolkit, device plugin, DCGM, exporter, validator, NFD, MIG manager) to an internal registry.
2. Set `--set operator.repository=...`, `driver.repository=...`, and so on, or use a global registry override.
3. For on-node driver compilation, provide a **local package repository** via a ConfigMap (`driver.repoConfig.configMapName`), or use precompiled drivers.
4. Provide custom CA certificates via `driver.certConfig.name` if your mirror uses a private CA.

## 6.8 Proxy environments

```yaml
driver:
  env:
    - name: HTTPS_PROXY
      value: http://proxy.example.com:3128
    - name: HTTP_PROXY
      value: http://proxy.example.com:3128
    - name: NO_PROXY
      value: .svc,.cluster.local,10.0.0.0/8
```
