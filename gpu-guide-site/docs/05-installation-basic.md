# 5. Installation (Basic)


## 5.1 Add the Helm repo

```bash
helm repo add nvidia https://helm.ngc.nvidia.com/nvidia
helm repo update
helm search repo nvidia/gpu-operator --versions | head
```

## 5.2 Create the namespace with privileged pod security

```bash
kubectl create ns gpu-operator
kubectl label --overwrite ns gpu-operator pod-security.kubernetes.io/enforce=privileged
```

## 5.3 Install with defaults

```bash
helm install gpu-operator nvidia/gpu-operator \
  -n gpu-operator \
  --version=<chart-version> \
  --wait
```

This deploys NFD, the driver, the toolkit, the device plugin, GFD, DCGM, the DCGM exporter, the MIG manager, and the validator.

> If NFD already runs in your cluster, add `--set nfd.enabled=false` to avoid running two copies.

## 5.4 Watch it come up

```bash
kubectl get pods -n gpu-operator -w
```

Expected final state (names vary):

```
gpu-feature-discovery-xxxxx                    1/1  Running
gpu-operator-xxxxxxxxxx-xxxxx                  1/1  Running
nvidia-container-toolkit-daemonset-xxxxx       1/1  Running
nvidia-cuda-validator-xxxxx                    0/1  Completed
nvidia-dcgm-exporter-xxxxx                     1/1  Running
nvidia-device-plugin-daemonset-xxxxx           1/1  Running
nvidia-driver-daemonset-xxxxx                  1/1  Running
nvidia-operator-validator-xxxxx                1/1  Running
```

The first install takes about 5 to 10 minutes per node because the driver container compiles kernel modules.
