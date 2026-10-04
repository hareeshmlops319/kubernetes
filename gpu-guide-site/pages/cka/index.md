# CKA Exam Prep

**Certified Kubernetes Administrator: from the basics to exam-ready, with a plan for the last 24 hours**

> **Check before the exam:** The Linux Foundation updates the exam's Kubernetes version and rules. Read the current [CKA Candidate Handbook](https://docs.linuxfoundation.org/tc-docs/certification/lf-handbook2) and [Important Instructions](https://docs.linuxfoundation.org/tc-docs/certification/tips-cka-and-ckad) the day before. This guide follows the curriculum revised in **February 2025**, which added Helm, Kustomize, Gateway API, CRDs/operators and extension interfaces.

---

## How this section is organized

| Page | Level | What you get |
|---|---|---|
| [1. Fundamentals & kubectl Speed](01-kubectl-fundamentals.md) | Beginner | Architecture, imperative commands, YAML generation, JSONPath, contexts |
| [2. Workloads & Scheduling](02-workloads-scheduling.md) | Beginner → Intermediate | Deployments, rollouts, ConfigMaps/Secrets, HPA, probes, sidecars, affinity, taints, quotas |
| [3. Services & Networking](03-services-networking.md) | Intermediate | Services, DNS, NetworkPolicy, Ingress, **Gateway API** |
| [4. Storage](04-storage.md) | Intermediate | StorageClass, PV, PVC, access modes, reclaim policies, expansion |
| [5. Cluster Architecture, Installation & Configuration](05-cluster-architecture.md) | Advanced | kubeadm install/upgrade, etcd backup/restore, RBAC, certificates, HA, **Helm, Kustomize, CRDs**, CNI/CSI/CRI |
| [6. Troubleshooting](06-troubleshooting.md) | Advanced | Broken nodes, control plane, apps, services, DNS: the 30% domain |
| [7. Practice Tasks](07-practice-tasks.md) | Exam-style | 25 timed tasks with hidden solutions |
| [8. Cheat Sheet](08-cheat-sheet.md) | Last-minute | One page to read right before the exam |

---

## The exam at a glance

| Item | Detail |
|---|---|
| Format | Online, remotely proctored, **performance-based**: you fix and build things in real clusters from a command line |
| Duration | **2 hours** |
| Tasks | About **15–20** tasks, each with its own weight (shown per task) |
| Passing score | **66%** |
| Environment | Remote Linux desktop (PSI) with a terminal and a browser. Multiple clusters, and you switch context per task |
| Allowed docs | kubernetes.io/docs, kubernetes.io/blog, and the other sites listed in the handbook (check the current list; Helm and Gateway API docs have been added for the new curriculum) |
| Retake | One free retake is included |
| Simulator | Two **killer.sh** sessions come with your registration (36 hours each). The simulator is harder than the real exam |

### Curriculum weights (where the points are)

| Domain | Weight | Focus |
|---|---|---|
| **Troubleshooting** | **30%** | Nodes, control plane components, apps, services, logs, resource usage |
| **Cluster Architecture, Installation & Configuration** | **25%** | RBAC, kubeadm, upgrades, HA, Helm, Kustomize, CRDs/operators, CNI/CSI/CRI |
| **Services & Networking** | **20%** | Pod connectivity, NetworkPolicy, Service types, Gateway API, Ingress, CoreDNS |
| **Workloads & Scheduling** | **15%** | Deployments, rollouts, ConfigMaps/Secrets, autoscaling, self-healing, scheduling |
| **Storage** | **10%** | StorageClasses, dynamic provisioning, volume types, access modes, PV/PVC |

**Takeaway:** Troubleshooting plus cluster administration make up **55%**. If you only have one day, those two get most of your time.

---

## Your 24-hour plan (exam tomorrow)

You can't learn Kubernetes in a day. You *can* get faster, fill gaps in high-weight topics, and avoid silly point losses.

### Today

