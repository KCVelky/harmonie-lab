"""Contrôles d'intégration sans serveur graphique (Streamlit AppTest)."""
from pathlib import Path
from streamlit.testing.v1 import AppTest

def app():
    at=AppTest.from_file(str(Path(__file__).with_name('app.py')),default_timeout=60).run()
    assert not at.exception
    return at

def button(at,label):
    return next(b for b in at.button if b.label==label)

def test_ui_material_boundary_strings_and_modes():
    at=app()
    at.selectbox(key='material').select('Bouleau CP — WISA 4 mm / 3 plis (comparaison)').run()
    assert not at.exception and at.number_input(key='p_Es').value==16.471
    at.selectbox(key='p_boundary').select('Encastrement').run()
    assert not at.exception
    at.number_input(key='nstrings').set_value(7).run()
    assert not at.exception and len(at.session_state.rows)==7
    next(x for x in at.radio if x.label=='Système observé').set_value('Ensemble couplé').run()
    assert not at.exception

def test_ui_inverse_tuning_and_project_reset():
    at=app()
    button(at,'Appliquer cette tension à la corde').click().run()
    assert not at.exception
    assert abs(at.session_state.rows[0]['T (N)']-34.096)<.1
    button(at,'Calculer l’épaisseur correspondante').click().run()
    assert not at.exception
    button(at,'Appliquer cette épaisseur').click().run()
    assert not at.exception and 2<at.number_input(key='p_h').value<3
    button(at,'Réinitialiser le prototype').click().run()
    assert not at.exception and at.number_input(key='p_h').value==2

def test_ui_frf_audio_and_convergence():
    at=app()
    for label in ['Calculer la réponse fréquentielle','Créer le son combiné']:
        button(at,label).click().run()
        assert not at.exception

def test_ui_harmonic_configuration():
    at=app()
    at.selectbox(key='harmonic_0').select(2).run()
    button(at,'Configurer tous les électroaimants').click().run()
    assert not at.exception
    assert abs(at.session_state.rows[0]['Aimant 1 / L']-.25)<1e-9
    assert at.session_state.rows[0]['Phase 2 relative (°)']==180

def test_ui_example_sequence_audio():
    at=app()
    button(at,'Utiliser cet exemple maintenant').click().run()
    assert not at.exception and at.session_state.score_name=='exemple_fur_elise.csv'
    button(at,'Écouter cette séquence sur la table').click().run()
    assert not at.exception

def test_ui_invalid_geometry_is_reported():
    at=app()
    at.number_input(key='p_bridge_s').set_value(900.).run()
    assert not at.exception
    assert any('Chevalet' in x.value for x in at.error)

def test_ui_museum_scenario():
    at=app()
    button(at,'Charger le scénario musée · 5 × 8 pi').click().run()
    assert not at.exception
    assert abs(at.number_input(key='p_H').value-2438.4)<.01
    assert abs(at.number_input(key='p_W').value-1524)<.01
    assert abs(at.number_input(key='p_h').value-3.175)<.001
    assert at.checkbox(key='support_enabled').value
    assert at.number_input(key='support_E').value==10
    assert at.number_input(key='g_installation_height').value==15000
