import tempfile
from pathlib import Path

import pandas as pd
from nicegui import ui

from core import load_db, send_batch_sms

COLUMNS = [
    {"field": "dest", "headerName": "Nom", "flex": 2, "editable": True},
    {"field": "phone", "headerName": "Numéro", "flex": 2, "editable": True},
    {"field": "header", "headerName": "En-tête", "flex": 2, "editable": True},
    {"field": "message", "headerName": "Message", "flex": 4, "editable": True},
]
EMPTY_ROW = {"dest": "", "phone": "", "header": "", "message": ""}


@ui.page("/")
def page():
    rows: list[dict] = [dict(EMPTY_ROW)]

    # --- Fenêtres d'import de fichiers
    with ui.dialog() as import_dialog, ui.card():

        async def handle_db_import(e):
            path = Path(e.file.name).resolve()
            db = load_db(path)

            rows.clear()
            for _, s in db.iterrows():
                rows.append(dict(s))

            grid.options["rowData"] = rows
            grid.update()
            import_dialog.close()

        ui.upload(on_upload=handle_db_import, auto_upload=True).props(
            "accept=.csv,.ods"
        )

    # ── Grille ────────────────────────────────────────────────────────────────
    grid = ui.aggrid(
        {
            "columnDefs": COLUMNS,
            "rowData": rows,
            "rowSelection": {"mode": "multiRow"},
        }
    )

    # ── Ajouter une ligne ─────────────────────────────────────────────────────
    async def add_row():
        # 1. Récupérer l'état actuel de la grille (éditions comprises)
        current = await grid.run_grid_method("getGridOption", "rowData")
        if current:
            rows.clear()
            rows.extend(current)

        # 2. Ajouter la nouvelle ligne
        rows.append(dict(EMPTY_ROW))
        grid.options["rowData"] = rows
        grid.update()

    # ── Supprimer les lignes sélectionnées ────────────────────────────────────
    async def delete_selected():
        selected = await grid.run_grid_method("getSelectedRows")
        for s in selected:
            if s in rows:
                rows.remove(s)
        grid.options["rowData"] = rows
        grid.update()

    # ── Générer un CSV temporaire depuis l'état actuel de la grille ───────────
    async def get_temp_csv() -> Path:
        current = await grid.run_grid_method("getGridOption", "rowData")
        df = pd.DataFrame(current)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode="w")
        df.to_csv(tmp, index=False)
        return Path(tmp.name)

    # ── Envoyer ───────────────────────────────────────────────────────────────
    async def send():
        csv_path = await get_temp_csv()
        try:
            send_batch_sms(csv_path, Path("device.json"))

        except Exception:
            pass

        finally:
            print(csv_path.read_text().splitlines())
            csv_path.unlink(missing_ok=True)

    # ── Boutons ───────────────────────────────────────────────────────────────
    with ui.row():
        ui.button("Importer", on_click=import_dialog.open)
        ui.button("Ajouter", on_click=add_row)
        ui.button("Supprimer", on_click=delete_selected)
        ui.button("Envoyer", on_click=send)


ui.run()
