# launcher.py
import json
import sys
import subprocess
from pathlib import Path
import time
import pygame

PROFILES_PATH = Path("profiles.json")
MECHANIK_SCRIPT = "mechanik_controller.py"  # seu script oficial

MAIN_HEADER = """
Ardurail Controller

selecione o jogo:
"""

CFG_MENU = """
Configurar perfil

1 - configurar botao
2 - configurar eixo
3 - salvar configuração

0 - sair
"""

SPECIAL_KEYS_TABLE = """
Teclas especiais suportadas (digite exatamente como abaixo):

space      → espaço
delete     → Delete
pagedown   → Page Down
pageup     → Page Up
tab        → Tab
ctrl       → Control
shift      → Shift
alt        → Alt
esc        → Escape
enter      → Enter
backspace  → Backspace
up         → Seta para cima
down       → Seta para baixo
left       → Seta para esquerda
right      → Seta para direita
home       → Home
insert     → Insert
f1 f2 f3 f4 f5 f6 f7 f8 f9 f10 f11 f12 → Teclas de função

[Teclado numérico — aliases práticos]
num0 num1 num2 num3 num4 num5 num6 num7 num8 num9
num_add ( + ), num_subtract ( - ), num_multiply ( * ), num_divide ( / )
num_decimal ( . ), num_enter ( Enter do numérico )

Obs.: em muitos sistemas o pynput não diferencia numérico do topo do teclado.
Os aliases 'numX' mapeiam para os mesmos sinais (0–9, +, -, *, /, ., Enter).
"""

# ---------- I/O perfis ----------
def load_profiles():
    if PROFILES_PATH.exists():
        return json.loads(PROFILES_PATH.read_text(encoding="utf-8"))
    return {}

def save_profiles(data):
    PROFILES_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

# ---------- Execução ----------
def run_mechanik():
    try:
        subprocess.run([sys.executable, MECHANIK_SCRIPT], check=False)
    except FileNotFoundError:
        print(f"\n[ERRO] Não encontrei {MECHANIK_SCRIPT}.")
        input("Enter para voltar...")

def run_generic(profile_name):
    try:
        subprocess.run([sys.executable, "generic_controller.py", "--profile", profile_name], check=False)
    except FileNotFoundError:
        print("\n[ERRO] generic_controller.py não encontrado.")
        input("Enter para voltar...")

# ---------- Helpers joystick ----------
def init_joystick():
    pygame.init()
    pygame.joystick.init()
    if pygame.joystick.get_count() == 0:
        print("Nenhum joystick encontrado. Conecte e tente de novo.")
        return None
    js = pygame.joystick.Joystick(0)
    js.init()
    print(f"Usando joystick: {js.get_name()} | Botões: {js.get_numbuttons()} | Eixos: {js.get_numaxes()}")
    return js

def wait_button_press(js):
    print("Pressione o botão que deseja configurar (ESC para cancelar)...")
    clock = pygame.time.Clock()
    last = [0] * js.get_numbuttons()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return None
        pygame.event.pump()
        for b in range(js.get_numbuttons()):
            s = js.get_button(b)
            if s == 1 and last[b] == 0:
                print(f"Botão {b} detectado.")
                return b
            last[b] = s
        clock.tick(120)

def wait_axis_move(js, msg="Mova o eixo que deseja configurar (ESC para cancelar)...", threshold=0.25):
    print(msg)
    clock = pygame.time.Clock()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return None, None
        pygame.event.pump()
        for a in range(js.get_numaxes()):
            try:
                v = js.get_axis(a)
            except Exception:
                v = 0.0
            if abs(v) >= threshold:
                print(f"Eixo {a} detectado (valor {v:+.3f}).")
                return a, v
        clock.tick(120)

def input_nonempty(prompt):
    while True:
        s = input(prompt).strip()
        if s:
            return s

def input_int(prompt, valid=None):
    while True:
        s = input(prompt).strip()
        if s.isdigit() or (s.startswith('-') and s[1:].isdigit()):
            v = int(s)
            if valid is None or v in valid:
                return v
        print("Valor inválido.")

def input_key_with_help(prompt):
    print(SPECIAL_KEYS_TABLE)
    return input_nonempty(prompt).lower()

# ---------- Construção de perfis ----------
def configure_button(profile):
    js = init_joystick()
    if js is None:
        input("Enter para voltar...")
        return

    btn = wait_button_press(js)
    if btn is None:
        print("Cancelado.")
        return

    key = input_key_with_help("Digite a tecla a ser acionada (ex: a, s, space, delete, pageup, pagedown...): ")

    print("Tipo de botão:")
    print("1 - press (normal)   [um acionamento com duração mínima]")
    print("2 - hold (auto-repeat enquanto pressionado)")
    print("3 - instant (tap seco)  [avançado, não recomendado]")
    t = input_int("> ", valid={1,2,3})
    mode = {1:"single", 2:"hold", 3:"instant"}[t]

    press_seconds = None
    if mode == "single":
        ans = input("Duração do press (seg.) [Enter para usar padrão do perfil]: ").strip()
        if ans:
            try:
                press_seconds = float(ans)
            except:
                print("Valor inválido, usando padrão do perfil.")

    profile.setdefault("buttons", {})
    profile["buttons"][str(btn)] = {
        "key": key,
        "mode": mode
    }
    if press_seconds is not None:
        profile["buttons"][str(btn)]["press_seconds"] = press_seconds

    print(f"✓ Botão {btn} → '{key}' ({mode}" + (f", {press_seconds:.2f}s" if press_seconds else "") + ").")

