"""
VoSMS – Interface graphique NiceGUI
Lancer avec : uv run app.py  (ou python app.py)
"""

import json
import tempfile
from pathlib import Path

import pandas as pd
from nicegui import ui

from core import SMSSender, load_db

# ── Colonnes du tableau ───────────────────────────────────────────────────────
COLUMNS = [
    {"field": "dest", "headerName": "Nom", "flex": 2, "editable": True},
    {"field": "phone", "headerName": "Numéro", "flex": 2, "editable": True},
    {"field": "header", "headerName": "En-tête", "flex": 2, "editable": True},
    {"field": "message", "headerName": "Message", "flex": 4, "editable": True},
]

EMPTY_ROW: dict = {"dest": "", "phone": "", "header": "", "message": ""}

# ── État global ───────────────────────────────────────────────────────────────
_sender: SMSSender | None = None
_device_cfg: dict = {"local_adress": "", "username": "", "password": ""}


def try_load_default_device() -> str:
    global _sender, _device_cfg
    # p = Path("device.json")
    p = Path("dev_device.json")
    if not p.exists():
        return "Aucun device.json trouvé"
    try:
        _device_cfg = json.loads(p.read_text())
        _sender = SMSSender(p)
        return f"device.json chargé  ·  {_device_cfg.get('local_adress', '')}"
    except Exception as e:
        return f"Erreur device.json : {e}"


def build_sender_from_cfg() -> str:
    global _sender
    if not all(_device_cfg.values()):
        return "Champs manquants"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
        json.dump(_device_cfg, tmp)
        tmp_path = Path(tmp.name)
    try:
        _sender = SMSSender(tmp_path)
        return f"Connecté  ·  {_device_cfg['local_adress']}"
    except Exception as e:
        _sender = None
        return f"Erreur : {e}"
    finally:
        tmp_path.unlink(missing_ok=True)


