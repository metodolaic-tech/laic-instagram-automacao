"""
Kids Animation Studio AI - Construtor de cenas 3D (roda DENTRO do Blender).

Este script e executado de duas formas:
  1) Blender instalado:   blender -b -P scene_builder.py -- cena.json
  2) Modulo bpy (pip):    python scene_builder.py cena.json

Ele le um arquivo JSON com a descricao da cena (cenario, personagens, acoes,
camera, falas para sincronia labial) e:
  - monta o cenario 3D procedural (chao, arvores, pedras, flores, nuvens, ceu);
  - constroi cada personagem original a partir da ficha (cores, proporcoes,
    especie) com uma hierarquia de articulacoes (quadril, cabeca, bracos,
    pernas, cauda, olhos, sobrancelhas, boca);
  - anima com keyframes reais (andar, pular, acenar, comemorar, entregar
    objetos, piscar, respirar, expressoes e movimento da boca sincronizado
    com o volume da fala);
  - posiciona camera cinematografica (plano geral/medio/close, travelling,
    panoramica, grua) com profundidade de campo;
  - renderiza os quadros PNG com Cycles (CPU) ou EEVEE (se houver GPU).

Nao ha imagens estaticas "animadas": tudo e geometria 3D com movimento real.
"""
import json
import math
import os
import random
import sys

import bpy
from mathutils import Vector

# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

FPS = 24


def hex_rgba(h, alpha=1.0):
    h = h.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))

    # converte sRGB -> linear (o Blender trabalha em linear)
    def lin(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    return (lin(r), lin(g), lin(b), alpha)


def frame_of(t):
    return int(round(t * FPS)) + 1


_MATS = {}


def material(name, color, rough=0.55, sheen=0.0, emission=0.0, coat=0.0, metallic=0.0):
    key = (name, color, rough, sheen, emission, coat)
    if key in _MATS:
        return _MATS[key]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    rgba = hex_rgba(color)
    bsdf.inputs["Base Color"].default_value = rgba
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metallic
    if sheen and "Sheen Weight" in bsdf.inputs:
        bsdf.inputs["Sheen Weight"].default_value = sheen
    if coat and "Coat Weight" in bsdf.inputs:
        bsdf.inputs["Coat Weight"].default_value = coat
    if emission:
        bsdf.inputs["Emission Color"].default_value = rgba
        bsdf.inputs["Emission Strength"].default_value = emission
    _MATS[key] = m
    return m


def empty(name, parent=None, loc=(0, 0, 0)):
    o = bpy.data.objects.new(name, None)
    o.empty_display_size = 0.05
    bpy.context.scene.collection.objects.link(o)
    o.parent = parent
    o.location = loc
    return o


def sphere(name, parent, loc, scale, mat, segs=32, rings=16, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segs, ring_count=rings, radius=1.0)
    o = bpy.context.active_object
    o.name = name
    bpy.ops.object.shade_smooth()
    o.parent = parent
    o.location = loc
    o.scale = scale
    o.rotation_euler = rot
    o.data.materials.append(mat)
    return o


def cylinder(name, parent, loc, radius, depth, mat, rot=(0, 0, 0), verts=24):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=radius, depth=depth)
    o = bpy.context.active_object
    o.name = name
    bpy.ops.object.shade_smooth()
    o.parent = parent
    o.location = loc
    o.rotation_euler = rot
    o.data.materials.append(mat)
    return o


def cone(name, parent, loc, r1, depth, mat, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=r1, radius2=0.0, depth=depth)
    o = bpy.context.active_object
    o.name = name
    bpy.ops.object.shade_smooth()
    o.parent = parent
    o.location = loc
    o.rotation_euler = rot
    o.data.materials.append(mat)
    return o


def torus(name, parent, loc, major, minor, mat, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor,
                                     major_segments=32, minor_segments=12)
    o = bpy.context.active_object
    o.name = name
    bpy.ops.object.shade_smooth()
    o.parent = parent
    o.location = loc
    o.rotation_euler = rot
    o.data.materials.append(mat)
    return o


def key(obj, path, frame, value, index=-1):
    setattr_path = path
    cur = getattr(obj, setattr_path)
    if index >= 0:
        cur[index] = value
    else:
        setattr(obj, setattr_path, value)
    obj.keyframe_insert(data_path=path, frame=frame, index=index)


# ---------------------------------------------------------------------------
# Personagens
# ---------------------------------------------------------------------------

