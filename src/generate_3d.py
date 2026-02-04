#!/usr/bin/env python3
"""
Network Graph Visualization Generator - 3D Version (Extended)

Generates interactive 3D network visualizations with:
- True 3D space with orbit controls (rotate, zoom, pan)
- Toggle between 2D and 3D views
- Click-to-show info panel
- Navigation through connected nodes
- Nodes positioned by tier in spherical shells

Extended Features (v2.0):
VISUAL ENHANCEMENTS:
- Custom node geometries (sphere, cube, octahedron, ring, diamond)
- Node sprites/labels with always-facing text
- Edge particles showing directional flow
- Glow/bloom effects for highlighted nodes
- Node halos indicating importance/age

INTERACTION EXTENSIONS:
- Path highlighting with animated traversal
- Expand/collapse clustered groups
- Multi-select with shift-click
- Search with zoom-to-result
- Time slider for graph evolution
- VR mode support (WebXR)

LAYOUT VARIATIONS:
- Layered 3D (Z-axis = hierarchy/time)
- Spherical layout (nodes on sphere surface)
- Cylinder layout (time on Y, categories on circumference)
- Force + constraints (pin nodes to fixed positions)

DATA-DRIVEN FEATURES:
- Edge thickness by relationship strength
- Pulsing nodes based on recency/activity
- Heat map coloring by continuous metric
- Size by centrality measures

Usage:
    python generate_3d.py --input data/examples/fbc_partners.json --output output/html/fbc_ecosystem.html
"""

import argparse
import json
import math
from pathlib import Path
from typing import Any


def load_json_data(filepath: str) -> dict[str, Any]:
    """Load graph data from JSON file."""
    with open(filepath, "r") as f:
        return json.load(f)


