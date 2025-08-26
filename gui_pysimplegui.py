import json
import subprocess
import sys
import PySimpleGUI as sg
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROFILE_FILE = BASE_DIR / "profiles.json"
GENERIC_CONTROLLER = BASE_DIR / "generic_controller.py"

# Utilitários para lidar com profiles

def load_profiles():
    if PROFILE_FILE.exists():
        with open(PROFILE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_profiles(data):
    with open(PROFILE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# Layout da GUI
sg.theme("DarkBlue14")

profiles = load_profiles()

profile_names = list(profiles.keys())

layout = [
    [sg.TabGroup([
        [
            sg.Tab("Perfis", [
                [sg.Text("Perfil atual:"), sg.Combo(profile_names, default_value=profile_names[0] if profile_names else "", key="-PROFILE-", enable_events=True)],
                [sg.Multiline("", size=(80, 20), key="-PROFILE_DATA-")],
                [sg.Button("Novo"), sg.Button("Salvar"), sg.Button("Excluir")]
            ]),
            sg.Tab("Execução", [
                [sg.Text("Selecione perfil:"), sg.Combo(profile_names, default_value=profile_names[0] if profile_names else "", key="-RUN_PROFILE-")],
                [sg.Button("Iniciar"), sg.Button("Parar")],
                [sg.Multiline("", size=(80,20), key="-OUTPUT-")]
            ]),
            sg.Tab("Ajuda", [
                [sg.Text("Teclas especiais suportadas:")],
                [sg.Multiline("seta_esquerda, seta_direita, seta_cima, seta_baixo, pageup, pagedown, home, insert, f1..f12, numpad0..numpad9", size=(80,10), disabled=True)],
                [sg.Text("Edite o JSON do perfil para mapear buttons e axes conforme exemplos.")]
            ])
        ]
    ])]
]

window = sg.Window("ArduRail Controller GUI", layout, finalize=True)

proc = None

# Lógica da GUI
while True:
    event, values = window.read()
    if event == sg.WINDOW_CLOSED:
        if proc and proc.poll() is None:
            proc.terminate()
        break

    if event == "-PROFILE-":
        sel = values["-PROFILE-"]
        if sel in profiles:
            window["-PROFILE_DATA-"].update(json.dumps(profiles[sel], indent=4, ensure_ascii=False))

    if event == "Novo":
        name = sg.popup_get_text("Nome do novo perfil:")
        if name:
            profiles[name] = {}
            save_profiles(profiles)
            window["-PROFILE-"].update(values=list(profiles.keys()), value=name)
            window["-RUN_PROFILE-"].update(values=list(profiles.keys()), value=name)
            window["-PROFILE_DATA-"].update("{}")

    if event == "Salvar":
        sel = values["-PROFILE-"]
        if not sel:
            sg.popup("Nenhum perfil selecionado")
            continue
        try:
            data = json.loads(values["-PROFILE_DATA-"])
            profiles[sel] = data
            save_profiles(profiles)
            sg.popup("Perfil salvo com sucesso")
        except Exception as e:
            sg.popup_error(f"Erro ao salvar: {e}")

    if event == "Excluir":
        sel = values["-PROFILE-"]
        if sel and sg.popup_yes_no(f"Excluir perfil {sel}?") == "Yes":
            profiles.pop(sel, None)
            save_profiles(profiles)
            window["-PROFILE-"].update(values=list(profiles.keys()), value="")
            window["-RUN_PROFILE-"].update(values=list(profiles.keys()), value="")
            window["-PROFILE_DATA-"].update("")

    if event == "Iniciar":
        sel = values["-RUN_PROFILE-"]
        if not sel:
            sg.popup("Selecione um perfil para rodar")
            continue
        if proc and proc.poll() is None:
            sg.popup("Já existe um processo rodando")
            continue
        cmd = [sys.executable, str(GENERIC_CONTROLLER), "--profile", sel]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        sg.popup("Controlador iniciado")

    if event == "Parar":
        if proc and proc.poll() is None:
            proc.terminate()
            sg.popup("Processo parado")

    # Atualiza output se processo ativo
    if proc and proc.poll() is None:
        try:
            line = proc.stdout.readline()
            if line:
                window["-OUTPUT-"].update(line, append=True)
        except:
            pass

window.close()