class Character:
    """Personagem procedural com hierarquia de articulacoes (rig por pivots)."""

    def __init__(self, sheet, start=(0, 0), facing=0.0):
        self.sheet = sheet
        self.id = sheet["id"]
        c = sheet["cores"]
        p = sheet.get("proporcoes", {})
        s = float(p.get("altura", 1.0))
        self.s = s
        hs = float(p.get("cabeca", 1.0))
        ey = float(p.get("olhos", 1.0))
        self.ear_type = sheet.get("orelhas", "redondas")
        self.extra = sheet.get("extras", [])
        self.tail_type = sheet.get("cauda", "curta")

        fur = material(f"{self.id}_pelo", c["pelo"], rough=0.6, sheen=0.4)
        belly = material(f"{self.id}_barriga", c.get("barriga", c["pelo"]), rough=0.65, sheen=0.4)
        dark = material(f"{self.id}_escuro", c.get("nariz", "#3a2a25"), rough=0.3)
        white = material("olho_branco", "#FFFFFF", rough=0.08, coat=0.6)
        iris = material(f"{self.id}_iris", c.get("olhos", "#5B3A1A"), rough=0.1, coat=0.8)
        pupil = material("pupila", "#0A0A0A", rough=0.05, coat=1.0)
        shine = material("brilho_olho", "#FFFFFF", rough=0.0, emission=4.0)
        mouthm = material("boca", "#5A1E1E", rough=0.5)
        blush = material(f"{self.id}_bochecha", c.get("bochecha", "#FF9AA2"), rough=0.7)
        extra_m = material(f"{self.id}_extra", c.get("juba", c.get("pelo")), rough=0.75, sheen=0.5)
        cloth = material(f"{self.id}_roupa", c.get("roupa", "#3B82F6"), rough=0.7, sheen=0.3)

        # ---------------- hierarquia ----------------
        self.root = empty(f"{self.id}_raiz", None, (start[0], start[1], 0))
        self.root.rotation_euler[2] = math.radians(facing)
        self.root.scale = (s, s, s)
        self.hips = empty(f"{self.id}_quadril", self.root, (0, 0, 0.30))
        self.body = sphere(f"{self.id}_corpo", self.hips, (0, 0, 0.17), (0.24, 0.21, 0.27), fur)
        sphere(f"{self.id}_barriga", self.hips, (0, -0.10, 0.13), (0.17, 0.12, 0.19), belly)

        # cabeca
        self.neck = empty(f"{self.id}_pescoco", self.hips, (0, 0, 0.38))
        self.head = sphere(f"{self.id}_cabeca", self.neck, (0, 0, 0.21 * hs), (0.27 * hs, 0.25 * hs, 0.25 * hs), fur)
        hz = 0.21 * hs  # centro da cabeca relativo ao pescoco
        R = 0.25 * hs

        # extras de especie
        if "juba" in self.extra:
            n = 14
            for i in range(n):
                a = 2 * math.pi * i / n
                sphere(f"{self.id}_juba{i}", self.neck,
                       (math.cos(a) * R * 1.05, 0.06, hz + math.sin(a) * R * 1.05),
                       (0.11 * hs, 0.09 * hs, 0.11 * hs), extra_m, segs=16, rings=8)
        if "la" in self.extra:
            for i in range(10):
                a = 2 * math.pi * i / 10
                sphere(f"{self.id}_la{i}", self.hips, (math.cos(a) * 0.2, math.sin(a) * 0.17, 0.2 + (i % 2) * 0.06),
                       (0.11, 0.11, 0.11), extra_m, segs=16, rings=8)
            for i in range(6):
                a = 2 * math.pi * i / 6
                sphere(f"{self.id}_topete{i}", self.neck, (math.cos(a) * 0.08, 0.02, hz + R * 0.85 + math.sin(a) * 0.04),
                       (0.07, 0.07, 0.07), extra_m, segs=16, rings=8)

        # orelhas
        self.ears = []
        for side in (-1, 1):
            if self.ear_type == "longas":  # coelho
                piv = empty(f"{self.id}_orelha_piv{side}", self.neck, (side * 0.09 * hs, 0.02, hz + R * 0.8))
                piv.rotation_euler = (0, math.radians(side * 12), 0)
                sphere(f"{self.id}_orelha{side}", piv, (0, 0, 0.2 * hs), (0.06 * hs, 0.035 * hs, 0.22 * hs), fur)
                sphere(f"{self.id}_orelha_int{side}", piv, (0, -0.02, 0.2 * hs), (0.035 * hs, 0.02 * hs, 0.17 * hs), blush)
            elif self.ear_type == "pontudas":  # raposa, gato
                piv = empty(f"{self.id}_orelha_piv{side}", self.neck, (side * 0.15 * hs, 0.0, hz + R * 0.75))
                piv.rotation_euler = (0, math.radians(side * 22), 0)
                cone(f"{self.id}_orelha{side}", piv, (0, 0, 0.08 * hs), 0.08 * hs, 0.2 * hs, fur)
                cone(f"{self.id}_orelha_int{side}", piv, (0, -0.025, 0.07 * hs), 0.05 * hs, 0.14 * hs, blush)
            elif self.ear_type == "grandes":  # elefante
                piv = empty(f"{self.id}_orelha_piv{side}", self.neck, (side * R * 0.95, 0.05, hz + 0.02))
                sphere(f"{self.id}_orelha{side}", piv, (side * 0.12 * hs, 0, 0), (0.17 * hs, 0.03 * hs, 0.2 * hs), fur)
                sphere(f"{self.id}_orelha_int{side}", piv, (side * 0.12 * hs, -0.02, 0), (0.12 * hs, 0.02 * hs, 0.15 * hs), blush)
            elif self.ear_type == "caidas":  # cachorro
                piv = empty(f"{self.id}_orelha_piv{side}", self.neck, (side * R * 0.85, 0.0, hz + R * 0.45))
                piv.rotation_euler = (0, math.radians(side * -25), 0)
                sphere(f"{self.id}_orelha{side}", piv, (side * 0.03, 0, -0.1 * hs), (0.07 * hs, 0.04 * hs, 0.15 * hs), extra_m)
            else:  # redondas (leao, urso, macaco)
                piv = empty(f"{self.id}_orelha_piv{side}", self.neck, (side * R * 0.72, 0.02, hz + R * 0.72))
                sphere(f"{self.id}_orelha{side}", piv, (0, 0, 0), (0.08 * hs, 0.05 * hs, 0.08 * hs), fur)
                sphere(f"{self.id}_orelha_int{side}", piv, (0, -0.03, 0), (0.05 * hs, 0.02 * hs, 0.05 * hs), belly)
            self.ears.append(piv)

        # rosto
        fy = -R * 0.86  # frente da cabeca
        sphere(f"{self.id}_focinho", self.neck, (0, fy - 0.01, hz - 0.07 * hs), (0.12 * hs, 0.08 * hs, 0.08 * hs), belly)
        if "tromba" in self.extra:
            prev = self.neck
            seg_parent = empty(f"{self.id}_tromba_piv", self.neck, (0, fy - 0.05, hz - 0.06 * hs))
            self.trunk = seg_parent
            for i in range(4):
                r = 0.055 * hs * (1 - i * 0.15)
                sphere(f"{self.id}_tromba{i}", seg_parent, (0, -0.02 * i, -0.06 * i * hs), (r, r, r * 1.3), fur)
        else:
            self.trunk = None
            sphere(f"{self.id}_nariz", self.neck, (0, fy - 0.08 * hs, hz - 0.03 * hs), (0.045 * hs, 0.03 * hs, 0.032 * hs), dark)
        self.mouth = sphere(f"{self.id}_boca", self.neck, (0, fy - 0.05 * hs, hz - 0.125 * hs),
                            (0.045 * hs, 0.02 * hs, 0.012 * hs), mouthm)
        for side in (-1, 1):
            sphere(f"{self.id}_bochecha{side}", self.neck, (side * 0.15 * hs, fy + 0.03, hz - 0.06 * hs),
                   (0.045 * hs, 0.015 * hs, 0.03 * hs), blush, segs=16, rings=8)

        # olhos (pivot proprio para piscar e expressoes)
        self.eyes = []
        self.brows = []
        es = 0.075 * hs * ey
        for side in (-1, 1):
            piv = empty(f"{self.id}_olho_piv{side}", self.neck, (side * 0.10 * hs, fy + 0.035, hz + 0.045 * hs))
            sphere(f"{self.id}_olho{side}", piv, (0, 0, 0), (es, es * 0.55, es * 1.2), white)
            sphere(f"{self.id}_iris{side}", piv, (0, -es * 0.42, -es * 0.1), (es * 0.62, es * 0.25, es * 0.75), iris)
            sphere(f"{self.id}_pupila{side}", piv, (0, -es * 0.6, -es * 0.1), (es * 0.36, es * 0.12, es * 0.44), pupil)
            sphere(f"{self.id}_brilho{side}", piv, (side * -es * 0.2, -es * 0.72, es * 0.25),
                   (es * 0.16, es * 0.08, es * 0.16), shine, segs=12, rings=6)
            self.eyes.append(piv)
            bpiv = empty(f"{self.id}_sobr_piv{side}", self.neck, (side * 0.10 * hs, fy + 0.045, hz + 0.15 * hs))
            sphere(f"{self.id}_sobr{side}", bpiv, (0, 0, 0), (0.05 * hs, 0.015, 0.014), extra_m if "juba" in self.extra else dark,
                   segs=16, rings=8)
            self.brows.append(bpiv)

        # acessorio
        acc = sheet.get("acessorio", "")
        if acc == "lenco":
            torus(f"{self.id}_lenco", self.hips, (0, 0, 0.37), 0.15, 0.04, cloth)
            cone(f"{self.id}_lenco_ponta", self.hips, (0, -0.15, 0.31), 0.06, 0.12, cloth, rot=(math.radians(180), 0, 0))
        elif acc == "laco":
            for side in (-1, 1):
                sphere(f"{self.id}_laco{side}", self.neck, (side * 0.07, 0.0, hz + R * 1.0), (0.06, 0.03, 0.045), cloth)
            sphere(f"{self.id}_laco_c", self.neck, (0, 0.0, hz + R * 1.0), (0.03, 0.03, 0.03), cloth)
        elif acc == "chapeu":
            cylinder(f"{self.id}_chapeu_aba", self.neck, (0, 0, hz + R * 0.9), 0.2 * hs, 0.02, cloth)
            cylinder(f"{self.id}_chapeu_topo", self.neck, (0, 0, hz + R * 0.9 + 0.08), 0.12 * hs, 0.16, cloth)
        elif acc == "mochila":
            sphere(f"{self.id}_mochila", self.hips, (0, 0.2, 0.2), (0.15, 0.08, 0.17), cloth)

        # bracos
        self.arms = []
        for side in (-1, 1):
            piv = empty(f"{self.id}_ombro{side}", self.hips, (side * 0.21, 0, 0.31))
            piv.rotation_euler = (0, math.radians(-side * 12), 0)
            sphere(f"{self.id}_braco{side}", piv, (0, 0, -0.11), (0.06, 0.06, 0.13), fur)
            sphere(f"{self.id}_mao{side}", piv, (0, 0, -0.22), (0.065, 0.065, 0.06), belly)
            self.arms.append(piv)

        # pernas
        self.legs = []
        for side in (-1, 1):
            piv = empty(f"{self.id}_coxa{side}", self.hips, (side * 0.11, 0, 0.04))
            sphere(f"{self.id}_perna{side}", piv, (0, 0, -0.12), (0.075, 0.075, 0.14), fur)
            sphere(f"{self.id}_pe{side}", piv, (0, -0.04, -0.27), (0.085, 0.11, 0.045), belly)
            self.legs.append(piv)

        # cauda
        self.tail = empty(f"{self.id}_cauda_piv", self.hips, (0, 0.2, 0.08))
        t = self.tail_type
        if t in ("tufo", "fina"):
            for i in range(5):
                sphere(f"{self.id}_cauda{i}", self.tail, (0, 0.06 * i, 0.04 * i * i * 0.4), (0.03, 0.03, 0.03), fur,
                       segs=12, rings=6)
            if t == "tufo":
                sphere(f"{self.id}_cauda_tufo", self.tail, (0, 0.3, 0.42), (0.07, 0.07, 0.08), extra_m)
        elif t == "fofa":
            sphere(f"{self.id}_cauda", self.tail, (0, 0.03, 0.02), (0.09, 0.09, 0.09), belly)
        elif t == "longa":
            sphere(f"{self.id}_cauda", self.tail, (0, 0.15, 0.12), (0.09, 0.2, 0.09), fur, rot=(math.radians(-35), 0, 0))
            sphere(f"{self.id}_cauda_ponta", self.tail, (0, 0.3, 0.24), (0.07, 0.08, 0.07), belly)
        else:
            sphere(f"{self.id}_cauda", self.tail, (0, 0.02, 0.0), (0.05, 0.06, 0.05), fur)

        # estado para animacao
        self.pos = Vector((start[0], start[1], 0))
        self.facing = facing

    # ------------------------------------------------------------------
    # Movimentos
    # ------------------------------------------------------------------
    def idle(self, t0, t1, seed=0):
        """Respiracao, balanco da cabeca, cauda e piscadas (vida constante)."""
        rnd = random.Random(seed)
        f0, f1 = frame_of(t0), frame_of(t1)
        step = 6
        ph = rnd.random() * 6.28
        for f in range(f0, f1 + 1, step):
            t = (f - 1) / FPS
            b = 1.0 + 0.025 * math.sin(2 * math.pi * t / 2.4 + ph)
            key(self.body, "scale", f, (0.24, 0.21, 0.27 * b))
            key(self.tail, "rotation_euler", f, (0, 0, math.radians(18 * math.sin(2 * math.pi * t / 1.6 + ph))))
            for i, e in enumerate(self.ears):
                key(e, "rotation_euler", f, (math.radians(4 * math.sin(2 * math.pi * t / 2.0 + i)), e.rotation_euler[1], 0))
        # piscadas
        t = t0 + rnd.uniform(0.5, 1.5)
        for e in self.eyes:
            key(e, "scale", f0, (1, 1, 1))
        while t < t1 - 0.3:
            fb = frame_of(t)
            for e in self.eyes:
                key(e, "scale", fb - 1, (1, 1, 1))
                key(e, "scale", fb + 1, (1, 1, 0.08))
                key(e, "scale", fb + 3, (1, 1, 1))
            t += rnd.uniform(2.2, 4.0)

    def head_sway(self, t0, t1, amount=6, seed=0):
        rnd = random.Random(seed + 7)
        f0, f1 = frame_of(t0), frame_of(t1)
        ph = rnd.random() * 6.28
        for f in range(f0, f1 + 1, 8):
            t = (f - 1) / FPS
            key(self.neck, "rotation_euler", f, (
                math.radians(2 * math.sin(2 * math.pi * t / 3.1 + ph)),
                math.radians(amount * math.sin(2 * math.pi * t / 2.7 + ph)),
                math.radians(4 * math.sin(2 * math.pi * t / 4.3 + ph))))

    def walk(self, t0, t1, to):
        f0, f1 = frame_of(t0), frame_of(t1)
        start = self.pos.copy()
        end = Vector((to[0], to[1], 0))
        d = end - start
        heading = math.degrees(math.atan2(d.x, -d.y))  # frente do personagem = -Y
        turn = min(0.25, (t1 - t0) * 0.2)
        key(self.root, "rotation_euler", f0, (0, 0, math.radians(self.facing)))
        key(self.root, "rotation_euler", frame_of(t0 + turn), (0, 0, math.radians(heading)))
        key(self.root, "location", f0, start)
        key(self.root, "location", f1, end)
        key(self.root, "rotation_euler", f1, (0, 0, math.radians(heading)))
        key(self.root, "rotation_euler", frame_of(t1 + turn), (0, 0, math.radians(self.facing)))
        # ciclo de passos
        freq = 2.4
        for f in range(f0, f1 + 1, 2):
            t = (f - f0) / FPS
            a = math.sin(2 * math.pi * freq * t)
            for i, leg in enumerate(self.legs):
                sgn = 1 if i == 0 else -1
                key(leg, "rotation_euler", f, (math.radians(28 * a * sgn), 0, 0))
            for i, arm in enumerate(self.arms):
                sgn = -1 if i == 0 else 1
                key(arm, "rotation_euler", f, (math.radians(25 * a * sgn), math.radians((1 if i == 0 else -1) * 12), 0))
            key(self.hips, "location", f, (0, 0, 0.30 + 0.035 * abs(math.cos(2 * math.pi * freq * t))))
        for leg in self.legs:
            key(leg, "rotation_euler", f1 + 2, (0, 0, 0))
        for i, arm in enumerate(self.arms):
            key(arm, "rotation_euler", f1 + 2, (0, math.radians((1 if i == 0 else -1) * 12), 0))
        key(self.hips, "location", f1 + 2, (0, 0, 0.30))
        self.pos = end

    def jump(self, t0, height=0.45):
        f = frame_of(t0)
        p = self.pos
        key(self.hips, "scale", f, (1, 1, 1))
        key(self.hips, "scale", f + 4, (1.12, 1.12, 0.82))  # agacha (squash)
        key(self.hips, "scale", f + 7, (0.92, 0.92, 1.12))  # estica (stretch)
        key(self.root, "location", f + 4, p)
        key(self.root, "location", f + 12, (p.x, p.y, height))
        key(self.root, "location", f + 20, p)
        key(self.hips, "scale", f + 13, (1, 1, 1))
        key(self.hips, "scale", f + 20, (1.1, 1.1, 0.85))
        key(self.hips, "scale", f + 25, (1, 1, 1))
        for i, arm in enumerate(self.arms):
            side = -1 if i == 0 else 1
            key(arm, "rotation_euler", f + 4, (0, math.radians(-side * 12), 0))
            key(arm, "rotation_euler", f + 10, (0, math.radians(-side * 130), 0))
            key(arm, "rotation_euler", f + 22, (0, math.radians(-side * 12), 0))

    def celebrate(self, t0, t1):
        t = t0
        while t < t1 - 0.8:
            self.jump(t, height=0.3)
            t += 1.05

    def wave(self, t0, t1, side=1):
        arm = self.arms[1 if side > 0 else 0]
        sgn = -1 if side > 0 else 1  # rotacao Y positiva leva o braco para dentro
        f0, f1 = frame_of(t0), frame_of(t1)
        base = (0, math.radians(sgn * 12), 0)
        key(arm, "rotation_euler", f0, base)
        f = f0 + 6
        i = 0
        while f < f1 - 6:
            ang = 120 + (20 if i % 2 == 0 else -20)
            key(arm, "rotation_euler", f, (0, math.radians(sgn * ang), 0))
            f += 6
            i += 1
        key(arm, "rotation_euler", f1, base)

    def reach(self, t0, t1, side=1):
        """Estende o braco para frente (entregar / oferecer algo)."""
        arm = self.arms[1 if side > 0 else 0]
        sgn = -1 if side > 0 else 1
        f0, f1 = frame_of(t0), frame_of(t1)
        base = (0, math.radians(sgn * 12), 0)
        key(arm, "rotation_euler", f0, base)
        key(arm, "rotation_euler", f0 + 8, (math.radians(-75), math.radians(sgn * 5), 0))
        key(arm, "rotation_euler", f1 - 6, (math.radians(-75), math.radians(sgn * 5), 0))
        key(arm, "rotation_euler", f1, base)

    def hold(self, t0, t1):
        """Segura algo contra o peito com os dois bracos (ex.: nao quer dividir)."""
        f0, f1 = frame_of(t0), frame_of(t1)
        for i, arm in enumerate(self.arms):
            sgn = 1 if i == 0 else -1  # +: para fora no braco esquerdo
            key(arm, "rotation_euler", f0, (0, math.radians(sgn * 12), 0))
            key(arm, "rotation_euler", f0 + 8, (math.radians(-60), math.radians(-sgn * 35), 0))
            key(arm, "rotation_euler", f1 - 6, (math.radians(-60), math.radians(-sgn * 35), 0))
            key(arm, "rotation_euler", f1, (0, math.radians(sgn * 12), 0))

    def turn_to(self, t, angle, dur=0.3):
        key(self.root, "rotation_euler", frame_of(t), (0, 0, math.radians(self.facing)))
        key(self.root, "rotation_euler", frame_of(t + dur), (0, 0, math.radians(angle)))
        self.facing = angle

    def nod(self, t0):
        f = frame_of(t0)
        for k, a in enumerate((0, 14, -4, 12, 0)):
            key(self.neck, "rotation_euler", f + k * 4, (math.radians(a), 0, 0))

    def expression(self, t, expr, dur=0.25):
        """Expressoes faciais: feliz, triste, surpreso, bravo, neutro, pensativo."""
        f = frame_of(t)
        fe = f + int(dur * FPS)
        cfg = {
            "neutro": dict(brow_z=0.0, brow_rot=0, eye=1.0, mouth=(1.0, 1.0)),
            "feliz": dict(brow_z=0.015, brow_rot=0, eye=0.88, mouth=(1.35, 1.6)),
            "triste": dict(brow_z=0.005, brow_rot=-18, eye=0.9, mouth=(0.8, 0.8)),
            "surpreso": dict(brow_z=0.035, brow_rot=0, eye=1.18, mouth=(0.75, 3.2)),
            "bravo": dict(brow_z=-0.012, brow_rot=20, eye=0.85, mouth=(0.9, 0.9)),
            "pensativo": dict(brow_z=0.01, brow_rot=-8, eye=0.95, mouth=(0.7, 0.9)),
        }.get(expr, None)
        if cfg is None:
            return
        for i, b in enumerate(self.brows):
            side = -1 if i == 0 else 1
            base_z = b.location.z
            key(b, "location", f, b.location.copy())
            key(b, "rotation_euler", f, b.rotation_euler.copy())
            b.location.z = self._brow_base(i) + cfg["brow_z"]
            key(b, "location", fe, b.location.copy())
            key(b, "rotation_euler", fe, (0, math.radians(side * cfg["brow_rot"]), 0))
        self._mouth_shape = cfg["mouth"]
        self._eye_open = cfg["eye"]
        if expr == "triste":
            key(self.neck, "rotation_euler", fe, (math.radians(-12), 0, 0))
        hs = float(self.sheet.get("proporcoes", {}).get("cabeca", 1.0))
        mx, mz = cfg["mouth"]
        key(self.mouth, "scale", f, self.mouth.scale.copy())
        key(self.mouth, "scale", fe, (0.045 * hs * mx, 0.02 * hs, 0.012 * hs * mz))

    def _brow_base(self, i):
        if not hasattr(self, "_brow_bases"):
            self._brow_bases = [b.location.z for b in self.brows]
        return self._brow_bases[i]

    def talk(self, t0, env, fps_env):
        """Sincronia labial: abre a boca conforme o volume da fala (envelope)."""
        hs = float(self.sheet.get("proporcoes", {}).get("cabeca", 1.0))
        mx, mz = getattr(self, "_mouth_shape", (1.0, 1.0))
        base_z = 0.012 * hs * mz
        f0 = frame_of(t0)
        step = max(1, int(round(FPS / fps_env)))
        f = f0
        key(self.mouth, "scale", f0 - 1, (0.045 * hs * mx, 0.02 * hs, base_z))
        for v in env:
            v = max(0.0, min(1.0, v))
            key(self.mouth, "scale", f, (0.045 * hs * (mx * (1 - 0.25 * v)), 0.02 * hs, base_z + 0.05 * hs * v))
            f += step
        key(self.mouth, "scale", f + 1, (0.045 * hs * mx, 0.02 * hs, base_z))
        # cabeca acompanha levemente a fala
        for k, v in enumerate(env[::4]):
            ff = f0 + k * 4 * step
            key(self.neck, "rotation_euler", ff, (math.radians(3 * v), math.radians(2 * math.sin(k)), 0))

    def world_hand(self):
        return self.pos + Vector((0, -0.25 * self.s, 0.45 * self.s))


