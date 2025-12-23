#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Exemple complet d'utilisation de Dear PyGui avec un node editor et des combo boxes colorés.

Ce script démontre :
1. Une fenêtre avec un node editor
2. Un mvCombo (droplist) pour sélectionner un "domaine" parmi plusieurs
3. Chaque domaine a une couleur spécifique pour ses nodes
4. Le background du combo reflète la couleur du domaine sélectionné
5. Les éléments de la liste déroulante ont leur fond coloré avec éclaircissement au survol
6. Création dynamique de thèmes pour chaque sélection
7. Fonction brighter() pour éclaircir les couleurs au survol
8. Trois domaines avec couleurs différentes et trois nodes fictifs par domaine
"""

import dearpygui.dearpygui as dpg


def delete_item_if_exists(item_tag):
    """
    Supprime un item DearPyGui s'il existe.
    
    Args:
        item_tag: Tag de l'item à supprimer
    """
    if dpg.does_item_exist(item_tag):
        dpg.delete_item(item_tag)


def brighter(color_tuple, factor=1.3):
    """
    Prend un tuple RGBA (0-255) et renvoie un tuple un peu plus clair.
    
    Args:
        color_tuple: Tuple de 4 entiers (R, G, B, A) entre 0-255
        factor: Facteur d'éclaircissement (> 1 pour éclaircir)
    
    Returns:
        Tuple RGBA plus clair, plafonné à 255
    """
    r, g, b, a = color_tuple
    r = min(255, int(r * factor))
    g = min(255, int(g * factor))
    b = min(255, int(b * factor))
    return (r, g, b, a)


# Définition des domaines avec leurs couleurs (RGBA 0-255)
DOMAINS = {
    "Vision": {
        "color": (70, 130, 180, 255),  # Steel Blue
        "nodes": ["Camera Input", "Image Processing", "Object Detection"]
    },
    "Audio": {
        "color": (144, 70, 180, 255),  # Purple
        "nodes": ["Microphone Input", "Audio Processing", "Spectrogram"]
    },
    "Network": {
        "color": (180, 100, 70, 255),  # Orange/Brown
        "nodes": ["HTTP Request", "WebSocket", "Data Parser"]
    }
}

# Variable globale pour stocker la sélection actuelle
# Note: Pour une application production, ces variables devraient être encapsulées dans une classe
current_domain = "Vision"
domain_themes = {}
node_theme_cache = {}


def create_combo_theme(domain_name, base_color):
    """
    Crée un thème pour le combo box avec la couleur du domaine.
    
    Args:
        domain_name: Nom du domaine
        base_color: Tuple RGBA (0-255) de la couleur de base
    
    Returns:
        Tag du thème créé
    """
    theme_tag = f"combo_theme_{domain_name}"
    
    # Supprimer le thème s'il existe déjà
    delete_item_if_exists(theme_tag)
    
    # Couleur hover (plus claire)
    hover_color = brighter(base_color, 1.2)
    active_color = brighter(base_color, 1.4)
    
    with dpg.theme(tag=theme_tag):
        with dpg.theme_component(dpg.mvCombo):
            # Couleur de fond du combo
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, base_color, category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, hover_color, category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, active_color, category=dpg.mvThemeCat_Core)
            # Couleur du popup (liste déroulante)
            dpg.add_theme_color(dpg.mvThemeCol_PopupBg, base_color, category=dpg.mvThemeCat_Core)
            # Couleur du texte en blanc pour contraste
            dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255, 255), category=dpg.mvThemeCat_Core)
    
    return theme_tag


def create_node_theme(domain_name, base_color):
    """
    Crée un thème pour les nodes avec la couleur du domaine.
    
    Args:
        domain_name: Nom du domaine
        base_color: Tuple RGBA (0-255) de la couleur de base
    
    Returns:
        Tag du thème créé
    """
    theme_tag = f"node_theme_{domain_name}"
    
    # Supprimer le thème s'il existe déjà
    delete_item_if_exists(theme_tag)
    
    # Couleur plus sombre pour le node
    dark_color = (
        int(base_color[0] * 0.7),
        int(base_color[1] * 0.7),
        int(base_color[2] * 0.7),
        base_color[3]
    )
    
    with dpg.theme(tag=theme_tag):
        with dpg.theme_component(dpg.mvNode):
            # Couleur de fond du node
            dpg.add_theme_color(dpg.mvNodeCol_NodeBackground, dark_color, category=dpg.mvThemeCat_Nodes)
            dpg.add_theme_color(dpg.mvNodeCol_NodeBackgroundHovered, base_color, category=dpg.mvThemeCat_Nodes)
            dpg.add_theme_color(dpg.mvNodeCol_NodeBackgroundSelected, base_color, category=dpg.mvThemeCat_Nodes)
            dpg.add_theme_color(dpg.mvNodeCol_TitleBar, base_color, category=dpg.mvThemeCat_Nodes)
            dpg.add_theme_color(dpg.mvNodeCol_TitleBarHovered, brighter(base_color, 1.2), category=dpg.mvThemeCat_Nodes)
            dpg.add_theme_color(dpg.mvNodeCol_TitleBarSelected, brighter(base_color, 1.3), category=dpg.mvThemeCat_Nodes)
    
    return theme_tag


def on_domain_change(sender, app_data, user_data):
    """
    Callback appelé quand la sélection du domaine change.
    Met à jour le thème du combo box et les nodes affichés.
    """
    global current_domain
    current_domain = app_data
    
    # Créer et appliquer le thème pour ce domaine
    domain_color = DOMAINS[current_domain]["color"]
    theme_tag = create_combo_theme(current_domain, domain_color)
    
    # Appliquer le thème au combo box
    dpg.bind_item_theme("domain_combo", theme_tag)
    
    # Mettre à jour l'affichage des nodes
    update_node_display()


def update_node_display():
    """
    Met à jour l'affichage des nodes dans le node editor selon le domaine sélectionné.
    """
    global current_domain
    
    # Supprimer tous les nodes existants dans l'éditeur
    children = dpg.get_item_children("node_editor", 1)
    if children:
        for child in children:
            if dpg.does_item_exist(child):
                dpg.delete_item(child)
    
    # Créer les nodes pour le domaine actuel
    domain_color = DOMAINS[current_domain]["color"]
    node_theme = create_node_theme(current_domain, domain_color)
    
    nodes = DOMAINS[current_domain]["nodes"]
    
    for idx, node_name in enumerate(nodes):
        node_tag = f"node_{current_domain}_{idx}"
        
        with dpg.node(label=node_name, parent="node_editor", tag=node_tag, pos=(50 + idx * 250, 50)):
            with dpg.node_attribute(label="Input", attribute_type=dpg.mvNode_Attr_Input):
                dpg.add_text(f"Input {idx + 1}")
            
            with dpg.node_attribute(label="Output", attribute_type=dpg.mvNode_Attr_Output):
                dpg.add_text(f"Output {idx + 1}")
        
        # Appliquer le thème au node
        dpg.bind_item_theme(node_tag, node_theme)


def setup_gui():
    """
    Configure l'interface graphique principale.
    """
    # Créer les thèmes pour tous les domaines
    for domain_name, domain_data in DOMAINS.items():
        domain_themes[domain_name] = create_combo_theme(domain_name, domain_data["color"])
        node_theme_cache[domain_name] = create_node_theme(domain_name, domain_data["color"])
    
    # Fenêtre principale
    with dpg.window(label="Node Editor avec Combo Coloré", tag="main_window", width=1000, height=700):
        
        # Section de sélection du domaine
        with dpg.group(horizontal=True):
            dpg.add_text("Sélectionner un domaine :")
            combo = dpg.add_combo(
                items=list(DOMAINS.keys()),
                default_value=current_domain,
                callback=on_domain_change,
                tag="domain_combo",
                width=200
            )
            # Appliquer le thème initial
            dpg.bind_item_theme(combo, domain_themes[current_domain])
        
        dpg.add_separator()
        
        # Texte d'information
        dpg.add_text(
            "Les nodes ci-dessous appartiennent au domaine sélectionné.\n"
            "Changez le domaine pour voir différentes couleurs et nodes.",
            color=(200, 200, 200, 255)
        )
        
        dpg.add_separator()
        
        # Node Editor
        with dpg.node_editor(
            tag="node_editor",
            callback=lambda sender, app_data: None,
            minimap=True,
            minimap_location=dpg.mvNodeMiniMap_Location_BottomRight
        ):
            pass
    
    # Initialiser l'affichage des nodes
    update_node_display()


def main():
    """
    Point d'entrée principal de l'application.
    """
    # Créer le contexte DearPyGui
    dpg.create_context()
    
    # Configurer la fenêtre et l'interface
    setup_gui()
    
    # Créer le viewport
    dpg.create_viewport(
        title="DearPyGui - Node Editor avec Domaines Colorés",
        width=1024,
        height=768
    )
    
    # Setup et affichage
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window("main_window", True)
    
    # Boucle principale
    dpg.start_dearpygui()
    
    # Nettoyage
    dpg.destroy_context()


if __name__ == "__main__":
    main()
