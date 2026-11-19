#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Build docs/DISTILLATION_YOLOX.pdf, the illustrated guide of the
YoloxDistillation node.

    pip install reportlab
    python tools/make_distillation_pdf.py

The figures of the tables below were measured with the command-line tool
(node/DLNode/online_training/distill/cli.py); update them here when they are
measured again.
"""
import os

from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT = os.path.join(ROOT, "docs", "DISTILLATION_YOLOX.pdf")

NAVY = colors.HexColor("#1F3A5F")
BLUE = colors.HexColor("#2E86AB")
PALE = colors.HexColor("#E8F1F8")
GREEN = colors.HexColor("#3A9D5D")
ORANGE = colors.HexColor("#E08E45")
GREY = colors.HexColor("#B8BEC6")
LIGHT = colors.HexColor("#F4F6F8")
INK = colors.HexColor("#22262B")

# ---------------------------------------------------------------------- #
# Measured data

# name, input (width x height), pixels relative to yolox_nano, latency in ms
# (onnxruntime, CPU, 2 cores, network only), what it is for
STUDENTS = [
    ("yolox_nano_320x192", "320 x 192", "61 000", "6",
     "Machine très limitée, caméra 16:9, objets de taille moyenne ou grande."),
    ("yolox_nano_320", "320 x 320", "102 000", "10",
     "Petit student pour une image 4:3, carrée ou verticale."),
    ("yolox_nano_416x256", "416 x 256", "106 000", "10",
     "<b>Caméra 16:9 : le choix conseillé.</b> Même finesse que yolox_nano, sans calculer "
     "les bandes vides."),
    ("yolox_nano", "416 x 416", "173 000", "16",
     "Modèle d'origine, pour toute forme d'image. Sélectionné par défaut."),
    ("yolox_tiny_416x256", "416 x 256", "106 000", "29",
     "Caméra 16:9 quand la précision compte plus que la vitesse : réseau 5 fois plus gros."),
    ("yolox_tiny", "416 x 416", "173 000", "46",
     "Modèle d'origine, le plus précis des students."),
]

# video, samples, then per student: (AP50 before, after, F1 before, after)
RESULTS = [
    ("Allée de magasin, caméra fixe, personnes petites et lointaines (65 s, 590 échantillons)", [
        ("yolox_nano_320x192", 0.232, 0.314, 0.376, 0.476),
        ("yolox_nano_320", 0.233, 0.319, 0.377, 0.482),
        ("yolox_nano_416x256", 0.237, 0.514, 0.382, 0.652),
        ("yolox_nano", 0.237, 0.520, 0.383, 0.659),
        ("yolox_tiny_416x256", 0.523, 0.877, 0.642, 0.831),
    ]),
    ("Passage de personnes, caméra fixe, personnes proches (139 s, 879 échantillons)", [
        ("yolox_nano_320x192", 0.986, 0.991, 0.905, 0.991),
        ("yolox_nano_320", 0.985, 0.994, 0.710, 0.994),
        ("yolox_nano_416x256", 0.991, 0.994, 0.802, 0.993),
        ("yolox_tiny_416x256", 0.994, 0.994, 0.717, 0.993),
    ]),
    ("Personne filmée de près, clip court (36 s, 270 échantillons)", [
        ("yolox_nano_320x192", 0.508, 0.516, 0.604, 0.505),
        ("yolox_nano_416x256", 0.561, 0.574, 0.612, 0.588),
    ]),
    ("Caméra embarquée sur route (36 s, 270 échantillons)", [
        ("yolox_nano_416x256", 0.370, 0.440, 0.522, 0.562),
    ]),
]

# ---------------------------------------------------------------------- #
# Styles

BODY = ParagraphStyle("body", fontName="Helvetica", fontSize=10, leading=14.2,
                      textColor=INK, spaceAfter=6)
SMALL = ParagraphStyle("small", parent=BODY, fontSize=8.6, leading=11.4, spaceAfter=0)
CELL = ParagraphStyle("cell", parent=BODY, fontSize=8.8, leading=11.6, spaceAfter=0)
CELL_HEAD = ParagraphStyle("cell_head", parent=CELL, fontName="Helvetica-Bold",
                           textColor=colors.white)
CODE = ParagraphStyle("code", fontName="Courier", fontSize=8.4, leading=11.2,
                      textColor=INK, backColor=LIGHT, borderPadding=6,
                      leftIndent=6, rightIndent=6, spaceBefore=4, spaceAfter=12)
H1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=15, leading=19,
                    textColor=NAVY, spaceBefore=12, spaceAfter=7)
H2 = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=11.5, leading=15,
                    textColor=BLUE, spaceBefore=8, spaceAfter=4)
TITLE = ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=23, leading=28,
                       textColor=colors.white)
SUBTITLE = ParagraphStyle("subtitle", fontName="Helvetica", fontSize=11.5, leading=16,
                          textColor=colors.white)
CAPTION = ParagraphStyle("caption", parent=SMALL, alignment=TA_CENTER,
                         textColor=colors.HexColor("#5A6470"), spaceBefore=3, spaceAfter=10)
BULLET = ParagraphStyle("bullet", parent=BODY, leftIndent=14, bulletIndent=3, spaceAfter=3)

WIDTH = A4[0] - 4 * cm


def p(text, style=BODY):
    return Paragraph(text, style)


def bullets(items):
    return [Paragraph(item, BULLET, bulletText="\u2022") for item in items]


def code(text):
    return Paragraph(text.strip("\n").replace(" ", "&nbsp;").replace("\n", "<br/>"), CODE)


def table(rows, widths, head=True, zebra=True):
    data = [
        [Paragraph(str(cell), CELL_HEAD if head and r == 0 else CELL) for cell in row]
        for r, row in enumerate(rows)
    ]
    style = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, GREY),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]
    if head:
        style.append(("BACKGROUND", (0, 0), (-1, 0), NAVY))
    if zebra:
        for r in range(1 + (not head), len(rows), 2):
            style.append(("BACKGROUND", (0, r), (-1, r), LIGHT))
    result = Table(data, colWidths=[w * WIDTH for w in widths], repeatRows=1 if head else 0)
    result.setStyle(TableStyle(style))
    return result


# ---------------------------------------------------------------------- #
# Drawings


def box(d, x, y, w, h, lines, fill=PALE, stroke=BLUE, text=INK, bold=False, size=8.5):
    d.add(Rect(x, y, w, h, rx=5, ry=5, fillColor=fill, strokeColor=stroke, strokeWidth=1))
    font = "Helvetica-Bold" if bold else "Helvetica"
    top = y + h / 2 + (len(lines) - 1) * (size + 2) / 2 - size * 0.35
    for i, line in enumerate(lines):
        d.add(String(x + w / 2, top - i * (size + 2), line, fontName=font,
                     fontSize=size, fillColor=text, textAnchor="middle"))


def arrow(d, x1, y1, x2, y2, color=NAVY, dashed=False):
    d.add(Line(x1, y1, x2, y2, strokeColor=color, strokeWidth=1.3,
               strokeDashArray=[3, 2] if dashed else None))
    length = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5 or 1.0
    ux, uy = (x2 - x1) / length, (y2 - y1) / length
    size = 5.5
    d.add(Polygon(
        [x2, y2,
         x2 - size * ux - size * 0.55 * uy, y2 - size * uy + size * 0.55 * ux,
         x2 - size * ux + size * 0.55 * uy, y2 - size * uy - size * 0.55 * ux],
        fillColor=color, strokeColor=color,
    ))


def label(d, x, y, text, size=7.6, color=INK, anchor="middle", bold=False):
    d.add(String(x, y, text, fontName="Helvetica-Bold" if bold else "Helvetica",
                 fontSize=size, fillColor=color, textAnchor=anchor))


def pipeline_drawing():
    d = Drawing(WIDTH, 196)
    # Real-time path
    box(d, 0, 140, 92, 40, ["Images", "(caméra, vidéo)"], fill=LIGHT, stroke=GREY)
    box(d, 168, 134, 150, 52, ["STUDENT déployé", "petit YOLOX, onnxruntime", "détection en temps réel"],
        fill=GREEN, stroke=GREEN, text=colors.white, bold=True)
    box(d, 388, 140, 94, 40, ["Détections", "(image + JSON)"], fill=LIGHT, stroke=GREY)
    arrow(d, 92, 160, 166, 160)
    arrow(d, 318, 160, 386, 160)
    label(d, 129, 165, "chaque image")

    # Background path
    box(d, 0, 30, 92, 46, ["TEACHER", "gros YOLOX", "thread de fond"],
        fill=NAVY, stroke=NAVY, text=colors.white, bold=True)
    box(d, 122, 30, 92, 46, ["Stock", "image + prédictions", "du teacher (disque)"])
    box(d, 244, 30, 100, 46, ["Entraînement", "PyTorch, par cycles", "thread de fond"])
    box(d, 374, 30, 108, 46, ["Validation", "sur les images", "les plus récentes"],
        fill=ORANGE, stroke=ORANGE, text=colors.white, bold=True)
    arrow(d, 46, 139, 46, 78, dashed=True)
    label(d, 51, 106, "1 image toutes les 0,5 s", anchor="start")
    arrow(d, 92, 53, 120, 53)
    arrow(d, 214, 53, 242, 53)
    arrow(d, 344, 53, 372, 53)
    # Deployment
    d.add(Line(428, 76, 428, 104, strokeColor=GREEN, strokeWidth=1.6))
    d.add(Line(428, 104, 243, 104, strokeColor=GREEN, strokeWidth=1.6))
    arrow(d, 243, 104, 243, 132, color=GREEN)
    label(d, 336, 109, "nouveau student, seulement s'il est meilleur", color=GREEN, bold=True)
    label(d, 241, 10, "Le teacher et l'entraînement ne sont jamais dans le chemin temps réel.",
          size=8, color=colors.HexColor("#5A6470"))
    return d


def _grid(d, x, top, cols, rows, cell, color=GREY):
    for i in range(1, cols):
        d.add(Line(x + i * cell, top - rows * cell, x + i * cell, top,
                   strokeColor=color, strokeWidth=0.3))
    for j in range(1, rows):
        d.add(Line(x, top - j * cell, x + cols * cell, top - j * cell,
                   strokeColor=color, strokeWidth=0.3))


def dense_drawing():
    d = Drawing(WIDTH, 176)
    scale = 0.22
    cell = 32 * scale
    top = 160
    # Teacher input: 640 x 640, the 16:9 image fills its top 360 rows
    x0, side = 30, 640 * scale
    d.add(Rect(x0, top - side, side, side, fillColor=GREY, strokeColor=NAVY, strokeWidth=1.2))
    d.add(Rect(x0, top - 360 * scale, side, 360 * scale, fillColor=PALE, strokeColor=NAVY,
               strokeWidth=1.2))
    _grid(d, x0, top, 20, 11, cell, color=colors.HexColor("#9FB4C7"))
    label(d, x0 + side / 2, top - 360 * scale - 16, "TEACHER : l'image en 640 de large",
          color=NAVY, bold=True)
    label(d, x0 + side / 2, top - 360 * scale - 27, "grille fine, petits objets visibles")
    label(d, x0 + side / 2, top - side + 8, "(vide)")

    # Student input: 416 x 256, the same image 416 pixels wide
    x1 = 330
    sw, sh = 416 * scale, 256 * scale
    d.add(Rect(x1, top - sh, sw, sh, fillColor=GREY, strokeColor=GREEN, strokeWidth=1.4))
    d.add(Rect(x1, top - 234 * scale, sw, 234 * scale, fillColor=PALE, strokeColor=GREEN,
               strokeWidth=1.4))
    _grid(d, x1, top, 13, 7, cell, color=colors.HexColor("#9FB4C7"))
    label(d, x1 + sw / 2, top - sh - 12, "STUDENT : la même image en 416 de large",
          color=GREEN, bold=True)
    label(d, x1 + sw / 2, top - sh - 23, "grille plus grossière")
    # The teacher cells falling into one student cell
    d.add(Rect(x0 + 6 * cell, top - 5 * cell, 2 * cell, 2 * cell,
               fillColor=ORANGE, strokeColor=ORANGE))
    d.add(Rect(x1 + 4 * cell, top - 3 * cell, cell, cell, fillColor=ORANGE, strokeColor=ORANGE))
    arrow(d, x0 + 8 * cell + 3, top - 4 * cell, x1 + 4 * cell - 3, top - 2.5 * cell,
          color=ORANGE)
    middle = (x0 + side + x1) / 2
    label(d, middle, top - 2 * cell + 4, "même endroit de l'image", color=ORANGE, bold=True)
    label(d, x1 + sw / 2, top - sh - 48, "Dans chaque case, le student imite la case",
          bold=True)
    label(d, x1 + sw / 2, top - sh - 59, "la plus sûre du teacher au même endroit :", bold=True)
    label(d, x1 + sw / 2, top - sh - 71, "objectness, classes et boîte")
    return d


def sizes_drawing():
    d = Drawing(WIDTH, 150)
    scale = 0.27
    shapes = [
        ("yolox_nano  (416 x 416)", 416, 416, 234, "44 % de l'entrée est vide"),
        ("yolox_nano_416x256", 416, 256, 234, "9 % de vide"),
        ("yolox_nano_320x192", 320, 192, 180, "6 % de vide"),
    ]
    x = 8
    top = 136
    for name, w, h, used, note in shapes:
        d.add(Rect(x, top - h * scale, w * scale, h * scale, fillColor=GREY,
                   strokeColor=NAVY, strokeWidth=1))
        d.add(Rect(x, top - used * scale, w * scale, used * scale, fillColor=BLUE,
                   strokeColor=NAVY, strokeWidth=1))
        label(d, x + w * scale / 2, top - used * scale / 2 - 3, "image 16:9",
              color=colors.white, bold=True)
        label(d, x + w * scale / 2, top - h * scale - 11, name, bold=True, color=NAVY)
        label(d, x + w * scale / 2, top - h * scale - 21, note)
        x += w * scale + 52
    return d


def timeline_drawing():
    d = Drawing(WIDTH, 78)
    y, h = 34, 24
    d.add(Rect(0, y, 330, h, fillColor=BLUE, strokeColor=NAVY))
    d.add(Rect(330, y, 90, h, fillColor=ORANGE, strokeColor=NAVY))
    d.add(Rect(420, y, 62, h, fillColor=colors.white, strokeColor=GREY, strokeDashArray=[3, 2]))
    label(d, 165, y + 8, "échantillons d'entraînement (jusqu'à 4 000)", color=colors.white,
          bold=True, size=8.4)
    label(d, 375, y + 8, "validation : 96", color=colors.white, bold=True, size=8.4)
    label(d, 451, y + 8, "à venir", size=8.4)
    arrow(d, 0, 20, 482, 20, color=colors.HexColor("#5A6470"))
    label(d, 4, 8, "plus ancien", anchor="start")
    label(d, 478, 8, "temps", anchor="end")
    label(d, 375, y + h + 6, "jamais utilisés par le cycle en cours", color=ORANGE, bold=True)
    return d


# ---------------------------------------------------------------------- #
# Document


def first_page(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(NAVY)
    canvas.rect(0, A4[1] - 4.6 * cm, A4[0], 4.6 * cm, stroke=0, fill=1)
    canvas.setFillColor(BLUE)
    canvas.rect(0, A4[1] - 4.75 * cm, A4[0], 0.15 * cm, stroke=0, fill=1)
    canvas.restoreState()
    later_pages(canvas, doc)


def later_pages(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#5A6470"))
    canvas.drawString(2 * cm, 1.2 * cm, "CV Studio - nœud YoloxDistillation")
    canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"page {doc.page}")
    canvas.restoreState()


def results_table():
    def number(value, reference=None):
        text = f"{value:.3f}".replace(".", ",")
        return f"<b>{text}</b>" if reference is not None and value - reference >= 0.02 else text

    rows = [["Student", "AP50 avant", "AP50 après", "F1 avant", "F1 après"]]
    titles = []
    for video, runs in RESULTS:
        titles.append(len(rows))
        rows.append([f"<b>{video}</b>", "", "", "", ""])
        for student, ap0, ap1, f0, f1 in runs:
            rows.append([student, number(ap0), number(ap1, ap0), number(f0), number(f1, f0)])
    result = table(rows, [0.40, 0.15, 0.15, 0.15, 0.15], zebra=False)
    result.setStyle(TableStyle(
        [("SPAN", (0, r), (-1, r)) for r in titles]
        + [("BACKGROUND", (0, r), (-1, r), PALE) for r in titles]
    ))
    return result


def story():
    s = []
    s.append(Spacer(1, 0.1 * cm))
    s.append(p("Distillation YOLOX en direct", TITLE))
    s.append(p("Fonctionnement du nœud YoloxDistillation et choix du student", SUBTITLE))
    s.append(Spacer(1, 1.9 * cm))

    s.append(p("1. À quoi ça sert", H1))
    s.append(p(
        "Un gros détecteur est précis mais lent ; un petit est rapide mais se trompe plus. "
        "La distillation fait apprendre au petit modèle (le <b>student</b>) les réponses du "
        "gros (le <b>teacher</b>), <b>sur les images de votre caméra et sans aucune "
        "annotation</b>. Le student n'a pas besoin de savoir tout reconnaître partout : il "
        "lui suffit d'être bon sur la scène qu'il regarde."
    ))
    s.extend(bullets([
        "Le student détecte en temps réel pendant qu'il apprend ; le teacher travaille en "
        "arrière-plan et ne ralentit pas le pipeline.",
        "Un nouveau student ne remplace l'ancien que s'il est <b>mesuré meilleur</b> sur des "
        "images récentes qu'il n'a pas apprises.",
        "Le résultat est un fichier ONNX YOLOX ordinaire, exportable et utilisable ailleurs.",
        "Fonctionne avec ou sans GPU.",
    ]))

    s.append(p("2. Vue d'ensemble", H1))
    s.append(pipeline_drawing())
    s.append(p("Figure 1 - Trois activités indépendantes : détection, collecte, entraînement.",
               CAPTION))
    s.append(table([
        ["Activité", "Ce qui se passe", "Où"],
        ["Détection", "Le student déployé traite chaque image. Il n'attend jamais les deux "
                      "autres activités.", "pipeline"],
        ["Collecte", "Toutes les 0,5 s, une image est montrée au teacher. Elle est gardée "
                     "avec ses prédictions si la scène a changé ou si teacher et student ne "
                     "sont pas d'accord.", "thread de fond"],
        ["Entraînement", "Par cycles : entraîner le student sur le stock, le valider, le "
                         "déployer s'il est meilleur.", "thread de fond"],
    ], [0.17, 0.63, 0.20]))

    s.append(PageBreak())
    s.append(p("3. Ce que le student apprend", H1))
    s.append(p(
        "Un YOLOX découpe l'image en cases, sur trois grilles (cases de 8, 16 et 32 pixels). "
        "Pour chaque case il prédit une boîte, une probabilité « il y a un objet » "
        "(<i>objectness</i>) et une probabilité par classe. Teacher et student ont la même "
        "structure de sortie."
    ))
    s.append(p(
        "Le teacher regarde l'image <b>à une résolution plus élevée que le student</b> "
        "(jusqu'à 1,6 fois, dans la limite de son entrée) : il voit mieux les petits "
        "objets. Les deux grilles couvrent la même image ; chaque case du student recouvre "
        "une ou plusieurs cases du teacher, et la plus sûre d'entre elles parle pour la "
        "case. Le student imite ainsi le teacher <b>case par case</b>, sans tri ni "
        "appariement de boîtes : c'est la distillation <i>dense</i>."
    ))
    s.append(dense_drawing())
    s.append(p("Figure 2 - Teacher et student regardent la même image, chacun à sa "
               "résolution ; la comparaison se fait case par case.", CAPTION))
    s.append(table([
        ["Sortie", "Ce que le student imite", "Poids"],
        ["objectness", "La probabilité du teacher, sur <b>toutes</b> les cases : le student "
                       "apprend aussi ce qui est du fond, ce qui supprime ses fausses "
                       "détections.", "1"],
        ["classes", "Les probabilités du teacher, là où il voit un objet.", "1"],
        ["boîte", "La boîte du teacher de la même case (écart mesuré par 1 - GIoU), là où "
                  "il voit un objet.", "5"],
    ], [0.17, 0.71, 0.12]))
    s.append(Spacer(1, 6))
    s.append(p("Pourquoi c'est mieux que de recopier les boîtes du teacher", H2))
    s.extend(bullets([
        "Le student reçoit des <b>probabilités</b> (0,62 « personne », 0,08 « vélo »), pas "
        "une liste de boîtes déjà triées : les hésitations du teacher sont de l'information.",
        "Les cases où le student a déjà raison comptent très peu ; l'effort porte sur ses "
        "erreurs. Un student identique à son teacher n'est pas modifié.",
        "C'est le fichier ONNX déployé lui-même qui est entraîné, puis réécrit : le modèle "
        "en production est exactement celui qui a été validé.",
        "Seules les dernières couches sont entraînées (30 %) : c'est ce qui se généralise le "
        "mieux avec quelques centaines d'images.",
    ]))

    s.append(p("4. Le garde-fou : valider sur ce qui vient après", H1))
    s.append(p(
        "Les images d'une vidéo se ressemblent d'une seconde à l'autre : un student peut "
        "paraître meilleur simplement parce qu'il a retenu des images presque identiques. "
        "Les échantillons sont donc rangés dans l'ordre du temps, et les <b>96 plus récents</b> "
        "ne servent jamais à l'entraînement en cours."
    ))
    s.append(timeline_drawing())
    s.append(p("Figure 3 - La validation porte toujours sur des images postérieures à "
               "l'entraînement.", CAPTION))
    s.extend(bullets([
        "Le candidat est déployé si sa perte de validation baisse d'au moins 1 % <b>et</b> si "
        "son accord avec les détections du teacher (AP50) ne baisse pas.",
        "Sinon rien ne change en production. Après 3 cycles sans progrès, ou dès qu'un cycle "
        "dérape, l'entraînement repart du student déployé avec un pas divisé par deux.",
        "Les 5 derniers students déployés sont conservés ; <b>Reset student</b> revient au "
        "modèle d'origine.",
    ]))

    s.append(p("5. Choisir le student", H1))
    s.append(p(
        "Six students sont fournis et apparaissent dans la liste <b>student</b> du nœud, du "
        "moins coûteux au plus coûteux. Le teacher fourni est <b>yolox_s</b> (640 x 640)."
    ))
    rows = [["Student", "Entrée (L x H)", "Pixels", "Temps CPU", "Pour quoi"]]
    rows += [list(row[:3]) + [row[3] + " ms", row[4]] for row in STUDENTS]
    s.append(table(rows, [0.22, 0.13, 0.14, 0.10, 0.41]))
    s.append(p(
        "Temps du réseau seul, onnxruntime sur 2 cœurs de processeur ; pour comparaison, le "
        "teacher yolox_s demande 157 ms sur la même machine. À réseau égal, le temps de calcul "
        "suit le nombre de pixels de l'entrée.", SMALL))
    s.append(Spacer(1, 8))
    s.append(p("D'où viennent les students réduits", H2))
    s.append(p(
        "Un YOLOX est entièrement convolutif : <b>les mêmes poids fonctionnent à n'importe "
        "quelle taille d'entrée multiple de 32</b>, et le temps de calcul est proportionnel "
        "au nombre de pixels. Les students réduits sont donc yolox_nano et yolox_tiny, avec "
        "leurs poids officiels, réglés sur une entrée plus petite. Moins de pixels, c'est "
        "moins de détail : la distillation sert précisément à apprendre au student à tirer "
        "le meilleur de ces pixels sur votre scène."
    ))
    s.append(KeepTogether([
        p("Pourquoi une entrée rectangulaire", H2),
        p(
            "Une image de caméra est le plus souvent en 16:9. Dans une entrée carrée, elle "
            "n'occupe que le haut : le réseau calcule pour rien sur une bande vide. Une "
            "entrée 416 x 256 contient la même image, <b>à la même échelle</b>, avec 38 % "
            "de pixels en moins."
        ),
        sizes_drawing(),
        p("Figure 4 - La même image 16:9 dans trois entrées (en bleu : l'image, en gris : "
          "le vide).", CAPTION),
    ]))
    s.append(p("Créer un student à une autre taille", H2))
    s.append(p(
        "Tout fichier <font face='Courier'>yolox*.onnx</font> placé dans "
        "<font face='Courier'>node/DLNode/object_detection/YOLOX/model/</font> apparaît dans "
        "les listes. Pour en créer un à la taille voulue (largeur x hauteur, multiples de 32, "
        "au plus la taille du teacher) :"
    ))
    s.append(code(
        "python -m node.DLNode.online_training.distill.resize \\\n"
        "    --model node/DLNode/object_detection/YOLOX/model/yolox_nano.onnx \\\n"
        "    --size 512x288"
    ))

    s.append(p("6. Utilisation", H1))
    s.append(p("Dans l'application", H2))
    s.extend(bullets([
        "Menu <b>VisionModel</b>, nœud <b>YoloxDistillation</b> ; relier une source d'images.",
        "Choisir le <b>teacher</b> (yolox_s) et le <b>student</b> (tableau de la section 5).",
        "Cocher <b>Distill (background)</b> et laisser tourner : il faut 60 échantillons "
        "avant le premier cycle, et plusieurs centaines pour un résultat net.",
        "<b>Export ONNX</b> écrit le student déployé dans "
        "<font face='Courier'>_Distillation/exports/</font>.",
    ]))
    s.append(p("Le nœud affiche trois lignes d'état :"))
    s.append(code(
        "student v3 - training (cpu)      version déployée, activité, matériel\n"
        "samples: 412 train / 96 val      échantillons collectés\n"
        "val loss 0.871  AP50 0.76        mesure du student déployé"
    ))
    s.append(p(
        "Tout est conservé dans <font face='Courier'>_Distillation/&lt;student&gt;__from__"
        "&lt;teacher&gt;/</font> : au redémarrage, le nœud reprend avec le dernier student "
        "déployé et les échantillons déjà collectés. Chaque couple teacher/student a son "
        "propre dossier."
    ))
    s.append(p("Mesurer avant de se fier au résultat", H2))
    s.append(p(
        "L'outil en ligne de commande rejoue une vidéo enregistrée comme un flux. La fin de "
        "la vidéo (30 %) n'est jamais montrée au moteur et sert à comparer le student avant "
        "et après :"
    ))
    s.append(code(
        "python -m node.DLNode.online_training.distill.cli \\\n"
        "    --teacher node/DLNode/object_detection/YOLOX/model/yolox_s.onnx \\\n"
        "    --student node/DLNode/object_detection/YOLOX/model/yolox_nano_416x256.onnx \\\n"
        "    --source camera.mp4 --workdir _Distillation/essai --rounds 30"
    ))

    s.append(PageBreak())
    s.append(p("7. Résultats mesurés", H1))
    s.append(p(
        "Teacher yolox_s, processeur 2 cœurs sans GPU, réglages par défaut, 30 cycles. Le "
        "début de chaque vidéo (70 %) alimente le moteur ; les chiffres sont mesurés sur la "
        "fin, jamais vue. Référence : les détections du teacher en pleine résolution. "
        "<b>AP50</b> : qualité du classement des détections ; <b>F1</b> : équilibre entre "
        "détections manquées et fausses détections, au seuil 0,3. En gras : gain d'au moins "
        "0,02."
    ))
    s.append(results_table())
    s.append(Spacer(1, 6))
    s.extend(bullets([
        "<b>yolox_nano_416x256 fait jeu égal avec yolox_nano</b> (0,514 contre 0,520 d'AP50) "
        "pour 38 % de pixels en moins : sur une caméra 16:9, c'est le student à choisir.",
        "<b>Les students en 320 de large suffisent quand les objets sont gros</b> (passage de "
        "personnes : F1 0,99), <b>pas quand ils sont petits</b> (allée de magasin : 0,31 "
        "d'AP50 contre 0,51 en 416). La distillation ne remplace pas les pixels qui manquent.",
        "yolox_tiny_416x256 est nettement au-dessus sur la scène difficile (0,88 d'AP50), "
        "pour 3 fois le temps de calcul de yolox_nano_416x256.",
        "Sur le passage de personnes, l'AP50 était déjà proche de 1 : le gain de F1 vient "
        "de scores mieux réglés (les fausses détections passent sous le seuil), pas de "
        "nouvelles détections.",
        "<b>Clip court (270 échantillons) : pas de gain fiable, et le F1 peut baisser</b>, "
        "surtout pour le plus petit student. Laissez collecter plusieurs centaines "
        "d'échantillons avant de juger.",
    ]))

    s.append(KeepTogether([
        p("8. Limites", H1),
        *bullets([
            "<b>YOLOX uniquement</b>, teacher et student avec les mêmes classes.",
            "Le student se rapproche du teacher et ne le dépasse pas : il apprend aussi ses "
            "erreurs.",
            "Un student distillé sur une caméra est spécialisé sur cette scène ; le modèle "
            "d'origine reste disponible.",
            "Les mesures ci-dessus portent sur des vidéos courtes : elles donnent un ordre "
            "de grandeur, pas une garantie. Mesurez sur vos images.",
            "L'entraînement sur GPU utilise le même code mais n'a pas été exécuté sur une "
            "machine avec GPU.",
        ]),
    ]))

    s.append(KeepTogether([
        p("9. Où est le code", H1),
        table([
            ["Fichier", "Rôle"],
            ["node/DLNode/node_yolox_distillation.py", "le nœud et ses listes de modèles"],
            ["node/DLNode/online_training/distill/engine.py",
             "collecte, entraînement, validation, déploiement"],
            [".../distill/yolox_torch.py", "student entraînable depuis l'ONNX, perte de "
                                           "distillation"],
            [".../distill/resize.py", "student à une autre taille d'entrée"],
            [".../distill/cli.py", "mesure et entraînement sur une vidéo enregistrée"],
            ["docs/DISTILLATION_YOLOX.md", "documentation détaillée et réglages"],
            ["tools/make_distillation_pdf.py", "génère ce document"],
        ], [0.46, 0.54]),
    ]))
    return s


def main():
    doc = SimpleDocTemplate(
        OUTPUT, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=1.9 * cm, bottomMargin=2 * cm,
        title="Distillation YOLOX en direct", author="CV Studio",
        subject="Fonctionnement du nœud YoloxDistillation",
    )
    doc.build(story(), onFirstPage=first_page, onLaterPages=later_pages)
    print(OUTPUT)


if __name__ == "__main__":
    main()
