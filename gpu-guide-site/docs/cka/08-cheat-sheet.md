# 8. Cheat Sheet

**Read this right before the exam.** Everything here is covered in depth on the earlier pages.

---

## First minute

```bash
alias k=kubectl; export do="--dry-run=client -o yaml"; export now="--force --grace-period=0"
echo 'set expandtab tabstop=2 shiftwidth=2 autoindent' >> ~/.vimrc
```

**Every task:** run the given `use-context` command → ssh if told → `sudo -i` if needed → solve → **verify** → `exit` back.

---

## Generators

```bash
k run p --image=nginx --port=80 -l app=p $do
k create deploy d --image=nginx --replicas=3 $do
k expose deploy d --port=80 --target-port=8080 [--type=NodePort]
k create cm c --from-literal=K=V ; k create secret generic s --from-literal=K=V
k create sa sa1 ; k create role r --verb=get,list --resource=pods
k create rolebinding rb --role=r --serviceaccount=ns:sa1   # or --user / --group
k create clusterrole cr --verb=get --resource=nodes ; k create clusterrolebinding crb --clusterrole=cr --user=u
k create job j --image=busybox -- echo hi ; k create cronjob cj --image=busybox --schedule="*/5 * * * *" -- date
k create ingress i --class=nginx --rule="host/path*=svc:80,tls=secret"
k create priorityclass pc --value=1000 ; k create pdb p --selector=app=x --min-available=1
k autoscale deploy d --min=2 --max=5 --cpu-percent=70
k create token sa1 ; k auth can-i <verb> <res> --as=system:serviceaccount:ns:sa1
```

## Rollouts and edits

```bash
k set image deploy/d c=nginx:1.27 ; k rollout status|history|undo [--to-revision=N] deploy/d
k scale deploy d --replicas=5 ; k set resources deploy d --requests=cpu=100m
k replace --force -f pod.yaml          # change immutable pod fields
k label|annotate|taint node n key=val[:Effect][-]
k cordon|drain|uncordon n  (drain: --ignore-daemonsets --delete-emptydir-data)
```

## Output

```bash
-o wide | -o yaml | -o name | --show-labels | -l k=v | -A | --no-headers
--sort-by=.metadata.creationTimestamp
-o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}'
-o custom-columns=N:.metadata.name,NODE:.spec.nodeName
k top pods -A --sort-by=cpu|memory ; k logs p [-c c] [--previous] [-f] [-l k=v]
k explain kind.spec.field [--recursive] ; k api-resources
```

---

## etcd

```bash
ETCDCTL_API=3 etcdctl --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key snapshot save /opt/snap.db
etcdutl snapshot restore /opt/snap.db --data-dir /var/lib/etcd-restore
# then: etcd.yaml -> etcd-data hostPath: /var/lib/etcd-restore ; wait for crictl ps
```

## kubeadm upgrade

```
CP:     edit apt .list to vX.Y → install kubeadm=X.Y.Z-* → kubeadm upgrade plan → kubeadm upgrade apply vX.Y.Z
        → drain → install kubelet,kubectl=X.Y.Z-* → daemon-reload + restart kubelet → uncordon
Worker: drain (from CP) → kubeadm=X.Y.Z-* → kubeadm upgrade node → kubelet,kubectl → restart → uncordon
```

## Join, certs, CSR

```bash
kubeadm token create --print-join-command
kubeadm certs check-expiration ; kubeadm certs renew all
openssl req -new -key u.key -subj "/CN=user/O=group" -out u.csr
# CSR: signerName kubernetes.io/kube-apiserver-client, usages [client auth], request: base64 -w0
k certificate approve u ; k get csr u -o jsonpath='{.status.certificate}' | base64 -d > u.crt
```

## Helm and Kustomize

```bash
helm repo add r URL ; helm install rel r/chart -n ns --create-namespace --version V --set k=v
helm upgrade|rollback|uninstall|list -A|history|template|show values
k kustomize dir ; k apply -k dir     # resources, namespace, images(newTag), replicas, patches
```

---

## Key file paths

| Path | What |
|---|---|
| `/etc/kubernetes/manifests/` | Static pods: apiserver, etcd, scheduler, controller-manager |
| `/etc/kubernetes/pki/` (`etcd/`) | Cluster certificates |
| `/etc/kubernetes/admin.conf` | Admin kubeconfig |
| `/etc/kubernetes/kubelet.conf` | Kubelet's kubeconfig |
| `/var/lib/kubelet/config.yaml` | Kubelet config (staticPodPath, clusterDNS, clientCAFile) |
| `/var/lib/kubelet/kubeadm-flags.env` | Kubelet flags (runtime endpoint) |
| `/usr/lib/systemd/system/kubelet.service.d/10-kubeadm.conf` | Kubelet systemd drop-in |
| `/var/lib/etcd` | etcd data |
| `/etc/cni/net.d/`, `/opt/cni/bin/` | CNI config and binaries |
| `/var/log/pods/`, `/var/log/containers/` | Container logs on the node |
| `/etc/apt/sources.list.d/kubernetes.list` | pkgs.k8s.io repo (per minor version) |

## Troubleshooting reflexes

| See | Think |
|---|---|
| `kubectl` connection refused | apiserver manifest → `crictl ps -a`, `crictl logs` |
| Node NotReady | `systemctl status kubelet`, `journalctl -u kubelet`, containerd, CNI |
| Pending + no events | Scheduler down |
| Pending + events | Resources, taints, affinity, PVC |
| Deployment, no pods | Controller-manager down, or quota/LimitRange rejection (check RS events) |
| CrashLoopBackOff | `logs --previous`, command, env, probe, OOM |
| Svc no endpoints | Selector vs labels, readiness |
| Svc endpoints but refused | targetPort |
| DNS fails | CoreDNS pods/ConfigMap, NetworkPolicy DNS egress |
| `k top` fails | metrics-server |

## NetworkPolicy reminders

- Selecting a pod with any policy makes it **deny-by-default** for the listed `policyTypes`
- One `from` item with `namespaceSelector` + `podSelector` = **AND**. Two items = **OR**
- Namespace by name: `kubernetes.io/metadata.name: <ns>`
- Egress policies need **DNS port 53 (UDP+TCP)**

## Gateway API skeleton

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata: {name: r}
spec:
  parentRefs: [{name: gw}]
  hostnames: ["a.example.com"]
  rules:
  - matches: [{path: {type: PathPrefix, value: /api}}]
    backendRefs: [{name: api, port: 8080}]
  - backendRefs: [{name: v1, port: 80, weight: 90}, {name: v2, port: 80, weight: 10}]
```

## Storage reminders

- PVC binds to a PV when **storageClassName, accessModes and capacity ≥ request** match
- `WaitForFirstConsumer`: the PVC stays Pending until a pod uses it (normal)
- One default SC: `storageclass.kubernetes.io/is-default-class: "true"`
- Retain → PV `Released`, data kept. Delete → storage removed

---

## Final reminders

- [ ] Context switched for **every** task
- [ ] Exact names, namespaces, file paths, output formats
- [ ] Skip anything taking more than 8 minutes and come back later
- [ ] Verify every answer (`get`, `describe`, `auth can-i`, curl)
- [ ] `exit` back from ssh sessions
- [ ] Use kubernetes.io/docs search for YAML you can't generate (PV, PVC, NetworkPolicy, HTTPRoute)

**Good luck, you've got this.**
