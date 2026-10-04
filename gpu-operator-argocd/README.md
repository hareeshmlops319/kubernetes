# NVIDIA GPU Operator with Argo CD

GitOps setup for deploying and operating the NVIDIA GPU Operator (chart v26.7.1) with Argo CD.

Full walkthrough: **https://hareeshmlops319.github.io/kubernetes/gitops-argocd/**

## Quick start (single cluster)

```bash
# 1. Custom health checks (ClusterPolicy, NVIDIADriver, Application)
kubectl -n argocd patch configmap argocd-cm --type merge \
  --patch-file gpu-operator-argocd/argocd-config/argocd-cm-health-patch.yaml

# 2. Bootstrap: the only manual apply
kubectl apply -n argocd -f gpu-operator-argocd/bootstrap/root-app.yaml

# 3. Wait until the GPU stack is ready
argocd app wait gpu-operator --health --timeout 1800
```

The manifests track `targetRevision: main`. If these files are on another branch, update
`targetRevision` in `bootstrap/root-app.yaml`, `apps/gpu-operator.yaml` and
`fleet/gpu-operator-appset.yaml`.

## Layout

| Path | Purpose |
|---|---|
| `bootstrap/root-app.yaml` | App-of-apps root; manages `apps/` |
| `apps/project.yaml` | `gpu-platform` AppProject (allowed sources, namespace, cluster-scoped kinds) |
| `apps/gpu-operator.yaml` | GPU Operator Application: NVIDIA chart + values from this repo |
| `fleet/gpu-operator-appset.yaml` | Multi-cluster ApplicationSet with canary/stable channels (use instead of `apps/gpu-operator.yaml`) |
| `values/common.yaml` | Base values: driver upgrade policy, sharing profiles, MIG layouts, DCGM metrics |
| `values/clusters/<name>.yaml` | Per-cluster overrides (file name = Argo CD cluster name) |
| `argocd-config/argocd-cm-health-patch.yaml` | Health checks to merge into `argocd-cm` |
| `hack/crd2schema.py` | Turns the chart's CRDs into strict JSON schemas for CI validation |

Pull requests touching this folder are checked by
`.github/workflows/gpu-operator-argocd-validate.yaml` (helm template + kubeconform).
