# 7. Verifying the Installation


## 7.1 Check node resources and labels

```bash
kubectl get nodes -o custom-columns=NAME:.metadata.name,GPU:.status.allocatable.'nvidia\.com/gpu'
kubectl get node <node> --show-labels | tr ',' '\n' | grep nvidia.com
```

Important GFD labels:

```
nvidia.com/gpu.present=true
nvidia.com/gpu.product=NVIDIA-H100-80GB-HBM3
nvidia.com/gpu.memory=81559
nvidia.com/gpu.count=8
nvidia.com/gpu.family=hopper
nvidia.com/gpu.compute.major=9
nvidia.com/cuda.driver.major=12
nvidia.com/mig.capable=true
nvidia.com/gpu.replicas=1
nvidia.com/gpu.sharing-strategy=none
nvidia.com/gpu.deploy.driver=true
```

## 7.2 Run a CUDA test pod

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: cuda-vectoradd
spec:
  restartPolicy: OnFailure
  containers:
    - name: cuda-vectoradd
      image: nvcr.io/nvidia/k8s/cuda-sample:vectoradd-cuda12.5.0
      resources:
        limits:
          nvidia.com/gpu: 1
```

```bash
kubectl apply -f cuda-vectoradd.yaml
kubectl logs cuda-vectoradd
# [Vector addition of 50000 elements] ... Test PASSED
```

## 7.3 Run nvidia-smi from inside the driver container

```bash
kubectl exec -n gpu-operator -it ds/nvidia-driver-daemonset -- nvidia-smi
kubectl exec -n gpu-operator -it ds/nvidia-driver-daemonset -- nvidia-smi topo -m
```

## 7.4 Check ClusterPolicy status

```bash
kubectl get clusterpolicies.nvidia.com cluster-policy -o jsonpath='{.status.state}'
# ready
```
