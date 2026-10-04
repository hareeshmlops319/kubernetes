# 7. Practice Tasks

**25 exam-style tasks.** Set a **2-hour timer** and try each one before opening its solution. Each task's weight is relative, like in the real exam. Aim for **66% or more** of the total weight (see [Scoring yourself](#scoring-yourself)).

Run these on a practice cluster: a kubeadm lab with 1 control plane + 1–2 workers, killer.sh, or Killercoda. Names, namespaces and paths are exact. In the real exam, getting them wrong costs the points.

| # | Domain | Weight | Topic |
|---|---|---|---|
| 1–5 | Cluster Architecture | 4–8% | etcd, upgrade, RBAC, CSR, Helm |
| 6–8 | Cluster Architecture | 3–5% | Kustomize, CRD, sysctl/runtime |
| 9–13 | Workloads & Scheduling | 3–5% | Rollback, HPA, sidecar, PriorityClass, scheduling |
| 14–18 | Services & Networking | 4–6% | NetworkPolicy, Gateway API, Ingress, DNS, Service |
| 19–20 | Storage | 3–4% | StorageClass, PV/PVC |
| 21–25 | Troubleshooting | 5–8% | Node, control plane, app, service, logs |

---

## Cluster Architecture, Installation & Configuration

### Task 1: etcd backup and restore (8%)

Take a snapshot of etcd running on the control plane at `https://127.0.0.1:2379` and save it to `/opt/etcd-snap.db`. Then create a Deployment `canary` (nginx). Then restore the snapshot so that `canary` no longer exists.

??? success "Solution"
    ```bash
    ssh controlplane; sudo -i
    grep -E 'cert-file|key-file|trusted-ca-file' /etc/kubernetes/manifests/etcd.yaml

    ETCDCTL_API=3 etcdctl --endpoints=https://127.0.0.1:2379 \
      --cacert=/etc/kubernetes/pki/etcd/ca.crt \
      --cert=/etc/kubernetes/pki/etcd/server.crt \
      --key=/etc/kubernetes/pki/etcd/server.key \
      snapshot save /opt/etcd-snap.db
    etcdutl snapshot status /opt/etcd-snap.db -w table

    kubectl create deploy canary --image=nginx

    etcdutl snapshot restore /opt/etcd-snap.db --data-dir /var/lib/etcd-restore
    vim /etc/kubernetes/manifests/etcd.yaml      # etcd-data hostPath -> /var/lib/etcd-restore
    watch crictl ps                               # wait for etcd + apiserver
    kubectl get deploy canary                     # NotFound = success
    ```

### Task 2: Upgrade the control plane (7%)

Upgrade the control plane node `controlplane` from the current version to the next patch or minor version given (for example `X.Y.Z`). Upgrade kubeadm, kubelet and kubectl on that node only. Leave workers untouched.

??? success "Solution"
    ```bash
    kubectl drain controlplane --ignore-daemonsets
    ssh controlplane; sudo -i
    # If minor version changes: update /etc/apt/sources.list.d/kubernetes.list to vX.Y
    apt-get update && apt-cache madison kubeadm
    apt-mark unhold kubeadm && apt-get install -y kubeadm='X.Y.Z-*' && apt-mark hold kubeadm
    kubeadm upgrade plan
    kubeadm upgrade apply vX.Y.Z
    apt-mark unhold kubelet kubectl && apt-get install -y kubelet='X.Y.Z-*' kubectl='X.Y.Z-*' && apt-mark hold kubelet kubectl
    systemctl daemon-reload && systemctl restart kubelet
    exit; exit
    kubectl uncordon controlplane
    kubectl get nodes            # controlplane shows vX.Y.Z
    ```

### Task 3: RBAC for a ServiceAccount (5%)

In namespace `app-team`, create ServiceAccount `cicd`. Allow it to **create, update and delete Deployments, StatefulSets and DaemonSets** in `app-team` only. Use a ClusterRole named `deployment-clusterrole` and a binding named `cicd-binding`.