# ---------------------------------------------------------------------------
# Cenario
# ---------------------------------------------------------------------------

def build_world(sky_top, sky_horizon, strength=1.0):
    world = bpy.data.worlds.new("Ceu")
    bpy.context.scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    ramp.color_ramp.elements[0].position = 0.5  # horizonte
    ramp.color_ramp.elements[0].color = hex_rgba(sky_horizon)
    ramp.color_ramp.elements[1].position = 0.58
    ramp.color_ramp.elements[1].color = hex_rgba(sky_top)
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = strength
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])


def ground_material(c1, c2, name="chao"):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs["Roughness"].default_value = 0.9
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 0.35
    noise.inputs["Detail"].default_value = 4.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = hex_rgba(c1)
    ramp.color_ramp.elements[1].color = hex_rgba(c2)
    ramp.color_ramp.elements[0].position = 0.35
    ramp.color_ramp.elements[1].position = 0.7
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    return m


def build_set(setd, seed=1):
    rnd = random.Random(seed)
    build_world(setd["ceu_topo"], setd["ceu_horizonte"], setd.get("luz_ceu", 1.0))
    bpy.ops.mesh.primitive_plane_add(size=120)
    g = bpy.context.active_object
    g.name = "chao"
    g.data.materials.append(ground_material(setd["chao"][0], setd["chao"][1]))

    # colinas ao fundo
    hill_m = material("colina", setd.get("colinas", setd["chao"][1]), rough=0.95)
    for i in range(7):
        x = rnd.uniform(-40, 40)
        sphere(f"colina{i}", None, (x, rnd.uniform(28, 45), -2), (rnd.uniform(10, 18), rnd.uniform(6, 10), rnd.uniform(4, 8)),
               hill_m, segs=24, rings=12)

    def place(min_r=4.0, spread=22, back_bias=True):
        for _ in range(100):
            x = rnd.uniform(-spread, spread)
            y = rnd.uniform(-4, spread) if back_bias else rnd.uniform(-spread, spread)
            # zona de acao livre no centro
            if abs(x) < min_r and -6 < y < 4:
                continue
            return x, y
        return spread, spread

    for el in setd.get("elementos", []):
        tipo, n = el["tipo"], el.get("quantidade", 5)
        for i in range(n):
            x, y = place(min_r=el.get("raio_livre", 4.0), spread=el.get("espalhar", 22))
            sc = rnd.uniform(0.75, 1.3)
            add_element(tipo, f"{tipo}{i}", (x, y), sc, el, rnd)

    # nuvens
    cloud_m = material("nuvem", "#FFFFFF", rough=1.0, emission=0.4)
    for i in range(setd.get("nuvens", 6)):
        cx, cy, cz = rnd.uniform(-35, 35), rnd.uniform(35, 55), rnd.uniform(12, 20)
        for k in range(5):
            sphere(f"nuvem{i}_{k}", None, (cx + k * 1.6 - 3.2, cy, cz + rnd.uniform(-0.6, 0.8)),
                   (rnd.uniform(1.6, 2.6),) * 3, cloud_m, segs=16, rings=8)

    join_static()


