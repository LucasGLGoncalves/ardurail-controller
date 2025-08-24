"""
Gamepad -> Teclado (Python)
- Índice 0..6 mapeado para ['z','x','c','v','b','n','m']
- Botão NEXT incrementa o índice (até 6), botão PREV decrementa (até 0)
- Outros botões: A, S, Espaço, Delete, End, PageDown
- Eixo analógico 1 em 0..10 etapas (freios):
  • Avança etapas: seta PARA BAIXO (↓) — 1 tap por passo (sequenciado)
  • Regride etapas: seta PARA CIMA  (↑) — 1 tap por passo (sequenciado)
- Eixo analógico 2 em 7 seções:
  • Navega por Z X C V B N M
  • (por padrão) NÃO repete continuamente; só pressiona ao mudar de seção

Extra:
- Delete e PageDown: instantâneos (press/release imediato)
- INSPECT: imprime estados (botões/eixos) e NÃO envia teclas.

Requisitos: pip install pygame pynput
"""

import time
import sys
import argparse
import pygame
from pynput.keyboard import Controller, Key

# ===================== CONFIG PADRÃO =====================

# Joystick
JOYSTICK_ID = 0

# Ativar modo inspeção (pode ser sobrescrito por --inspect)
INSPECT = False

# Duração geral de "segurar" teclas (usada pelo agendador para teclas normais)
PRESS_HOLD_SECONDS = 0.5

# Teclas com comportamento INSTANTÂNEO (sem segurar)
INSTANT_KEYS = {'delete', 'pagedown'}

# Repetição (hold) para alguns botões
REPEAT_DELAY = 0.35      # atraso inicial (s) para A/S/End
REPEAT_INTERVAL = 0.05   # intervalo entre repetições (s) para A/S/End

# Eixo 2 (Z..M): repetição contínua desativada por padrão
REPEAT_AXIS2 = False           # <<<<< altere para True se quiser repetir
KEYS_REPEAT_INTERVAL = 0.5     # usado só se REPEAT_AXIS2=True

# “Tap” curto e sequenciado para setas ↑/↓ (evita perder passos no jogo)
ARROW_TAP_HOLD = 0.06      # quanto tempo segurar cada tap de ↑/↓
ARROW_TAP_INTERVAL = 0.06  # intervalo mínimo entre taps ↑/↓

# Sequência de teclas "indexadas"
KEY_SEQUENCE = ['z', 'x', 'c', 'v', 'b', 'n', 'm']
MIN_IDX = 0
MAX_IDX = len(KEY_SEQUENCE) - 1

# Botões do controle (ajuste aos índices do seu dispositivo)
BUTTON_A     = 17
BUTTON_S     = 18
BUTTON_DEL   = 19
BUTTON_PGDN  = 20
BUTTON_END   = 21
BUTTON_SPACE = 22
BUTTON_PREV  = 23  # decrementa índice
BUTTON_NEXT  = 24  # incrementa índice

# Teclas especiais
SPECIALS = {
    'space': Key.space,
    'delete': Key.delete,
    'end': Key.end,
    'pagedown': Key.page_down,
    'up': Key.up,
    'down': Key.down,
}

# Botões com comportamento de HOLD (auto-repeat)
HOLD_BUTTONS = {
    BUTTON_A: 'a',
    BUTTON_S: 's',
    BUTTON_END: 'end',
}

# ============ EIXO 1: ANALÓGICO EM ETAPAS 0..10 PARA ↑/↓ ============
ANALOG_AXIS = 1
STEP_LEVELS = 10
AXIS_INVERT = False
STEP_DEBUG  = True

# ============ EIXO 2: ANALÓGICO EM SEÇÕES PARA Z..M ================
ANALOG_AXIS_KEYS = 2
AXIS_KEYS_INVERT = False
AXIS_KEYS_DEBUG  = True
# ===================================================================

kb = Controller()

# ---------- Agendador de pressionamentos ----------
active_holds = {}

def _resolve_key(k):
    """Converte rótulo ('a','space',...) em objeto Key/char para pynput."""
    if isinstance(k, str) and len(k) == 1:
        return k
    if isinstance(k, str):
        return SPECIALS.get(k.lower(), k)
    return k

