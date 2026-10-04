# 2. Workloads & Scheduling (15%)

**Level: Beginner → Intermediate.** These topics also show up inside troubleshooting and networking tasks, so they're worth more than their 15%.

---

## 2.1 Deployments, rolling updates and rollbacks

```bash
k create deploy web --image=nginx:1.25 --replicas=3
k set image deploy/web nginx=nginx:1.27          # container name = image name by default
k annotate deploy web kubernetes.io/change-cause="upgrade to 1.27"   # shows in history
k rollout status deploy/web
k rollout history deploy/web
k rollout history deploy/web --revision=2
k rollout undo deploy/web                        # previous revision
k rollout undo deploy/web --to-revision=1
k rollout pause deploy/web / k rollout resume deploy/web
k rollout restart deploy/web                     # re-create pods (e.g. after ConfigMap change)
```

Strategy tuning:

```yaml
spec:
  strategy:
    type: RollingUpdate          # or Recreate (all old pods killed first)
    rollingUpdate:
      maxSurge: 25%              # extra pods allowed during update
      maxUnavailable: 0          # zero-downtime
  minReadySeconds: 10
  revisionHistoryLimit: 5
```

**Other workload kinds to know:** ReplicaSet (Deployments manage these), DaemonSet (one pod per node; no `create` generator, so generate a Deployment and change the kind, then remove `replicas` and `strategy`), StatefulSet (stable names and per-pod PVCs via `volumeClaimTemplates`, needs a headless Service), Job (`completions`, `parallelism`, `backoffLimit`, `activeDeadlineSeconds`), CronJob (`schedule`, `concurrencyPolicy`, `successfulJobsHistoryLimit`).

---

## 2.2 ConfigMaps and Secrets

```bash
k create cm app-cfg --from-literal=MODE=prod --from-literal=LOG=debug
k create secret generic db --from-literal=USER=admin --from-literal=PASS=s3cr3t
```

```yaml
spec:
  containers:
  - name: app
    image: nginx
    env:
    - name: MODE                       # single key
      valueFrom:
        configMapKeyRef: {name: app-cfg, key: MODE}
    - name: DB_PASS
      valueFrom:
        secretKeyRef: {name: db, key: PASS}
    envFrom:                           # all keys as env vars
    - configMapRef: {name: app-cfg}
    - secretRef: {name: db}
    volumeMounts:
    - name: cfg
      mountPath: /etc/app              # each key becomes a file
      readOnly: true
  volumes:
  - name: cfg
    configMap:
      name: app-cfg
  # - name: creds
  #   secret:
  #     secretName: db
  #     defaultMode: 0400
```

- Env vars **don't** update when the ConfigMap changes. Mounted volumes do (eventually), except with `subPath`. After a change, run `k rollout restart`.
- Secrets are base64-*encoded*, not encrypted. Encryption at rest needs an `EncryptionConfiguration` on the API server.
- `immutable: true` stops edits (and improves performance).

---

## 2.3 Workload autoscaling

**HPA** needs **metrics-server** (`k top pods` must work) and **CPU requests** on the pods.

```bash
k autoscale deploy web --min=2 --max=10 --cpu-percent=70
k get hpa
```

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: AverageValue
        averageValue: 500Mi
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300   # wait 5 min before scaling down
```

- `TARGETS: <unknown>/70%` means metrics-server is missing or broken, or the pods have no CPU requests.
- **VPA** (Vertical Pod Autoscaler) is a separate add-on with its own CRDs. It adjusts requests and limits. Know what it does; installing it is less likely.
- **In-place pod resize:** Recent versions can change container CPU and memory without recreating the pod (`k patch pod ... --subresource resize`). Check whether it's GA in your exam's version.

---

## 2.4 Self-healing primitives

```yaml
spec:
  containers:
  - name: app
    image: nginx
    livenessProbe:                 # failing -> container restarted
      httpGet: {path: /healthz, port: 80}
      initialDelaySeconds: 10
      periodSeconds: 10
      failureThreshold: 3
    readinessProbe:                # failing -> removed from Service endpoints
      tcpSocket: {port: 80}
      periodSeconds: 5
    startupProbe:                  # protects slow starters; other probes wait for it
      exec: {command: ["cat", "/tmp/ready"]}
      failureThreshold: 30
      periodSeconds: 10
  restartPolicy: Always            # Always (Deployments) | OnFailure | Never (Jobs)
```

Also know: ReplicaSets replace dead pods, **PodDisruptionBudgets** protect availability during drains (`k create pdb web --selector=app=web --min-available=2`), and multiple replicas plus topology spread constraints survive node loss.

### Init containers and native sidecars

```yaml
spec:
  initContainers:
  - name: wait-db                    # runs to completion BEFORE app starts
    image: busybox:1.36
    command: ["sh", "-c", "until nslookup db; do sleep 2; done"]
  - name: log-shipper                # native sidecar: restartPolicy Always
    image: busybox:1.36              # starts before app, runs alongside it,
    restartPolicy: Always            # stopped after app exits
    command: ["sh", "-c", "tail -F /var/log/app/app.log"]
    volumeMounts:
    - {name: logs, mountPath: /var/log/app}
  containers:
  - name: app
    image: busybox:1.36
    command: ["sh", "-c", "while true; do date >> /var/log/app/app.log; sleep 5; done"]
    volumeMounts:
    - {name: logs, mountPath: /var/log/app}
  volumes:
  - name: logs
    emptyDir: {}