def join_static():
    """Funde o cenario estatico em uma unica malha: renderiza bem mais rapido."""
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH" and o.parent is None and o.name != "chao"]
    if len(meshes) < 2:
        return
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.join()
    bpy.context.active_object.name = "cenario_estatico"


def add_element(tipo, name, pos, sc, el, rnd):
    x, y = pos
    c = el.get("cores", {})
    if tipo == "acacia":
        trunk = material("tronco", c.get("tronco", "#7A4E2D"), rough=0.9)
        leaf = material("copa_acacia", c.get("copa", "#5E8C31"), rough=0.8, sheen=0.3)
        cylinder(name + "_t", None, (x, y, 1.4 * sc), 0.18 * sc, 2.8 * sc, trunk)
        sphere(name + "_c", None, (x, y, 3.0 * sc), (2.2 * sc, 2.0 * sc, 0.55 * sc), leaf, segs=24, rings=10)
        sphere(name + "_c2", None, (x + 0.8 * sc, y, 3.3 * sc), (1.3 * sc, 1.2 * sc, 0.4 * sc), leaf, segs=24, rings=10)
    elif tipo == "arvore":
        trunk = material("tronco", c.get("tronco", "#6B4226"), rough=0.9)
        leaf = material("copa", c.get("copa", "#3FA34D"), rough=0.8, sheen=0.3)
        cylinder(name + "_t", None, (x, y, 1.0 * sc), 0.22 * sc, 2.0 * sc, trunk)
        for k in range(3):
            sphere(name + f"_c{k}", None, (x + rnd.uniform(-0.6, 0.6) * sc, y + rnd.uniform(-0.4, 0.4), (2.6 + k * 0.5) * sc),
                   (1.3 * sc,) * 3, leaf, segs=24, rings=12)
    elif tipo == "pinheiro":
        trunk = material("tronco", c.get("tronco", "#6B4226"), rough=0.9)
        leaf = material("pinheiro", c.get("copa", "#2E7D4F"), rough=0.8)
        cylinder(name + "_t", None, (x, y, 0.5 * sc), 0.18 * sc, 1.0 * sc, trunk)
        for k in range(3):
            cone(name + f"_c{k}", None, (x, y, (1.4 + k * 0.9) * sc), (1.3 - k * 0.3) * sc, 1.6 * sc, leaf)
    elif tipo == "pedra":
        m = material("pedra", c.get("cor", "#9A9A92"), rough=0.85)
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1.0)
        o = bpy.context.active_object
        o.name = name
        bpy.ops.object.shade_smooth()
        o.location = (x, y, 0.1)
        o.scale = (0.6 * sc, 0.5 * sc, 0.35 * sc)
        o.rotation_euler[2] = rnd.uniform(0, 6.28)
        o.data.materials.append(m)
    elif tipo == "arbusto":
        m = material("arbusto", c.get("cor", "#4CAF50"), rough=0.85, sheen=0.3)
        for k in range(3):
            sphere(name + f"_{k}", None, (x + k * 0.4 * sc - 0.4, y, 0.35 * sc), (0.55 * sc,) * 3, m, segs=16, rings=8)
    elif tipo == "flor":
        stem = material("caule", "#3E8E41", rough=0.8)
        cores = c.get("petalas", ["#FF6B9A", "#FFD23F", "#FFFFFF", "#B388FF"])
        pet = material("petala_" + cores[hash(name) % len(cores)], cores[hash(name) % len(cores)], rough=0.6, sheen=0.4)
        mid = material("miolo", "#FFC107", rough=0.6)
        cylinder(name + "_c", None, (x, y, 0.15), 0.015, 0.3, stem, verts=8)
        for k in range(5):
            a = 2 * math.pi * k / 5
            sphere(name + f"_p{k}", None, (x + math.cos(a) * 0.06, y + math.sin(a) * 0.06, 0.31), (0.05, 0.05, 0.02), pet,
                   segs=10, rings=6)
        sphere(name + "_m", None, (x, y, 0.32), (0.035, 0.035, 0.025), mid, segs=10, rings=6)
    elif tipo == "cogumelo":
        cap = material("chapeu_cog", c.get("cor", "#E53935"), rough=0.5)
        st = material("pe_cog", "#FFF3E0", rough=0.7)
        cylinder(name + "_p", None, (x, y, 0.12 * sc), 0.06 * sc, 0.24 * sc, st)
        sphere(name + "_c", None, (x, y, 0.25 * sc), (0.18 * sc, 0.18 * sc, 0.1 * sc), cap)
    elif tipo == "capim":
        m = material("capim", c.get("cor", "#C9A227"), rough=0.9)
        for k in range(5):
            cone(name + f"_{k}", None, (x + rnd.uniform(-0.3, 0.3), y + rnd.uniform(-0.3, 0.3), 0.25 * sc), 0.05,
                 0.5 * sc, m, rot=(rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3), 0))
    elif tipo == "casinha":
        wall = material("parede", c.get("parede", "#FFE0B2"), rough=0.8)
        roof = material("telhado", c.get("telhado", "#D84315"), rough=0.7)
        bpy.ops.mesh.primitive_cube_add(size=1)
        o = bpy.context.active_object
        o.name = name
        o.location = (x, y, 1.0 * sc)
        o.scale = (2.0 * sc, 1.6 * sc, 2.0 * sc)
        o.data.materials.append(wall)
        cone(name + "_t", None, (x, y, 2.6 * sc), 1.9 * sc, 1.4 * sc, roof, rot=(0, 0, math.radians(45)))