def configure_axis(profile):
    js = init_joystick()
    if js is None:
        input("Enter para voltar...")
        return

    axis, sample = wait_axis_move(js)
    if axis is None:
        print("Cancelado.")
        return

    print("\nTipo de mapeamento do eixo:")
    print("1 - passos (escolher duas teclas para + e -)")
    print("2 - seções (definir quantas seções e tecla por seção)")
    t = input_int("> ", valid={1,2})

    profile.setdefault("axes", {})

    if t == 1:
        steps = input_int("Quantos passos (ex.: 10): ")
        invert = input_int("Inverter sentido? 1=sim, 0=não: ", valid={0,1}) == 1
        key_pos = input_key_with_help("Tecla para passo POSITIVO (ex.: down): ")
        key_neg = input_key_with_help("Tecla para passo NEGATIVO (ex.: up): ")
        tap_hold = float(input_nonempty("Segurar cada tap (seg.) [sugestão 0.06]: "))
        tap_interval = float(input_nonempty("Intervalo entre taps (seg.) [sugestão 0.06]: "))

        profile["axes"][str(axis)] = {
            "type": "steps_to_buttons",
            "steps": steps,
            "invert": invert,
            "key_pos": key_pos,   # delta > 0
            "key_neg": key_neg,   # delta < 0
            "tap_hold": tap_hold,
            "tap_interval": tap_interval
        }
        print(f"✓ Eixo {axis}: passos→({key_pos}/{key_neg}) (steps={steps}, invert={invert}, hold={tap_hold}s, interval={tap_interval}s).")

    else:
        buckets = input_int("Quantas seções? (ex.: 11): ")
        invert = input_int("Inverter sentido? 1=sim, 0=não: ", valid={0,1}) == 1
        keys = []
        print("Defina as teclas por seção:")
        for i in range(1, buckets+1):
            k = input_key_with_help(f"Seção {i} → tecla: ")
            keys.append(k)

        repeat = input_int("Repetição contínua? 1=sim, 0=não: ", valid={0,1}) == 1
        repeat_interval = 0.5
        if repeat:
            try:
                repeat_interval = float(input_nonempty("Intervalo de repetição (seg.) [ex.: 0.5]: "))
            except:
                print("Valor inválido, usando 0.5s.")

        profile["axes"][str(axis)] = {
            "type": "sections_to_keys",
            "buckets": buckets,
            "keys": keys,
            "invert": invert,
            "repeat": repeat,
            "repeat_interval": repeat_interval
        }
        print(f"✓ Eixo {axis}: seções={buckets} → teclas definidas (invert={invert}, repeat={repeat}).")

def create_profile():
    # defaults seguros (sem "tap seco" implícito)
    profile = {
        "press_hold_seconds": 0.12,         # press normal
        "button_hold_repeat_hold": 0.06,    # cada repetição do HOLD
        "repeat_delay": 0.35,
        "repeat_interval": 0.05,
        "buttons": {},       # "idx" -> {"key": "a", "mode": "single|hold|instant", "press_seconds": opcional}
        "axes": {},          # "idx" -> {type, ...}
        "joystick_id": 0
    }

    while True:
        print(CFG_MENU)
        opt = input("> ").strip()
        if opt == "1":
            configure_button(profile)
        elif opt == "2":
            configure_axis(profile)
        elif opt == "3":
            name = input_nonempty("Nome do jogo/perfil (como deve aparecer no menu): ")
            profiles = load_profiles()
            profiles[name] = profile
            save_profiles(profiles)
            print(f"✓ Perfil '{name}' salvo.")
            input("Enter para voltar ao menu principal...")
            return
        elif opt == "0":
            return
        else:
            print("Opção inválida.")

# ---------- Menu principal dinâmico ----------
def main_menu():
    while True:
        profiles = load_profiles()
        profile_names = sorted(profiles.keys(), key=str.lower)

        print(MAIN_HEADER.strip(), end="\n\n")

        # 1) mechanik (fixo)
        print("1 - mechanik")
        num_to_action = {"1": ("mechanik", None)}

        # 2..N) perfis
        start_idx = 2
        for i, name in enumerate(profile_names, start=start_idx):
            print(f"{i} - {name}")
            num_to_action[str(i)] = ("profile", name)

        print("\n9 - criar nova config")
        print("0 - sair")

        opt = input("> ").strip()

        if opt == "1":
            run_mechanik()
        elif opt == "9":
            create_profile()
        elif opt == "0":
            print("Até mais!")
            return
        elif opt in num_to_action:
            action, payload = num_to_action[opt]
            if action == "profile" and payload:
                run_generic(payload)
            else:
                print("Opção inválida.")
        else:
            print("Opção inválida.")

if __name__ == "__main__":
    main_menu()