def schedule_press(k, now=None, hold_seconds=PRESS_HOLD_SECONDS, force_instant=False):
    """
    Pressiona e agenda soltura após hold_seconds (não bloqueante).
    - force_instant=True -> press/release imediato
    - INSTANT_KEYS -> sempre instantâneas
    """
    global active_holds
    if now is None:
        now = time.time()
    keyobj = _resolve_key(k)

    # Instantâneo por regra
    if force_instant or (isinstance(k, str) and k.lower() in INSTANT_KEYS):
        kb.press(keyobj)
        kb.release(keyobj)
        return

    # Se já está ativa, prorroga a soltura
    if keyobj in active_holds:
        active_holds[keyobj] = now + hold_seconds
        return

    # Pressiona e agenda soltura
    kb.press(keyobj)
    active_holds[keyobj] = now + hold_seconds

def process_releases(now=None):
    """Solta quaisquer teclas cujo tempo de segurar tenha expirado."""
    global active_holds
    if now is None:
        now = time.time()
    to_release = [k for k, t in active_holds.items() if now >= t]
    for k in to_release:
        try:
            kb.release(k)
        except Exception:
            pass
        active_holds.pop(k, None)

# --------------------------------------------------------------------

def axis_value_to_step(val, levels=STEP_LEVELS, invert=AXIS_INVERT):
    """Converte valor do eixo [-1..1] para etapa inteira [0..levels]."""
    if invert:
        val = -val
    norm = (val + 1.0) / 2.0
    norm = max(0.0, min(1.0, norm))
    step = int(norm * levels + 1e-9)
    return max(0, min(levels, step))

def axis_value_to_bucket(val, buckets, invert=False):
    """Converte valor do eixo [-1..1] para índice [0..buckets-1]."""
    if invert:
        val = -val
    norm = (val + 1.0) / 2.0
    norm = max(0.0, min(1.0, norm))
    idx = int(norm * buckets - 1e-9)
    return max(0, min(buckets - 1, idx))

def parse_args():
    p = argparse.ArgumentParser(description="Mapeia joystick -> teclado")
    p.add_argument("--inspect", action="store_true", help="Rodar em modo inspeção (não envia teclas)")
    p.add_argument("--joystick-id", type=int, default=JOYSTICK_ID, help="ID do joystick (padrão 0)")
    return p.parse_args()

