# generic_controller.py
import argparse
import json
import time
from pathlib import Path
import pygame
from pynput.keyboard import Controller, Key

SPECIALS = {
    'space': Key.space,
    'delete': Key.delete,
    'end': Key.end,
    'pagedown': Key.page_down,
    'pageup': Key.page_up,
    'tab': Key.tab,
    'ctrl': Key.ctrl,
    'shift': Key.shift,
    'alt': Key.alt,
    'esc': Key.esc,
    'enter': Key.enter,
    'backspace': Key.backspace,
    'up': Key.up,
    'down': Key.down,
    'left': Key.left,
    'right': Key.right,
}


kb = Controller()

def resolve_key(k):
    if isinstance(k, str) and len(k) == 1:
        return k
    if isinstance(k, str):
        return SPECIALS.get(k.lower(), k)
    return k

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", required=True, help="Nome do perfil salvo no profiles.json")
    args = ap.parse_args()

    data = json.loads(Path("profiles.json").read_text(encoding="utf-8"))
    if args.profile not in data:
        print(f"Perfil '{args.profile}' não encontrado.")
        return
    cfg = data[args.profile]

    joystick_id = cfg.get("joystick_id", 0)
    press_hold_seconds = float(cfg.get("press_hold_seconds", 0.5))
    instant_keys = set(k.lower() for k in cfg.get("instant_keys", []))
    repeat_delay = float(cfg.get("repeat_delay", 0.35))
    repeat_interval = float(cfg.get("repeat_interval", 0.05))

    pygame.init()
    pygame.joystick.init()
    if pygame.joystick.get_count() == 0:
        print("Nenhum joystick encontrado.")
        return
    js = pygame.joystick.Joystick(joystick_id); js.init()
    print(f"Perfil: {args.profile} | Joystick: {js.get_name()}")

    # Estados
    num_buttons = js.get_numbuttons()
    last_button = [0]*num_buttons
    hold_state = {}        # botão -> {"held": bool, "next": t}
    active_holds = {}      # keyobj -> release_time

    axes_cfg = cfg.get("axes", {})
    axis_state = {}        # estados por eixo
    # sections:
    section_repeat = {}    # axis -> next_time
    section_bucket = {}    # axis -> last_bucket
    # steps:
    step_queue = {}        # axis -> {"pos": int, "neg": int, "next": float}

    def schedule_press(key_label, now, hold_s=None, force_instant=False):
        keyobj = resolve_key(key_label)
        kname = key_label.lower() if isinstance(key_label, str) else str(key_label)

        if force_instant or (kname in instant_keys):
            kb.press(keyobj); kb.release(keyobj)
            return

        end_time = now + (hold_s if hold_s is not None else press_hold_seconds)
        if keyobj in active_holds:
            active_holds[keyobj] = end_time
        else:
            kb.press(keyobj)
            active_holds[keyobj] = end_time

    def process_releases(now):
        to_rel = [k for k,t in active_holds.items() if now >= t]
        for k in to_rel:
            try: kb.release(k)
            except: pass
            active_holds.pop(k, None)

    def axis_to_step(val, steps, invert=False):
        if invert: val = -val
        norm = (val + 1.0)/2.0
        norm = max(0.0, min(1.0, norm))
        s = int(norm*steps + 1e-9)
        return max(0, min(steps, s))

    def axis_to_bucket(val, buckets, invert=False):
        if invert: val = -val
        norm = (val + 1.0)/2.0
        norm = max(0.0, min(1.0, norm))
        idx = int(norm*buckets - 1e-9)
        return max(0, min(buckets-1, idx))

    clock = pygame.time.Clock()

    while True:
        pygame.event.pump()
        now = time.time()

        # ---- Botões
        for b in range(num_buttons):
            s = js.get_button(b)
            if s == 1 and last_button[b] == 0:
                bmap = cfg.get("buttons", {}).get(str(b))
                if bmap:
                    key = bmap.get("key")
                    if bmap.get("mode","single") == "hold":
                        schedule_press(key, now)
                        hold_state[b] = {"held": True, "next": now + repeat_delay}
                    else:
                        schedule_press(key, now, force_instant=(key.lower() in instant_keys))
                last_button[b] = s
                continue

            if s == 1 and last_button[b] == 1:
                bmap = cfg.get("buttons", {}).get(str(b))
                if bmap and bmap.get("mode") == "hold":
                    info = hold_state.get(b)
                    if info and now >= info["next"]:
                        schedule_press(bmap["key"], now)
                        info["next"] = now + repeat_interval

            if s == 0 and last_button[b] == 1:
                if b in hold_state:
                    hold_state.pop(b, None)

            last_button[b] = s

        # ---- Eixos
        for a_str, ac in axes_cfg.items():
            a = int(a_str)
            try: val = js.get_axis(a)
            except: val = 0.0

            if ac["type"] == "steps_to_buttons":
                steps = int(ac.get("steps", 10))
                invert = bool(ac.get("invert", False))
                key_pos = ac.get("key_pos", "down")  # delta > 0
                key_neg = ac.get("key_neg", "up")    # delta < 0
                tap_hold = float(ac.get("tap_hold", 0.06))
                tap_interval = float(ac.get("tap_interval", 0.06))

                st = axis_state.setdefault(a, {"last_step": axis_to_step(val, steps, invert)})
                cur_step = axis_to_step(val, steps, invert)
                if cur_step != st["last_step"]:
                    delta = cur_step - st["last_step"]
                    q = step_queue.setdefault(a, {"pos":0, "neg":0, "next":now})
                    if delta > 0:
                        q["pos"] += delta
                    else:
                        q["neg"] += -delta
                    st["last_step"] = cur_step

                # dispara sequenciado por eixo
                q = step_queue.setdefault(a, {"pos":0, "neg":0, "next":now})
                if now >= q["next"]:
                    if q["pos"] > 0:
                        schedule_press(key_pos, now, hold_s=tap_hold)
                        q["pos"] -= 1
                        q["next"] = now + tap_interval
                    elif q["neg"] > 0:
                        schedule_press(key_neg, now, hold_s=tap_hold)
                        q["neg"] -= 1
                        q["next"] = now + tap_interval

            elif ac["type"] == "sections_to_keys":
                buckets = int(ac.get("buckets", len(ac.get("keys", [])) or 1))
                keys = list(ac.get("keys", []))
                if len(keys) != buckets:
                    # segurança: se o JSON tiver divergência, ajusta
                    if len(keys) < buckets:
                        keys += [""]*(buckets-len(keys))
                    else:
                        keys = keys[:buckets]
                invert = bool(ac.get("invert", False))
                repeat = bool(ac.get("repeat", False))
                repeat_interval = float(ac.get("repeat_interval", 0.5))

                cur_bucket = axis_to_bucket(val, buckets, invert)
                last_b = section_bucket.get(a, cur_bucket)

                if cur_bucket != last_b:
                    k = keys[cur_bucket]
                    if k:
                        schedule_press(k, now)
                    section_bucket[a] = cur_bucket
                    if repeat:
                        section_repeat[a] = now + repeat_interval

                elif repeat:
                    nxt = section_repeat.get(a, now + repeat_interval)
                    if now >= nxt:
                        k = keys[cur_bucket]
                        if k:
                            schedule_press(k, now)
                        section_repeat[a] = now + repeat_interval

        # soltar teclas cuja janela acabou
        process_releases(now)

        clock.tick(120)

if __name__ == "__main__":
    main()