def build_prop(prop, rnd):
    tipo = prop["tipo"]
    x, y = prop.get("pos", (0, 0))
    z = prop.get("z", 0.0)
    root = empty("prop_" + prop["id"], None, (x, y, z))
    if tipo in ("frutas", "cesta"):
        basket = material("cesta", "#A1662F", rough=0.85)
        cylinder("cesta", root, (0, 0, 0.1), 0.2, 0.2, basket)
        cores = ["#E53935", "#FFB300", "#FB8C00", "#7CB342"]
        for k in range(6):
            a = 2 * math.pi * k / 6
            m = material("fruta" + str(k % 4), cores[k % 4], rough=0.35, coat=0.3)
            sphere(f"fruta{k}", root, (math.cos(a) * 0.1, math.sin(a) * 0.1, 0.25), (0.075,) * 3, m, segs=16, rings=8)
    elif tipo == "bola":
        m1 = material("bola_a", "#E53935", rough=0.3, coat=0.5)
        sphere("bola", root, (0, 0, 0.15), (0.15,) * 3, m1)
        m2 = material("bola_b", "#FFFFFF", rough=0.3)
        torus("bola_faixa", root, (0, 0, 0.15), 0.15, 0.025, m2, rot=(math.radians(90), 0, 0))
    elif tipo == "estrela":
        m = material("estrela", "#FFD54F", rough=0.2, emission=2.0)
        sphere("estrela", root, (0, 0, 0.6), (0.12,) * 3, m)
    elif tipo == "presente":
        m = material("presente", "#8E24AA", rough=0.5)
        r = material("fita", "#FFD54F", rough=0.4)
        bpy.ops.mesh.primitive_cube_add(size=0.3)
        o = bpy.context.active_object
        o.parent = root
        o.location = (0, 0, 0.15)
        o.data.materials.append(m)
        torus("fita", root, (0, 0, 0.3), 0.06, 0.02, r)
    else:  # brinquedo generico
        m = material("brinquedo", "#29B6F6", rough=0.4)
        sphere("brinquedo", root, (0, 0, 0.12), (0.12,) * 3, m)
    return root


