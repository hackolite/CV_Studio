#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""SecurityAgent — LLM-driven security assessment via OpenRouter.

Shares the same architecture as AmbianceAgent; specialised by its system
prompt which focuses on intrusion detection, access control, and alerts.
"""

from node.AgentNode.node_ambiance_agent import Node as AmbianceAgentNode

_AGENT_TYPE = 'SecurityAgent'

_SYSTEM_PROMPT = (
    "You are an expert security analyst. "
    "Analyse the provided sensor data (cameras, motion sensors, access logs, etc.) "
    "and user prompt, then select and configure the available tools to respond to "
    "the detected security situation. "
    "Return ONLY a single valid JSON object matching the required schema — "
    "no markdown fences, no commentary, no chain-of-thought text."
)


class FactoryNode:
    node_label = _AGENT_TYPE
    node_tag = _AGENT_TYPE

    def __init__(self):
        pass

    def add_node(self, parent, node_id, pos=None, opencv_setting_dict=None, callback=None):
        if pos is None:
            pos = [0, 0]
        node = Node()
        return node.add_node(parent, node_id, pos, opencv_setting_dict, callback)


class Node(AmbianceAgentNode):
    _ver = '0.0.1'
    node_label = _AGENT_TYPE
    node_tag = _AGENT_TYPE

    def __init__(self):
        super().__init__()

    def _build_messages(self, data, prompt, tools):
        import json
        from node.AgentNode.node_ambiance_agent import _RESPONSE_SCHEMA
        user_content = {
            'sensor_data': data,
            'user_prompt': prompt,
            'available_tools': tools,
            'response_schema': _RESPONSE_SCHEMA,
            'instruction': (
                'Based on the sensor data and user prompt, assess the security situation '
                'and decide which tools to activate. '
                'Only use tools listed in available_tools. '
                'Return a single JSON object matching response_schema exactly.'
            ),
        }
        return [
            {'role': 'system', 'content': _SYSTEM_PROMPT},
            {'role': 'user', 'content': json.dumps(user_content, ensure_ascii=False)},
        ]
