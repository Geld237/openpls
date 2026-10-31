"""Vérification de l'interface dans un vrai navigateur (éditeur glisser-déposer, ordre supérieur,
changement de jeu de données). AppTest ne peut pas piloter le composant de l'éditeur.

    pip install playwright && playwright install chromium
    openpls-gui &          # puis :
    python tests/browser_check.py
"""
import time

from playwright.sync_api import sync_playwright

URL = "http://localhost:8501"


def editor(pg):
    pg.wait_for_selector("iframe[title*='openpls_model_editor']", timeout=60000)
    time.sleep(2)
    return next(f for f in pg.frames if "openpls_model_editor" in f.url)


with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1500, "height": 2000})
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(URL)
    fr = editor(pg)

    # 1. glisser un indicateur libéré sur le fond crée une latente ; tirer une poignée crée un chemin
    fr.click(".lv[data-name='ETA2'] .ind:text-is('eta2_3')")
    fr.drag_and_drop(".chip[data-col='eta2_3']", "#canvas", target_position={"x": 700, "y": 420})
    new = [e.inner_text() for e in fr.query_selector_all(".lv .name") if e.inner_text() not in
           ("XI1", "XI2", "ETA1", "ETA2")][0]
    h = fr.query_selector(".lv[data-name='ETA1'] .handle").bounding_box()
    t = fr.query_selector(f".lv[data-name='{new}']").bounding_box()
    pg.mouse.move(h["x"] + 8, h["y"] + 8); pg.mouse.down()
    pg.mouse.move(t["x"] + 30, t["y"] + 15, steps=10); pg.mouse.up()
    fr.click("button:has-text('Appliquer au modèle')")
    time.sleep(4)
    pg.get_by_role("tab", name="Syntaxe").click()
    syntax = pg.input_value("textarea")
    assert f"{new} =~ eta2_3" in syntax and f"{new} ~ ETA1" in syntax, syntax

    # 2. second ordre : refus d'un chemin depuis une composante, syntaxe conservée
    pg.get_by_text("Exemple de second ordre", exact=True).click()
    time.sleep(4)
    assert pg.get_by_role("button", name="Estimer le modèle").is_enabled(), \
        "changement de données : l'ancienne syntaxe de l'éditeur a été réappliquée"
    pg.get_by_role("tab", name="Syntaxe").click()
    assert "QUALITE =~ L1 + L2 + L3" in pg.input_value("textarea")
    pg.get_by_role("tab", name="Éditeur visuel").click()
    fr = editor(pg)
    h = fr.query_selector(".lv[data-name='L1'] .handle").bounding_box()
    t = fr.query_selector(".lv[data-name='Y']").bounding_box()
    pg.mouse.move(h["x"] + 8, h["y"] + 8); pg.mouse.down()
    pg.mouse.move(t["x"] + 30, t["y"] + 15, steps=8); pg.mouse.up()
    assert "composante de QUALITE" in fr.inner_text("#msg")

    # 3. régression : revenir aux données d'exemple ne doit pas réappliquer l'ancienne syntaxe
    pg.get_by_text("Données d'exemple", exact=True).click()
    time.sleep(5)
    btn = pg.get_by_role("button", name="Estimer le modèle")
    assert btn.is_enabled(), "le bouton Estimer est désactivé après changement de données"
    btn.click()
    pg.wait_for_selector("h3:has-text('Coefficients de chemin')", timeout=60000)

    # 4. régression (audit) : un fichier corrigé de même nom et même taille efface les résultats,
    #    mais conserve le modèle saisi
    import tempfile
    from pathlib import Path

    from openpls.simulate import simulate

    tmp = Path(tempfile.mkdtemp())
    (tmp / "v1").mkdir(); (tmp / "v2").mkdir()
    simulate(300, seed=1).to_csv(tmp / "v1" / "enquete.csv", index=False)
    simulate(300, seed=2, eta_path=-0.2).to_csv(tmp / "v2" / "enquete.csv", index=False)
    pg.get_by_text("Importer un fichier", exact=True).click(); time.sleep(3)
    pg.set_input_files("input[type=file]", str(tmp / "v1" / "enquete.csv")); time.sleep(5)
    pg.get_by_role("tab", name="Syntaxe").click()
    model_txt = "XI1 =~ xi1_1 + xi1_2 + xi1_3\nETA1 =~ eta1_1 + eta1_2 + eta1_3\nETA1 ~ XI1"
    pg.locator("textarea").fill(model_txt); pg.locator("textarea").press("Control+Enter"); time.sleep(3)
    pg.get_by_role("button", name="Estimer le modèle").click()
    pg.wait_for_selector("h3:has-text('Coefficients de chemin')", timeout=60000); time.sleep(2)
    pg.set_input_files("input[type=file]", str(tmp / "v2" / "enquete.csv")); time.sleep(6)
    assert pg.locator("h3:has-text('Coefficients de chemin')").count() == 0, "résultats du fichier précédent encore affichés (onglet Résultats)"
    pg.get_by_role("tab", name="Syntaxe").click(); time.sleep(1)
    assert pg.locator("textarea").input_value().startswith("XI1 =~ xi1_1"), "modèle saisi perdu"

    assert not errors, errors
    print("OK — éditeur, ordre supérieur, changement et remplacement de fichiers vérifiés dans Chromium")
    b.close()
