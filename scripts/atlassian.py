#!/usr/bin/env python3
"""Jira / Confluence. Solo actua si existe harness/atlassian.json.

El binding (sitio, proyecto, space) es versionable; el TOKEN nunca:
va en ~/.harness-hub/.env o en el entorno como ATLASSIAN_EMAIL /
ATLASSIAN_API_TOKEN.

  atlassian.py status
  atlassian.py bind --site x.atlassian.net --jira-project K --confluence-space S
  atlassian.py push --feature <id>          # crea/actualiza historia + subtasks AC
  atlassian.py outbox                       # lo pendiente, para drenar con MCP
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from comun import (get_feature, hub_env, load_backlog, now_iso, paths,  # noqa: E402
                   save_backlog, spec_acs, spec_path)


def binding(p):
    if not p["atlassian"].exists():
        sys.exit("[i]  este proyecto no tiene harness/atlassian.json: la integracion\n"
                 "     esta apagada y el flujo funciona igual.\n"
                 "     Si el usuario quiere integrarla, PREGUNTALE a que proyecto Jira\n"
                 "     y space de Confluence pertenece el repo, y corre:\n"
                 "       atlassian.py bind --site <x> --jira-project <K> --confluence-space <S>")
    return json.loads(p["atlassian"].read_text(encoding="utf-8"))


def credenciales():
    e = hub_env()
    email = os.environ.get("ATLASSIAN_EMAIL") or e.get("ATLASSIAN_EMAIL")
    token = os.environ.get("ATLASSIAN_API_TOKEN") or e.get("ATLASSIAN_API_TOKEN")
    return email, token


def api(site, email, token, metodo, ruta, cuerpo=None):
    url = f"https://{site}{ruta}"
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    auth = base64.b64encode(f"{email}:{token}".encode()).decode()
    req = urllib.request.Request(url, data=datos, method=metodo, headers={
        "Authorization": f"Basic {auth}", "Content-Type": "application/json",
        "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            txt = r.read().decode()
            return r.status, (json.loads(txt) if txt else {})
    except urllib.error.HTTPError as ex:
        return ex.code, {"error": ex.read().decode()[:500]}
    except Exception as ex:
        return 0, {"error": str(ex)}


def cmd_status(args) -> None:
    p = paths(); b = binding(p)
    email, token = credenciales()
    print(f"sitio:      {b.get('site')}")
    print(f"proyecto:   {b.get('jira_project')}")
    print(f"space:      {b.get('confluence_space')}")
    print(f"issue type: {b.get('issue_type','Story')}")
    if not (email and token):
        print("\n[i]  sin token: el push queda en la OUTBOX para drenarlo con tu MCP de\n"
              "     Atlassian. Para push directo define ATLASSIAN_EMAIL y\n"
              "     ATLASSIAN_API_TOKEN en ~/.harness-hub/.env")
        return
    code, data = api(b["site"], email, token, "GET",
                     f"/rest/api/3/project/{b['jira_project']}")
    print(f"\n[{'ok' if code == 200 else '!!'}] Jira responde {code}"
          + (f" — {data.get('name')}" if code == 200 else f" — {data.get('error','')[:200]}"))


def cmd_bind(args) -> None:
    p = paths()
    p["harness"].mkdir(parents=True, exist_ok=True)
    p["atlassian"].write_text(json.dumps({
        "site": args.site, "jira_project": args.jira_project,
        "confluence_space": args.confluence_space,
        "issue_type": args.issue_type}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    print(f"[ok] {p['atlassian']} (versionable: no contiene credenciales)")


def _intent(p, tipo, payload):
    d = p["harness"] / "outbox"; d.mkdir(parents=True, exist_ok=True)
    n = len(list(d.glob("*.json"))) + 1
    f = d / f"{n:04d}-{tipo}.json"
    f.write_text(json.dumps({"tipo": tipo, "at": now_iso(), **payload},
                            ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return f


def cmd_push(args) -> None:
    p = paths(); b = binding(p)
    data = load_backlog(p); f = get_feature(data, args.feature)
    sp = spec_path(p, f)
    acs = spec_acs(sp.read_text(encoding="utf-8")) if sp.exists() else []
    tipo = {"bug": "Bug", "task": "Task"}.get(f.get("kind"), b.get("issue_type", "Story"))
    resumen = f"#{f['id']} {f.get('name')}"
    email, token = credenciales()

    if not (email and token):
        ruta = _intent(p, "jira-upsert", {"feature": f["id"], "issue_type": tipo,
                                          "resumen": resumen, "acs": acs,
                                          "project": b["jira_project"]})
        print(f"[ok] intent en la outbox: {ruta}")
        print("[i]  drenalo con tu MCP de Atlassian y registra la clave con:")
        print(f"     atlassian.py ack --feature {f['id']} --key <KEY-123>")
        return

    if f.get("jira_key"):
        code, r = api(b["site"], email, token, "PUT",
                      f"/rest/api/3/issue/{f['jira_key']}",
                      {"fields": {"summary": resumen}})
        print(f"[{'ok' if code < 300 else '!!'}] actualizado {f['jira_key']} ({code})")
    else:
        code, r = api(b["site"], email, token, "POST", "/rest/api/3/issue", {
            "fields": {"project": {"key": b["jira_project"]},
                       "summary": resumen, "issuetype": {"name": tipo}}})
        if code >= 300:
            sys.exit(f"[!!] Jira rechazo la creacion ({code}): {r.get('error','')[:300]}")
        f["jira_key"] = r.get("key"); save_backlog(p, data)
        print(f"[ok] creado {f['jira_key']}")

    padre = f.get("jira_key")
    creadas = f.setdefault("jira_ac_keys", {})
    stext = sp.read_text(encoding="utf-8") if sp.exists() else ""
    for ac in acs:
        if ac in creadas:
            continue
        texto = next((l.strip() for l in stext.splitlines() if ac in l), ac)[:200]
        code, r = api(b["site"], email, token, "POST", "/rest/api/3/issue", {
            "fields": {"project": {"key": b["jira_project"]},
                       "parent": {"key": padre}, "summary": f"{ac} · {texto}",
                       "issuetype": {"name": "Subtask"}}})
        if code < 300:
            creadas[ac] = r.get("key")
            print(f"   [ok] subtask {ac} -> {r.get('key')}")
        else:
            print(f"   [!] subtask {ac} fallo ({code})")
    save_backlog(p, data)


def cmd_ack(args) -> None:
    p = paths(); data = load_backlog(p); f = get_feature(data, args.feature)
    f["jira_key"] = args.key; save_backlog(p, data)
    print(f"[ok] feature #{f['id']} ligada a {args.key}")


def cmd_outbox(args) -> None:
    p = paths()
    d = p["harness"] / "outbox"
    files = sorted(d.glob("*.json")) if d.exists() else []
    if not files:
        print("[i]  outbox vacia")
        return
    print(f"{len(files)} intent(s) pendientes:")
    for f in files:
        j = json.loads(f.read_text(encoding="utf-8"))
        print(f"   {f.name}: {j.get('tipo')} feature #{j.get('feature')}")
    print("\n[i]  ejecutalos con tu MCP de Atlassian, y borra el archivo al confirmarlo.")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    s = sub.add_parser("bind"); s.add_argument("--site", required=True)
    s.add_argument("--jira-project", required=True, dest="jira_project")
    s.add_argument("--confluence-space", dest="confluence_space")
    s.add_argument("--issue-type", default="Story", dest="issue_type")
    s.set_defaults(fn=cmd_bind)
    s = sub.add_parser("push"); s.add_argument("--feature", required=True)
    s.set_defaults(fn=cmd_push)
    s = sub.add_parser("ack"); s.add_argument("--feature", required=True)
    s.add_argument("--key", required=True); s.set_defaults(fn=cmd_ack)
    sub.add_parser("outbox").set_defaults(fn=cmd_outbox)
    a = ap.parse_args(); a.fn(a)


if __name__ == "__main__":
    main()
