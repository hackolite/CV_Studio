"""
CvStudio JSON save-file parser.

Parses the export format produced by CvStudio's _callback_file_export:
{
    "node_list": ["<id>:<NodeTag>", ...],
    "link_list": [["<output_port>", "<input_port>"], ...],
    "<id>:<NodeTag>": {
        "id": "<id>",
        "name": "<NodeTag>",
        "setting": { ... }
    }
}
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class NodeInfo:
    """Parsed representation of a single CvStudio node."""

    node_id: int
    node_tag: str
    settings: dict[str, Any] = field(default_factory=dict)


@dataclass
class LinkInfo:
    """A connection between two node ports."""

    source_port: str
    target_port: str

    @property
    def source_node_id(self) -> int:
        return int(self.source_port.split(":")[0])

    @property
    def target_node_id(self) -> int:
        return int(self.target_port.split(":")[0])

    @property
    def source_node_tag(self) -> str:
        return self.source_port.split(":")[1]

    @property
    def target_node_tag(self) -> str:
        return self.target_port.split(":")[1]


@dataclass
class CvStudioProject:
    """Full parsed CvStudio project."""

    nodes: dict[int, NodeInfo] = field(default_factory=dict)
    links: list[LinkInfo] = field(default_factory=list)

    # Convenience accessors
    def nodes_by_tag(self, tag: str) -> list[NodeInfo]:
        return [n for n in self.nodes.values() if n.node_tag == tag]

    def get_downstream(self, node_id: int) -> list[NodeInfo]:
        """Return nodes that receive data from *node_id*."""
        downstream_ids = set()
        for link in self.links:
            if link.source_node_id == node_id:
                downstream_ids.add(link.target_node_id)
        return [self.nodes[nid] for nid in downstream_ids if nid in self.nodes]

    def get_upstream(self, node_id: int) -> list[NodeInfo]:
        """Return nodes that feed data into *node_id*."""
        upstream_ids = set()
        for link in self.links:
            if link.target_node_id == node_id:
                upstream_ids.add(link.source_node_id)
        return [self.nodes[nid] for nid in upstream_ids if nid in self.nodes]


def parse(path: str | Path) -> CvStudioProject:
    """Parse a CvStudio JSON save file and return a CvStudioProject."""
    path = Path(path)
    with open(path, "r", encoding="utf-8") as fp:
        data = json.load(fp)

    project = CvStudioProject()

    # Parse nodes
    for node_id_name in data.get("node_list", []):
        parts = node_id_name.split(":")
        node_id = int(parts[0])
        node_tag = parts[1]

        node_data = data.get(node_id_name, {})
        settings = node_data.get("setting", {})

        project.nodes[node_id] = NodeInfo(
            node_id=node_id,
            node_tag=node_tag,
            settings=settings,
        )

    # Parse links
    for link_pair in data.get("link_list", []):
        if len(link_pair) >= 2:
            project.links.append(LinkInfo(
                source_port=link_pair[0],
                target_port=link_pair[1],
            ))

    return project