# ---------------------------------------------------------------------------
# Camera e luz
# ---------------------------------------------------------------------------

def setup_lights(setd):
    sun_d = bpy.data.lights.new("Sol", type="SUN")
    sun_d.energy = setd.get("sol_forca", 3.5)
    sun_d.color = hex_rgba(setd.get("sol_cor", "#FFF1D6"))[:3]
    sun_d.angle = math.radians(8)  # sombras suaves
    sun = bpy.data.objects.new("Sol", sun_d)
    bpy.context.scene.collection.objects.link(sun)
    el = math.radians(setd.get("sol_elevacao", 50))
    az = math.radians(setd.get("sol_azimute", -35))
    sun.rotation_euler = (math.pi / 2 - el, 0, az)
    # luz de preenchimento (fill) suave do lado oposto
    fill_d = bpy.data.lights.new("Preenchimento", type="AREA")
    fill_d.energy = 300
    fill_d.size = 6
    fill_d.color = hex_rgba(setd.get("ceu_horizonte", "#DDEEFF"))[:3]
    fill = bpy.data.objects.new("Preenchimento", fill_d)
    bpy.context.scene.collection.objects.link(fill)
    fill.location = (4, -6, 4)
    fill.rotation_euler = (math.radians(55), 0, math.radians(35))
    # luz de recorte (rim) por tras para destacar os personagens
    rim_d = bpy.data.lights.new("Recorte", type="AREA")
    rim_d.energy = 250
    rim_d.size = 4
    rim = bpy.data.objects.new("Recorte", rim_d)
    bpy.context.scene.collection.objects.link(rim)
    rim.location = (-3, 5, 3.5)
    rim.rotation_euler = (math.radians(-60), 0, math.radians(-30))