| Block | Time | Do this |
|---|---|---|
| 1 | 30 min | Read the [Cheat Sheet](08-cheat-sheet.md) and set up your aliases on a practice cluster until they're muscle memory |
| 2 | 90 min | **Cluster admin drills:** etcd backup and restore, kubeadm upgrade (control plane, then worker), join a node, RBAC with a ServiceAccount, CSR for a user. See [Page 5](05-cluster-architecture.md) |
| 3 | 90 min | **Troubleshooting drills:** break and fix kubelet, kube-apiserver manifest, scheduler, a Service with no endpoints, DNS. See [Page 6](06-troubleshooting.md) |
| 4 | 60 min | **New-curriculum topics:** Gateway API HTTPRoute, Helm install with values, Kustomize overlay, CRD/operator, HPA, native sidecar, PriorityClass |
| 5 | 60 min | NetworkPolicy (AND vs OR selectors), Ingress, StorageClass + PVC + pod |
| 6 | 2 h | **Timed mock:** [Practice Tasks](07-practice-tasks.md) under a 2-hour timer, or a killer.sh session. Review every miss |
| 7 | — | Stop early and **sleep**. A rested brain beats one more hour of practice |

Free hands-on practice environments: **killer.sh** (included with registration) and **Killercoda** CKA scenarios (free, in the browser).

### Exam morning

- [ ] Run the PSI system check on the **same computer and network** you'll use
- [ ] Clean desk, clear room, only one monitor, government ID ready
- [ ] Close all other apps (VPNs, chat, screen recorders)
- [ ] Log in **30 minutes early**. Check-in takes time
- [ ] Re-read the [Cheat Sheet](08-cheat-sheet.md) once

---

## Exam-day strategy

1. **Run the context command at the start of every task.** Each task shows a command like `kubectl config use-context <cluster>`. Copy it, run it, and only then work. Doing a correct task on the wrong cluster scores **zero**.
2. **Note the host.** Some tasks say "ssh to node X". Do it, use `sudo -i` if you need root, and **`exit` back** to the base terminal afterwards.
3. **Triage.** Do quick, high-weight tasks first. If a task takes more than about 8 minutes, flag it and move on. About 6 minutes per task is the average budget.
4. **Generate YAML, don't type it.** Use `kubectl create ... --dry-run=client -o yaml > file.yaml`, then edit. Copy examples from kubernetes.io for kinds without generators (PV, PVC, NetworkPolicy, HTTPRoute).
5. **Verify every answer.** `k get`, `k describe`, `k logs`, `k auth can-i`, curl from a test pod. Partial credit exists, so a verified half-solution beats an unverified full one.
6. **Use the exact names, namespaces and paths given.** Graders check `name`, `namespace`, `labels`, the file path and the output format literally.
7. **Copy and paste:** in the PSI terminal, use **Ctrl+Shift+C / Ctrl+Shift+V**. Copy names straight from the task text to avoid typos.
8. **Don't fight the environment.** If the browser docs are slow, use `kubectl explain <kind>.spec --recursive` in the terminal.

---

## Set up the terminal in the first minute

`kubectl` and the `k` alias with completion are usually preconfigured. If not, or to add helpers:

```bash
alias k=kubectl                                   # usually already set
export do="--dry-run=client -o yaml"              # k create deploy x --image=nginx $do > x.yaml
export now="--force --grace-period=0"             # k delete pod x $now
source <(kubectl completion bash); complete -o default -F __start_kubectl k
```

Vim, for YAML that doesn't break:

```vim
" ~/.vimrc
set expandtab tabstop=2 shiftwidth=2 autoindent number
```

Useful vim keys: `:set paste` before pasting, `V` + `>` / `<` to indent a block, `u` to undo, `:%s/old/new/g` to replace.

---

Start with **[1. Fundamentals & kubectl Speed →](01-kubectl-fundamentals.md)**, or jump to the [Practice Tasks](07-practice-tasks.md) if you're already confident.
