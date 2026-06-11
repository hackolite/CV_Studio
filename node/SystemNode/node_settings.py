#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Settings Node (System category)

Manages persistent global settings for CV Studio, including Copernicus / CDSE
credentials (client_id and client_secret).

Credentials are stored in ``~/.cv_studio/copernicus_credentials.json`` so that
the file survives PyInstaller .exe packaging (sys._MEIPASS is read-only at
runtime; the user home directory is always writable).
"""

import json
import os
import threading

import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node.basenode import Node


# ---------------------------------------------------------------------------
# Persistent config helpers — works in both dev mode and PyInstaller .exe
# ---------------------------------------------------------------------------

def _get_config_dir() -> str:
    """Return the user-level config directory, creating it if necessary.

    Uses ``~/.cv_studio/`` so the path is always writable regardless of
    whether the application is running from source or as a frozen .exe.
    """
    config_dir = os.path.join(os.path.expanduser("~"), ".cv_studio")
    os.makedirs(config_dir, exist_ok=True)
    return config_dir


_CREDENTIALS_FILE = os.path.join(_get_config_dir(), "copernicus_credentials.json")


def load_copernicus_credentials() -> dict:
    """Load Copernicus CDSE credentials from the user config file.

    Returns a dict with ``client_id`` and ``client_secret`` keys.
    Both default to empty strings when the file is absent or invalid.
    """
    if os.path.exists(_CREDENTIALS_FILE):
        try:
            with open(_CREDENTIALS_FILE, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            return {
                "client_id": str(data.get("client_id", "")),
                "client_secret": str(data.get("client_secret", "")),
            }
        except Exception:
            pass
    return {"client_id": "", "client_secret": ""}


def save_copernicus_credentials(client_id: str, client_secret: str) -> None:
    """Persist Copernicus CDSE credentials to ``~/.cv_studio/copernicus_credentials.json``."""
    payload = {"client_id": client_id, "client_secret": client_secret}
    with open(_CREDENTIALS_FILE, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)


# ---------------------------------------------------------------------------
# FactoryNode — registered by node_main's dynamic discovery
# ---------------------------------------------------------------------------

class FactoryNode:
    node_label = "Settings"
    node_tag = "Settings"

    def __init__(self):
        pass

    def add_node(
        self,
        parent,
        node_id,
        pos=None,
        opencv_setting_dict=None,
        callback=None,
    ):
        if pos is None:
            pos = [0, 0]

        node = _Node()
        node.tag_node_name = str(node_id) + ":" + node.node_tag
        node._opencv_setting_dict = opencv_setting_dict

        tag = node.tag_node_name
        tag_section   = tag + ":SectionStatic"
        tag_client_id = tag + ":ClientId"
        tag_secret    = tag + ":ClientSecret"
        tag_status    = tag + ":Status"
        tag_save_btn  = tag + ":SaveBtn"
        tag_test_btn  = tag + ":TestBtn"
        tag_output    = tag + ":JSON:Output01"
        tag_out_val   = tag + ":JSON:Output01Value"

        creds = load_copernicus_credentials()

        with dpg.node(tag=tag, parent=parent, label=node.node_label, pos=pos):

            # ── Copernicus / CDSE credentials ──────────────────────────────
            with dpg.node_attribute(
                tag=tag_section,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_text("─── Copernicus / CDSE ───")
                dpg.add_spacer(height=4)

                dpg.add_input_text(
                    tag=tag_client_id,
                    label="Client ID",
                    default_value=creds["client_id"],
                    width=270,
                    hint="Enter your CDSE client_id",
                )
                dpg.add_spacer(height=2)
                dpg.add_input_text(
                    tag=tag_secret,
                    label="Secret",
                    default_value=creds["client_secret"],
                    width=270,
                    hint="Enter your CDSE client_secret",
                    password=True
                )
                dpg.add_spacer(height=6)
                with dpg.group(horizontal=True):
                    dpg.add_button(
                        tag=tag_save_btn,
                        label="  Save  ",
                        width=110,
                        callback=node._on_save,
                        user_data=(tag_client_id, tag_secret, tag_status),
                    )
                    dpg.add_button(
                        tag=tag_test_btn,
                        label="  Test connection  ",
                        width=160,
                        callback=node._on_test,
                        user_data=(tag_client_id, tag_secret, tag_status),
                    )
                dpg.add_spacer(height=4)
                dpg.add_text(tag=tag_status, default_value="Status: —")
                dpg.add_spacer(height=2)

            # ── JSON output (credentials status for downstream nodes) ───────
            with dpg.node_attribute(
                tag=tag_output,
                attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_text(tag=tag_out_val, default_value="Credentials")

        return node


# ---------------------------------------------------------------------------
# Node implementation
# ---------------------------------------------------------------------------

class _Node(Node):
    _ver = "0.0.1"
    node_label = "Settings"
    node_tag = "Settings"

    _opencv_setting_dict = None

    def __init__(self):
        pass

    # ── Button callbacks ────────────────────────────────────────────────────

    def _on_save(self, sender, app_data, user_data):
        tag_client_id, tag_secret, tag_status = user_data
        client_id = dpg_get_value(tag_client_id) or ""
        secret    = dpg_get_value(tag_secret)    or ""
        try:
            save_copernicus_credentials(client_id, secret)
            dpg_set_value(tag_status, "Status: Saved ✓")
        except Exception as exc:
            dpg_set_value(tag_status, f"Error saving: {exc}")

    def _on_test(self, sender, app_data, user_data):
        tag_client_id, tag_secret, tag_status = user_data
        client_id = dpg_get_value(tag_client_id) or ""
        secret    = dpg_get_value(tag_secret)    or ""
        dpg_set_value(tag_status, "Status: Testing…")

        def _run():
            try:
                import requests  # noqa: PLC0415
                resp = requests.post(
                    "https://identity.dataspace.copernicus.eu/auth/realms/CDSE"
                    "/protocol/openid-connect/token",
                    data={
                        "grant_type":    "client_credentials",
                        "client_id":     client_id,
                        "client_secret": secret,
                    },
                    timeout=20,
                )
                if resp.status_code == 200:
                    dpg_set_value(tag_status, "Status: Connected ✓")
                else:
                    body = resp.text[:80].replace("\n", " ")
                    dpg_set_value(tag_status, f"Status: HTTP {resp.status_code} — {body}")
            except Exception as exc:
                dpg_set_value(tag_status, f"Status: {str(exc)[:60]}")

        threading.Thread(target=_run, daemon=True).start()

    # ── Node lifecycle ──────────────────────────────────────────────────────

    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
        node_audio_dict,
    ):
        creds = load_copernicus_credentials()
        return {
            "image": None,
            "json": {
                "copernicus_client_id":   creds["client_id"],
                "copernicus_has_secret":  bool(creds["client_secret"]),
            },
            "audio": None,
        }

    def close(self, node_id):
        pass