??? success "Solution"
    ```bash
    k create ns app-team
    k create sa cicd -n app-team
    k create clusterrole deployment-clusterrole --verb=create,update,delete \
      --resource=deployments,statefulsets,daemonsets
    k create rolebinding cicd-binding -n app-team \
      --clusterrole=deployment-clusterrole --serviceaccount=app-team:cicd
    k auth can-i create deployments -n app-team --as=system:serviceaccount:app-team:cicd   # yes
    k auth can-i create deployments -n default  --as=system:serviceaccount:app-team:cicd   # no
    ```
    A **RoleBinding** to a ClusterRole limits the permissions to that namespace.

### Task 4: User certificate and kubeconfig (6%)

Create a CSR for user `john` (group `devs`) using the key `/opt/john.key` (generate it). Approve it, save the cert to `/opt/john.crt`, and give john permission to `get,list` pods in namespace `dev`. Add a context `john` to your kubeconfig.

??? success "Solution"
    ```bash
    openssl genrsa -out /opt/john.key 2048
    openssl req -new -key /opt/john.key -subj "/CN=john/O=devs" -out /opt/john.csr
    cat <<EOF | k apply -f -
    apiVersion: certificates.k8s.io/v1
    kind: CertificateSigningRequest
    metadata:
      name: john
    spec:
      request: $(base64 -w0 < /opt/john.csr)
      signerName: kubernetes.io/kube-apiserver-client
      usages: ["client auth"]
    EOF
    k certificate approve john
    k get csr john -o jsonpath='{.status.certificate}' | base64 -d > /opt/john.crt

    k create ns dev
    k create role pod-reader -n dev --verb=get,list --resource=pods
    k create rolebinding john-pods -n dev --role=pod-reader --user=john

    k config set-credentials john --client-key=/opt/john.key --client-certificate=/opt/john.crt --embed-certs
    k config set-context john --cluster=kubernetes --user=john --namespace=dev
    k --context=john get pods            # works (may be empty)
    k --context=john get pods -n default # Forbidden
    ```

### Task 5: Helm install (5%)

Add the repo `https://stefanprodan.github.io/podinfo` as `podinfo`. Install chart `podinfo/podinfo` as release `web` into namespace `web` (create it) with `replicaCount=3`. Then write the rendered manifests of that same configuration to `/opt/podinfo.yaml`.

??? success "Solution"
    ```bash
    helm repo add podinfo https://stefanprodan.github.io/podinfo && helm repo update
    helm install web podinfo/podinfo -n web --create-namespace --set replicaCount=3
    helm list -n web
    k get deploy -n web                          # 3/3
    helm template web podinfo/podinfo -n web --set replicaCount=3 > /opt/podinfo.yaml
    ```

### Task 6: Kustomize overlay (4%)

A base exists in `/opt/app/base` (a Deployment `web` with image `nginx:1.25`). Create overlay `/opt/app/overlays/prod` that deploys it into namespace `prod` with image tag `1.27` and **4** replicas, then apply it.

??? success "Solution"
    ```bash
    mkdir -p /opt/app/overlays/prod
    cat > /opt/app/overlays/prod/kustomization.yaml <<EOF
    resources:
    - ../../base
    namespace: prod
    images:
    - name: nginx
      newTag: "1.27"
    replicas:
    - name: web
      count: 4
    EOF
    k create ns prod
    k kustomize /opt/app/overlays/prod      # preview
    k apply -k /opt/app/overlays/prod
    k get deploy web -n prod -o wide        # 4 replicas, nginx:1.27
    ```

### Task 7: CRDs (3%)

List all CRDs whose group contains `cert-manager` and save their names to `/opt/crds.txt`. Save the documentation of the `spec` field of the `Certificate` kind to `/opt/cert-spec.txt`.

??? success "Solution"
    ```bash
    k get crd | grep cert-manager | awk '{print $1}' > /opt/crds.txt
    k explain certificate.spec > /opt/cert-spec.txt
    # if ambiguous: k explain certificates.spec --api-version=cert-manager.io/v1
    ```

