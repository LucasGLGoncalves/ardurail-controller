"""
Gamepad -> Teclado (Python)
- Índice 0..6 mapeado para ['z','x','c','v','b','n','m']
- Botão NEXT incrementa o índice (até 6), botão PREV decrementa (até 0)
- Outros botões: A, S, Espaço, Delete, End, PageDown
- Eixo analógico mapeado em 0..10 etapas:
  • Ao avançar etapas: seta PARA BAIXO (↓)
  • Ao recuar etapas:  seta PARA CIMA  (↑)

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

# ============ ANALÓGICO EM ETAPAS 0..10 ============
# Qual eixo usar (0, 1, 2, 3...). Teste com INSPECT ou prints.
ANALOG_AXIS = 1

# Número de etapas entre 0 e 10 (no seu caso 10)
# Observação: posições possíveis são 0..STEP_LEVELS (inclusive), ou seja, 11 posições.
STEP_LEVELS = 10

# Inverter o sentido do eixo (True se o "para baixo" sair invertido)
AXIS_INVERT = False

# Debug das mudanças de etapa (True para ver logs de passo a passo)
STEP_DEBUG = True
# ===================================================

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
    Ex.: levels=10 => etapas 0,1,2,...,10 (11 posições, 10 "saltos").
    """
    if invert:
        val = -val
    # Normaliza para [0..1]
    norm = (val + 1.0) / 2.0
    if norm < 0.0: norm = 0.0
    if norm > 1.0: norm = 1.0
    # Mapeia para etapa inteira [0..levels]; 1.0 cai em 'levels'
    step = int(norm * levels + 1e-9)
    if step < 0: step = 0
    if step > levels: step = levels
    return step

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

    # Estado do eixo em etapas
    try:
        axis_val = js.get_axis(ANALOG_AXIS)
    except Exception:
        axis_val = 0.0
    last_axis_step = axis_value_to_step(axis_val)

    if STEP_DEBUG:
        print(f"[AXIS {ANALOG_AXIS}] etapa inicial = {last_axis_step} (de 0..{STEP_LEVELS})")

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
                    # print(f"HOLD START [{b}] -> {key_to_type}")

                elif state == 1 and last_state[b] == 1:
                    info = hold_state.get(b)
                    if info and info.get("held") and now >= info.get("next_time", 0):
                        press_key(key_to_type)
                        info["next_time"] = now + REPEAT_INTERVAL

                elif state == 0 and last_state[b] == 1:
                    if b in hold_state:
                        hold_state.pop(b, None)
                        # print(f"HOLD END   [{b}]")
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

        # ======= Leitura e tradução do EIXO ANALÓGICO =======
        try:
            axis_val = js.get_axis(ANALOG_AXIS)  # valor em [-1.0..1.0]
        except Exception:
            axis_val = 0.0

        step = axis_value_to_step(axis_val)

        if step != last_axis_step:
            delta = step - last_axis_step
            if STEP_DEBUG:
                print(f"[AXIS {ANALOG_AXIS}] {last_axis_step} -> {step} (delta {delta}, val={axis_val:.3f})")

            if delta > 0:
                # Avançou etapas: pressiona ↓ delta vezes
                for _ in range(delta):
                    press_key('down')
            else:
                # Recuou etapas: pressiona ↑ -delta vezes
                for _ in range(-delta):
                    press_key('up')

            last_axis_step = step

        clock.tick(120)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nEncerrado pelo usuário.")
