"""Convert a Helm chart's CRDs into strict JSON schemas for kubeconform.

Usage: python crd2schema.py <crds-dir> <out-dir>
Writes <out-dir>/<group>/<kind>_<version>.json. Objects that declare properties
reject unknown fields, so typos in values (e.g. a misspelled ClusterPolicy field) fail CI.
"""
import json
import pathlib
import sys

import yaml


def strict(node):
    if isinstance(node, dict):
        if (
            "properties" in node
            and "additionalProperties" not in node
            and not node.get("x-kubernetes-preserve-unknown-fields")
        ):
            node["additionalProperties"] = False
        for v in node.values():
            strict(v)
    elif isinstance(node, list):
        for v in node:
            strict(v)
    return node


def main(src, dst):
    for f in sorted(pathlib.Path(src).glob("*.yaml")):
        for crd in yaml.safe_load_all(f.read_text(encoding="utf-8")):
            if not crd or crd.get("kind") != "CustomResourceDefinition":
                continue
            group = crd["spec"]["group"]
            kind = crd["spec"]["names"]["kind"].lower()
            for version in crd["spec"]["versions"]:
                schema = strict(version["schema"]["openAPIV3Schema"])
                # Allow apiVersion/kind/metadata at the root even if the CRD omits them.
                schema.setdefault("properties", {}).setdefault("apiVersion", {"type": "string"})
                schema["properties"].setdefault("kind", {"type": "string"})
                schema["properties"].setdefault("metadata", {"type": "object"})
                out = pathlib.Path(dst) / group / f"{kind}_{version['name']}.json"
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(json.dumps(schema), encoding="utf-8")
                print(f"{group}/{kind}_{version['name']}.json")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