# ── Page principale ───────────────────────────────────────────────────────────
@ui.page("/")
def page_main():

    ui.add_head_html("""
    <style>
      body, html { margin: 0; padding: 0; height: 100%; overflow: hidden;
                   font-family: ui-sans-serif, system-ui, sans-serif; }
      .app-frame { display: flex; height: 100vh; }

      .sidebar {
        width: 52px; flex-shrink: 0;
        background: #fff; border-right: 1px solid #e5e5e5;
        display: flex; flex-direction: column; align-items: center;
        padding: 12px 0; gap: 6px; z-index: 1;
      }
      .sb-btn {
        width: 36px; height: 36px; border-radius: 8px; border: none;
        background: transparent; cursor: pointer;
        display: flex; align-items: center; justify-content: center;
        color: #737373; transition: background .12s;
      }
      .sb-btn:hover { background: #f5f5f4; color: #171717; }
      .sb-btn.active { background: #eff6ff; color: #2563eb; }
      .sb-spacer { flex: 1; }

      .main-area { flex: 1; display: flex; flex-direction: column; overflow: hidden; }

      .toolbar {
        height: 48px; flex-shrink: 0;
        background: #fff; border-bottom: 1px solid #e5e5e5;
        display: flex; align-items: center; gap: 6px; padding: 0 14px;
      }
      .tb-btn {
        height: 30px; padding: 0 10px; border-radius: 6px;
        border: 1px solid #e5e5e5; background: #fafafa; cursor: pointer;
        font-size: 13px; color: #525252;
        display: inline-flex; align-items: center; gap: 5px;
        white-space: nowrap; font-family: inherit;
      }
      .tb-btn:hover { background: #f5f5f4; color: #171717; }
      .tb-sep { width: 1px; height: 20px; background: #e5e5e5; margin: 0 4px; }
      .tb-spacer { flex: 1; }

      .grid-wrap { flex: 1; overflow: hidden; }

      .statusbar {
        height: 26px; flex-shrink: 0;
        background: #fff; border-top: 1px solid #e5e5e5;
        display: flex; align-items: center; padding: 0 14px; gap: 20px;
      }
      .statusbar .sb-text { font-size: 11px; color: #a3a3a3; }
    </style>
    <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
    """)

    rows: list[dict] = [dict(EMPTY_ROW)]

    # ── Dialogue configuration ────────────────────────────────────────────────
    with (
        ui.dialog() as cfg_dialog,
        ui.card().style("width:420px; padding:24px; gap:16px"),
    ):
        ui.label("Configuration du gateway").style(
            "font-size:15px; font-weight:500; color:#292524"
        )
        inp_addr = ui.input("Adresse locale", placeholder="192.168.1.42:8080").classes(
            "w-full"
        )
        inp_user = ui.input("Identifiant").classes("w-full")
        inp_pwd = ui.input(
            "Mot de passe", password=True, password_toggle_button=True
        ).classes("w-full")
        cfg_msg = ui.label("").style("font-size:12px; color:#dc2626; min-height:16px")

        with ui.row().classes("items-center gap-2"):
            ui.label("Importer device.json").style("font-size:12px; color:#a3a3a3")

            def handle_json_upload(e):
                try:
                    data = json.loads(e.content.read())
                    _device_cfg.update(data)
                    inp_addr.set_value(_device_cfg.get("local_adress", ""))
                    inp_user.set_value(_device_cfg.get("username", ""))
                    inp_pwd.set_value(_device_cfg.get("password", ""))
                    cfg_msg.set_text("")
                except Exception:
                    cfg_msg.set_text("Fichier JSON invalide.")

            ui.upload(on_upload=handle_json_upload, auto_upload=True).props(
                "accept=.json flat dense"
            )

        with ui.row().classes("w-full justify-end gap-2").style("padding-top:8px"):
            ui.button("Annuler", on_click=cfg_dialog.close).props("flat dense").style(
                "color:#737373; font-size:13px"
            )

            def save_cfg():
                _device_cfg["local_adress"] = inp_addr.value.strip()
                _device_cfg["username"] = inp_user.value.strip()
                _device_cfg["password"] = inp_pwd.value.strip()
                status = build_sender_from_cfg()
                device_lbl.set_text(status)
                if status.startswith(("Erreur", "Champs")):
                    cfg_msg.set_text(status)
                else:
                    cfg_msg.set_text("")
                    cfg_dialog.close()

            ui.button("Enregistrer", on_click=save_cfg).style(
                "background:#1c1917; color:#fff; font-size:13px; padding:0 16px; border-radius:6px"
            )

    def open_config():
        inp_addr.set_value(_device_cfg.get("local_adress", ""))
        inp_user.set_value(_device_cfg.get("username", ""))
        inp_pwd.set_value(_device_cfg.get("password", ""))
        cfg_dialog.open()

    # ── Layout ────────────────────────────────────────────────────────────────
    with ui.element("div").classes("app-frame"):
        # Sidebar
        with ui.element("div").classes("sidebar"):
            ui.button(icon="message", on_click=lambda: None).classes(
                "sb-btn active"
            ).props("flat dense unelevated")
            ui.element("div").classes("sb-spacer")
            ui.button(icon="settings", on_click=open_config).classes("sb-btn").props(
                "flat dense unelevated"
            )

        # Main
        with ui.element("div").classes("main-area"):
            # Toolbar
            with ui.element("div").classes("toolbar"):
                # Importer
                def handle_import(e):
                    suffix = Path(e.name).suffix.lower()
                    with tempfile.NamedTemporaryFile(
                        delete=False, suffix=suffix
                    ) as tmp:
                        tmp.write(e.content.read())
                        tmp_path = Path(tmp.name)
                    try:
                        df = load_db(tmp_path)
                        new_rows = df.to_dict("records")
                        for r in new_rows:
                            for k in EMPTY_ROW:
                                r.setdefault(k, "")
                        rows.clear()
                        rows.extend(new_rows)
                        grid.options["rowData"] = rows
                        grid.update()
                        count_lbl.set_text(_count_text(rows))
                        ui.notify(
                            f"{e.name} — {len(rows)} lignes importées", type="positive"
                        )
                    except Exception as ex:
                        ui.notify(f"Erreur import : {ex}", type="negative")
                    finally:
                        tmp_path.unlink(missing_ok=True)

                with ui.element("label").style(
                    "height:30px; padding:0 10px; border-radius:6px; border:1px solid #e5e5e5;"
                    "background:#fafafa; cursor:pointer; font-size:13px; color:#525252;"
                    "display:inline-flex; align-items:center; gap:5px; white-space:nowrap;"
                ):
                    ui.html("⬆ Importer")
                    ui.upload(on_upload=handle_import, auto_upload=True).props(
                        "accept=.csv,.ods"
                    ).style("display:none")

                # Exporter
                async def export_csv():
                    df = pd.DataFrame(rows)
                    with tempfile.NamedTemporaryFile(
                        mode="w", suffix=".csv", delete=False, newline=""
                    ) as tmp:
                        df.to_csv(tmp, index=False)
                        tmp_path = Path(tmp.name)
                    ui.download(tmp_path, "messages_export.csv")
                    ui.notify("Export CSV prêt", type="positive")

                ui.button("⬇ Exporter", on_click=export_csv).classes("tb-btn").props(
                    "flat dense unelevated no-caps"
                )

                ui.element("div").classes("tb-sep")

                # Ajouter ligne
                def add_row():
                    rows.append(dict(EMPTY_ROW))
                    grid.options["rowData"] = rows
                    grid.update()
                    count_lbl.set_text(_count_text(rows))

                ui.button("+ Ajouter", on_click=add_row).classes("tb-btn").props(
                    "flat dense unelevated no-caps"
                )

                # Supprimer
                async def delete_selected():
                    selected = await grid.run_grid_method("getSelectedRows")
                    if not selected:
                        ui.notify("Aucune ligne sélectionnée.", type="warning")
                        return
                    before = len(rows)
                    for s in selected:
                        for r in rows:
                            if all(r.get(k) == s.get(k) for k in EMPTY_ROW):
                                rows.remove(r)
                                break
                    if not rows:
                        rows.append(dict(EMPTY_ROW))
                    grid.options["rowData"] = rows
                    grid.update()
                    removed = before - len(rows)
                    count_lbl.set_text(_count_text(rows))
                    ui.notify(f"{removed} ligne(s) supprimée(s)", type="info")

                ui.button("🗑 Supprimer", on_click=delete_selected).classes(
                    "tb-btn"
                ).props("flat dense unelevated no-caps")

                ui.element("div").classes("tb-spacer")

            # AG Grid
            with ui.element("div").classes("grid-wrap"):
                grid = ui.aggrid(
                    {
                        "columnDefs": COLUMNS,
                        "rowData": rows,
                        "rowSelection": {"mode": "multiRow"},
                        "defaultColDef": {
                            "resizable": True,
                            "sortable": False,
                            "suppressMovable": True,
                            "cellStyle": {
                                "fontSize": "13px",
                                "fontFamily": "ui-sans-serif, system-ui, sans-serif",
                            },
                        },
                        "stopEditingWhenCellsLoseFocus": True,
                        "undoRedoCellEditing": True,
                        "domLayout": "normal",
                    }
                ).style("height: 100%; width: 100%;")

            # Sync rows après édition inline
            async def sync_rows_from_grid():
                data = await grid.run_grid_method("getGridOption", "rowData")
                if data:
                    rows.clear()
                    rows.extend(data)

            grid.on("cellValueChanged", lambda _: sync_rows_from_grid())

            # Barre de statut
            with ui.element("div").classes("statusbar"):
                count_lbl = ui.element("span").classes("sb-text")
                with count_lbl:
                    ui.label(_count_text(rows))

                status_text = try_load_default_device()
                device_lbl = ui.element("span").classes("sb-text")
                with device_lbl:
                    ui.label(status_text)


def _count_text(rows: list) -> str:
    n = len(rows)
    return f"{n} ligne{'s' if n > 1 else ''}"


# ── Lancement ─────────────────────────────────────────────────────────────────
ui.run(
    title="VoSMS",
    host="0.0.0.0",
    port=8080,
    reload=False,
    dark=False,
    favicon="💬",
)