```

"Add a sidecar that streams the log file" is a classic task. The classic answer is a second entry under `containers`. The native-sidecar form above (GA since v1.33) is the modern answer. Use whichever the task asks for.

---

## 2.5 Resources, LimitRange, ResourceQuota

```yaml
resources:
  requests: {cpu: 250m, memory: 128Mi}   # used for SCHEDULING
  limits:   {cpu: 500m, memory: 256Mi}   # cpu throttled; memory over limit -> OOMKilled
```

QoS classes: **Guaranteed** (requests = limits for all containers), **Burstable** (some requests set), and **BestEffort** (none). BestEffort pods are evicted first.

```yaml
apiVersion: v1
kind: LimitRange                  # per-container defaults/min/max in a namespace
metadata: {name: defaults, namespace: dev}
spec:
  limits:
  - type: Container
    default:        {cpu: 500m, memory: 256Mi}   # default limits
    defaultRequest: {cpu: 100m, memory: 128Mi}   # default requests
    max:            {cpu: "1",  memory: 1Gi}
---
apiVersion: v1
kind: ResourceQuota               # namespace totals
metadata: {name: q, namespace: dev}
spec:
  hard:
    pods: "10"
    requests.cpu: "4"
    requests.memory: 8Gi
    limits.memory: 16Gi
```

With a quota on cpu or memory, every new pod **must** set those requests and limits (or get them from a LimitRange). Otherwise creation is rejected, which is a common "why won't my pod create" trap. Check `k describe quota -n dev` and the ReplicaSet events.

Task pattern: "Split the node's allocatable resources evenly across N pods." Run `k describe node` to read *Allocatable*, subtract overhead, then divide.

---

## 2.6 Scheduling: putting pods where you want

### nodeSelector and nodeName

```bash
k label node worker1 disktype=ssd
```

```yaml
spec:
  nodeSelector: {disktype: ssd}
  # nodeName: worker1        # bypasses the scheduler entirely (works even if scheduler is down)
```

### Node affinity

```yaml
spec:
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:     # hard
        nodeSelectorTerms:
        - matchExpressions:
          - {key: disktype, operator: In, values: [ssd, nvme]}
      preferredDuringSchedulingIgnoredDuringExecution:    # soft
      - weight: 50
        preference:
          matchExpressions:
          - {key: zone, operator: In, values: [a]}
```

### Pod affinity and anti-affinity

```yaml
spec:
  affinity:
    podAntiAffinity:                       # one replica per node
      requiredDuringSchedulingIgnoredDuringExecution:
      - labelSelector:
          matchLabels: {app: web}
        topologyKey: kubernetes.io/hostname
```

### Taints and tolerations

```bash
k taint node worker1 gpu=true:NoSchedule        # add
k taint node worker1 gpu=true:NoSchedule-       # remove (trailing dash)
k describe node worker1 | grep -i taint
```

```yaml
spec:
  tolerations:
  - key: gpu
    operator: Equal          # or Exists (no value)
    value: "true"
    effect: NoSchedule       # NoSchedule | PreferNoSchedule | NoExecute
```

A toleration *allows* a pod onto a tainted node; it doesn't *attract* it there. To pin pods to tainted nodes, combine the toleration with nodeSelector or affinity. Control plane nodes carry `node-role.kubernetes.io/control-plane:NoSchedule`.

### Topology spread constraints

```yaml
spec:
  topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: topology.kubernetes.io/zone
    whenUnsatisfiable: DoNotSchedule
    labelSelector:
      matchLabels: {app: web}
```

### PriorityClass and preemption

```bash
k create priorityclass high-priority --value=1000000 --description="business critical"
k get priorityclass
```

```yaml
spec:
  priorityClassName: high-priority      # may preempt lower-priority pods when resources are short
```

### Node maintenance

```bash
k cordon worker1                                  # no new pods
k drain worker1 --ignore-daemonsets --delete-emptydir-data   # evict pods (+cordon)
k uncordon worker1
```

---

## 2.7 Static pods

```bash
# On the node: where does the kubelet look?
grep staticPodPath /var/lib/kubelet/config.yaml     # usually /etc/kubernetes/manifests
k run static-web --image=nginx --dry-run=client -o yaml > /etc/kubernetes/manifests/static-web.yaml
# The mirror pod appears as static-web-<nodename>; delete the FILE to remove it
```

---

## 2.8 Checklist

- [ ] Roll out a new image, check history, roll back to a specific revision
- [ ] Inject a ConfigMap as env vars and a Secret as a mounted file
- [ ] Create an HPA (imperative and v2 YAML) and explain `<unknown>` targets
- [ ] Add liveness and readiness probes. Add an init container and a native sidecar
- [ ] Create a LimitRange and ResourceQuota, and deploy a pod that satisfies them
- [ ] Use nodeSelector, node affinity, pod anti-affinity, taints/tolerations
- [ ] Create a PriorityClass and use it in a Deployment
- [ ] Create a static pod on a worker node
- [ ] Drain and uncordon a node

Next: **[3. Services & Networking →](03-services-networking.md)**
