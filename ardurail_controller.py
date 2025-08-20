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

# Escolha o joystick (0 se houver só um)
JOYSTICK_ID = 0

# Mapeamento dos BOTÕES do seu controle (ajuste os índices!)
# Use INSPECT para descobrir os números: ao apertar, ele imprime "bot X pressed"
BUTTON_NEXT = 0       # aumenta índice (→ próxima tecla da lista)
BUTTON_PREV = 1       # diminui índice (→ tecla anterior)
BUTTON_A     = 2      # tecla 'A'
BUTTON_S     = 3      # tecla 'S'
BUTTON_SPACE = 4      # tecla Space
BUTTON_DEL   = 5      # tecla Delete
BUTTON_END   = 6      # tecla End
BUTTON_PGDN  = 7      # tecla PageDown

# Se seu controle tiver menos/mais botões, ajuste os índices acima.
# ==================================================

KEY_SEQUENCE = ['z', 'x', 'c', 'v', 'b', 'n', 'm']  # 0..6
MIN_IDX = 0
MAX_IDX = len(KEY_SEQUENCE) - 1

# teclas especiais do pynput
SPECIALS = {
    'space': Key.space,
    'delete': Key.delete,
    'end': Key.end,
    'pagedown': Key.page_down,
}

kb = Controller()

def press_key(k):
    """Pressiona e solta uma tecla (char ou Key.*)."""
    keyobj = k
    if isinstance(k, str) and len(k) == 1:
        keyobj = k  # caractere simples (ex.: 'a')
    elif isinstance(k, str):
        # se veio como string de especial, converte
        keyobj = SPECIALS.get(k.lower(), k)
    kb.press(keyobj)
    kb.release(keyobj)

def main():
    global INSPECT

    parser = argparse.ArgumentParser()
    parser.add_argument("--inspect", action="store_true", help="Modo de inspeção de botões.")
    args = parser.parse_args()
    if args.inspect:
        INSPECT = True

    pygame.init()
    pygame.joystick.init()

    if pygame.joystick.get_count() == 0:
        print("Nenhum joystick encontrado.")
        sys.exit(1)

    if JOYSTICK_ID >= pygame.joystick.get_count():
        print(f"Joystick {JOYSTICK_ID} não existe. Encontrados: {pygame.joystick.get_count()}")
        sys.exit(1)

    js = pygame.joystick.Joystick(JOYSTICK_ID)
    js.init()
    print(f"Usando joystick: {js.get_name()} (id={JOYSTICK_ID})")
    print(f"Botões detectados: {js.get_numbuttons()}")

    # estado anterior para detecção de borda de subida
    num_buttons = js.get_numbuttons()
    last_state = [0] * num_buttons

    current_idx = 0  # começa em 'z'
    print(f"Índice inicial: {current_idx} -> tecla '{KEY_SEQUENCE[current_idx]}'")

    # dispara uma vez a tecla inicial? normalmente não; comente/descomente:
    # press_key(KEY_SEQUENCE[current_idx])

    clock = pygame.time.Clock()

    while True:
        pygame.event.pump()  # atualiza estados

        # lê todos os botões
        for b in range(num_buttons):
            state = js.get_button(b)  # 1 = pressionado, 0 = solto

            # Modo inspeção: mostra quando qualquer botão é apertado/solto
            if INSPECT and state != last_state[b]:
                print(f"bot {b} {'pressed' if state else 'released'}")

            # detecta borda de subida
            if state == 1 and last_state[b] == 0:
                # mapeamentos:
                if b == BUTTON_NEXT:
                    if current_idx < MAX_IDX:
                        current_idx += 1
                        press_key(KEY_SEQUENCE[current_idx])
                        print(f"[NEXT] idx={current_idx} -> '{KEY_SEQUENCE[current_idx]}'")
                    else:
                        # já está no máximo -> opcionalmente repete a 'm' ou ignora
                        print("[NEXT] já no máximo (m)")

                elif b == BUTTON_PREV:
                    if current_idx > MIN_IDX:
                        current_idx -= 1
                        press_key(KEY_SEQUENCE[current_idx])
                        print(f"[PREV] idx={current_idx} -> '{KEY_SEQUENCE[current_idx]}'")
                    else:
                        print("[PREV] já no mínimo (z)")

                elif b == BUTTON_A:
                    press_key('a')
                    print("A")

                elif b == BUTTON_S:
                    press_key('s')
                    print("S")

                elif b == BUTTON_SPACE:
                    press_key('space')
                    print("SPACE")

                elif b == BUTTON_DEL:
                    press_key('delete')
                    print("DELETE")

                elif b == BUTTON_END:
                    press_key('end')
                    print("END")

                elif b == BUTTON_PGDN:
                    press_key('pagedown')
                    print("PAGEDOWN")

                # se quiser mapear mais botões, adicione elifs aqui

            last_state[b] = state

        clock.tick(120)  # limita a ~120 iterações/seg (debounce amigável)
        # time.sleep(0.001)  # opcional

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nEncerrado pelo usuário.")