### Task 8: Node preparation (4%)

On node `node01`, make the following kernel parameters persistent and active: `net.ipv4.ip_forward=1` and `net.bridge.bridge-nf-call-iptables=1`. Install the package `/root/cri-dockerd.deb` and make sure the `cri-docker` service is enabled and running.

??? success "Solution"
    ```bash
    ssh node01; sudo -i
    modprobe br_netfilter
    cat <<EOF > /etc/sysctl.d/k8s.conf
    net.ipv4.ip_forward = 1
    net.bridge.bridge-nf-call-iptables = 1
    EOF
    sysctl --system
    sysctl net.ipv4.ip_forward net.bridge.bridge-nf-call-iptables
    dpkg -i /root/cri-dockerd.deb
    systemctl enable --now cri-docker.service
    systemctl is-active cri-docker
    ```

---

## Workloads & Scheduling

### Task 9: Rollout and rollback (4%)

Create Deployment `api` in namespace `prod` with image `nginx:1.25` and 3 replicas. Update it to `nginx:1.27-broken` (an image that doesn't exist), observe the failure, then roll back to the working version. Write the revision number you rolled back to into `/opt/rev.txt`.

??? success "Solution"
    ```bash
    k create deploy api -n prod --image=nginx:1.25 --replicas=3
    k set image deploy/api -n prod nginx=nginx:1.27-broken
    k rollout status deploy/api -n prod --timeout=30s    # stalls: ImagePullBackOff
    k rollout history deploy/api -n prod                 # revision 1 = nginx:1.25
    k rollout undo deploy/api -n prod --to-revision=1
    echo 1 > /opt/rev.txt
    k get deploy api -n prod -o jsonpath='{.spec.template.spec.containers[0].image}'
    ```

### Task 10: HPA (4%)

Create an HPA `api-hpa` for Deployment `api` in `prod`: min 2, max 8, target 60% average CPU, and a scale-down stabilization window of 120 seconds.

??? success "Solution"
    ```yaml
    # hpa.yaml
    apiVersion: autoscaling/v2
    kind: HorizontalPodAutoscaler
    metadata:
      name: api-hpa
      namespace: prod
    spec:
      scaleTargetRef: {apiVersion: apps/v1, kind: Deployment, name: api}
      minReplicas: 2
      maxReplicas: 8
      metrics:
      - type: Resource
        resource:
          name: cpu
          target: {type: Utilization, averageUtilization: 60}
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 120
    ```
    ```bash
    k apply -f hpa.yaml
    k set resources deploy api -n prod --requests=cpu=100m   # HPA needs CPU requests
    k get hpa -n prod                                          # targets show a %, not <unknown>
    ```

### Task 11: Logging sidecar (5%)

Deployment `legacy` in namespace `default` writes logs to `/var/log/legacy.log` inside container `app`. Add a sidecar container `log-tail` (image `busybox:1.36`) that streams that file to stdout, using a shared `emptyDir` volume `logs`. The logs must be visible with `kubectl logs ... -c log-tail`.

??? success "Solution"
    ```bash
    k edit deploy legacy
    ```
    ```yaml
    spec:
      template:
        spec:
          containers:
          - name: app
            # ...existing...
            volumeMounts:
            - {name: logs, mountPath: /var/log}
          - name: log-tail                        # classic sidecar
            image: busybox:1.36
            command: ["sh", "-c", "tail -n+1 -F /var/log/legacy.log"]
            volumeMounts:
            - {name: logs, mountPath: /var/log}
          volumes:
          - name: logs
            emptyDir: {}
    ```
    ```bash
    k logs deploy/legacy -c log-tail
    ```
    For a **native** sidecar, put the same container under `initContainers` with `restartPolicy: Always`.

### Task 12: PriorityClass (3%)

Create PriorityClass `high-priority` with a value **one less** than the highest existing user-defined PriorityClass. Patch Deployment `busybox-logger` in namespace `priority` to use it.

??? success "Solution"
    ```bash
    k get pc            # ignore system-* classes; say highest user one = 1000000
    k create priorityclass high-priority --value=999999 --description="high priority"
    k patch deploy busybox-logger -n priority \
      -p '{"spec":{"template":{"spec":{"priorityClassName":"high-priority"}}}}'
    k get pods -n priority -o jsonpath='{.items[*].spec.priorityClassName}'
    ```

### Task 13: Scheduling with taints and affinity (4%)

Node `node01` is tainted `dedicated=batch:NoSchedule` and labeled `workload=batch`. Create pod `batch-job` (image `busybox:1.36`, command `sleep 3600`) that runs **only** on `node01`.

??? success "Solution"
    ```bash
    k run batch-job --image=busybox:1.36 --dry-run=client -o yaml -- sleep 3600 > p.yaml
    ```
    ```yaml
    spec:
      tolerations:
      - {key: dedicated, operator: Equal, value: batch, effect: NoSchedule}
      nodeSelector:
        workload: batch
    ```
    ```bash
    k apply -f p.yaml && k get pod batch-job -o wide    # NODE = node01
    ```
    The toleration allows the pod onto the node, and the nodeSelector forces it there. You need both.

---

## Services & Networking

### Task 14: NetworkPolicy (6%)

In namespace `backend`, allow ingress to pods labeled `app=api` on TCP 8080 **only** from pods labeled `app=web` in namespace `frontend`. Deny all other ingress to those pods. Name it `api-allow-web`.

??? success "Solution"
    ```yaml
    apiVersion: networking.k8s.io/v1
    kind: NetworkPolicy
    metadata:
      name: api-allow-web
      namespace: backend
    spec:
      podSelector:
        matchLabels: {app: api}
      policyTypes: [Ingress]
      ingress:
      - from:
        - namespaceSelector:
            matchLabels: {kubernetes.io/metadata.name: frontend}
          podSelector:                 # same item = AND
            matchLabels: {app: web}
        ports:
        - {protocol: TCP, port: 8080}
    ```
    ```bash
    k -n frontend run t --rm -it --image=busybox:1.36 -l app=web --restart=Never -- wget -qO- -T2 api.backend:8080    # ok
    k -n frontend run t --rm -it --image=busybox:1.36 -l app=x   --restart=Never -- wget -qO- -T2 api.backend:8080    # timeout
    ```

### Task 15: Gateway API (6%)

A GatewayClass `nginx` exists. In namespace `default`, create Gateway `web-gateway` with an HTTP listener on port 80 for host `shop.example.com`. Create HTTPRoute `shop-route` that sends `/api` to Service `api-svc:8080`, and everything else 90/10 to `shop-v1:80` and `shop-v2:80`.

??? success "Solution"
    ```yaml
    apiVersion: gateway.networking.k8s.io/v1
    kind: Gateway
    metadata: {name: web-gateway, namespace: default}
    spec:
      gatewayClassName: nginx
      listeners:
      - name: http
        protocol: HTTP
        port: 80
        hostname: shop.example.com
    ---
    apiVersion: gateway.networking.k8s.io/v1
    kind: HTTPRoute
    metadata: {name: shop-route, namespace: default}
    spec:
      parentRefs:
      - name: web-gateway
      hostnames: ["shop.example.com"]
      rules:
      - matches:
        - path: {type: PathPrefix, value: /api}
        backendRefs:
        - {name: api-svc, port: 8080}
      - backendRefs:
        - {name: shop-v1, port: 80, weight: 90}
        - {name: shop-v2, port: 80, weight: 10}
    ```
    ```bash
    k describe gateway web-gateway | grep -A3 Conditions     # Programmed True
    k describe httproute shop-route | grep -A8 Parents       # Accepted, ResolvedRefs True
    ```

### Task 16: Ingress (4%)

Create Ingress `shop` (class `nginx`) in namespace `shop` routing `shop.example.com/` to Service `front:80` and `shop.example.com/pay` to Service `pay:9000`, with TLS using the existing secret `shop-tls`.

??? success "Solution"
    ```bash
    k create ingress shop -n shop --class=nginx \
      --rule="shop.example.com/*=front:80,tls=shop-tls" \
      --rule="shop.example.com/pay*=pay:9000"
    k describe ingress shop -n shop
    ```
    Check that both paths are `Prefix` and the TLS section lists `shop.example.com`. Edit with `k edit ingress` if needed.

### Task 17: Expose and DNS (4%)

Expose pod `nginx-resolver` (create it, image `nginx`) as Service `nginx-resolver-svc` on port 80. From a temporary busybox pod, look up the Service and the pod's DNS records. Save the outputs to `/opt/svc.dns` and `/opt/pod.dns`.

??? success "Solution"
    ```bash
    k run nginx-resolver --image=nginx
    k expose pod nginx-resolver --name=nginx-resolver-svc --port=80
    k run t --rm -i --image=busybox:1.28 --restart=Never -- nslookup nginx-resolver-svc > /opt/svc.dns
    IP=$(k get pod nginx-resolver -o jsonpath='{.status.podIP}' | tr . -)
    k run t --rm -i --image=busybox:1.28 --restart=Never -- nslookup $IP.default.pod.cluster.local > /opt/pod.dns
    cat /opt/svc.dns /opt/pod.dns
    ```
    (`busybox:1.28` has the most reliable `nslookup` output for this classic task.)

### Task 18: Fix a NodePort Service (5%)

Service `web` in namespace `shop` must be reachable on every node at port `30080`, forwarding to container port `8080` of pods labeled `app=web`. It currently doesn't work. Fix it.

??? success "Solution"
    ```bash
    k get svc web -n shop -o yaml          # check type, selector, targetPort, nodePort
    k get pods -n shop --show-labels
    k get endpointslices -n shop -l kubernetes.io/service-name=web
    k edit svc web -n shop
    #   type: NodePort
    #   selector: {app: web}               # fix mismatched label
    #   ports: [{port: 80, targetPort: 8080, nodePort: 30080}]
    curl -s <node-ip>:30080
    ```

---

## Storage

### Task 19: Default StorageClass (3%)

Create StorageClass `local-fast` (provisioner `rancher.io/local-path`, `volumeBindingMode: WaitForFirstConsumer`, `allowVolumeExpansion: true`) and make it the **only** default StorageClass.

??? success "Solution"
    ```yaml
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: local-fast
      annotations:
        storageclass.kubernetes.io/is-default-class: "true"
    provisioner: rancher.io/local-path
    volumeBindingMode: WaitForFirstConsumer
    allowVolumeExpansion: true
    reclaimPolicy: Delete
    ```
    ```bash
    k apply -f sc.yaml
    k get sc                                    # find the old (default)
    k patch sc <old> -p '{"metadata":{"annotations":{"storageclass.kubernetes.io/is-default-class":"false"}}}'
    k get sc                                    # only local-fast marked (default)
    ```

### Task 20: PV, PVC and pod (4%)

Create PV `app-pv` (2Gi, RWO, hostPath `/srv/app`, reclaim `Retain`, storageClassName `manual`). Create PVC `app-pvc` in namespace `storage` requesting 1Gi that binds to it. Mount it at `/data` in pod `app` (image `nginx`).

??? success "Solution"
    ```yaml
    apiVersion: v1
    kind: PersistentVolume
    metadata: {name: app-pv}
    spec:
      capacity: {storage: 2Gi}
      accessModes: [ReadWriteOnce]
      persistentVolumeReclaimPolicy: Retain
      storageClassName: manual
      hostPath: {path: /srv/app}
    ---
    apiVersion: v1
    kind: PersistentVolumeClaim
    metadata: {name: app-pvc, namespace: storage}
    spec:
      accessModes: [ReadWriteOnce]
      resources: {requests: {storage: 1Gi}}
      storageClassName: manual
    ---
    apiVersion: v1
    kind: Pod
    metadata: {name: app, namespace: storage}
    spec:
      containers:
      - name: app
        image: nginx
        volumeMounts: [{name: data, mountPath: /data}]
      volumes:
      - name: data
        persistentVolumeClaim: {claimName: app-pvc}
    ```
    ```bash
    k create ns storage; k apply -f storage.yaml
    k get pv,pvc -n storage        # Bound
    ```

---

## Troubleshooting

### Task 21: NotReady worker (8%)

Node `node01` is `NotReady`. Fix it and make sure the fix survives a reboot.

??? success "Solution"
    ```bash
    k describe node node01 | grep -A5 Conditions
    ssh node01; sudo -i
    systemctl status kubelet                       # inactive? failed?
    journalctl -u kubelet --no-pager | tail -30    # read the actual error
    # Typical fixes:
    systemctl enable --now kubelet                 # stopped/disabled
    vim /var/lib/kubelet/config.yaml               # wrong clientCAFile / path
    systemctl status containerd                    # runtime down -> enable --now containerd
    systemctl daemon-reload && systemctl restart kubelet
    exit; exit
    k get nodes -w                                 # Ready
    ```
    "Survives a reboot" means `systemctl enable`, not just `start`.

### Task 22: Broken API server (8%)

After a config change, `kubectl` returns `connection refused`. Fix the cluster.

??? success "Solution"
    ```bash
    ssh controlplane; sudo -i
    crictl ps -a | grep kube-apiserver             # Exited / not present
    crictl logs <id>                               # flag error? cert path? etcd URL?
    tail -30 /var/log/pods/kube-system_kube-apiserver-*/kube-apiserver/*.log
    journalctl -u kubelet | tail -20               # YAML parse errors show here
    vim /etc/kubernetes/manifests/kube-apiserver.yaml
    #   common: --etcd-servers=https://127.0.0.1:2379 (not 2380), typo'd flag,
    #   wrong --tls-cert-file path, invalid YAML indentation
    watch crictl ps                                # apiserver Running
    kubectl get nodes
    ```

### Task 23: Pods stuck Pending (5%)

New pods in namespace `default` stay `Pending` with **no events**. Find and fix the cause.

??? success "Solution"
    No events at all means nothing tried to schedule them, so the **scheduler** is down.
    ```bash
    k get pods -n kube-system | grep scheduler       # CrashLoopBackOff / missing
    k logs -n kube-system kube-scheduler-controlplane
    ssh controlplane; sudo -i
    vim /etc/kubernetes/manifests/kube-scheduler.yaml
    #   fix e.g. --kubeconfig=/etc/kubernetes/scheduler.conf, command name, image
    ```
    Then confirm the pods get scheduled.

### Task 24: CrashLoopBackOff (5%)

Pod `payments` in namespace `prod` keeps restarting. Find why, fix it, and write the original error message to `/opt/payments-error.txt`.

??? success "Solution"
    ```bash
    k describe pod payments -n prod | sed -n '/Last State/,/Ready/p'   # OOMKilled? exit code?
    k logs payments -n prod --previous > /opt/payments-error.txt
    # Fix per the cause: missing env/ConfigMap key, wrong command, liveness probe, memory limit
    k get pod payments -n prod -o yaml > p.yaml && vim p.yaml
    k replace --force -f p.yaml
    k get pod payments -n prod -w            # Running, restarts stop increasing
    ```

### Task 25: Resource usage (5%)

Among pods with label `tier=backend` in all namespaces, find the one using the most memory. Write `<namespace>/<pod>` to `/opt/top-mem.txt`.

??? success "Solution"
    ```bash
    k top pods -A -l tier=backend --sort-by=memory --no-headers | head -1 \
      | awk '{print $1"/"$2}' > /opt/top-mem.txt
    cat /opt/top-mem.txt
    ```

---

## Scoring yourself

Add up the weights of the tasks you solved fully and correctly (verified, exact names). The weights total **125**, so **83 or more (66%)** means you're on track. For every miss, write the one command or concept you lacked and drill it tonight.

Last stop: **[8. Cheat Sheet →](08-cheat-sheet.md)**