SHOTS = {
    # distancia, altura da camera, lente(mm), altura do alvo, abertura (f-stop)
    "geral": (5.6, 1.4, 32, 0.6, 8.0),
    "medio": (3.8, 1.0, 40, 0.65, 4.0),
    "close": (2.0, 0.95, 55, 0.85, 2.4),
    "dois": (4.6, 1.1, 38, 0.6, 4.5),
}


def setup_camera(cam_spec, targets_fn, duration, aspect_vertical):
    shot = cam_spec.get("plano", "medio")
    move = cam_spec.get("movimento", "parado")
    dist, h, lens, th, fstop = SHOTS.get(shot, SHOTS["medio"])
    if aspect_vertical:
        dist *= 1.35
        lens *= 0.9
    cam_d = bpy.data.cameras.new("Camera")
    cam_d.lens = lens
    cam_d.dof.use_dof = True
    cam_d.dof.aperture_fstop = fstop
    cam = bpy.data.objects.new("Camera", cam_d)
    bpy.context.scene.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    target = empty("alvo_camera", None, (0, 0, th))
    cam_d.dof.focus_object = target
    con = cam.constraints.new("TRACK_TO")
    con.target = target
    con.track_axis = "TRACK_NEGATIVE_Z"
    con.up_axis = "UP_Y"

    f_end = frame_of(duration)
    # alvo segue o centro dos personagens
    for f in range(1, f_end + 1, 6):
        c = targets_fn((f - 1) / FPS)
        key(target, "location", f, (c.x, c.y, th + c.z))
    ang0 = math.radians(cam_spec.get("angulo", 0))

    def cam_at(d, ang, hh, center, side=0.0):
        return Vector((center.x + math.sin(ang) * d + side, center.y - math.cos(ang) * d, hh))

    c0 = targets_fn(0)
    c1 = targets_fn(duration)
    if move == "aproximar":
        a, b = cam_at(dist * 1.15, ang0, h * 1.1, c0), cam_at(dist * 0.85, ang0, h, c1)
    elif move == "afastar":
        a, b = cam_at(dist * 0.85, ang0, h, c0), cam_at(dist * 1.3, ang0, h * 1.15, c1)
    elif move == "panoramica":
        a, b = cam_at(dist, ang0 - math.radians(18), h, c0), cam_at(dist, ang0 + math.radians(18), h, c1)
    elif move == "lateral":
        a, b = cam_at(dist, ang0, h, c0, side=-1.2), cam_at(dist, ang0, h, c1, side=1.2)
    elif move == "grua":
        a, b = cam_at(dist * 1.1, ang0, h * 0.6, c0), cam_at(dist * 1.1, ang0, h * 2.2, c1)
    elif move == "seguir":
        a, b = cam_at(dist, ang0, h, c0), cam_at(dist, ang0, h, c1)
        for f in range(1, f_end + 1, 6):
            key(cam, "location", f, cam_at(dist, ang0, h, targets_fn((f - 1) / FPS)))
        return cam
    else:  # parado com leve respiracao de camera
        a, b = cam_at(dist * 1.02, ang0, h, c0), cam_at(dist * 0.97, ang0, h, c1)
    key(cam, "location", 1, a)
    key(cam, "location", f_end, b)
    return cam


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

def enable_gpu():
    """Tenta usar a placa de video (NVIDIA OptiX/CUDA, AMD HIP, Apple Metal). Sem GPU, usa CPU."""
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
    except Exception:
        return False
    for kind in ("OPTIX", "CUDA", "HIP", "ONEAPI", "METAL"):
        try:
            prefs.compute_device_type = kind
            prefs.get_devices()
            devs = [d for d in prefs.devices if d.type == kind]
            if devs:
                for d in prefs.devices:
                    d.use = d.type == kind
                print("KAS_GPU", kind, [d.name for d in devs])
                return True
        except Exception:
            continue
    return False


