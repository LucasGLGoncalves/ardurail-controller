"""
Gamepad -> Teclado (Python)
- Índice 0..6 mapeado para ['z','x','c','v','b','n','m']
- Botão NEXT incrementa o índice (até 6), botão PREV decrementa (até 0)
- Outros botões: A, S, Espaço, Delete, End, PageDown
- Eixo analógico 1 em 0..10 etapas:
  • Avança etapas: seta PARA BAIXO (↓)
  • Regride etapas: seta PARA CIMA  (↑)
- Eixo analógico 2 em 7 seções:
  • Navega por Z X C V B N M
  • Ao cruzar seções, digita a tecla da seção atual

Requisitos: pip install pygame pynput
"""

import time
import sys
import argparse
import pygame
from pynput.keyboard import Controller, Key

# ===================== CONFIG =====================

INSPECT = False  # ou use: python script.py --inspect

# Repetição (hold) para alguns botões
REPEAT_DELAY = 0.35      # atraso inicial (s)
REPEAT_INTERVAL = 0.05   # intervalo entre repetições (s)

# Joystick
JOYSTICK_ID = 0

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
ANALOG_AXIS = 1      # por exemplo: 0=X, 1=Y, 2=Rx, 3=Z (depende do dispositivo)
STEP_LEVELS = 10     # etapas entre 0 e 10 -> 11 posições
AXIS_INVERT = False  # inverte sentido se necessário
STEP_DEBUG  = True   # logs

# ============ EIXO 2: ANALÓGICO EM SEÇÕES PARA Z..M ================
ANALOG_AXIS_KEYS = 2          # eixo dedicado a navegar Z..M
AXIS_KEYS_INVERT = False      # inverte sentido se necessário
AXIS_KEYS_DEBUG  = True       # logs
# ===================================================================

kb = Controller()

def press_key(k):
    """Pressiona e solta uma tecla (char ou Key.*)."""
    keyobj = k
    if isinstance(k, str) and len(k) == 1:
        keyobj = k
    elif isinstance(k, str):
        keyobj = SPECIALS.get(k.lower(), k)
    kb.press(keyobj)
    kb.release(keyobj)

def axis_value_to_step(val, levels=STEP_LEVELS, invert=AXIS_INVERT):
    """
    Converte valor do eixo em [-1.0, 1.0] para etapa inteira em [0..levels].
    Ex.: levels=10 => etapas 0..10.
    """
    if invert:
        val = -val
    norm = (val + 1.0) / 2.0  # [0..1]
    if norm < 0.0: norm = 0.0
    if norm > 1.0: norm = 1.0
    step = int(norm * levels + 1e-9)
    if step < 0: step = 0
    if step > levels: step = levels
    return step

def axis_value_to_bucket(val, buckets, invert=False):
    """
    Converte valor do eixo em [-1.0, 1.0] para um índice de seção [0..buckets-1].
    Para 7 teclas (Z..M), buckets=7 -> índices 0..6.
    """
    if invert:
        val = -val
    norm = (val + 1.0) / 2.0  # [0..1]
    if norm < 0.0: norm = 0.0
    if norm > 1.0: norm = 1.0
    # Cada seção tem largura 1/buckets; 1.0 deve cair no último índice
    idx = int(norm * buckets - 1e-9)
    if idx < 0: idx = 0
    if idx > buckets - 1: idx = buckets - 1
    return idx