def generate_html(data: dict[str, Any], title: str) -> str:
    """Generate custom HTML with 3D interactive features."""

    # Get group info for legend
    groups = data.get("groups", {})

    # Get physical groups if available (for Logical/Physical view toggle)
    physical_groups = data.get("physical_groups", {})

    # Prepare nodes JSON with 3D positions based on tier
    nodes_list = []
    tier_counts = {}  # Track count per tier for positioning

    for node in data["nodes"]:
        node_id = node["id"]
        group = node.get("group", "default")
        tier = node.get("tier", 0)
        group_info = groups.get(group, {"color": "#888888", "label": group})

        # Get physical group info if available
        physical_group = node.get("physical_group", "")
        physical_group_info = physical_groups.get(physical_group, {"color": "#888888", "label": physical_group}) if physical_group else None

        # Count nodes per tier
        if tier not in tier_counts:
            tier_counts[tier] = 0
        tier_counts[tier] += 1

        nodes_list.append({
            "id": node_id,
            "name": node.get("label", node_id),
            "description": node.get("title", ""),
            "val": node.get("size", 20),
            "color": group_info.get("color", "#888888"),
            "group": group,
            "groupLabel": group_info.get("label", group),
            "tier": tier,
            "logo": node.get("logo", ""),
            "createdAt": node.get("created_at"),
            "physicalGroup": physical_group,
            "physicalGroupColor": physical_group_info.get("color", "#888888") if physical_group_info else None,
            "physicalGroupLabel": physical_group_info.get("label", physical_group) if physical_group_info else None,
        })

    # Prepare links JSON with relationship type labels
    # Default edge styles - can be overridden by data's edge_types
    default_edge_styles = {
        # Explicit relationships
        "references": {"color": "#3182ce", "width": 3, "label": "References"},
        "informs": {"color": "#2f855a", "width": 2, "label": "Informs"},
        # Semantic similarity
        "highly_similar": {"color": "#9f7aea", "width": 3, "label": "Highly Similar"},
        "similar": {"color": "#b794f4", "width": 2, "label": "Similar"},
        # Metadata-based
        "same_category": {"color": "#ed8936", "width": 1, "label": "Same Category"},
        "same_agent": {"color": "#4fd1c5", "width": 1, "label": "Same Agent"},
        # Temporal
        "temporal_context": {"color": "#fc8181", "width": 1, "label": "Temporal"},
        # Generic
        "related": {"color": "#a0aec0", "width": 1, "label": "Related"},
        # Partner ecosystem types
        "strategic_partner": {"color": "#2f855a", "width": 3, "label": "Strategic Partner"},
        "emerging_partner": {"color": "#3182ce", "width": 2, "label": "Emerging Partner"},
        "collaboration": {"color": "#a0aec0", "width": 1, "label": "Collaboration"},
        "member": {"color": "#718096", "width": 1, "label": "Member"},
    }

    # Use edge_types from data if provided, otherwise use defaults
    edge_styles = data.get("edge_types", default_edge_styles)
    # Merge with defaults to ensure all types are covered
    for k, v in default_edge_styles.items():
        if k not in edge_styles:
            edge_styles[k] = v

    # Track unique edge types for filtering
    edge_types_used = set()

    links_list = []
    for edge in data["edges"]:
        edge_type = edge.get("type", "default")
        style = edge_styles.get(edge_type, {"color": "#888888", "width": 1, "label": edge_type})
        edge_types_used.add(edge_type)

        links_list.append({
            "source": edge["source"],
            "target": edge["target"],
            "color": style.get("color", "#888888"),
            "width": style.get("width", 1),
            "relationType": style.get("label", edge_type),
            "edgeType": edge_type,  # Keep original type for filtering
        })

    nodes_json = json.dumps(nodes_list)
    links_json = json.dumps(links_list)
    groups_json = json.dumps(groups)
    physical_groups_json = json.dumps(physical_groups)
    edge_styles_json = json.dumps(edge_styles)

    # Check if physical groups are available for the view toggle
    has_physical_groups = bool(physical_groups) and any(n.get("physical_group") for n in data["nodes"])

    # Generate node filter chips
    node_chips_html = ""
    for group_id, group_info in groups.items():
        color = group_info.get("color", "#888888")
        label = group_info.get("label", group_id)
        node_chips_html += f'''<span class="filter-chip active" data-group="{group_id}"><span class="chip-color" style="background:{color}"></span>{label}</span>\n                        '''

    # Generate edge filter chips
    edge_chips_html = ""
    for edge_type in sorted(edge_types_used):
        style = edge_styles.get(edge_type, {"color": "#888888", "label": edge_type})
        color = style.get("color", "#888888")
        label = style.get("label", edge_type)
        edge_chips_html += f'''<span class="filter-chip active" data-edge-type="{edge_type}"><span class="chip-color" style="background:{color}"></span>{label}</span>\n                        '''

    # Generate view mode toggle (only if physical groups exist)
    view_mode_toggle_html = ""
    if has_physical_groups:
        view_mode_toggle_html = '''<div class="toolbar-divider"></div>
                <div class="toolbar-section view-mode-section" id="view-mode-toggle">
                    <span class="view-mode-label">View:</span>
                    <button class="view-mode-btn active" id="btn-logical" onclick="setViewMode('logical')">Logical</button>
                    <button class="view-mode-btn" id="btn-physical" onclick="setViewMode('physical')">Physical</button>
                </div>'''

    # Get description from metadata
    description = data.get("metadata", {}).get("description", "Click a node to explore")

    html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <title>{title}</title>
    <link rel="icon" href="data:,">
    <!-- Load THREE.js first, then 3d-force-graph will use the global THREE -->
    <script src="//unpkg.com/three@0.160.0/build/three.min.js"></script>
    <script src="//unpkg.com/3d-force-graph@1.73.4/dist/3d-force-graph.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: #0a0a1a;
            overflow: hidden;
        }}
        .container {{
            display: flex;
            height: 100vh;
            width: 100vw;
        }}
        #graph-wrapper {{
            flex: 1;
            background: #0a0a1a;
            position: relative;
            overflow: hidden;
        }}
        #graph {{
            width: 100%;
            height: 100%;
            position: absolute;
            top: 0;
            left: 0;
        }}
        #graph canvas {{
            width: 100% !important;
            height: 100% !important;
        }}
        #sidebar {{
            width: 350px;
            min-width: 350px;
            background: #ffffff;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            z-index: 100;
            box-shadow: -2px 0 10px rgba(0,0,0,0.3);
            transition: transform 0.3s ease;
        }}
        #sidebar.hidden {{
            transform: translateX(100%);
        }}
        #sidebar-toggle {{
            position: fixed;
            right: 350px;
            top: 50%;
            transform: translateY(-50%);
            width: 24px;
            height: 60px;
            background: #1a365d;
            border: none;
            border-radius: 6px 0 0 6px;
            color: white;
            cursor: pointer;
            z-index: 101;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
            transition: right 0.3s ease;
        }}
        #sidebar-toggle.sidebar-hidden {{
            right: 0;
        }}
        #sidebar-toggle:hover {{
            background: #2d4a7c;
        }}
        .header {{
            background: #1a365d;
            color: white;
            padding: 20px;
            text-align: center;
        }}
        .header h1 {{
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 5px;
        }}
        .header p {{
            font-size: 12px;
            opacity: 0.8;
        }}
        #info-panel {{
            padding: 20px;
            flex: 1;
        }}
        .info-placeholder {{
            color: #666;
            text-align: center;
            padding: 40px 20px;
        }}
        .info-placeholder p {{
            margin-bottom: 10px;
        }}
        .node-info {{
            display: none;
        }}
        .node-info.active {{
            display: block;
        }}
        .node-header {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 15px;
            padding-bottom: 15px;
            border-bottom: 2px solid #e0e0e0;
        }}
        .node-logo {{
            width: 50px;
            height: 50px;
            object-fit: contain;
            border-radius: 6px;
            background: #f8f9fa;
            padding: 4px;
            flex-shrink: 0;
        }}
        .node-logo[src=""], .node-logo:not([src]) {{
            display: none;
        }}
        .node-header-text {{
            flex: 1;
        }}
        .node-title {{
            font-size: 16px;
            font-weight: 600;
            color: #1a365d;
            margin-bottom: 5px;
        }}
        .node-tier {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 600;
            color: white;
            margin-bottom: 15px;
        }}
        .tier-hub {{ background: #1a365d; }}
        .tier-1 {{ background: #2f855a; }}
        .tier-2 {{ background: #3182ce; }}
        .tier-3 {{ background: #805ad5; }}
        .tier-4 {{ background: #718096; }}
        .node-description {{
            color: #444;
            line-height: 1.6;
            margin-bottom: 15px;
            font-size: 13px;
        }}
        .view-full-btn {{
            display: inline-block;
            margin-bottom: 15px;
            padding: 6px 12px;
            background: #1a365d;
            color: white;
            text-decoration: none;
            border-radius: 4px;
            font-size: 12px;
            cursor: pointer;
            border: none;
        }}
        .view-full-btn:hover {{
            background: #2d4a7c;
        }}
        .modal-overlay {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.7);
            z-index: 20000;
            justify-content: center;
            align-items: center;
        }}
        .modal-overlay.active {{
            display: flex;
        }}
        .modal-content {{
            background: white;
            border-radius: 12px;
            max-width: 800px;
            max-height: 85vh;
            width: 90%;
            display: flex;
            flex-direction: column;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        .modal-section {{
            margin-bottom: 20px;
        }}
        .modal-section:last-child {{
            margin-bottom: 0;
        }}
        .modal-section-title {{
            font-size: 12px;
            font-weight: 600;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 10px;
            padding-bottom: 6px;
            border-bottom: 1px solid #e0e0e0;
        }}
        .modal-detail-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
        }}
        .modal-detail-item {{
            background: #f8f9fa;
            padding: 10px 12px;
            border-radius: 6px;
        }}
        .modal-detail-item .detail-label {{
            font-size: 10px;
            color: #666;
            text-transform: uppercase;
            margin-bottom: 4px;
        }}
        .modal-detail-item .detail-value {{
            font-size: 13px;
            color: #1a365d;
            font-weight: 500;
        }}
        .modal-connections {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }}
        .modal-conn-chip {{
            display: inline-flex;
            align-items: center;
            padding: 6px 12px;
            background: #e8f4fd;
            border-radius: 20px;
            font-size: 12px;
            color: #2b6cb0;
            cursor: pointer;
            transition: all 0.15s;
        }}
        .modal-conn-chip:hover {{
            background: #bee3f8;
        }}
        .modal-conn-chip .conn-type {{
            font-size: 10px;
            color: #666;
            margin-left: 6px;
        }}
        .modal-logo {{
            width: 48px;
            height: 48px;
            object-fit: contain;
            margin-right: 15px;
            background: #f8f9fa;
            border-radius: 8px;
            padding: 6px;
        }}
        .modal-header-content {{
            display: flex;
            align-items: center;
        }}
        .modal-tier-badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
            color: white;
            margin-top: 6px;
        }}
        .modal-header {{
            padding: 20px;
            border-bottom: 1px solid #e0e0e0;
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
        }}
        .modal-header h2 {{
            font-size: 18px;
            color: #1a365d;
            margin: 0;
            flex: 1;
            padding-right: 20px;
        }}
        .modal-close {{
            background: none;
            border: none;
            font-size: 24px;
            cursor: pointer;
            color: #666;
            padding: 0;
            line-height: 1;
        }}
        .modal-close:hover {{
            color: #333;
        }}
        .modal-body {{
            padding: 20px;
            overflow-y: auto;
            flex: 1;
            min-height: 0;
        }}
        .modal-body .full-content {{
            white-space: pre-wrap;
            font-family: inherit;
            line-height: 1.7;
            color: #333;
        }}
        .modal-meta {{
            padding: 15px 20px;
            background: #f8f9fa;
            border-top: 1px solid #e0e0e0;
            font-size: 12px;
            color: #666;
        }}
        .modal-meta span {{
            margin-right: 20px;
        }}
        .modal-meta .label {{
            font-weight: 600;
        }}
        .node-meta {{
            font-size: 11px;
            color: #888;
            margin-bottom: 15px;
            padding: 8px;
            background: #f8f9fa;
            border-radius: 4px;
        }}
        .node-meta span {{
            display: block;
            margin-bottom: 4px;
        }}
        .node-meta .label {{
            color: #666;
            font-weight: 500;
        }}
        .connections-header {{
            font-size: 14px;
            font-weight: 600;
            color: #666;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .connection-list {{
            list-style: none;
        }}
        .connection-item {{
            padding: 10px 12px;
            margin-bottom: 8px;
            background: #f8f9fa;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.15s ease;
            border-left: 4px solid #e0e0e0;
            display: flex;
            align-items: center;
            gap: 10px;
            user-select: none;
        }}
        .connection-item:hover {{
            background: #e8f4fd;
            border-left-color: #3182ce;
            transform: translateX(3px);
        }}
        .connection-item:active {{
            background: #d0e8fa;
            transform: translateX(5px);
        }}
        .connection-item .conn-logo {{
            width: 32px;
            height: 32px;
            object-fit: contain;
            border-radius: 4px;
            background: #fff;
            padding: 2px;
            flex-shrink: 0;
        }}
        .connection-item .conn-logo[src=""] {{
            display: none;
        }}
        .connection-item .conn-info {{
            flex: 1;
        }}
        .connection-item .name {{
            font-weight: 500;
            color: #1a365d;
            margin-bottom: 3px;
        }}
        .connection-item .relation {{
            font-size: 11px;
            color: #666;
        }}
        #toolbar {{
            position: absolute;
            top: 10px;
            left: 10px;
            background: rgba(255, 255, 255, 0.95);
            padding: 6px 10px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.3);
            z-index: 10000;
            pointer-events: auto;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .toolbar-section {{
            display: flex;
            align-items: center;
            gap: 4px;
        }}
        .toolbar-label {{
            font-size: 9px;
            font-weight: 600;
            color: #1a365d;
            text-transform: uppercase;
            white-space: nowrap;
            cursor: pointer;
            user-select: none;
            padding: 2px 6px;
            border-radius: 3px;
            background: #e8f4fd;
        }}
        .toolbar-label:hover {{
            background: #d0e8fa;
        }}
        .toolbar-label .arrow {{
            font-size: 8px;
            margin-left: 3px;
            display: inline-block;
            transition: transform 0.2s;
        }}
        .toolbar-label.collapsed .arrow {{
            transform: rotate(-90deg);
        }}
        .filter-group {{
            display: flex;
            align-items: center;
            gap: 4px;
            overflow: hidden;
            transition: max-width 0.3s ease, opacity 0.2s ease;
            max-width: 2000px;
            opacity: 1;
        }}
        .filter-group.collapsed {{
            max-width: 0;
            opacity: 0;
            gap: 0;
        }}
        .toolbar-divider {{
            width: 1px;
            height: 20px;
            background: #ddd;
        }}
        .filter-chip {{
            display: inline-flex;
            align-items: center;
            font-size: 10px;
            color: #333;
            cursor: pointer;
            padding: 3px 8px;
            border-radius: 12px;
            background: #f0f0f0;
            border: 1px solid #ddd;
            transition: all 0.15s;
            white-space: nowrap;
        }}
        .filter-chip:hover {{
            background: #e0e0e0;
        }}
        .filter-chip.active {{
            background: #1a365d;
            color: white;
            border-color: #1a365d;
        }}
        .filter-chip .chip-color {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            margin-right: 4px;
        }}
        .filter-chip.active .chip-color {{
            border: 1px solid rgba(255,255,255,0.5);
        }}
        .view-btn {{
            padding: 5px 12px;
            border: 1px solid #1a365d;
            background: white;
            color: #1a365d;
            font-weight: 600;
            font-size: 11px;
            cursor: pointer;
            border-radius: 4px;
            transition: all 0.2s;
        }}
        .view-btn.active {{
            background: #1a365d;
            color: white;
        }}
        .view-btn:hover:not(.active) {{
            background: #e8f4fd;
        }}
        .mini-btn {{
            font-size: 9px;
            padding: 2px 6px;
            border: 1px solid #ccc;
            background: white;
            border-radius: 3px;
            cursor: pointer;
            color: #666;
        }}
        .mini-btn:hover {{
            background: #f0f0f0;
        }}
        .date-select {{
            font-size: 10px;
            padding: 3px 6px;
            border: 1px solid #ccc;
            border-radius: 4px;
            background: white;
            cursor: pointer;
        }}
        .date-input {{
            font-size: 10px;
            padding: 3px 6px;
            border: 1px solid #ccc;
            border-radius: 4px;
            width: 110px;
        }}
        .date-count {{
            font-size: 10px;
            color: #666;
            margin-left: 4px;
        }}
        /* View Mode Toggle (Logical/Physical) */
        .view-mode-section {{
            display: flex;
            align-items: center;
            gap: 4px;
        }}
        .view-mode-label {{
            font-size: 9px;
            font-weight: 600;
            color: #666;
            text-transform: uppercase;
        }}
        .view-mode-btn {{
            padding: 3px 10px;
            border: 1px solid #805ad5;
            background: white;
            color: #805ad5;
            font-weight: 600;
            font-size: 10px;
            cursor: pointer;
            transition: all 0.2s;
        }}
        .view-mode-btn:first-of-type {{
            border-radius: 4px 0 0 4px;
            border-right: none;
        }}
        .view-mode-btn:last-of-type {{
            border-radius: 0 4px 4px 0;
        }}
        .view-mode-btn.active {{
            background: #805ad5;
            color: white;
        }}
        .view-mode-btn:hover:not(.active) {{
            background: #f3e8ff;
        }}
        .view-mode-hidden {{
            display: none !important;
        }}
        /* Extended Features - v2.0 Styles */

        /* Search bar */
        .search-container {{
            display: flex;
            align-items: center;
            gap: 4px;
        }}
        #search-input {{
            font-size: 11px;
            padding: 4px 8px;
            border: 1px solid #ccc;
            border-radius: 4px;
            width: 150px;
            background: white;
        }}
        #search-input:focus {{
            outline: none;
            border-color: #3182ce;
            box-shadow: 0 0 0 2px rgba(49, 130, 206, 0.2);
        }}
        .search-results {{
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: white;
            border: 1px solid #ddd;
            border-radius: 4px;
            max-height: 200px;
            overflow-y: auto;
            z-index: 10001;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            display: none;
        }}
        .search-results.active {{
            display: block;
        }}
        .search-result-item {{
            padding: 8px 12px;
            cursor: pointer;
            border-bottom: 1px solid #eee;
            font-size: 11px;
        }}
        .search-result-item:hover {{
            background: #f0f7ff;
        }}
        .search-result-item:last-child {{
            border-bottom: none;
        }}
        .search-result-item .name {{
            font-weight: 500;
            color: #1a365d;
        }}
        .search-result-item .type {{
            font-size: 10px;
            color: #666;
        }}

        /* Time slider */
        .time-slider-container {{
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        #time-slider {{
            width: 120px;
            height: 4px;
            -webkit-appearance: none;
            background: #ddd;
            border-radius: 2px;
            cursor: pointer;
        }}
        #time-slider::-webkit-slider-thumb {{
            -webkit-appearance: none;
            width: 14px;
            height: 14px;
            background: #3182ce;
            border-radius: 50%;
            cursor: pointer;
        }}
        .time-display {{
            font-size: 10px;
            color: #666;
            min-width: 80px;
        }}
        .play-btn {{
            font-size: 12px;
            padding: 2px 8px;
            border: 1px solid #ccc;
            background: white;
            border-radius: 3px;
            cursor: pointer;
        }}
        .play-btn:hover {{
            background: #f0f0f0;
        }}
        .play-btn.playing {{
            background: #3182ce;
            color: white;
            border-color: #3182ce;
        }}

        /* Layout selector */
        .layout-select {{
            font-size: 10px;
            padding: 3px 6px;
            border: 1px solid #ccc;
            border-radius: 4px;
            background: white;
            cursor: pointer;
        }}

        /* Geometry selector */
        .geometry-chip {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 9px;
            cursor: pointer;
            padding: 3px 6px;
            border-radius: 3px;
            background: #f0f0f0;
            border: 1px solid #ddd;
            transition: all 0.15s;
        }}
        .geometry-chip:hover {{
            background: #e0e0e0;
        }}
        .geometry-chip.active {{
            background: #1a365d;
            color: white;
            border-color: #1a365d;
        }}

        /* VR button */
        .vr-btn {{
            padding: 4px 10px;
            border: 1px solid #805ad5;
            background: white;
            color: #805ad5;
            font-weight: 600;
            font-size: 10px;
            cursor: pointer;
            border-radius: 4px;
            transition: all 0.2s;
        }}
        .vr-btn:hover {{
            background: #805ad5;
            color: white;
        }}
        .vr-btn:disabled {{
            opacity: 0.5;
            cursor: not-allowed;
        }}

        /* Multi-select indicator */
        .selection-count {{
            font-size: 10px;
            color: #666;
            padding: 2px 8px;
            background: #e8f4fd;
            border-radius: 10px;
            display: none;
        }}
        .selection-count.active {{
            display: inline-block;
        }}

        /* Effects toggle */
        .effects-toggle {{
            display: flex;
            align-items: center;
            gap: 4px;
        }}
        .toggle-switch {{
            position: relative;
            width: 28px;
            height: 16px;
            background: #ccc;
            border-radius: 8px;
            cursor: pointer;
            transition: background 0.2s;
        }}
        .toggle-switch.active {{
            background: #3182ce;
        }}
        .toggle-switch::after {{
            content: '';
            position: absolute;
            top: 2px;
            left: 2px;
            width: 12px;
            height: 12px;
            background: white;
            border-radius: 50%;
            transition: left 0.2s;
        }}
        .toggle-switch.active::after {{
            left: 14px;
        }}
        .toggle-label {{
            font-size: 9px;
            color: #666;
        }}

        /* Path highlight animation */
        @keyframes pathPulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.5; }}
        }}

        /* Node pulse animation for recent items */
        @keyframes nodePulse {{
            0%, 100% {{ transform: scale(1); }}
            50% {{ transform: scale(1.2); }}
        }}

        /* Expand/collapse group indicator */
        .cluster-badge {{
            position: absolute;
            background: #1a365d;
            color: white;
            font-size: 9px;
            padding: 2px 6px;
            border-radius: 10px;
            pointer-events: none;
        }}

        /* Stats display */
        .stats-display {{
            font-size: 9px;
            color: #666;
            padding: 2px 6px;
            background: rgba(255,255,255,0.9);
            border-radius: 3px;
        }}

        /* Heat map legend */
        .heatmap-legend {{
            display: none;
            position: absolute;
            bottom: 20px;
            left: 20px;
            background: rgba(255,255,255,0.95);
            padding: 10px;
            border-radius: 6px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        }}
        .heatmap-legend.active {{
            display: block;
        }}
        .heatmap-gradient {{
            width: 150px;
            height: 12px;
            background: linear-gradient(to right, #3182ce, #38a169, #ecc94b, #e53e3e);
            border-radius: 2px;
            margin-bottom: 4px;
        }}
        .heatmap-labels {{
            display: flex;
            justify-content: space-between;
            font-size: 9px;
            color: #666;
        }}

        /* Toolbar extended section */
        .toolbar-extended {{
            position: absolute;
            top: 50px;
            left: 10px;
            background: rgba(255, 255, 255, 0.95);
            padding: 6px 10px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.3);
            z-index: 9999;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .toolbar-extended.hidden {{
            display: none;
        }}

        /* Overlay styles */
        .overlay-chip {{
            display: inline-flex;
            align-items: center;
            font-size: 10px;
            cursor: pointer;
            padding: 3px 8px;
            border-radius: 12px;
            background: #f0f0f0;
            border: 1px solid #ddd;
            transition: all 0.15s;
            white-space: nowrap;
        }}
        .overlay-chip:hover {{
            background: #e0e0e0;
        }}
        .overlay-chip.active {{
            border-width: 2px;
        }}
        .overlay-chip.active[data-overlay="projects"] {{
            background: rgba(255, 215, 0, 0.2);
            border-color: #ffd700;
            color: #8b6914;
        }}
        .overlay-chip.active[data-overlay="initiatives"] {{
            background: rgba(0, 255, 136, 0.2);
            border-color: #00ff88;
            color: #006633;
        }}
        .overlay-chip.active[data-overlay="dashboards"] {{
            background: rgba(255, 107, 107, 0.2);
            border-color: #ff6b6b;
            color: #8b0000;
        }}
        .overlay-chip .chip-icon {{
            margin-right: 4px;
            font-size: 11px;
        }}
        .overlay-chip .chip-count {{
            margin-left: 4px;
            font-size: 9px;
            background: rgba(0,0,0,0.1);
            padding: 1px 5px;
            border-radius: 8px;
        }}
        .overlay-chip.active .chip-count {{
            background: rgba(0,0,0,0.15);
        }}

        /* Overlay info in sidebar */
        .overlay-info-panel {{
            margin-bottom: 15px;
            padding: 12px;
            border-radius: 8px;
            background: #f8f9fa;
        }}
        .overlay-info-panel.project {{
            border-left: 4px solid #ffd700;
        }}
        .overlay-info-panel.initiative {{
            border-left: 4px solid #00ff88;
        }}
        .overlay-info-panel.dashboard {{
            border-left: 4px solid #ff6b6b;
        }}
        .overlay-info-panel h4 {{
            font-size: 12px;
            color: #1a365d;
            margin-bottom: 6px;
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .overlay-info-panel p {{
            font-size: 11px;
            color: #666;
            margin-bottom: 4px;
        }}
        .overlay-meta {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 6px;
            font-size: 10px;
            color: #888;
        }}
        .overlay-meta span {{
            background: rgba(0,0,0,0.05);
            padding: 2px 6px;
            border-radius: 4px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div id="graph-wrapper">
            <div id="graph"></div>
            <div id="toolbar">
                <div class="toolbar-section">
                    <button class="view-btn active" id="btn-3d" onclick="setView('3d')">3D</button>
                    <button class="view-btn" id="btn-2d" onclick="setView('2d')">2D</button>
                </div>
                <div class="toolbar-divider"></div>
                <div class="toolbar-section">
                    <span class="toolbar-label collapsed" onclick="toggleFilterSection('nodes')">Nodes <span class="arrow">▼</span></span>
                    <div class="filter-group collapsed" id="nodes-filters">
                        {node_chips_html}
                        <button class="mini-btn" onclick="toggleAllNodes()">Toggle</button>
                    </div>
                </div>
                <div class="toolbar-divider"></div>
                <div class="toolbar-section">
                    <span class="toolbar-label collapsed" onclick="toggleFilterSection('edges')">Edges <span class="arrow">▼</span></span>
                    <div class="filter-group collapsed" id="edges-filters">
                        {edge_chips_html}
                        <button class="mini-btn" onclick="toggleAllEdges()">Toggle</button>
                    </div>
                </div>
                <div class="toolbar-divider"></div>
                <div class="toolbar-section">
                    <span class="toolbar-label" onclick="toggleFilterSection('dates')">Date <span class="arrow">▼</span></span>
                    <div class="filter-group" id="dates-filters">
                        <select id="date-preset" class="date-select" onchange="applyDatePreset()">
                            <option value="all">All Time</option>
                            <option value="7d">Last 7 Days</option>
                            <option value="30d">Last 30 Days</option>
                            <option value="90d">Last 90 Days</option>
                            <option value="custom">Custom Range</option>
                        </select>
                        <input type="date" id="date-from" class="date-input" style="display:none" onchange="applyCustomDateFilter()">
                        <input type="date" id="date-to" class="date-input" style="display:none" onchange="applyCustomDateFilter()">
                        <span id="date-count" class="date-count"></span>
                    </div>
                </div>
                {view_mode_toggle_html}
            </div>
            <!-- Extended Toolbar (v2.0 Features) -->
            <div id="toolbar-extended" class="toolbar-extended">
                <!-- Search -->
                <div class="toolbar-section search-container" style="position: relative;">
                    <input type="text" id="search-input" placeholder="Search nodes..." onkeyup="handleSearch(event)" onfocus="showSearchResults()" onblur="hideSearchResults()">
                    <div id="search-results" class="search-results"></div>
                </div>
                <div class="toolbar-divider"></div>
                <!-- Layout selector -->
                <div class="toolbar-section">
                    <span class="toolbar-label" style="background: transparent; cursor: default;">Layout:</span>
                    <select id="layout-select" class="layout-select" onchange="changeLayout()">
                        <option value="force">Force-Directed</option>
                        <option value="layered">Layered 3D</option>
                        <option value="spherical">Spherical</option>
                        <option value="cylinder">Cylinder</option>
                    </select>
                </div>
                <div class="toolbar-divider"></div>
                <!-- Node geometry -->
                <div class="toolbar-section">
                    <span class="toolbar-label" style="background: transparent; cursor: default;">Shape:</span>
                    <span class="geometry-chip active" data-geometry="sphere" onclick="setNodeGeometry('sphere')">●</span>
                    <span class="geometry-chip" data-geometry="cube" onclick="setNodeGeometry('cube')">■</span>
                    <span class="geometry-chip" data-geometry="octahedron" onclick="setNodeGeometry('octahedron')">◆</span>
                    <span class="geometry-chip" data-geometry="ring" onclick="setNodeGeometry('ring')">○</span>
                </div>
                <div class="toolbar-divider"></div>
                <!-- Effects toggles -->
                <div class="toolbar-section effects-toggle">
                    <span class="toggle-label">Glow</span>
                    <div id="glow-toggle" class="toggle-switch" onclick="toggleGlow()"></div>
                </div>
                <div class="toolbar-section effects-toggle">
                    <span class="toggle-label">Particles</span>
                    <div id="particles-toggle" class="toggle-switch" onclick="toggleParticles()"></div>
                </div>
                <div class="toolbar-section effects-toggle">
                    <span class="toggle-label">Labels</span>
                    <div id="labels-toggle" class="toggle-switch active" onclick="toggleLabels()"></div>
                </div>
                <div class="toolbar-section effects-toggle">
                    <span class="toggle-label">Light</span>
                    <div id="theme-toggle" class="toggle-switch" onclick="toggleTheme()"></div>
                </div>
                <div class="toolbar-section effects-toggle">
                    <span class="toggle-label">Rings</span>
                    <div id="rings-toggle" class="toggle-switch active" onclick="toggleRings()"></div>
                </div>
                <div class="toolbar-section effects-toggle">
                    <span class="toggle-label">Logos</span>
                    <div id="logo-labels-toggle" class="toggle-switch active" onclick="toggleLogoLabels()"></div>
                </div>
                <div class="toolbar-divider"></div>
                <!-- Overlays -->
                <div class="toolbar-section">
                    <span class="toolbar-label" style="background: transparent; cursor: default;">Overlays:</span>
                    <span class="overlay-chip" data-overlay="projects" onclick="toggleOverlay('projects')">
                        <span class="chip-icon">&#128203;</span>Projects<span class="chip-count" id="projects-count">0</span>
                    </span>
                    <span class="overlay-chip" data-overlay="initiatives" onclick="toggleOverlay('initiatives')">
                        <span class="chip-icon">&#127919;</span>Initiatives<span class="chip-count" id="initiatives-count">0</span>
                    </span>
                    <span class="overlay-chip" data-overlay="dashboards" onclick="toggleOverlay('dashboards')">
                        <span class="chip-icon">&#128202;</span>Dashboards<span class="chip-count" id="dashboards-count">0</span>
                    </span>
                </div>
                <div class="toolbar-divider"></div>
                <!-- Multi-select indicator -->
                <span id="selection-count" class="selection-count">0 selected</span>
                <!-- VR button -->
                <button id="vr-btn" class="vr-btn" onclick="enterVR()" disabled>VR</button>
                <!-- Stats -->
                <span id="stats-display" class="stats-display"></span>
            </div>
            <!-- Time slider (for temporal data) -->
            <div id="time-toolbar" class="toolbar-extended" style="top: 90px; display: none;">
                <div class="toolbar-section time-slider-container">
                    <span class="toolbar-label" style="background: transparent; cursor: default;">Time:</span>
                    <button id="play-btn" class="play-btn" onclick="toggleTimePlay()">▶</button>
                    <input type="range" id="time-slider" min="0" max="100" value="100" oninput="updateTimeSlider()">
                    <span id="time-display" class="time-display">All time</span>
                </div>
            </div>
            <!-- Heat map legend -->
            <div id="heatmap-legend" class="heatmap-legend">
                <div class="heatmap-gradient"></div>
                <div class="heatmap-labels">
                    <span>Low</span>
                    <span>High</span>
                </div>
            </div>
        </div>
        <button id="sidebar-toggle" onclick="toggleSidebar()">◀</button>
        <div id="sidebar">
            <div class="header">
                <h1>{title}</h1>
                <p>{description}</p>
            </div>
            <div id="info-panel">
                <div class="info-placeholder" id="placeholder">
                    <p><strong>Select a node</strong></p>
                    <p>Click on any node in the graph to see details and navigate to connected items.</p>
                    <p style="margin-top: 20px; font-size: 11px; color: #999;">Drag to rotate • Scroll to zoom • Right-drag to pan</p>
                </div>
                <div class="node-info" id="node-info">
                    <div class="node-header">
                        <img id="node-logo" class="node-logo" src="" alt="">
                        <div class="node-header-text">
                            <div class="node-title" id="node-title"></div>
                            <div class="node-tier" id="node-tier"></div>
                        </div>
                    </div>
                    <div class="node-meta" id="node-meta"></div>
                    <div class="node-description" id="node-description"></div>
                    <button class="view-full-btn" id="view-full-btn" onclick="showFullContent()">View Full Content</button>
                    <div class="connections-header">Connected Nodes</div>
                    <ul class="connection-list" id="connections"></ul>
                    <div id="overlay-info-container" style="margin-top: 15px;"></div>
                </div>
            </div>
        </div>
    </div>

    <!-- Full Content Modal -->
    <div class="modal-overlay" id="content-modal" onclick="closeModal(event)">
        <div class="modal-content" onclick="event.stopPropagation()">
            <div class="modal-header">
                <div class="modal-header-content">
                    <img id="modal-logo" class="modal-logo" src="" alt="" style="display:none;">
                    <div>
                        <h2 id="modal-title">Node Details</h2>
                        <span id="modal-tier-badge" class="modal-tier-badge"></span>
                    </div>
                </div>
                <button class="modal-close" onclick="closeModal()">&times;</button>
            </div>
            <div class="modal-body">
                <div class="modal-section">
                    <div class="modal-section-title">Description</div>
                    <div class="full-content" id="modal-content"></div>
                </div>
                <div class="modal-section" id="modal-details-section">
                    <div class="modal-section-title">Details</div>
                    <div class="modal-detail-grid" id="modal-details"></div>
                </div>
                <div class="modal-section" id="modal-connections-section">
                    <div class="modal-section-title">Connected Nodes</div>
                    <div class="modal-connections" id="modal-connections"></div>
                </div>
            </div>
            <div class="modal-meta" id="modal-meta"></div>
        </div>
    </div>

    <script>
        // Data
        const nodesData = {nodes_json};
        const linksData = {links_json};
        const groupsData = {groups_json};
        const physicalGroupsData = {physical_groups_json};

        // View mode state (logical or physical)
        let currentViewMode = 'logical';

        // Theme state (dark or light)
        let currentTheme = 'dark';

        // Create node lookup map
        const nodeMap = {{}};
        nodesData.forEach(node => {{
            nodeMap[node.id] = node;
        }});

        // Create link lookup for connections
        const linksByNode = {{}};
        linksData.forEach(link => {{
            const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
            const targetId = typeof link.target === 'object' ? link.target.id : link.target;

            if (!linksByNode[sourceId]) linksByNode[sourceId] = [];
            if (!linksByNode[targetId]) linksByNode[targetId] = [];

            linksByNode[sourceId].push({{ nodeId: targetId, relationType: link.relationType }});
            linksByNode[targetId].push({{ nodeId: sourceId, relationType: link.relationType }});
        }});

        // Graph data
        const graphData = {{
            nodes: nodesData,
            links: linksData
        }};

        let graph;
        let selectedNode = null;
        let sidebarVisible = true;
        const highlightedNodes = new Set();

        // Overlay state
        let overlayData = {{ projects: [], initiatives: [], dashboards: [] }};
        let activeOverlays = {{ projects: false, initiatives: false, dashboards: false }};

        // Load overlay data from API
        async function loadOverlayData() {{
            try {{
                const [projectsRes, initiativesRes, dashboardsRes] = await Promise.all([
                    fetch('/api/overlays/projects').catch(() => ({{ json: () => ({{ items: [] }}) }})),
                    fetch('/api/overlays/initiatives').catch(() => ({{ json: () => ({{ items: [] }}) }})),
                    fetch('/api/overlays/dashboards').catch(() => ({{ json: () => ({{ items: [] }}) }}))
                ]);
                const projects = await projectsRes.json();
                const initiatives = await initiativesRes.json();
                const dashboards = await dashboardsRes.json();
                overlayData.projects = projects.items || [];
                overlayData.initiatives = initiatives.items || [];
                overlayData.dashboards = dashboards.items || [];
                document.getElementById('projects-count').textContent = overlayData.projects.length;
                document.getElementById('initiatives-count').textContent = overlayData.initiatives.length;
                document.getElementById('dashboards-count').textContent = overlayData.dashboards.length;
                console.log('[Athena] Overlay data loaded:', overlayData.projects.length, 'projects');
            }} catch (error) {{
                console.log('[Athena] Overlay API not available');
            }}
        }}

        function toggleOverlay(overlayType) {{
            activeOverlays[overlayType] = !activeOverlays[overlayType];
            const chip = document.querySelector(`.overlay-chip[data-overlay="${{overlayType}}"]`);
            if (chip) chip.classList.toggle('active', activeOverlays[overlayType]);
            updateGraphColors();
        }}

        function getNodeOverlays(nodeId) {{
            const result = [];
            if (activeOverlays.projects) {{
                overlayData.projects.forEach(p => {{
                    if (p.affected_nodes && p.affected_nodes.includes(nodeId)) result.push({{ type: 'project', data: p }});
                }});
            }}
            if (activeOverlays.initiatives) {{
                overlayData.initiatives.forEach(i => {{
                    if (i.affected_nodes && i.affected_nodes.includes(nodeId)) result.push({{ type: 'initiative', data: i }});
                }});
            }}
            if (activeOverlays.dashboards) {{
                overlayData.dashboards.forEach(d => {{
                    if (d.data_sources && d.data_sources.includes(nodeId)) result.push({{ type: 'dashboard', data: d }});
                }});
            }}
            return result;
        }}

        function updateGraphColors() {{
            if (!graph) return;
            graph.nodeColor(node => {{
                const overlays = getNodeOverlays(node.id);
                if (overlays.length > 0) {{
                    if (overlays.some(o => o.type === 'project')) return '#ffd700';
                    if (overlays.some(o => o.type === 'initiative')) return '#00ff88';
                    if (overlays.some(o => o.type === 'dashboard')) return '#ff6b6b';
                }}
                return node.color;
            }});
        }}

        function renderOverlayInfo(nodeId) {{
            const container = document.getElementById('overlay-info-container');
            if (!container) return;
            container.innerHTML = '';
            const overlays = getNodeOverlays(nodeId);
            if (overlays.length === 0) {{ container.style.display = 'none'; return; }}
            container.style.display = 'block';
            overlays.forEach(o => {{
                let html = '';
                if (o.type === 'project') {{
                    html = `<div class="overlay-info-panel project"><h4>&#128203; ${{o.data.name}}</h4><p>Status: ${{o.data.status}}</p><div class="overlay-meta"><span>Jira: ${{o.data.jira_key || 'N/A'}}</span><span>Hours: ${{o.data.hours_spent || 0}}</span><span>Due: ${{o.data.due_date || 'TBD'}}</span></div></div>`;
                }} else if (o.type === 'initiative') {{
                    html = `<div class="overlay-info-panel initiative"><h4>&#127919; ${{o.data.name}}</h4><p>${{o.data.dimension || ''}} - ${{o.data.status}}</p></div>`;
                }} else if (o.type === 'dashboard') {{
                    html = `<div class="overlay-info-panel dashboard"><h4>&#128202; ${{o.data.name}}</h4><p>Client: ${{o.data.client}}</p></div>`;
                }}
                container.innerHTML += html;
            }});
        }}

        loadOverlayData();

        // Track current graph data ourselves since graphData() getter is unreliable
        let currentGraphData = {{ nodes: [], links: [] }};

        function getGraphNodes() {{
            return currentGraphData.nodes || [];
        }}

        function getGraphLinks() {{
            return currentGraphData.links || [];
        }}

        // Wrapper to set graph data and track it
        function setGraphData(data) {{
            currentGraphData = data;
            if (graph) {{
                graph.graphData(data);
            }}
        }}

        // Click handling - immediate selection, double-click for zoom
        let lastClickTime = 0;
        let lastClickNode = null;
        const DOUBLE_CLICK_DELAY = 300;

        function handleNodeClick(node) {{
            console.log('[Athena] handleNodeClick called:', node ? node.name : 'null');
            const now = Date.now();

            // Always select immediately on click
            selectNodeOnly(node);

            // Check for double-click (zoom in)
            if (lastClickNode === node && (now - lastClickTime) < DOUBLE_CLICK_DELAY) {{
                focusNodeIn2D(node);
            }}

            lastClickNode = node;
            lastClickTime = now;
        }}

        // Track which groups (nodes) are visible - initialize from data
        const allGroups = Object.keys(groupsData);
        const visibleGroups = new Set(allGroups);

        // Track which edge types are visible
        const allEdgeTypes = [...new Set(linksData.map(l => l.edgeType))];
        const visibleEdgeTypes = new Set(allEdgeTypes);

        // Attach event listeners to node filter chips
        document.querySelectorAll('.filter-chip[data-group]').forEach(chip => {{
            chip.addEventListener('click', function() {{
                const group = this.dataset.group;
                if (visibleGroups.has(group)) {{
                    visibleGroups.delete(group);
                    this.classList.remove('active');
                }} else {{
                    visibleGroups.add(group);
                    this.classList.add('active');
                }}
                applyFilters();
            }});
        }});

        // Attach event listeners to edge filter chips
        document.querySelectorAll('.filter-chip[data-edge-type]').forEach(chip => {{
            chip.addEventListener('click', function() {{
                const edgeType = this.dataset.edgeType;
                if (visibleEdgeTypes.has(edgeType)) {{
                    visibleEdgeTypes.delete(edgeType);
                    this.classList.remove('active');
                }} else {{
                    visibleEdgeTypes.add(edgeType);
                    this.classList.add('active');
                }}
                applyFilters();
            }});
        }});

        function toggleAllNodes() {{
            const allVisible = allGroups.every(g => visibleGroups.has(g));
            if (allVisible) {{
                visibleGroups.clear();
            }} else {{
                allGroups.forEach(g => visibleGroups.add(g));
            }}
            updateNodeChips();
            applyFilters();
        }}

        function toggleAllEdges() {{
            const allVisible = allEdgeTypes.every(e => visibleEdgeTypes.has(e));
            if (allVisible) {{
                visibleEdgeTypes.clear();
            }} else {{
                allEdgeTypes.forEach(e => visibleEdgeTypes.add(e));
            }}
            updateEdgeChips();
            applyFilters();
        }}

        function updateNodeChips() {{
            document.querySelectorAll('.filter-chip[data-group]').forEach(chip => {{
                const group = chip.dataset.group;
                chip.classList.toggle('active', visibleGroups.has(group));
            }});
        }}

        function updateEdgeChips() {{
            document.querySelectorAll('.filter-chip[data-edge-type]').forEach(chip => {{
                const edgeType = chip.dataset.edgeType;
                chip.classList.toggle('active', visibleEdgeTypes.has(edgeType));
            }});
        }}

        // Date filter state
        let dateFilterFrom = null;
        let dateFilterTo = null;

        function applyDatePreset() {{
            const preset = document.getElementById('date-preset').value;
            const fromInput = document.getElementById('date-from');
            const toInput = document.getElementById('date-to');

            if (preset === 'custom') {{
                fromInput.style.display = 'inline-block';
                toInput.style.display = 'inline-block';
                // Set defaults to last 30 days
                const today = new Date();
                const thirtyDaysAgo = new Date(today);
                thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
                toInput.value = today.toISOString().split('T')[0];
                fromInput.value = thirtyDaysAgo.toISOString().split('T')[0];
                applyCustomDateFilter();
                return;
            }}

            fromInput.style.display = 'none';
            toInput.style.display = 'none';

            if (preset === 'all') {{
                dateFilterFrom = null;
                dateFilterTo = null;
            }} else {{
                const days = parseInt(preset);
                const today = new Date();
                const fromDate = new Date(today);
                fromDate.setDate(fromDate.getDate() - days);
                dateFilterFrom = fromDate;
                dateFilterTo = today;
            }}

            applyFilters();
        }}

        function applyCustomDateFilter() {{
            const fromInput = document.getElementById('date-from');
            const toInput = document.getElementById('date-to');

            if (fromInput.value) {{
                dateFilterFrom = new Date(fromInput.value);
                dateFilterFrom.setHours(0, 0, 0, 0);
            }} else {{
                dateFilterFrom = null;
            }}

            if (toInput.value) {{
                dateFilterTo = new Date(toInput.value);
                dateFilterTo.setHours(23, 59, 59, 999);
            }} else {{
                dateFilterTo = null;
            }}

            applyFilters();
        }}

        function nodePassesDateFilter(node) {{
            // Hub node always passes
            if (node.id === 'zeus-memory-hub' || !node.createdAt) {{
                return dateFilterFrom === null && dateFilterTo === null ? true : !node.createdAt;
            }}

            const nodeDate = new Date(node.createdAt);

            if (dateFilterFrom && nodeDate < dateFilterFrom) {{
                return false;
            }}
            if (dateFilterTo && nodeDate > dateFilterTo) {{
                return false;
            }}
            return true;
        }}

        function applyFilters() {{
            // Filter nodes by group AND date
            const filteredNodes = nodesData.filter(node => {{
                let groupVisible;
                if (currentViewMode === 'physical' && node.physicalGroup) {{
                    // In physical view mode, filter by physical groups
                    groupVisible = visiblePhysicalGroups.has(node.physicalGroup);
                }} else {{
                    // In logical view mode, filter by logical groups
                    groupVisible = visibleGroups.has(node.group);
                }}
                const dateVisible = nodePassesDateFilter(node);
                return groupVisible && dateVisible;
            }});
            const filteredNodeIds = new Set(filteredNodes.map(n => n.id));

            // Filter links by node visibility AND edge type
            const filteredLinks = linksData.filter(link => {{
                const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
                const targetId = typeof link.target === 'object' ? link.target.id : link.target;
                const nodeVisible = filteredNodeIds.has(sourceId) && filteredNodeIds.has(targetId);
                const edgeVisible = visibleEdgeTypes.has(link.edgeType);
                return nodeVisible && edgeVisible;
            }});

            // Update count display
            const countEl = document.getElementById('date-count');
            const nodesWithDates = nodesData.filter(n => n.createdAt).length;
            if (dateFilterFrom || dateFilterTo) {{
                countEl.textContent = `(${{filteredNodes.length}} nodes)`;
            }} else {{
                countEl.textContent = '';
            }}

            setGraphData({{
                nodes: filteredNodes,
                links: filteredLinks
            }});
        }}

        // View toggle
        let currentView = '3d';

        function setView(view) {{
            currentView = view;
            document.getElementById('btn-3d').classList.toggle('active', view === '3d');
            document.getElementById('btn-2d').classList.toggle('active', view === '2d');

            if (view === '2d') {{
                graph.numDimensions(2);
                graph.cameraPosition({{ x: 0, y: 0, z: 500 }}, {{ x: 0, y: 0, z: 0 }}, 1000);
            }} else {{
                graph.numDimensions(3);
            }}
        }}

        // View mode toggle (Logical/Physical)
        function setViewMode(mode) {{
            currentViewMode = mode;
            const logicalBtn = document.getElementById('btn-logical');
            const physicalBtn = document.getElementById('btn-physical');
            if (logicalBtn) logicalBtn.classList.toggle('active', mode === 'logical');
            if (physicalBtn) physicalBtn.classList.toggle('active', mode === 'physical');

            // Update node colors based on view mode
            const nodes = getGraphNodes();
            nodes.forEach(node => {{
                if (mode === 'physical' && node.physicalGroupColor) {{
                    node.color = node.physicalGroupColor;
                }} else {{
                    // Restore original logical color from groupsData
                    const groupInfo = groupsData[node.group];
                    node.color = groupInfo ? groupInfo.color : '#888888';
                }}
            }});

            // Update filter chips visibility and content
            updateFilterChipsForViewMode(mode);

            // Re-render the graph
            if (graph) {{
                graph.nodeColor(node => node.color);
            }}
        }}

        // Update filter chips based on view mode
        function updateFilterChipsForViewMode(mode) {{
            const nodesFiltersContainer = document.getElementById('nodes-filters');
            if (!nodesFiltersContainer) return;

            // Get existing chips
            const existingChips = nodesFiltersContainer.querySelectorAll('.filter-chip[data-group]');
            const toggleBtn = nodesFiltersContainer.querySelector('.mini-btn');

            if (mode === 'physical' && Object.keys(physicalGroupsData).length > 0) {{
                // Hide logical chips, show physical chips
                existingChips.forEach(chip => chip.classList.add('view-mode-hidden'));

                // Remove any existing physical chips
                nodesFiltersContainer.querySelectorAll('.filter-chip[data-physical-group]').forEach(c => c.remove());

                // Create physical group chips
                Object.entries(physicalGroupsData).forEach(([groupId, groupInfo]) => {{
                    const chip = document.createElement('span');
                    chip.className = 'filter-chip active';
                    chip.dataset.physicalGroup = groupId;
                    chip.innerHTML = `<span class="chip-color" style="background:${{groupInfo.color}}"></span>${{groupInfo.label}}`;
                    chip.addEventListener('click', function() {{
                        togglePhysicalGroupFilter(groupId, this);
                    }});
                    nodesFiltersContainer.insertBefore(chip, toggleBtn);
                }});
            }} else {{
                // Show logical chips, hide physical chips
                existingChips.forEach(chip => chip.classList.remove('view-mode-hidden'));
                nodesFiltersContainer.querySelectorAll('.filter-chip[data-physical-group]').forEach(c => c.remove());
            }}
        }}

        // Track visible physical groups
        const visiblePhysicalGroups = new Set(Object.keys(physicalGroupsData));

        function togglePhysicalGroupFilter(groupId, chip) {{
            if (visiblePhysicalGroups.has(groupId)) {{
                visiblePhysicalGroups.delete(groupId);
                chip.classList.remove('active');
            }} else {{
                visiblePhysicalGroups.add(groupId);
                chip.classList.add('active');
            }}
            applyFilters();
        }}

        // Toggle filter sections
        function toggleFilterSection(section) {{
            const label = document.querySelector(`.toolbar-label[onclick*="${{section}}"]`);
            const group = document.getElementById(`${{section}}-filters`);
            label.classList.toggle('collapsed');
            group.classList.toggle('collapsed');
        }}

        // Toggle sidebar visibility
        function toggleSidebar() {{
            sidebarVisible = !sidebarVisible;
            const sidebar = document.getElementById('sidebar');
            const toggle = document.getElementById('sidebar-toggle');

            if (sidebarVisible) {{
                sidebar.classList.remove('hidden');
                toggle.classList.remove('sidebar-hidden');
                toggle.textContent = '▶';
            }} else {{
                sidebar.classList.add('hidden');
                toggle.classList.add('sidebar-hidden');
                toggle.textContent = '◀';
            }}

            // Resize graph after animation
            setTimeout(() => {{
                const wrapper = document.getElementById('graph-wrapper');
                graph.width(wrapper.offsetWidth).height(wrapper.offsetHeight);
            }}, 350);
        }}

        // Initialize graph
        function initGraph() {{
            const container = document.getElementById('graph');
            const wrapper = document.getElementById('graph-wrapper');

            const width = wrapper.offsetWidth;
            const height = wrapper.offsetHeight;

            console.log('[Athena] Initializing ForceGraph3D');
            // Initialize our tracking variable with the initial data
            currentGraphData = graphData;
            graph = ForceGraph3D()(container)
                .width(width)
                .height(height)
                .graphData(graphData)
                .backgroundColor('#0a0a1a')
                .nodeLabel(node => node.name)
                .nodeVal(node => Math.max(node.val / 5, 2))
                .nodeRelSize(6)
                .nodeColor(node => node.color)
                .linkColor(link => link.color)
                .linkWidth(link => link.width)
                .linkOpacity(0.6)
                .onNodeClick(node => {{
                    console.log('[Athena] onNodeClick fired:', node ? node.name : 'null');
                    handleNodeClick(node);
                }})
                .onBackgroundClick(() => {{
                    clearSelection();
                }})
                .enableNodeDrag(true)
                .onNodeDragEnd(node => {{
                    node.fx = node.x;
                    node.fy = node.y;
                    node.fz = node.z;
                }})
                .enableNavigationControls(true);

            // Set initial camera position
            setTimeout(() => {{
                graph.cameraPosition({{ x: 0, y: 0, z: 500 }});
            }}, 100);

            // Disable default double-click zoom on background
            const rendererEl = graph.renderer().domElement;
            rendererEl.addEventListener('dblclick', (e) => {{
                e.stopPropagation();
            }}, true);

            // Handle window resize
            window.addEventListener('resize', () => {{
                const newWidth = wrapper.offsetWidth;
                const newHeight = wrapper.offsetHeight;
                graph.width(newWidth).height(newHeight);
            }});

            // Apply labels after graph is ready
            setTimeout(() => {{
                if (logoLabelsEnabled) {{
                    applyLogoLabelRendering();
                }}
            }}, 500);
        }}

        // Show full content in modal
        function showFullContent() {{
            if (!selectedNode) return;

            // Set title and logo
            document.getElementById('modal-title').textContent = selectedNode.name;
            const modalLogo = document.getElementById('modal-logo');
            if (selectedNode.logo) {{
                modalLogo.src = selectedNode.logo;
                modalLogo.style.display = 'block';
            }} else {{
                modalLogo.style.display = 'none';
            }}

            // Set tier badge
            const tierBadge = document.getElementById('modal-tier-badge');
            tierBadge.textContent = selectedNode.groupLabel || selectedNode.group;
            tierBadge.style.background = selectedNode.color;

            // Set description
            document.getElementById('modal-content').textContent = selectedNode.description || 'No description available.';

            // Build details grid
            const detailsGrid = document.getElementById('modal-details');
            const detailsSection = document.getElementById('modal-details-section');
            let detailsHtml = '';

            // Add node type detail
            detailsHtml += `
                <div class="modal-detail-item">
                    <div class="detail-label">Node Type</div>
                    <div class="detail-value">${{selectedNode.groupLabel || selectedNode.group}}</div>
                </div>
            `;

            // Add tier detail
            detailsHtml += `
                <div class="modal-detail-item">
                    <div class="detail-label">Tier Level</div>
                    <div class="detail-value">Tier ${{selectedNode.tier}}</div>
                </div>
            `;

            // Add ID detail
            detailsHtml += `
                <div class="modal-detail-item">
                    <div class="detail-label">Node ID</div>
                    <div class="detail-value">${{selectedNode.id}}</div>
                </div>
            `;

            // Add size/importance detail
            detailsHtml += `
                <div class="modal-detail-item">
                    <div class="detail-label">Relative Size</div>
                    <div class="detail-value">${{selectedNode.val || 20}}</div>
                </div>
            `;

            detailsGrid.innerHTML = detailsHtml;
            detailsSection.style.display = detailsHtml ? 'block' : 'none';

            // Build connections section
            const connectionsEl = document.getElementById('modal-connections');
            const connectionsSection = document.getElementById('modal-connections-section');
            const connections = linksByNode[selectedNode.id] || [];

            if (connections.length > 0) {{
                let connectionsHtml = '';
                connections.forEach(conn => {{
                    const connNode = nodeMap[conn.nodeId];
                    if (!connNode) return;
                    connectionsHtml += `
                        <span class="modal-conn-chip" onclick="navigateToNodeFromModal('${{conn.nodeId}}')">
                            ${{connNode.name}}
                            <span class="conn-type">${{conn.relationType}}</span>
                        </span>
                    `;
                }});
                connectionsEl.innerHTML = connectionsHtml;
                connectionsSection.style.display = 'block';
            }} else {{
                connectionsSection.style.display = 'none';
            }}

            // Set footer meta
            document.getElementById('modal-meta').innerHTML = `
                <span><span class="label">Full ID:</span> ${{selectedNode.id}}</span>
                <span><span class="label">Group:</span> ${{selectedNode.group}}</span>
                <span><span class="label">Connections:</span> ${{connections.length}}</span>
            `;

            document.getElementById('content-modal').classList.add('active');
        }}

        // Navigate to node from modal and close modal
        function navigateToNodeFromModal(nodeId) {{
            closeModal();
            setTimeout(() => {{
                navigateToNode(nodeId);
            }}, 100);
        }}

        // Close modal
        function closeModal(event) {{
            if (!event || event.target === event.currentTarget) {{
                document.getElementById('content-modal').classList.remove('active');
            }}
        }}

        // Close modal on Escape key
        document.addEventListener('keydown', function(e) {{
            if (e.key === 'Escape') {{
                closeModal();
            }}
        }});

        // Navigate to a node by ID (works even if filtered out)
        function navigateToNode(nodeId) {{
            console.log('navigateToNode called with:', nodeId);

            // First check if node is in current graph view
            const currentNodes = getGraphNodes();
            let targetNode = currentNodes.find(n => n.id === nodeId);
            console.log('Found in current view:', !!targetNode, 'total nodes:', currentNodes.length);

            // If not found in filtered view, get from full node list
            if (!targetNode) {{
                targetNode = nodeMap[nodeId];
                if (targetNode) {{
                    // Make sure the node's group is visible
                    visibleGroups.add(targetNode.group);
                    updateNodeChips();
                    applyFilters();
                    // Wait for simulation to position the node, then navigate
                    setTimeout(() => {{
                        const updatedNodes = getGraphNodes();
                        targetNode = updatedNodes.find(n => n.id === nodeId);
                        if (targetNode) {{
                            selectNodeOnly(targetNode);
                            // Pan to the node (use 0,0,0 if position not yet set)
                            const x = targetNode.x || 0;
                            const y = targetNode.y || 0;
                            graph.cameraPosition(
                                {{ x: x, y: y, z: 300 }},
                                {{ x: x, y: y, z: 0 }},
                                500
                            );
                        }}
                    }}, 300);
                    return;
                }}
            }}

            if (targetNode) {{
                selectNodeOnly(targetNode);
                // Pan to the node
                graph.cameraPosition(
                    {{ x: targetNode.x || 0, y: targetNode.y || 0, z: 300 }},
                    targetNode,
                    500
                );
            }}
        }}

        // Single click - just select and populate sidebar
        function selectNodeOnly(node) {{
            console.log('[Athena] selectNodeOnly called for:', node.name);
            selectedNode = node;

            // Post message to parent window (for embed mode)
            console.log('[Athena] window.parent !== window:', window.parent !== window);
            if (window.parent !== window) {{
                console.log('[Athena] Sending postMessage to parent');
                window.parent.postMessage({{
                    type: 'nodeSelected',
                    node: {{
                        id: node.id,
                        name: node.name,
                        description: node.description,
                        group: node.group,
                        groupLabel: node.groupLabel,
                        tier: node.tier,
                        color: node.color,
                        logo: node.logo
                    }}
                }}, '*');
                console.log('[Athena] postMessage sent');
            }}

            // Update highlighted nodes
            highlightedNodes.clear();
            highlightedNodes.add(node.id);
            (linksByNode[node.id] || []).forEach(conn => {{
                highlightedNodes.add(conn.nodeId);
            }});

            // Update sidebar
            document.getElementById('placeholder').style.display = 'none';
            document.getElementById('node-info').classList.add('active');
            document.getElementById('node-title').textContent = node.name;

            // Set description (truncated in sidebar, full in modal)
            const descEl = document.getElementById('node-description');
            const fullDesc = node.description || 'No description available.';
            // Show truncated preview in sidebar
            descEl.textContent = fullDesc.length > 300 ? fullDesc.substring(0, 300) + '...' : fullDesc;

            // Show/hide view full button based on content length
            const viewFullBtn = document.getElementById('view-full-btn');
            // Always show View Full Content button to access detailed popup
            viewFullBtn.style.display = 'inline-block';

            // Show metadata
            const metaEl = document.getElementById('node-meta');
            metaEl.innerHTML = `
                <span><span class="label">ID:</span> ${{node.id.substring(0, 8)}}...</span>
                <span><span class="label">Type:</span> ${{node.groupLabel || node.group}}</span>
            `;

            // Show logo if available
            const logoEl = document.getElementById('node-logo');
            logoEl.src = node.logo || '';
            logoEl.style.display = node.logo ? 'block' : 'none';

            // Set tier badge using group label
            const tierEl = document.getElementById('node-tier');
            tierEl.textContent = node.groupLabel || 'Unknown';
            tierEl.style.background = node.color;
            tierEl.className = 'node-tier';

            // Build connections list
            const connections = linksByNode[node.id] || [];
            const connectionsList = document.getElementById('connections');
            connectionsList.innerHTML = '';

            connections.forEach(conn => {{
                const connNode = nodeMap[conn.nodeId];
                if (!connNode) return;

                const li = document.createElement('li');
                li.className = 'connection-item';
                const logoHtml = connNode.logo ? `<img class="conn-logo" src="${{connNode.logo}}" alt="">` : '';
                li.innerHTML = `
                    ${{logoHtml}}
                    <div class="conn-info">
                        <div class="name">${{connNode.name}}</div>
                        <div class="relation">${{conn.relationType}}</div>
                    </div>
                `;
                li.onclick = function(e) {{
                    console.log('Connection clicked:', conn.nodeId, connNode.name);
                    e.preventDefault();
                    e.stopPropagation();
                    navigateToNode(conn.nodeId);
                }};
                connectionsList.appendChild(li);
            }});

            // Render overlay info for this node
            renderOverlayInfo(node.id);

            // Update visuals - highlight connected, dim others
            graph
                .nodeColor(n => highlightedNodes.has(n.id) ? n.color : '#333333')
                .linkColor(l => {{
                    const sId = typeof l.source === 'object' ? l.source.id : l.source;
                    const tId = typeof l.target === 'object' ? l.target.id : l.target;
                    return (sId === node.id || tId === node.id) ? l.color : '#222222';
                }});
        }}

        // Double click - switch to 2D, zoom in, show direct connections
        function focusNodeIn2D(node) {{
            // First select the node
            selectNodeOnly(node);

            // Switch to 2D view
            setView('2d');

            // Zoom in on node after short delay for 2D transition
            setTimeout(() => {{
                const distance = 200;
                graph.cameraPosition(
                    {{ x: node.x, y: node.y, z: distance }},
                    {{ x: node.x, y: node.y, z: 0 }},
                    1000
                );
            }}, 100);
        }}

        function clearSelection() {{
            selectedNode = null;
            highlightedNodes.clear();
            lastClickNode = null;
            lastClickTime = 0;

            // Post message to parent window (for embed mode)
            if (window.parent !== window) {{
                window.parent.postMessage({{
                    type: 'nodeDeselected'
                }}, '*');
            }}

            document.getElementById('placeholder').style.display = 'block';
            document.getElementById('node-info').classList.remove('active');

            // Restore original colors
            graph
                .nodeColor(n => n.color)
                .linkColor(l => l.color);

            // Restore all filtered nodes
            applyFilters();
        }}

        function showDirectConnectionsOnly(node) {{
            // Filter to show only this node and its direct connections
            const directIds = new Set([node.id]);
            (linksByNode[node.id] || []).forEach(conn => {{
                directIds.add(conn.nodeId);
            }});

            const filteredNodes = nodesData.filter(n => directIds.has(n.id));
            const filteredLinks = linksData.filter(link => {{
                const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
                const targetId = typeof link.target === 'object' ? link.target.id : link.target;
                return sourceId === node.id || targetId === node.id;
            }});

            setGraphData({{
                nodes: filteredNodes,
                links: filteredLinks
            }});

            // Switch to 2D and center
            setView('2d');

            // Update sidebar
            const currentNodes = getGraphNodes();
            const nodeInGraph = currentNodes.find(n => n.id === node.id);
            if (nodeInGraph) selectNode(nodeInGraph);

            // Fit view after a short delay
            setTimeout(() => {{
                graph.zoomToFit(500, 50);
            }}, 100);
        }}

        // Check for embed mode
        function checkEmbedMode() {{
            const urlParams = new URLSearchParams(window.location.search);
            const isEmbed = urlParams.get('embed') === 'true';

            if (isEmbed) {{
                // Hide sidebar and toggle button in embed mode
                const sidebar = document.getElementById('sidebar');
                const toggle = document.getElementById('sidebar-toggle');
                if (sidebar) sidebar.style.display = 'none';
                if (toggle) toggle.style.display = 'none';

                // Expand graph to full width
                setTimeout(() => {{
                    const wrapper = document.getElementById('graph-wrapper');
                    if (wrapper && graph) {{
                        graph.width(wrapper.offsetWidth).height(wrapper.offsetHeight);
                    }}
                }}, 100);
            }}
        }}

        // ============================================================
        // EXTENDED FEATURES v2.0
        // ============================================================

        // --- State for extended features ---
        let currentGeometry = 'sphere';
        let glowEnabled = false;
        let particlesEnabled = false;
        let labelsEnabled = true;
        let ringsEnabled = true;
        let logoLabelsEnabled = true;  // Re-enabled with simpler implementation
        let currentLayout = 'force';
        let multiSelectedNodes = new Set();
        let timePlayInterval = null;
        let timeSliderValue = 100;

        // --- Logo/image cache for performance ---
        const logoCache = new Map();
        const logoLoadPromises = new Map();

        // --- Stage groupings for cylinder layout ---
        const stageGroups = {{
            'outputs': {{ label: 'Reporting & Dashboards', tiers: [0], color: '#2f855a' }},
            'management': {{ label: 'Account & Operations', tiers: [1, 2], color: '#3182ce' }},
            'processing': {{ label: 'Planning & Activation', tiers: [2, 3], color: '#e53e3e' }},
            'execution': {{ label: 'DSPs & Platforms', tiers: [4, 5], color: '#9f7aea' }}
        }};

        // --- Search functionality ---
        let searchTimeout = null;

        function handleSearch(event) {{
            const query = event.target.value.toLowerCase().trim();
            clearTimeout(searchTimeout);

            if (query.length < 2) {{
                document.getElementById('search-results').classList.remove('active');
                return;
            }}

            searchTimeout = setTimeout(() => {{
                const results = nodesData.filter(n =>
                    n.name.toLowerCase().includes(query) ||
                    (n.description && n.description.toLowerCase().includes(query))
                ).slice(0, 10);

                const resultsEl = document.getElementById('search-results');
                resultsEl.innerHTML = results.map(n => `
                    <div class="search-result-item" onmousedown="searchSelectNode('${{n.id}}')">
                        <div class="name">${{n.name}}</div>
                        <div class="type">${{n.groupLabel || n.group}}</div>
                    </div>
                `).join('');
                resultsEl.classList.add('active');
            }}, 150);

            // Handle Enter key to select first result
            if (event.key === 'Enter') {{
                const firstResult = nodesData.find(n =>
                    n.name.toLowerCase().includes(query) ||
                    (n.description && n.description.toLowerCase().includes(query))
                );
                if (firstResult) {{
                    searchSelectNode(firstResult.id);
                }}
            }}
        }}

        function showSearchResults() {{
            const query = document.getElementById('search-input').value.trim();
            if (query.length >= 2) {{
                document.getElementById('search-results').classList.add('active');
            }}
        }}

        function hideSearchResults() {{
            setTimeout(() => {{
                document.getElementById('search-results').classList.remove('active');
            }}, 200);
        }}

        function searchSelectNode(nodeId) {{
            document.getElementById('search-input').value = '';
            document.getElementById('search-results').classList.remove('active');
            navigateToNode(nodeId);
        }}

        // --- Node geometry ---
        function setNodeGeometry(geometry) {{
            currentGeometry = geometry;

            // Update chip states
            document.querySelectorAll('.geometry-chip').forEach(chip => {{
                chip.classList.toggle('active', chip.dataset.geometry === geometry);
            }});

            // Apply custom geometry via nodeThreeObject
            if (geometry === 'sphere') {{
                graph.nodeThreeObject(null); // Use default sphere
            }} else {{
                // Note: Custom geometries require THREE.js to be available
                // The 3d-force-graph library bundles THREE but doesn't expose it globally
                // For now, just use the default sphere for all geometries
                console.warn('Custom geometries not supported in this build - using default spheres');
                graph.nodeThreeObject(null);
            }}
        }}

        // --- Glow effect ---
        function toggleGlow() {{
            glowEnabled = !glowEnabled;
            document.getElementById('glow-toggle').classList.toggle('active', glowEnabled);

            if (glowEnabled) {{
                // Simulate glow with sprites around nodes
                graph.nodeThreeObject(node => {{
                    if (typeof THREE === 'undefined') {{
                        console.warn('THREE.js not available for glow effect');
                        return null;
                    }}
                    const size = Math.max(node.val / 5, 2) * 2;
                    const geom = new THREE.SphereGeometry(size / 2, 16, 16);
                    const material = new THREE.MeshBasicMaterial({{
                        color: node.color,
                        transparent: true,
                        opacity: 0.9
                    }});

                    const mesh = new THREE.Mesh(geom, material);

                    // Add glow sprite
                    const glowTexture = createGlowTexture(node.color);
                    const spriteMaterial = new THREE.SpriteMaterial({{
                        map: glowTexture,
                        transparent: true,
                        blending: THREE.AdditiveBlending,
                        opacity: 0.5
                    }});
                    const sprite = new THREE.Sprite(spriteMaterial);
                    sprite.scale.set(size * 4, size * 4, 1);
                    mesh.add(sprite);

                    return mesh;
                }});
                graph.nodeThreeObjectExtend(false);
            }} else {{
                // Reset to default rendering
                graph.nodeThreeObject(null);
                graph.nodeThreeObjectExtend(false);
            }}
        }}

        function createGlowTexture(color) {{
            const canvas = document.createElement('canvas');
            canvas.width = 128;
            canvas.height = 128;
            const ctx = canvas.getContext('2d');

            // Create radial gradient for glow effect
            const gradient = ctx.createRadialGradient(64, 64, 0, 64, 64, 64);
            gradient.addColorStop(0, color);
            gradient.addColorStop(0.2, color);
            gradient.addColorStop(0.4, hexToRgba(color, 0.5));
            gradient.addColorStop(0.7, hexToRgba(color, 0.2));
            gradient.addColorStop(1, 'rgba(0,0,0,0)');

            ctx.fillStyle = gradient;
            ctx.fillRect(0, 0, 128, 128);

            if (typeof THREE === 'undefined') return null;
            const texture = new THREE.CanvasTexture(canvas);
            return texture;
        }}

        function hexToRgba(hex, alpha) {{
            // Convert hex color to rgba
            let r = 0, g = 0, b = 0;
            if (hex.length === 4) {{
                r = parseInt(hex[1] + hex[1], 16);
                g = parseInt(hex[2] + hex[2], 16);
                b = parseInt(hex[3] + hex[3], 16);
            }} else if (hex.length === 7) {{
                r = parseInt(hex.slice(1, 3), 16);
                g = parseInt(hex.slice(3, 5), 16);
                b = parseInt(hex.slice(5, 7), 16);
            }}
            return `rgba(${{r}},${{g}},${{b}},${{alpha}})`;
        }}


        // --- Edge particles ---
        function toggleParticles() {{
            particlesEnabled = !particlesEnabled;
            document.getElementById('particles-toggle').classList.toggle('active', particlesEnabled);

            if (particlesEnabled) {{
                graph.linkDirectionalParticles(4)
                    .linkDirectionalParticleSpeed(0.005)
                    .linkDirectionalParticleWidth(2)
                    .linkDirectionalParticleColor(link => link.color);
            }} else {{
                graph.linkDirectionalParticles(0);
            }}
        }}

        // --- Labels toggle ---
        function toggleLabels() {{
            labelsEnabled = !labelsEnabled;
            document.getElementById('labels-toggle').classList.toggle('active', labelsEnabled);

            if (labelsEnabled) {{
                graph.nodeLabel(node => node.name);
            }} else {{
                graph.nodeLabel(null);
            }}
        }}

        // --- Logo + Label node rendering ---
        function toggleLogoLabels() {{
            logoLabelsEnabled = !logoLabelsEnabled;
            const toggle = document.getElementById('logo-labels-toggle');
            if (toggle) toggle.classList.toggle('active', logoLabelsEnabled);

            if (logoLabelsEnabled) {{
                applyLogoLabelRendering();
            }} else {{
                // Reset to default spheres
                graph.nodeThreeObject(null);
                graph.nodeThreeObjectExtend(false);
            }}
        }}

        function applyLogoLabelRendering() {{
            if (typeof THREE === 'undefined') {{
                console.warn('THREE.js not available for logo+label rendering');
                return;
            }}

            // Create a sprite that contains both logo and label
            // Using extend=false to REPLACE the default sphere with our custom sprite
            graph.nodeThreeObject(node => {{
                const size = Math.max(node.val / 5, 3) * 2;

                // Create a combined sprite with logo (if available) and label
                const sprite = createLogoLabelSprite(node.name, node.color, node.logo, size, node.group);
                return sprite;
            }});

            // extend=false replaces the default sphere entirely
            graph.nodeThreeObjectExtend(false);
        }}

        // Create a single sprite with logo and label combined
        // Default icons for nodes without logos (by group/category)
        // Default icons using Google Material Icons (reliable, consistent style)
        // These are base64 SVG data URIs for guaranteed loading
        const defaultIcons = {{
            'hub': 'data:image/svg+xml,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><defs><linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#dd6b20"/><stop offset="100%" stop-color="#c05621"/></linearGradient></defs><circle cx="50" cy="50" r="48" fill="url(#g)"/><path d="M25 30h50v8H35v12h35v8H35v12h40v8H25z" fill="white"/></svg>'),
            'output': 'data:image/svg+xml,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#9E9E9E"><path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zM9 17H7v-7h2v7zm4 0h-2V7h2v10zm4 0h-2v-4h2v4z"/></svg>'),
            'account': 'data:image/svg+xml,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#9E9E9E"><path d="M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z"/></svg>'),
            'client_data': 'data:image/svg+xml,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#9E9E9E"><path d="M12 3C7.58 3 4 4.79 4 7v10c0 2.21 3.58 4 8 4s8-1.79 8-4V7c0-2.21-3.58-4-8-4zm0 2c3.87 0 6 1.5 6 2s-2.13 2-6 2-6-1.5-6-2 2.13-2 6-2zm6 12c0 .5-2.13 2-6 2s-6-1.5-6-2v-2.23c1.61.78 3.72 1.23 6 1.23s4.39-.45 6-1.23V17zm0-5c0 .5-2.13 2-6 2s-6-1.5-6-2V9.77c1.61.78 3.72 1.23 6 1.23s4.39-.45 6-1.23V12z"/></svg>'),
            'audience': 'data:image/svg+xml,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#9E9E9E"><path d="M12 12.75c1.63 0 3.07.39 4.24.9 1.08.48 1.76 1.56 1.76 2.73V18H6v-1.61c0-1.18.68-2.26 1.76-2.73 1.17-.52 2.61-.91 4.24-.91zM4 13c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm1.13 1.1c-.37-.06-.74-.1-1.13-.1-.99 0-1.93.21-2.78.58C.48 14.9 0 15.62 0 16.43V18h4.5v-1.61c0-.83.23-1.61.63-2.29zM20 13c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm4 3.43c0-.81-.48-1.53-1.22-1.85-.85-.37-1.79-.58-2.78-.58-.39 0-.76.04-1.13.1.4.68.63 1.46.63 2.29V18H24v-1.57zM12 6c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3z"/></svg>'),
            'consumer_data': 'data:image/svg+xml,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#9E9E9E"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/></svg>'),
            'media_planning': 'data:image/svg+xml,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#9E9E9E"><path d="M19 4h-1V2h-2v2H8V2H6v2H5c-1.11 0-1.99.9-1.99 2L3 20c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 16H5V9h14v11zM9 11H7v2h2v-2zm4 0h-2v2h2v-2zm4 0h-2v2h2v-2zm-8 4H7v2h2v-2zm4 0h-2v2h2v-2zm4 0h-2v2h2v-2z"/></svg>'),
            'activation': 'data:image/svg+xml,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#9E9E9E"><path d="M13 2.05v3.03c3.39.49 6 3.39 6 6.92 0 .9-.18 1.75-.48 2.54l2.6 1.53c.56-1.24.88-2.62.88-4.07 0-5.18-3.95-9.45-9-9.95zM12 19c-3.87 0-7-3.13-7-7 0-3.53 2.61-6.43 6-6.92V2.05c-5.06.5-9 4.76-9 9.95 0 5.52 4.47 10 9.99 10 3.31 0 6.24-1.61 8.06-4.09l-2.6-1.53C16.17 17.98 14.21 19 12 19z"/></svg>'),
            'dsp': 'data:image/svg+xml,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#9E9E9E"><path d="M4 6h18V4H4c-1.1 0-2 .9-2 2v11H0v3h14v-3H4V6zm19 2h-6c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h6c.55 0 1-.45 1-1V9c0-.55-.45-1-1-1zm-1 9h-4v-7h4v7z"/></svg>'),
            'digital_media': 'data:image/svg+xml,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#9E9E9E"><path d="M21 3H3c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h5v2h8v-2h5c1.1 0 1.99-.9 1.99-2L23 5c0-1.1-.9-2-2-2zm0 14H3V5h18v12zm-5-6l-7 4V7z"/></svg>'),
            'flight': 'data:image/svg+xml,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#9E9E9E"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>'),
            'finance': 'data:image/svg+xml,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#9E9E9E"><path d="M11.8 10.9c-2.27-.59-3-1.2-3-2.15 0-1.09 1.01-1.85 2.7-1.85 1.78 0 2.44.85 2.5 2.1h2.21c-.07-1.72-1.12-3.3-3.21-3.81V3h-3v2.16c-1.94.42-3.5 1.68-3.5 3.61 0 2.31 1.91 3.46 4.7 4.13 2.5.6 3 1.48 3 2.41 0 .69-.49 1.79-2.7 1.79-2.06 0-2.87-.92-2.98-2.1h-2.2c.12 2.19 1.76 3.42 3.68 3.83V21h3v-2.15c1.95-.37 3.5-1.5 3.5-3.55 0-2.84-2.43-3.81-4.7-4.4z"/></svg>'),
            'default': 'data:image/svg+xml,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#9E9E9E"><circle cx="12" cy="12" r="8"/></svg>')
        }};

        function createLogoLabelSprite(name, color, logoUrl, nodeSize, group) {{
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            // Higher resolution for crisp logos
            canvas.width = 256;
            canvas.height = 320;

            // Start with fully transparent background
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            // Draw label below (scaled for higher res canvas)
            ctx.font = 'bold 28px -apple-system, BlinkMacSystemFont, sans-serif';
            ctx.fillStyle = '#ffffff';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'top';

            // Truncate text if too long
            let displayText = name;
            while (ctx.measureText(displayText).width > 240 && displayText.length > 3) {{
                displayText = displayText.slice(0, -4) + '...';
            }}
            ctx.fillText(displayText, 128, 240);

            // If logo URL provided, load it and update the sprite
            const texture = new THREE.CanvasTexture(canvas);
            const spriteMat = new THREE.SpriteMaterial({{
                map: texture,
                transparent: true,
                depthTest: false,  // Disable depth testing so sprites always render on top
                depthWrite: false
            }});
            const sprite = new THREE.Sprite(spriteMat);
            sprite.scale.set(nodeSize * 3, nodeSize * 3.75, 1);
            sprite.renderOrder = 1000;  // High render order ensures sprites render after edges

            // Draw colored circle as fallback (will be covered by logo if loaded)
            // Scaled for 256x320 canvas (center at 128, 120)
            ctx.beginPath();
            ctx.arc(128, 120, 96, 0, Math.PI * 2);
            ctx.fillStyle = color;
            ctx.fill();

            // Draw initials as fallback
            const initials = name.split(/[\\s\\-\\/]+/).filter(w => w.length > 0).slice(0, 2).map(w => w[0]).join('').toUpperCase();
            ctx.font = 'bold 64px -apple-system, BlinkMacSystemFont, sans-serif';
            ctx.fillStyle = '#ffffff';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(initials, 128, 120);

            // Determine the logo URL to use (provided or default based on group)
            let finalLogoUrl = logoUrl;
            if (!logoUrl && group) {{
                finalLogoUrl = defaultIcons[group] || defaultIcons['default'];
            }}

            // If we have a logo URL, try to load and overlay it
            if (finalLogoUrl) {{
                const img = new Image();
                img.crossOrigin = 'anonymous';

                // Use weserv.nl image proxy for CORS support (but not for data URIs)
                let proxiedUrl = finalLogoUrl;
                if (!finalLogoUrl.startsWith('data:')) {{
                    try {{
                        const urlObj = new URL(finalLogoUrl);
                        // Remove protocol and use weserv.nl proxy
                        const urlWithoutProtocol = urlObj.host + urlObj.pathname + urlObj.search;
                        proxiedUrl = 'https://images.weserv.nl/?url=' + encodeURIComponent(urlWithoutProtocol);
                    }} catch (e) {{
                        console.warn('Invalid logo URL:', finalLogoUrl);
                    }}
                }}

                img.onload = () => {{
                    // Clear the logo area for transparent background
                    ctx.clearRect(0, 0, 256, 220);

                    // Draw logo directly without background or border (fully transparent)
                    // Scaled for 256x320 canvas
                    ctx.save();
                    ctx.beginPath();
                    ctx.arc(128, 120, 96, 0, Math.PI * 2);
                    ctx.clip();
                    ctx.drawImage(img, 32, 24, 192, 192);
                    ctx.restore();

                    texture.needsUpdate = true;
                    console.log('Logo loaded for:', name);
                }};
                img.onerror = (e) => {{
                    console.warn('Failed to load logo for', name, ':', proxiedUrl, e);
                    // Initials already drawn, just update texture
                    texture.needsUpdate = true;
                }};
                img.src = proxiedUrl;
            }} else {{
                texture.needsUpdate = true;
            }}

            return sprite;
        }}

        function createLabelSprite(text, color, nodeSize) {{
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            canvas.width = 256;
            canvas.height = 64;

            // Background
            ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
            const textWidth = ctx.measureText(text).width;
            ctx.roundRect(10, 16, canvas.width - 20, 32, 6);
            ctx.fill();

            // Text
            ctx.font = 'bold 18px -apple-system, BlinkMacSystemFont, sans-serif';
            ctx.fillStyle = '#ffffff';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';

            // Truncate if too long
            let displayText = text;
            if (ctx.measureText(text).width > canvas.width - 30) {{
                while (ctx.measureText(displayText + '...').width > canvas.width - 30 && displayText.length > 0) {{
                    displayText = displayText.slice(0, -1);
                }}
                displayText += '...';
            }}
            ctx.fillText(displayText, canvas.width / 2, canvas.height / 2);

            const texture = new THREE.CanvasTexture(canvas);
            const spriteMat = new THREE.SpriteMaterial({{
                map: texture,
                transparent: true
            }});
            const sprite = new THREE.Sprite(spriteMat);
            sprite.scale.set(nodeSize * 4, nodeSize, 1);
            return sprite;
        }}

        function createInitialsSprite(initials, bgColor, size) {{
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            canvas.width = 128;
            canvas.height = 128;

            // Circle background
            ctx.beginPath();
            ctx.arc(64, 64, 60, 0, Math.PI * 2);
            ctx.fillStyle = bgColor;
            ctx.fill();

            // Initials text
            ctx.font = 'bold 48px -apple-system, BlinkMacSystemFont, sans-serif';
            ctx.fillStyle = '#ffffff';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(initials, 64, 68);

            const texture = new THREE.CanvasTexture(canvas);
            const spriteMat = new THREE.SpriteMaterial({{
                map: texture,
                transparent: true
            }});
            const sprite = new THREE.Sprite(spriteMat);
            sprite.scale.set(size * 2, size * 2, 1);
            return sprite;
        }}

        function getInitials(name) {{
            // Extract initials from name
            const words = name.split(/[\s\-\/]+/).filter(w => w.length > 0);
            if (words.length === 1) {{
                return words[0].substring(0, 2).toUpperCase();
            }}
            return words.slice(0, 2).map(w => w[0]).join('').toUpperCase();
        }}

        async function loadLogoTexture(url) {{
            // Check cache first
            if (logoCache.has(url)) {{
                return logoCache.get(url);
            }}

            // Check if already loading
            if (logoLoadPromises.has(url)) {{
                return logoLoadPromises.get(url);
            }}

            // Start loading
            const promise = new Promise((resolve) => {{
                const img = new Image();
                img.crossOrigin = 'anonymous';
                img.onload = () => {{
                    const texture = new THREE.Texture(img);
                    texture.needsUpdate = true;
                    logoCache.set(url, texture);
                    resolve(texture);
                }};
                img.onerror = () => {{
                    logoCache.set(url, null);
                    resolve(null);
                }};
                img.src = url;
            }});

            logoLoadPromises.set(url, promise);
            return promise;
        }}

        // --- Theme toggle (light/dark mode) ---
        function toggleTheme() {{
            currentTheme = currentTheme === 'dark' ? 'light' : 'dark';
            document.getElementById('theme-toggle').classList.toggle('active', currentTheme === 'light');
            applyTheme();
        }}

        function applyTheme() {{
            const body = document.body;
            const container = document.getElementById('container');
            const sidebar = document.getElementById('sidebar');
            const toolbar = document.getElementById('toolbar');

            if (currentTheme === 'light') {{
                // Light mode
                body.style.background = 'linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%)';
                if (container) container.style.background = 'transparent';
                if (sidebar) {{
                    sidebar.style.background = 'rgba(255, 255, 255, 0.95)';
                    sidebar.style.color = '#1a202c';
                }}
                if (toolbar) {{
                    toolbar.style.background = 'rgba(255, 255, 255, 0.9)';
                    toolbar.style.color = '#1a202c';
                }}
                // Update graph background
                if (graph && graph.backgroundColor) {{
                    graph.backgroundColor('#f0f4f8');
                }}
            }} else {{
                // Dark mode (default)
                body.style.background = 'linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 50%, #16213e 100%)';
                if (container) container.style.background = 'transparent';
                if (sidebar) {{
                    sidebar.style.background = 'rgba(15, 23, 42, 0.95)';
                    sidebar.style.color = '#e2e8f0';
                }}
                if (toolbar) {{
                    toolbar.style.background = 'rgba(15, 23, 42, 0.85)';
                    toolbar.style.color = '#e2e8f0';
                }}
                // Update graph background
                if (graph && graph.backgroundColor) {{
                    graph.backgroundColor('#0a0a14');
                }}
            }}

            // Refresh cylinder layout to update ring opacities
            if (currentLayout === 'cylinder' && ringsEnabled) {{
                clearTierPlatforms();
                applyCylinderLayout();
            }}
        }}

        // --- Rings toggle (for cylinder layout) ---
        function toggleRings() {{
            ringsEnabled = !ringsEnabled;
            document.getElementById('rings-toggle').classList.toggle('active', ringsEnabled);

            if (currentLayout === 'cylinder') {{
                if (ringsEnabled) {{
                    // Re-apply cylinder layout to recreate rings
                    clearTierPlatforms();
                    applyCylinderLayout();
                }} else {{
                    // Just clear the rings, keep node positions
                    clearTierPlatforms();
                }}
            }}
        }}

        // --- Layout variations ---
        function changeLayout() {{
            currentLayout = document.getElementById('layout-select').value;

            // Clear tier platforms when switching away from cylinder
            if (currentLayout !== 'cylinder') {{
                clearTierPlatforms();
            }}

            switch(currentLayout) {{
                case 'force':
                    applyForceLayout();
                    break;
                case 'layered':
                    applyLayeredLayout();
                    break;
                case 'spherical':
                    applySphericalLayout();
                    break;
                case 'cylinder':
                    applyCylinderLayout();
                    break;
            }}
        }}

        function applyForceLayout() {{
            // Reset to force-directed (clear fixed positions)
            const nodes = getGraphNodes();
            if (nodes.length === 0) return;
            nodes.forEach(node => {{
                node.fx = undefined;
                node.fy = undefined;
                node.fz = undefined;
            }});
            graph.d3ReheatSimulation();
        }}

        function applyLayeredLayout() {{
            // Z-axis represents tier/hierarchy
            const nodes = getGraphNodes();
            if (nodes.length === 0) return;

            const tierSpacing = 100;
            const tierCounts = {{}};

            nodes.forEach(node => {{
                const tier = node.tier || 0;
                if (!tierCounts[tier]) tierCounts[tier] = {{ count: 0, total: 0 }};
                tierCounts[tier].total++;
            }});

            nodes.forEach(node => {{
                const tier = node.tier || 0;
                const angle = (tierCounts[tier].count / tierCounts[tier].total) * Math.PI * 2;
                const radius = 50 + tier * 80;

                node.fx = Math.cos(angle) * radius;
                node.fy = Math.sin(angle) * radius;
                node.fz = tier * tierSpacing;

                tierCounts[tier].count++;
            }});

            graph.d3ReheatSimulation();
            setTimeout(() => graph.zoomToFit(500), 100);
        }}

        function applySphericalLayout() {{
            // Nodes on sphere surface, grouped by category
            const nodes = getGraphNodes();
            if (nodes.length === 0) return;

            const radius = 200;
            const groups = {{}};

            nodes.forEach(node => {{
                const group = node.group || 'default';
                if (!groups[group]) groups[group] = [];
                groups[group].push(node);
            }});

            const groupKeys = Object.keys(groups);
            groupKeys.forEach((group, gi) => {{
                const phi = (gi / groupKeys.length) * Math.PI * 2;

                groups[group].forEach((node, ni) => {{
                    const theta = (ni / groups[group].length) * Math.PI - Math.PI / 2;
                    const r = radius + (node.tier || 0) * 30;

                    node.fx = r * Math.cos(theta) * Math.cos(phi);
                    node.fy = r * Math.sin(theta);
                    node.fz = r * Math.cos(theta) * Math.sin(phi);
                }});
            }});

            graph.d3ReheatSimulation();
            setTimeout(() => graph.zoomToFit(500), 100);
        }}

        // Track tier platform meshes for cleanup
        let tierPlatforms = [];

        function applyCylinderLayout() {{
            // Y-axis = tier/time, circumference = category/group
            const nodes = getGraphNodes();
            if (nodes.length === 0) return;

            // Clean up existing tier platforms
            clearTierPlatforms();

            // Check if we have dates or tiers to use for Y-axis
            const nodesWithDates = nodes.filter(n => n.createdAt);
            const nodesWithTiers = nodes.filter(n => typeof n.tier === 'number');

            let useDate = nodesWithDates.length > nodes.length / 2;
            let minY, maxY, getYValue;
            let tierLabels = {{}};

            if (useDate && nodesWithDates.length > 0) {{
                // Use dates for Y positioning
                const dates = nodesWithDates.map(n => new Date(n.createdAt).getTime());
                minY = Math.min(...dates);
                maxY = Math.max(...dates);
                getYValue = (node) => node.createdAt ? new Date(node.createdAt).getTime() : minY;
            }} else if (nodesWithTiers.length > 0) {{
                // Use tiers for Y positioning
                const tiers = nodesWithTiers.map(n => n.tier);
                minY = Math.min(...tiers);
                maxY = Math.max(...tiers);
                getYValue = (node) => typeof node.tier === 'number' ? node.tier : minY;

                // Build tier labels from groupsData
                nodes.forEach(node => {{
                    const tier = node.tier;
                    if (typeof tier === 'number' && !tierLabels[tier]) {{
                        tierLabels[tier] = node.groupLabel || node.group || `Tier ${{tier}}`;
                    }}
                }});
            }} else {{
                // Fallback: use node index
                minY = 0;
                maxY = nodes.length - 1;
                getYValue = (node) => nodes.indexOf(node);
            }}

            const yRange = maxY - minY || 1;

            // Group nodes by their group property
            const groups = {{}};
            nodes.forEach(node => {{
                const group = node.group || 'default';
                if (!groups[group]) groups[group] = {{ nodes: [], index: Object.keys(groups).length }};
                groups[group].nodes.push(node);
            }});

            const totalGroups = Object.keys(groups).length;
            const radius = 200;
            const height = 500;

            // Build stage definitions dynamically from actual tier data
            // Group nodes by tier and get representative label/color for each
            const tierInfo = {{}};
            nodes.forEach(node => {{
                const tier = typeof node.tier === 'number' ? node.tier : 0;
                if (!tierInfo[tier]) {{
                    tierInfo[tier] = {{
                        tier: tier,
                        label: node.groupLabel || node.group || `Tier ${{tier}}`,
                        color: node.color || '#888888',
                        count: 0
                    }};
                }}
                tierInfo[tier].count++;
            }});

            // Sort tiers and create stage definitions with evenly spaced Y positions
            const sortedTiers = Object.keys(tierInfo).map(Number).sort((a, b) => a - b);
            const numTiers = sortedTiers.length;
            const stageDefinitions = sortedTiers.map((tier, index) => {{
                // Spread from -0.45 to 0.45 based on tier position
                const yPos = numTiers > 1 ? -0.45 + (0.9 * index / (numTiers - 1)) : 0;
                return {{
                    name: tierInfo[tier].label,
                    tiers: [tier],
                    color: tierInfo[tier].color,
                    yPos: yPos
                }};
            }});

            // Create stage-based platforms (rings with labels) - only if rings are enabled
            if (typeof THREE !== 'undefined' && ringsEnabled) {{
                const scene = graph.scene();

                stageDefinitions.forEach((stage, index) => {{
                    const yPos = stage.yPos * height;
                    const ringColor = stage.color;

                    // Create 3D torus ring with high transparency
                    const torusRadius = radius + 30;
                    const tubeRadius = 4;
                    const torusGeom = new THREE.TorusGeometry(torusRadius, tubeRadius, 16, 100);
                    const torusMat = new THREE.MeshBasicMaterial({{
                        color: ringColor,
                        transparent: true,
                        opacity: currentTheme === 'light' ? 0.15 : 0.2
                    }});
                    const torus = new THREE.Mesh(torusGeom, torusMat);
                    torus.rotation.x = Math.PI / 2;
                    torus.position.y = yPos;
                    scene.add(torus);
                    tierPlatforms.push(torus);

                    // Add outer glow ring - very subtle
                    const glowTorusGeom = new THREE.TorusGeometry(torusRadius, tubeRadius * 4, 16, 100);
                    const glowTorusMat = new THREE.MeshBasicMaterial({{
                        color: ringColor,
                        transparent: true,
                        opacity: currentTheme === 'light' ? 0.05 : 0.08
                    }});
                    const glowTorus = new THREE.Mesh(glowTorusGeom, glowTorusMat);
                    glowTorus.rotation.x = Math.PI / 2;
                    glowTorus.position.y = yPos;
                    scene.add(glowTorus);
                    tierPlatforms.push(glowTorus);

                    // Create stage label
                    const canvas = document.createElement('canvas');
                    const ctx = canvas.getContext('2d');
                    canvas.width = 512;
                    canvas.height = 64;

                    ctx.fillStyle = 'rgba(0, 0, 0, 0)';
                    ctx.fillRect(0, 0, canvas.width, canvas.height);

                    ctx.font = 'bold 28px -apple-system, BlinkMacSystemFont, sans-serif';
                    ctx.fillStyle = '#ffffff';
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.fillText(stage.name, canvas.width / 2, canvas.height / 2);

                    const texture = new THREE.CanvasTexture(canvas);
                    const spriteMat = new THREE.SpriteMaterial({{
                        map: texture,
                        transparent: true,
                        opacity: 0.95
                    }});
                    const sprite = new THREE.Sprite(spriteMat);
                    sprite.scale.set(180, 24, 1);
                    sprite.position.set(radius + 100, yPos, 0);
                    scene.add(sprite);
                    tierPlatforms.push(sprite);
                }});
            }}

            // Map tiers to stage Y positions for node placement
            const tierToStageY = {{}};
            stageDefinitions.forEach(stage => {{
                stage.tiers.forEach(tier => {{
                    tierToStageY[tier] = stage.yPos;
                }});
            }});

            nodes.forEach(node => {{
                const group = groups[node.group || 'default'];
                // Spread nodes within their group segment
                const nodeIndexInGroup = group.nodes.indexOf(node);
                const groupSpread = 0.8 / totalGroups; // How much of the circle each group takes
                const baseAngle = (group.index / totalGroups) * Math.PI * 2;
                const offsetAngle = (nodeIndexInGroup / Math.max(group.nodes.length, 1) - 0.5) * groupSpread * Math.PI * 2;
                const angle = baseAngle + offsetAngle;

                // Y position based on stage (mapped from tier) with small offset for separation
                const tier = typeof node.tier === 'number' ? node.tier : 0;
                const stageY = tierToStageY[tier] !== undefined ? tierToStageY[tier] : 0;
                // Add small random offset within stage band for visual separation
                const tierOffset = (tier % 2 === 0 ? 0.02 : -0.02) + (Math.random() - 0.5) * 0.04;

                node.fx = Math.cos(angle) * radius;
                node.fz = Math.sin(angle) * radius;
                node.fy = (stageY + tierOffset) * height;
            }});

            graph.d3ReheatSimulation();
            setTimeout(() => graph.zoomToFit(500), 100);
        }}

        function clearTierPlatforms() {{
            if (typeof THREE === 'undefined') return;
            const scene = graph.scene();
            tierPlatforms.forEach(obj => {{
                scene.remove(obj);
                if (obj.geometry) obj.geometry.dispose();
                if (obj.material) {{
                    if (obj.material.map) obj.material.map.dispose();
                    obj.material.dispose();
                }}
            }});
            tierPlatforms = [];
        }}

        // --- Multi-select with shift-click ---
        document.addEventListener('keydown', function(e) {{
            if (e.key === 'Shift') {{
                graph.onNodeClick((node, event) => {{
                    if (multiSelectedNodes.has(node.id)) {{
                        multiSelectedNodes.delete(node.id);
                    }} else {{
                        multiSelectedNodes.add(node.id);
                    }}
                    updateMultiSelectDisplay();
                    highlightMultiSelected();
                }});
            }}
        }});

        document.addEventListener('keyup', function(e) {{
            if (e.key === 'Shift') {{
                graph.onNodeClick(node => handleNodeClick(node));
            }}
        }});

        function updateMultiSelectDisplay() {{
            const countEl = document.getElementById('selection-count');
            if (multiSelectedNodes.size > 0) {{
                countEl.textContent = `${{multiSelectedNodes.size}} selected`;
                countEl.classList.add('active');
            }} else {{
                countEl.classList.remove('active');
            }}
        }}

        function highlightMultiSelected() {{
            graph.nodeColor(node => {{
                if (multiSelectedNodes.has(node.id)) {{
                    return '#ffd700'; // Gold highlight for multi-selected
                }}
                return node.color;
            }});
        }}

        // --- Time slider ---
        function initTimeSlider() {{
            const nodesWithDates = nodesData.filter(n => n.createdAt);
            if (nodesWithDates.length > 0) {{
                document.getElementById('time-toolbar').style.display = 'flex';

                // Calculate date range
                const dates = nodesWithDates.map(n => new Date(n.createdAt).getTime()).sort((a, b) => a - b);
                window.timeRange = {{
                    min: dates[0],
                    max: dates[dates.length - 1]
                }};
            }}
        }}

        function updateTimeSlider() {{
            timeSliderValue = parseInt(document.getElementById('time-slider').value);

            if (!window.timeRange) return;

            const cutoffTime = window.timeRange.min + (timeSliderValue / 100) * (window.timeRange.max - window.timeRange.min);
            const cutoffDate = new Date(cutoffTime);

            document.getElementById('time-display').textContent =
                timeSliderValue === 100 ? 'All time' : cutoffDate.toLocaleDateString();

            // Filter nodes by time
            const filteredNodes = nodesData.filter(node => {{
                if (!node.createdAt) return true; // Include nodes without dates
                const nodeDate = new Date(node.createdAt).getTime();
                return nodeDate <= cutoffTime && visibleGroups.has(node.group);
            }});

            const filteredNodeIds = new Set(filteredNodes.map(n => n.id));
            const filteredLinks = linksData.filter(link => {{
                const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
                const targetId = typeof link.target === 'object' ? link.target.id : link.target;
                return filteredNodeIds.has(sourceId) && filteredNodeIds.has(targetId) && visibleEdgeTypes.has(link.edgeType);
            }});

            setGraphData({{ nodes: filteredNodes, links: filteredLinks }});
        }}

        function toggleTimePlay() {{
            const btn = document.getElementById('play-btn');

            if (timePlayInterval) {{
                clearInterval(timePlayInterval);
                timePlayInterval = null;
                btn.textContent = '▶';
                btn.classList.remove('playing');
            }} else {{
                if (timeSliderValue >= 100) {{
                    document.getElementById('time-slider').value = 0;
                    timeSliderValue = 0;
                }}

                btn.textContent = '⏸';
                btn.classList.add('playing');

                timePlayInterval = setInterval(() => {{
                    timeSliderValue += 1;
                    document.getElementById('time-slider').value = timeSliderValue;
                    updateTimeSlider();

                    if (timeSliderValue >= 100) {{
                        toggleTimePlay(); // Stop at end
                    }}
                }}, 100);
            }}
        }}

        // --- VR mode ---
        function checkVRSupport() {{
            if (navigator.xr) {{
                navigator.xr.isSessionSupported('immersive-vr').then(supported => {{
                    document.getElementById('vr-btn').disabled = !supported;
                }});
            }}
        }}

        function enterVR() {{
            if (graph.scene && navigator.xr) {{
                // ForceGraph3D has built-in VR support
                const renderer = graph.renderer();
                renderer.xr.enabled = true;

                navigator.xr.requestSession('immersive-vr').then(session => {{
                    renderer.xr.setSession(session);
                }});
            }}
        }}

        // --- Update stats display ---
        function updateStats() {{
            const nodes = getGraphNodes();
            const links = getGraphLinks();
            const statsEl = document.getElementById('stats-display');
            statsEl.textContent = `${{nodes.length}} nodes · ${{links.length}} edges`;
        }}

        // --- Path highlighting (find shortest path between multi-selected nodes) ---
        function highlightPath() {{
            if (multiSelectedNodes.size !== 2) {{
                alert('Select exactly 2 nodes (shift-click) to highlight path');
                return;
            }}

            const [startId, endId] = Array.from(multiSelectedNodes);
            const path = findShortestPath(startId, endId);

            if (path) {{
                // Highlight path nodes and edges
                const pathSet = new Set(path);
                graph.nodeColor(node => pathSet.has(node.id) ? '#ffd700' : '#333333');
                graph.linkColor(link => {{
                    const sId = typeof link.source === 'object' ? link.source.id : link.source;
                    const tId = typeof link.target === 'object' ? link.target.id : link.target;
                    const sIdx = path.indexOf(sId);
                    const tIdx = path.indexOf(tId);
                    if (sIdx >= 0 && tIdx >= 0 && Math.abs(sIdx - tIdx) === 1) {{
                        return '#ffd700';
                    }}
                    return '#222222';
                }});
            }} else {{
                alert('No path found between selected nodes');
            }}
        }}

        function findShortestPath(startId, endId) {{
            // BFS for shortest path
            const visited = new Set();
            const queue = [[startId]];

            while (queue.length > 0) {{
                const path = queue.shift();
                const nodeId = path[path.length - 1];

                if (nodeId === endId) return path;

                if (visited.has(nodeId)) continue;
                visited.add(nodeId);

                const connections = linksByNode[nodeId] || [];
                for (const conn of connections) {{
                    if (!visited.has(conn.nodeId)) {{
                        queue.push([...path, conn.nodeId]);
                    }}
                }}
            }}

            return null;
        }}

        // --- Heat map coloring by metric ---
        function applyHeatMapColoring(metric = 'connections') {{
            let values = {{}};

            if (metric === 'connections') {{
                nodesData.forEach(node => {{
                    values[node.id] = (linksByNode[node.id] || []).length;
                }});
            }} else if (metric === 'recency') {{
                const now = Date.now();
                nodesData.forEach(node => {{
                    if (node.createdAt) {{
                        const age = now - new Date(node.createdAt).getTime();
                        values[node.id] = 1 - (age / (365 * 24 * 60 * 60 * 1000)); // Normalize to 1 year
                    }} else {{
                        values[node.id] = 0;
                    }}
                }});
            }}

            const maxVal = Math.max(...Object.values(values));
            const minVal = Math.min(...Object.values(values));
            const range = maxVal - minVal || 1;

            graph.nodeColor(node => {{
                const normalized = (values[node.id] - minVal) / range;
                return interpolateColor(normalized);
            }});

            document.getElementById('heatmap-legend').classList.add('active');
        }}

        function interpolateColor(t) {{
            // Blue -> Green -> Yellow -> Red gradient
            const colors = [
                [49, 130, 206],  // Blue
                [56, 161, 105],  // Green
                [236, 201, 75],  // Yellow
                [229, 62, 62]    // Red
            ];

            const idx = t * (colors.length - 1);
            const lower = Math.floor(idx);
            const upper = Math.min(lower + 1, colors.length - 1);
            const frac = idx - lower;

            const r = Math.round(colors[lower][0] + frac * (colors[upper][0] - colors[lower][0]));
            const g = Math.round(colors[lower][1] + frac * (colors[upper][1] - colors[lower][1]));
            const b = Math.round(colors[lower][2] + frac * (colors[upper][2] - colors[lower][2]));

            return `rgb(${{r}}, ${{g}}, ${{b}})`;
        }}

        function resetHeatMap() {{
            graph.nodeColor(node => node.color);
            document.getElementById('heatmap-legend').classList.remove('active');
        }}

        // --- Size by centrality ---
        function applyCentralitySizing() {{
            // Simple degree centrality
            const centrality = {{}};
            nodesData.forEach(node => {{
                centrality[node.id] = (linksByNode[node.id] || []).length;
            }});

            const maxCent = Math.max(...Object.values(centrality));

            graph.nodeVal(node => {{
                const c = centrality[node.id] || 0;
                return Math.max(node.val * (0.5 + (c / maxCent) * 1.5), 2);
            }});
        }}

        function resetCentralitySizing() {{
            graph.nodeVal(node => Math.max(node.val / 5, 2));
        }}

        // --- Pulsing recent nodes ---
        function enablePulsingNodes(dayThreshold = 7) {{
            if (typeof THREE === 'undefined') {{
                console.warn('THREE.js not available for pulsing nodes');
                return;
            }}
            const now = Date.now();
            const threshold = dayThreshold * 24 * 60 * 60 * 1000;

            graph.nodeThreeObject(node => {{
                const size = Math.max(node.val / 5, 2) * 2;

                const geom = new THREE.SphereGeometry(size / 2, 16, 16);
                const material = new THREE.MeshLambertMaterial({{
                    color: node.color,
                    transparent: true,
                    opacity: 0.9
                }});

                const mesh = new THREE.Mesh(geom, material);

                // Check if recent
                if (node.createdAt) {{
                    const age = now - new Date(node.createdAt).getTime();
                    if (age < threshold) {{
                        // Add pulsing animation
                        mesh.userData.pulsing = true;
                        mesh.userData.pulsePhase = Math.random() * Math.PI * 2;
                    }}
                }}

                return mesh;
            }});

            // Animate pulsing nodes
            const animate = () => {{
                const nodes = getGraphNodes();
                nodes.forEach(node => {{
                    const obj = graph.scene().getObjectByProperty('__data', node);
                    if (obj && obj.userData.pulsing) {{
                        const scale = 1 + 0.2 * Math.sin(Date.now() / 500 + obj.userData.pulsePhase);
                        obj.scale.set(scale, scale, scale);
                    }}
                }});
                requestAnimationFrame(animate);
            }};
            animate();
        }}

        // --- Expand/collapse cluster groups ---
        const collapsedGroups = new Set();

        function toggleGroupCollapse(groupId) {{
            if (collapsedGroups.has(groupId)) {{
                collapsedGroups.delete(groupId);
            }} else {{
                collapsedGroups.add(groupId);
            }}
            applyGroupCollapse();
        }}

        function applyGroupCollapse() {{
            // When collapsed, show only one representative node per group
            const visibleNodes = [];
            const groupReps = {{}};

            nodesData.forEach(node => {{
                if (collapsedGroups.has(node.group)) {{
                    // Show only first node as group representative
                    if (!groupReps[node.group]) {{
                        groupReps[node.group] = {{
                            ...node,
                            name: `${{node.groupLabel || node.group}} (${{nodesData.filter(n => n.group === node.group).length}})`,
                            val: 50, // Larger for group node
                            isGroupNode: true
                        }};
                        visibleNodes.push(groupReps[node.group]);
                    }}
                }} else {{
                    visibleNodes.push(node);
                }}
            }});

            const visibleIds = new Set(visibleNodes.map(n => n.id));
            const visibleLinks = linksData.filter(link => {{
                const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
                const targetId = typeof link.target === 'object' ? link.target.id : link.target;
                return visibleIds.has(sourceId) && visibleIds.has(targetId);
            }});

            setGraphData({{ nodes: visibleNodes, links: visibleLinks }});
        }}

        // --- Edge thickness by weight ---
        function applyEdgeThickness() {{
            graph.linkWidth(link => {{
                const weight = link.weight || 1;
                return Math.max(1, Math.min(link.width * weight, 8));
            }});
        }}

        // --- Initialize extended features ---
        function initExtendedFeatures() {{
            initTimeSlider();
            checkVRSupport();
            updateStats();

            // Update stats when graph data changes
            const originalGraphData = graph.graphData.bind(graph);
            graph.graphData = function(data) {{
                const result = originalGraphData(data);
                if (data) updateStats();
                return result;
            }};
        }}

        // Initialize
        initGraph();
        checkEmbedMode();
        initExtendedFeatures();
    </script>
</body>
</html>'''

    return html


def generate_visualization(
    input_path: str,
    output_path: str,
) -> str:
    """Generate a 3D network visualization from JSON data."""
    # Load data
    data = load_json_data(input_path)

    # Get metadata
    metadata = data.get("metadata", {})
    title = metadata.get("title", "Network Visualization")

    print(f"Loaded graph: {len(data['nodes'])} nodes, {len(data['edges'])} edges")

    # Generate HTML
    html = generate_html(data, title)

    # Ensure output directory exists
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Write HTML
    with open(output_file, 'w') as f:
        f.write(html)

    print(f"Generated 3D visualization: {output_file}")
    return str(output_file)


def main():
    parser = argparse.ArgumentParser(
        description="Generate 3D network graph visualizations from JSON data"
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Path to input JSON file"
    )
    parser.add_argument(
        "--output", "-o",
        required=True,
        help="Path for output HTML file"
    )

    args = parser.parse_args()

    generate_visualization(
        input_path=args.input,
        output_path=args.output,
    )


if __name__ == "__main__":
    main()