def setup_render(r, out_dir):
    sc = bpy.context.scene
    engine = r.get("motor", "CYCLES")
    sc.render.engine = "CYCLES" if engine == "CYCLES" else "BLENDER_EEVEE"
    if sc.render.engine == "CYCLES":
        sc.cycles.device = "GPU" if (r.get("gpu", True) and enable_gpu()) else "CPU"
        sc.cycles.samples = int(r.get("amostras", 16))
        sc.cycles.use_adaptive_sampling = True
        sc.cycles.use_denoising = True
        try:
            sc.cycles.denoiser = "OPENIMAGEDENOISE"
        except Exception:
            pass
        sc.cycles.max_bounces = 4
        sc.cycles.diffuse_bounces = 2
        sc.cycles.glossy_bounces = 2
        sc.cycles.transmission_bounces = 2
        sc.cycles.transparent_max_bounces = 4
        sc.cycles.caustics_reflective = False
        sc.cycles.caustics_refractive = False
        sc.render.use_persistent_data = True
    sc.render.resolution_x = int(r["largura"])
    sc.render.resolution_y = int(r["altura"])
    sc.render.resolution_percentage = 100
    sc.render.fps = FPS
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    sc.render.filepath = os.path.join(out_dir, "quadro_")
    try:
        sc.view_settings.view_transform = "AgX"
        sc.view_settings.look = r.get("look", "AgX - Punchy")
    except Exception:
        pass
    sc.render.threads_mode = "AUTO"


# ---------------------------------------------------------------------------
# Programa principal
# ---------------------------------------------------------------------------

def run(spec):
    global FPS
    FPS = int(spec["render"].get("fps", 24))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    rnd = random.Random(spec.get("semente", 1))
    duration = float(spec["duracao"])
    out_dir = spec["saida"]
    os.makedirs(out_dir, exist_ok=True)

    build_set(spec["cenario"], seed=spec.get("semente", 1))
    setup_lights(spec["cenario"])

    chars = {}
    for cs in spec["personagens"]:
        ch = Character(cs["ficha"], start=cs.get("inicio", (0, 0)), facing=cs.get("direcao", 0))
        chars[ch.id] = ch

    props = {}
    for p in spec.get("objetos", []):
        props[p["id"]] = build_prop(p, rnd)

    # posicoes ao longo do tempo (para camera e objetos) - pre-calculo simples
    paths = {cid: [(0.0, Vector((cs.get("inicio", (0, 0))[0], cs.get("inicio", (0, 0))[1], 0)))]
             for cid, cs in zip(chars.keys(), spec["personagens"])}

    # aplica acoes em ordem de tempo
    for cs in spec["personagens"]:
        ch = chars[cs["ficha"]["id"]]
        ch.idle(0, duration, seed=hash(ch.id) % 1000)
        acts = sorted(cs.get("acoes", []), key=lambda a: a["t0"])
        busy_head = [(a["t0"], a.get("t1", a["t0"] + 1)) for a in acts if a["tipo"] in ("acenar_cabeca",)]
        if not cs.get("falas"):
            ch.head_sway(0, duration, seed=hash(ch.id) % 1000)
        for a in acts:
            t0, t1 = a["t0"], a.get("t1", a["t0"] + 1.0)
            tp = a["tipo"]
            if tp == "andar":
                ch.walk(t0, t1, a["para"])
                paths[ch.id].append((t1, ch.pos.copy()))
            elif tp == "pular":
                ch.jump(t0)
            elif tp == "comemorar":
                ch.celebrate(t0, t1)
            elif tp == "acenar":
                ch.wave(t0, t1, side=a.get("lado", 1))
            elif tp == "oferecer":
                ch.reach(t0, t1, side=a.get("lado", 1))
            elif tp == "segurar":
                ch.hold(t0, t1)
            elif tp == "virar":
                ch.turn_to(t0, a["angulo"])
            elif tp == "acenar_cabeca":
                ch.nod(t0)
            elif tp == "expressao":
                ch.expression(t0, a["expressao"])
        for fala in cs.get("falas", []):
            ch.talk(fala["t0"], fala["envelope"], fala.get("env_fps", 12))

    def pos_at(cid, t):
        pts = paths[cid]
        prev = pts[0][1]
        for (tt, p) in pts:
            if t >= tt:
                prev = p
        # interpolacao com as caminhadas
        for a in next(cs for cs in spec["personagens"] if cs["ficha"]["id"] == cid).get("acoes", []):
            if a["tipo"] == "andar" and a["t0"] <= t <= a["t1"]:
                st = [p for (tt, p) in pts if tt <= a["t0"] + 1e-6][-1]
                en = Vector((a["para"][0], a["para"][1], 0))
                k = (t - a["t0"]) / max(1e-6, a["t1"] - a["t0"])
                return st.lerp(en, k)
        return prev

    # movimento de objetos entre personagens (ex.: entregar a cesta)
    for p in spec.get("objetos", []):
        obj = props[p["id"]]
        for mv in p.get("movimentos", []):
            t0, t1 = mv["t0"], mv["t1"]
            if "de" in mv:
                a = pos_at(mv["de"], t0) + Vector((0, -0.28, 0.42))
            else:
                a = obj.location.copy()
            b = pos_at(mv["para"], t1) + Vector((0, -0.28, 0.42)) if "para" in mv else Vector(mv["destino"])
            key(obj, "location", frame_of(t0), a)
            mid = a.lerp(b, 0.5) + Vector((0, 0, 0.25))
            key(obj, "location", frame_of((t0 + t1) / 2), mid)
            key(obj, "location", frame_of(t1), b)
            obj.location = b

    def center(t):
        pts = [pos_at(cid, t) for cid in chars]
        focus = spec["camera"].get("foco")
        if focus and focus in chars:
            pts = [pos_at(focus, t)]
        c = Vector((0, 0, 0))
        for p in pts:
            c += p
        return c / max(1, len(pts))

    setup_camera(spec["camera"], center, duration, spec["render"]["altura"] > spec["render"]["largura"])
    setup_render(spec["render"], out_dir)
    sc = bpy.context.scene
    sc.frame_start = 1
    sc.frame_end = frame_of(duration)

    if spec.get("salvar_blend"):
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out_dir, "cena.blend"))

    if spec.get("quadro_unico"):
        sc.frame_set(int(spec["quadro_unico"]))
        sc.render.filepath = os.path.join(out_dir, spec.get("nome_quadro", "quadro.png"))
        bpy.ops.render.render(write_still=True)
    else:
        first = spec.get("quadro_inicial", 1)
        sc.frame_start = first
        bpy.ops.render.render(animation=True)
    print("KAS_OK", out_dir)


if __name__ == "__main__":
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = argv[1:]
    with open(argv[0], encoding="utf-8") as fh:
        run(json.load(fh))
