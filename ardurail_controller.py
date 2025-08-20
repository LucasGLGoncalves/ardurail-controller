"""
Gamepad -> Teclado (Python)
- Índice 0..6 mapeado para ['z','x','c','v','b','n','m']
- Botão NEXT incrementa o índice (até 6), botão PREV decrementa (até 0)
- Outros botões: A, S, Espaço, Delete, End, PageDown

Requisitos: pip install pygame pynput
"""

import time
import sys
import argparse
import pygame
from pynput.keyboard import Controller, Key

# ===================== CONFIG =====================

# Coloque True para descobrir os índices dos botões
INSPECT = False  # ou use: python script.py --inspect

# Config de repetição para "hold"
REPEAT_DELAY = 0.35      # atraso inicial antes de repetir (segundos)
REPEAT_INTERVAL = 0.05   # intervalo entre repetições (segundos)

# ===================== CONFIG =====================
JOYSTICK_ID = 0  # se só tiver um controle, deixe 0

# Teclas em sequência
KEY_SEQUENCE = ['z', 'x', 'c', 'v', 'b', 'n', 'm']
MIN_IDX = 0
MAX_IDX = len(KEY_SEQUENCE) - 1

# Botões do controle
BUTTON_A     = 17
BUTTON_S     = 18
BUTTON_DEL   = 19
BUTTON_PGDN  = 20
BUTTON_END   = 21
BUTTON_SPACE = 22
BUTTON_PREV  = 23  # decrementa índice
BUTTON_NEXT  = 24  # incrementa índice

# teclas especiais
SPECIALS = {
    'space': Key.space,
    'delete': Key.delete,
    'end': Key.end,
    'pagedown': Key.page_down,
}

# Botões que terão comportamento de HOLD (auto-repeat)
HOLD_BUTTONS = {
    BUTTON_A: 'a',
    BUTTON_S: 's',
    BUTTON_END: 'end',
}

# ==================================================

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

    num_buttons = js.get_numbuttons()
    last_state = [0] * num_buttons

    # Controle de repetição por botão de HOLD
    # Estrutura: hold_state[b] = {"held": bool, "next_time": float}
    hold_state = {}

    current_idx = 0
    print(f"Índice inicial: {current_idx} -> tecla '{KEY_SEQUENCE[current_idx]}'")

    clock = pygame.time.Clock()

    while True:
        pygame.event.pump()
        now = time.time()

        for b in range(num_buttons):
            state = js.get_button(b)

            # Botões com comportamento de HOLD
            if b in HOLD_BUTTONS:
                key_to_type = HOLD_BUTTONS[b]

                # Transição de subida: 0 -> 1 (primeira pressão)
                if state == 1 and last_state[b] == 0:
                    # Dispara a primeira tecla imediatamente
                    press_key(key_to_type)
                    # Agenda as próximas repetições
                    hold_state[b] = {"held": True, "next_time": now + REPEAT_DELAY}
                    print(f"HOLD START [{b}] -> {key_to_type}")

                # Mantido pressionado: 1 -> 1
                elif state == 1 and last_state[b] == 1:
                    info = hold_state.get(b)
                    if info and info.get("held") and now >= info.get("next_time", 0):
                        press_key(key_to_type)
                        # agenda próxima repetição
                        info["next_time"] = now + REPEAT_INTERVAL

                # Soltou: 1 -> 0
                elif state == 0 and last_state[b] == 1:
                    if b in hold_state:
                        hold_state[b]["held"] = False
                        hold_state.pop(b, None)
                        print(f"HOLD END   [{b}]")

                # Atualiza e segue para o próximo botão
                last_state[b] = state
                continue

            # Botões normais, apenas borda de subida
            if state == 1 and last_state[b] == 0:
                # Mapeamento de botões
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

        clock.tick(120)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nEncerrado pelo usuário.")
