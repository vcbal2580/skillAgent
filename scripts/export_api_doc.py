"""Generate api.doc from FastAPI OpenAPI schema (no server startup required)."""
import sys, types, unittest.mock as mock, os

# ── Stub dependencies so FastAPI routes can be introspected without real config ──
cfg_mod = types.ModuleType("core.config")
cfg_mod.config = {"language": "en", "llm": {}}
sys.modules["core.config"] = cfg_mod

ag_mod = types.ModuleType("core.agent")
class _Agent:
    pass
ag_mod.Agent = _Agent
sys.modules["core.agent"] = ag_mod

import api.server as srv  # noqa: E402

app = srv.app
schema = app.openapi()

# ── Render Markdown ──────────────────────────────────────────────────────────────
lines = []
info = schema.get("info", {})
lines += [
    f"# {info.get('title', 'API')} Documentation",
    f"",
    f"**Version:** {info.get('version', '')}",
    f"",
    "---",
    "",
    "## Endpoints",
    "",
]

paths = schema.get("paths", {})
components = schema.get("components", {}).get("schemas", {})

METHOD_ORDER = ["get", "post", "put", "patch", "delete"]

for path in sorted(paths.keys()):
    methods = paths[path]
    for method in METHOD_ORDER:
        if method not in methods:
            continue
        detail = methods[method]
        lines.append(f"### {method.upper()} `{path}`")
        lines.append("")

        if detail.get("summary"):
            lines.append(f"**{detail['summary']}**")
            lines.append("")

        if detail.get("description"):
            lines.append(detail["description"].strip())
            lines.append("")

        # Tags
        if detail.get("tags"):
            lines.append(f"*Tags: {', '.join(detail['tags'])}*")
            lines.append("")

        # Path / Query parameters
        params = detail.get("parameters", [])
        if params:
            lines.append("**Parameters:**")
            lines.append("")
            lines.append("| Name | In | Type | Required | Description |")
            lines.append("|------|----|------|----------|-------------|")
            for p in params:
                ptype = p.get("schema", {}).get("type", "")
                req = "✓" if p.get("required") else ""
                desc = p.get("description", "")
                lines.append(f"| `{p['name']}` | {p.get('in','')} | {ptype} | {req} | {desc} |")
            lines.append("")

        # Request body
        rb = detail.get("requestBody", {})
        if rb:
            content = rb.get("content", {})
            for ct, schema_info in content.items():
                lines.append(f"**Request Body** (`{ct}`):")
                lines.append("")
                ref = schema_info.get("schema", {}).get("$ref", "")
                if ref:
                    model_name = ref.split("/")[-1]
                    model = components.get(model_name, {})
                    props = model.get("properties", {})
                    req_fields = model.get("required", [])
                    if props:
                        lines.append("| Field | Type | Required | Description |")
                        lines.append("|-------|------|----------|-------------|")
                        for prop, pdef in props.items():
                            ptype = pdef.get("type", pdef.get("$ref", "").split("/")[-1])
                            req = "✓" if prop in req_fields else ""
                            desc = pdef.get("description", "")
                            lines.append(f"| `{prop}` | {ptype} | {req} | {desc} |")
                        lines.append("")
                elif "multipart/form-data" in ct or "application/x-www-form-urlencoded" in ct:
                    # Form fields
                    props = schema_info.get("schema", {}).get("properties", {})
                    req_fields = schema_info.get("schema", {}).get("required", [])
                    if props:
                        lines.append("| Field | Type | Required | Description |")
                        lines.append("|-------|------|----------|-------------|")
                        for prop, pdef in props.items():
                            ptype = pdef.get("type", "")
                            req = "✓" if prop in req_fields else ""
                            desc = pdef.get("description", "")
                            lines.append(f"| `{prop}` | {ptype} | {req} | {desc} |")
                        lines.append("")

        # Responses
        responses = detail.get("responses", {})
        if responses:
            lines.append("**Responses:**")
            lines.append("")
            lines.append("| Status | Description |")
            lines.append("|--------|-------------|")
            for code, resp in sorted(responses.items()):
                lines.append(f"| {code} | {resp.get('description', '')} |")
            lines.append("")

        lines.append("---")
        lines.append("")

# ── Write file ───────────────────────────────────────────────────────────────────
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out_path = os.path.join(root, "api.doc")
with open(out_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"Exported {len(lines)} lines → {out_path}")