def main():
    pygame.init()
    pygame.joystick.init()

    if pygame.joystick.get_count() == 0:
        print("Nenhum joystick encontrado.")
        return

    js = pygame.joystick.Joystick(JOYSTICK_ID)
    js.init()
    print(f"Usando joystick: {js.get_name()} (id={JOYSTICK_ID})")
    print(f"Botões detectados: {js.get_numbuttons()}")
    print(f"Eixos detectados:  {js.get_numaxes()}")

    num_buttons = js.get_numbuttons()
    last_state = [0] * num_buttons

    # Repetição de HOLD por botão
    hold_state = {}

    # Índice inicial da sequência z..m
    current_idx = 0
    print(f"Índice inicial: {current_idx} -> tecla '{KEY_SEQUENCE[current_idx]}'")

    # Estado do eixo 1 em etapas
    try:
        axis_val = js.get_axis(ANALOG_AXIS)
    except Exception:
        axis_val = 0.0
    last_axis_step = axis_value_to_step(axis_val)
    if STEP_DEBUG:
        print(f"[AXIS {ANALOG_AXIS}] etapa inicial = {last_axis_step} (0..{STEP_LEVELS})")

    # Estado do eixo 2 em seções Z..M
    try:
        axis_keys_val = js.get_axis(ANALOG_AXIS_KEYS)
    except Exception:
        axis_keys_val = 0.0
    last_bucket = axis_value_to_bucket(axis_keys_val, len(KEY_SEQUENCE), invert=AXIS_KEYS_INVERT)
    if AXIS_KEYS_DEBUG:
        print(f"[AXIS {ANALOG_AXIS_KEYS}] bucket inicial = {last_bucket} -> '{KEY_SEQUENCE[last_bucket]}'")

    clock = pygame.time.Clock()

    while True:
        pygame.event.pump()
        now = time.time()

        # ======= Leitura e tradução de BOTÕES =======
        for b in range(num_buttons):
            state = js.get_button(b)

            # HOLD buttons
            if b in HOLD_BUTTONS:
                key_to_type = HOLD_BUTTONS[b]

                if state == 1 and last_state[b] == 0:
                    press_key(key_to_type)
                    hold_state[b] = {"held": True, "next_time": now + REPEAT_DELAY}

                elif state == 1 and last_state[b] == 1:
                    info = hold_state.get(b)
                    if info and info.get("held") and now >= info.get("next_time", 0):
                        press_key(key_to_type)
                        info["next_time"] = now + REPEAT_INTERVAL

                elif state == 0 and last_state[b] == 1:
                    if b in hold_state:
                        hold_state.pop(b, None)

                last_state[b] = state
                continue

            # Botões normais (borda de subida)
            if state == 1 and last_state[b] == 0:
                if b == BUTTON_A:
                    press_key('a'); print("A")
                elif b == BUTTON_S:
                    press_key('s'); print("S")
                elif b == BUTTON_DEL:
                    press_key('delete'); print("DELETE")
                elif b == BUTTON_PGDN:
                    press_key('pagedown'); print("PAGEDOWN")
                elif b == BUTTON_END:
                    press_key('end'); print("END")
                elif b == BUTTON_SPACE:
                    press_key('space'); print("SPACE")
                elif b == BUTTON_PREV:
                    if current_idx > MIN_IDX:
                        current_idx -= 1
                        press_key(KEY_SEQUENCE[current_idx])
                        print(f"[PREV] idx={current_idx} -> '{KEY_SEQUENCE[current_idx]}'")
                    else:
                        print("[PREV] já no mínimo (Z)")
                elif b == BUTTON_NEXT:
                    if current_idx < MAX_IDX:
                        current_idx += 1
                        press_key(KEY_SEQUENCE[current_idx])
                        print(f"[NEXT] idx={current_idx} -> '{KEY_SEQUENCE[current_idx]}'")
                    else:
                        print("[NEXT] já no máximo (M)")
            last_state[b] = state

        # ======= EIXO 1: etapas 0..10 para ↑/↓ =======
        try:
            axis_val = js.get_axis(ANALOG_AXIS)  # [-1.0..1.0]
        except Exception:
            axis_val = 0.0

        step = axis_value_to_step(axis_val)
        if step != last_axis_step:
            delta = step - last_axis_step
            if STEP_DEBUG:
                print(f"[AXIS {ANALOG_AXIS}] {last_axis_step} -> {step} (delta {delta}, val={axis_val:.3f})")
            if delta > 0:
                for _ in range(delta):
                    press_key('down')
            else:
                for _ in range(-delta):
                    press_key('up')
            last_axis_step = step

        # ======= EIXO 2: seções para Z..M =======
        try:
            axis_keys_val = js.get_axis(ANALOG_AXIS_KEYS)  # [-1.0..1.0]
        except Exception:
            axis_keys_val = 0.0

        bucket = axis_value_to_bucket(axis_keys_val, len(KEY_SEQUENCE), invert=AXIS_KEYS_INVERT)
        if bucket != last_bucket:
            # Quando cruza seção, dispara as teclas intermediárias na ordem
            if AXIS_KEYS_DEBUG:
                print(f"[AXIS {ANALOG_AXIS_KEYS}] {last_bucket} -> {bucket} (val={axis_keys_val:.3f})")

            if bucket > last_bucket:
                for i in range(last_bucket + 1, bucket + 1):
                    press_key(KEY_SEQUENCE[i])
            else:
                for i in range(last_bucket - 1, bucket - 1, -1):
                    press_key(KEY_SEQUENCE[i])

            current_idx = bucket  # mantém o índice global alinhado
            last_bucket = bucket

        clock.tick(120)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nEncerrado pelo usuário.")
