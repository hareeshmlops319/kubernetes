# 13. Performance Optimization: Kubernetes Level


## 13.1 Guaranteed QoS plus CPU pinning plus NUMA alignment

The data loader, preprocessing, and Python overhead often starve the GPU. Pin CPUs and align them with the GPU's NUMA node.

**Kubelet configuration:**

```yaml
apiVersion: kubelet.config.k8s.io/v1beta1
kind: KubeletConfiguration
cpuManagerPolicy: static
cpuManagerPolicyOptions:
  full-pcpus-only: "true"            # whole physical cores, no SMT sibling sharing
memoryManagerPolicy: Static
topologyManagerPolicy: single-numa-node   # or "restricted" / "best-effort"
topologyManagerScope: pod
reservedSystemCPUs: "0-3"
reservedMemory:
  - numaNode: 0
    limits:
      memory: 2Gi
kubeReserved:
  cpu: "1"
  memory: 2Gi
systemReserved:
  cpu: "1"
  memory: 2Gi
```

The NVIDIA device plugin reports NUMA hints to the Topology Manager, so GPU, CPU, and memory are aligned.

> **`single-numa-node`** rejects pods that can't be aligned (`TopologyAffinityError`). On 8-GPU nodes spanning 2 NUMA nodes, an 8-GPU pod can't fit in one NUMA node. Use `restricted`/`best-effort`, or the `prefer-closest-numa-nodes` policy option, for large pods.

**Pod (Guaranteed QoS, integer CPUs):**

```yaml
resources:
  requests:
    cpu: "16"
    memory: 128Gi
    nvidia.com/gpu: 2
  limits:
    cpu: "16"
    memory: 128Gi
    nvidia.com/gpu: 2
```

## 13.2 Shared memory (`/dev/shm`)

PyTorch DataLoader workers and NCCL use `/dev/shm`. The container default is 64 MB, which causes `Bus error` crashes or slowdowns.

```yaml
volumes:
  - name: dshm
    emptyDir:
      medium: Memory
      sizeLimit: 32Gi
containers:
  - volumeMounts:
      - name: dshm
        mountPath: /dev/shm
```

## 13.3 Image pull time

GPU images are large (10–30 GB). Slow pulls waste expensive GPU time.

- Pre-pull images with a DaemonSet, or bake them into node images.
- Use a local registry mirror or a pull-through cache.
- Use lazy-loading snapshotters (**SOCI**, **stargz/eStargz**, **Nydus**).
- Keep images lean: use `-runtime` rather than `-devel` bases and multi-stage builds.
- Set `imagePullPolicy: IfNotPresent`.

## 13.4 Model loading time (inference cold starts)

- Cache model weights on node-local NVMe (hostPath or local PV), or use a shared read-only PVC.
- Use safetensors with memory-mapped loading.
- Consider tools such as NVIDIA Run:ai Model Streamer or similar streaming loaders.
- Keep a warm pool (a minimum number of replicas) for latency-sensitive services.

## 13.5 Gang scheduling for distributed jobs

Distributed training needs **all** workers at once. If you schedule them one by one, partial allocations can deadlock and leave GPUs idle. Use a gang-aware scheduler:

- **Kueue** (admits the whole workload or nothing; works with Job, JobSet, PyTorchJob, RayJob, and others)
- **Volcano** (PodGroup with `minMember`)
- **Kubernetes native gang scheduling** (the Workload API, alpha in recent releases)
- **NVIDIA KAI Scheduler** (open-sourced from Run:ai; GPU-aware, gang, fractional GPUs, hierarchical queues)

## 13.6 Topology-aware placement across nodes

For multi-node training, place workers on nodes under the **same leaf switch / rack / NVLink domain**:

- Kueue **Topology Aware Scheduling (TAS)** with node labels such as `cloud.provider.com/topology-block` and `.../topology-rack`.
- Pod affinity on rack or block labels.
- On GB200 NVL72, use DRA **ComputeDomains** so pods share one NVLink domain.

## 13.7 Bin-packing GPUs (reduce fragmentation)

The default scheduler **spreads** pods (`LeastAllocated`), which fragments GPUs. A cluster can end up with 16 free GPUs spread 2 per node, so an 8-GPU job can't fit. Configure a bin-packing profile:

```yaml
apiVersion: kubescheduler.config.k8s.io/v1
kind: KubeSchedulerConfiguration
profiles:
  - schedulerName: gpu-binpack
    pluginConfig:
      - name: NodeResourcesFit
        args:
          scoringStrategy:
            type: MostAllocated
            resources:
              - name: nvidia.com/gpu
                weight: 10
              - name: cpu
                weight: 1
              - name: memory
                weight: 1
```

GPU pods then set `schedulerName: gpu-binpack`. The KAI Scheduler and Volcano also offer bin-pack policies.