def main():
    global INSPECT
    args = parse_args()
    if args.inspect:
        INSPECT = True
    js_id = args.joystick_id

    pygame.init()
    pygame.joystick.init()

    if pygame.joystick.get_count() == 0:
        print("Nenhum joystick encontrado.")
        return

    js = pygame.joystick.Joystick(js_id)
    js.init()
    print(f"Usando joystick: {js.get_name()} (id={js_id})")
    print(f"Botões detectados: {js.get_numbuttons()}")
    print(f"Eixos detectados:  {js.get_numaxes()}")
    if INSPECT:
        print("\n[MODO INSPECT] Mostrando mudanças de botões e valores de eixos. Nenhuma tecla será enviada.\n")

    num_buttons = js.get_numbuttons()
    last_state = [0] * num_buttons

    # Estado inicial dos eixos
    try:
        axis_val = js.get_axis(ANALOG_AXIS)
    except Exception:
        axis_val = 0.0
    last_axis_step = axis_value_to_step(axis_val)

    try:
        axis_keys_val = js.get_axis(ANALOG_AXIS_KEYS)
    except Exception:
        axis_keys_val = 0.0
    current_bucket = axis_value_to_bucket(axis_keys_val, len(KEY_SEQUENCE), invert=AXIS_KEYS_INVERT)

    # Controle de repetição (A/S/End) e (opcional) repetição do eixo Z..M
    hold_state = {}
    current_idx = current_bucket  # alinha índice com bucket inicial
    next_keys_repeat_time = time.time() + KEYS_REPEAT_INTERVAL

    # Fila sequenciada para setas ↑/↓
    pending_up = 0
    pending_down = 0
    next_arrow_time = time.time()

    clock = pygame.time.Clock()

    # ===== Loop principal =====
    while True:
        pygame.event.pump()
        now = time.time()

        # ----------------- MODO INSPECT -----------------
        if INSPECT:
            for b in range(num_buttons):
                state = js.get_button(b)
                if state != last_state[b]:
                    print(f"[BOTÃO {b}] -> {'PRESS' if state else 'RELEASE'}")
                last_state[b] = state

            axis_line = []
            for a in range(js.get_numaxes()):
                try:
                    val = js.get_axis(a)
                except Exception:
                    val = 0.0
                axis_line.append(f"E{a}:{val:+.3f}")
            print(" | ".join(axis_line))

            clock.tick(10)
            continue

        # ----------------- MODO NORMAL ------------------

        # ===== BOTÕES =====
        for b in range(num_buttons):
            state = js.get_button(b)

            if b in HOLD_BUTTONS:
                key_to_type = HOLD_BUTTONS[b]
                if state == 1 and last_state[b] == 0:
                    schedule_press(key_to_type, now)
                    hold_state[b] = {"held": True, "next_time": now + REPEAT_DELAY}
                elif state == 1 and last_state[b] == 1:
                    info = hold_state.get(b)
                    if info and info.get("held") and now >= info.get("next_time", 0):
                        schedule_press(key_to_type, now)
                        info["next_time"] = now + REPEAT_INTERVAL
                elif state == 0 and last_state[b] == 1:
                    if b in hold_state:
                        hold_state.pop(b, None)
                last_state[b] = state
                continue

            if state == 1 and last_state[b] == 0:
                if b == BUTTON_A: schedule_press('a', now); print("A")
                elif b == BUTTON_S: schedule_press('s', now); print("S")
                elif b == BUTTON_DEL: schedule_press('delete', now); print("DELETE")
                elif b == BUTTON_PGDN: schedule_press('pagedown', now); print("PAGEDOWN")
                elif b == BUTTON_END: schedule_press('end', now); print("END")
                elif b == BUTTON_SPACE: schedule_press('space', now); print("SPACE")
                elif b == BUTTON_PREV:
                    if current_idx > MIN_IDX:
                        current_idx -= 1
                        schedule_press(KEY_SEQUENCE[current_idx], now)
                        print(f"[PREV] idx={current_idx} -> '{KEY_SEQUENCE[current_idx]}'")
                    else:
                        print("[PREV] já no mínimo (Z)")
                elif b == BUTTON_NEXT:
                    if current_idx < MAX_IDX:
                        current_idx += 1
                        schedule_press(KEY_SEQUENCE[current_idx], now)
                        print(f"[NEXT] idx={current_idx} -> '{KEY_SEQUENCE[current_idx]}'")
            last_state[b] = state

        # ===== EIXO 1: ↑/↓ por etapas (sequenciado) =====
        try:
            axis_val = js.get_axis(ANALOG_AXIS)
        except Exception:
            axis_val = 0.0
        step = axis_value_to_step(axis_val)
        if step != last_axis_step:
            delta = step - last_axis_step
            if STEP_DEBUG:
                print(f"[AXIS {ANALOG_AXIS}] {last_axis_step} -> {step} (Δ {delta:+d})")
            if delta > 0:
                pending_down += delta   # acumula taps de "down"
            else:
                pending_up += -delta    # acumula taps de "up"
            last_axis_step = step

        # Dispara uma seta de cada vez, respeitando o espaçamento
        if now >= next_arrow_time:
            if pending_down > 0:
                schedule_press('down', now, hold_seconds=ARROW_TAP_HOLD, force_instant=False)
                pending_down -= 1
                next_arrow_time = now + ARROW_TAP_INTERVAL
            elif pending_up > 0:
                schedule_press('up', now, hold_seconds=ARROW_TAP_HOLD, force_instant=False)
                pending_up -= 1
                next_arrow_time = now + ARROW_TAP_INTERVAL

        # ===== EIXO 2: Z..M por seções (sem repetição contínua) =====
        try:
            axis_keys_val = js.get_axis(ANALOG_AXIS_KEYS)
        except Exception:
            axis_keys_val = 0.0
        bucket = axis_value_to_bucket(axis_keys_val, len(KEY_SEQUENCE), invert=AXIS_KEYS_INVERT)
        if bucket != current_bucket:
            if AXIS_KEYS_DEBUG:
                print(f"[AXIS {ANALOG_AXIS_KEYS}] {current_bucket} -> {bucket}")
            current_bucket = bucket
            current_idx = bucket
            schedule_press(KEY_SEQUENCE[current_bucket], now)  # uma vez ao entrar na seção
            if REPEAT_AXIS2:
                next_keys_repeat_time = now + KEYS_REPEAT_INTERVAL

        # Se quiser repetição contínua do eixo 2, habilite REPEAT_AXIS2=True
        if REPEAT_AXIS2 and now >= next_keys_repeat_time:
            schedule_press(KEY_SEQUENCE[current_bucket], now)
            next_keys_repeat_time = now + KEYS_REPEAT_INTERVAL

        # ===== PROCESSA SOLTURAS =====
        process_releases(now)

        clock.tick(120)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nEncerrado pelo usuário.")
