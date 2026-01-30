#!/usr/bin/env python3
"""
Radial/Concentric Ring Knowledge Graph Visualization Generator

World-class visualization following best practices:
- Concentric ring layout with tier-based positioning
- Visual hierarchy through size, opacity, and glow
- Curved edge bundling for reduced visual clutter
- Smooth polar coordinate animations
- Progressive disclosure on interaction
- Human-centered design principles (J5 philosophy)

Usage:
    python generate_radial.py --input data/examples/fbc_partners.json --output output/html/fbc_ecosystem.html
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


def generate_radial_html(data: dict[str, Any], title: str) -> str:
    """Generate radial/concentric ring visualization HTML."""

    groups = data.get("groups", {})

    # Process nodes with tier information
    nodes_list = []
    tier_nodes = {}  # Group nodes by tier

    for node in data["nodes"]:
        node_id = node["id"]
        group = node.get("group", "default")
        tier = node.get("tier", 0)
        group_info = groups.get(group, {"color": "#888888", "label": group})

        if tier not in tier_nodes:
            tier_nodes[tier] = []
        tier_nodes[tier].append(node_id)

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
        })

    # Edge styles
    edge_styles = {
        "strategic_partner": {"color": "#2f855a", "width": 4, "label": "Strategic Partner"},
        "emerging_partner": {"color": "#3182ce", "width": 3, "label": "Emerging Partner"},
        "sme_expert": {"color": "#805ad5", "width": 2, "label": "SME Expert"},
        "collaboration": {"color": "#a0aec0", "width": 1.5, "label": "Collaboration"},
        "member": {"color": "#718096", "width": 1, "label": "Member"},
        "direct_partner": {"color": "#e53e3e", "width": 3, "label": "Direct Partner"},
        "supply_chain": {"color": "#dd6b20", "width": 1, "label": "Supply Chain"},
    }
    edge_styles.update(data.get("edge_types", {}))

    links_list = []
    for edge in data["edges"]:
        edge_type = edge.get("type", "default")
        style = edge_styles.get(edge_type, {"color": "#888888", "width": 1, "label": edge_type})
        links_list.append({
            "source": edge["source"],
            "target": edge["target"],
            "color": style.get("color", "#888888"),
            "width": style.get("width", 1),
            "relationType": style.get("label", edge_type),
            "edgeType": edge_type,
        })

    nodes_json = json.dumps(nodes_list)
    links_json = json.dumps(links_list)
    groups_json = json.dumps(groups)
    tier_nodes_json = json.dumps(tier_nodes)

    description = data.get("metadata", {}).get("description", "Interactive knowledge graph")

    html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <link rel="icon" href="data:,">
    <script src="//unpkg.com/3d-force-graph"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #0a0a1a 0%, #1a1a2e 50%, #0a0a1a 100%);
            overflow: hidden;
        }}
        .container {{
            display: flex;
            height: 100vh;
            width: 100vw;
        }}
        #graph-wrapper {{
            flex: 1;
            position: relative;
            overflow: hidden;
        }}
        #graph {{
            width: 100%;
            height: 100%;
        }}

        /* Concentric ring guides (subtle) */
        .ring-guide {{
            position: absolute;
            border: 1px solid rgba(255,255,255,0.03);
            border-radius: 50%;
            pointer-events: none;
            transform: translate(-50%, -50%);
            left: 50%;
            top: 50%;
        }}

        /* Legend */
        #legend {{
            position: absolute;
            bottom: 20px;
            left: 20px;
            background: rgba(0,0,0,0.7);
            backdrop-filter: blur(10px);
            border-radius: 12px;
            padding: 16px;
            color: white;
            font-size: 12px;
            z-index: 100;
            max-width: 280px;
        }}
        #legend h3 {{
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #888;
            margin-bottom: 12px;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 8px;
        }}
        .legend-ring {{
            width: 24px;
            height: 24px;
            border-radius: 50%;
            border: 2px solid;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 9px;
            font-weight: 600;
        }}
        .legend-label {{
            flex: 1;
            color: #ccc;
        }}

        /* Tier labels on rings */
        .tier-label {{
            position: absolute;
            color: rgba(255,255,255,0.15);
            font-size: 10px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 2px;
            pointer-events: none;
            transform: translate(-50%, -50%);
            left: 50%;
        }}

        /* Sidebar */
        #sidebar {{
            width: 360px;
            min-width: 360px;
            background: rgba(255,255,255,0.98);
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            z-index: 100;
            box-shadow: -4px 0 20px rgba(0,0,0,0.3);
        }}
        #sidebar.hidden {{
            transform: translateX(100%);
        }}
        #sidebar-toggle {{
            position: fixed;
            right: 360px;
            top: 50%;
            transform: translateY(-50%);
            width: 28px;
            height: 64px;
            background: linear-gradient(135deg, #1a365d, #2d4a7c);
            border: none;
            border-radius: 8px 0 0 8px;
            color: white;
            cursor: pointer;
            z-index: 101;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
            transition: all 0.3s ease;
        }}
        #sidebar-toggle.sidebar-hidden {{
            right: 0;
        }}
        #sidebar-toggle:hover {{
            background: linear-gradient(135deg, #2d4a7c, #3d5a8c);
            width: 32px;
        }}

        .header {{
            background: linear-gradient(135deg, #1a365d, #2d4a7c);
            color: white;
            padding: 24px;
            text-align: center;
        }}
        .header h1 {{
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 6px;
        }}
        .header p {{
            font-size: 12px;
            opacity: 0.8;
        }}

        #info-panel {{
            padding: 24px;
            flex: 1;
        }}
        .info-placeholder {{
            color: #666;
            text-align: center;
            padding: 40px 20px;
        }}
        .info-placeholder p {{
            margin-bottom: 12px;
            line-height: 1.6;
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
            gap: 14px;
            margin-bottom: 18px;
            padding-bottom: 18px;
            border-bottom: 2px solid #e0e0e0;
        }}
        .node-logo {{
            width: 56px;
            height: 56px;
            object-fit: contain;
            border-radius: 8px;
            background: #f8f9fa;
            padding: 6px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .node-logo[src=""], .node-logo:not([src]) {{
            display: none;
        }}
        .node-title {{
            font-size: 18px;
            font-weight: 600;
            color: #1a365d;
            margin-bottom: 6px;
        }}
        .node-tier {{
            display: inline-block;
            padding: 5px 14px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 600;
            color: white;
        }}
        .node-description {{
            color: #444;
            line-height: 1.7;
            margin-bottom: 18px;
            font-size: 14px;
        }}

        .connections-header {{
            font-size: 12px;
            font-weight: 600;
            color: #888;
            margin-bottom: 12px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .connection-list {{
            list-style: none;
        }}
        .connection-item {{
            padding: 12px 14px;
            margin-bottom: 8px;
            background: #f8f9fa;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.2s ease;
            border-left: 4px solid #e0e0e0;
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .connection-item:hover {{
            background: #e8f4fd;
            border-left-color: #3182ce;
            transform: translateX(4px);
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }}
        .connection-item .conn-logo {{
            width: 36px;
            height: 36px;
            object-fit: contain;
            border-radius: 6px;
            background: #fff;
            padding: 3px;
        }}
        .connection-item .conn-logo[src=""] {{
            display: none;
        }}
        .connection-item .name {{
            font-weight: 500;
            color: #1a365d;
            margin-bottom: 2px;
        }}
        .connection-item .relation {{
            font-size: 11px;
            color: #666;
        }}

        /* Toolbar */
        #toolbar {{
            position: absolute;
            top: 16px;
            left: 16px;
            background: rgba(0, 0, 0, 0.75);
            backdrop-filter: blur(10px);
            padding: 10px 14px;
            border-radius: 10px;
            z-index: 1000;
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .toolbar-section {{
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .toolbar-divider {{
            width: 1px;
            height: 24px;
            background: rgba(255,255,255,0.2);
        }}
        .view-btn {{
            padding: 8px 16px;
            border: 1px solid rgba(255,255,255,0.3);
            background: transparent;
            color: white;
            font-weight: 500;
            font-size: 12px;
            cursor: pointer;
            border-radius: 6px;
            transition: all 0.2s;
        }}
        .view-btn.active {{
            background: white;
            color: #1a365d;
            border-color: white;
        }}
        .view-btn:hover:not(.active) {{
            background: rgba(255,255,255,0.1);
        }}

        /* Focus indicator */
        #focus-indicator {{
            position: absolute;
            top: 16px;
            right: 380px;
            background: rgba(0,0,0,0.75);
            backdrop-filter: blur(10px);
            padding: 10px 16px;
            border-radius: 10px;
            color: white;
            font-size: 13px;
            z-index: 100;
            display: none;
        }}
        #focus-indicator.active {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        #focus-indicator .reset-btn {{
            background: rgba(255,255,255,0.2);
            border: none;
            color: white;
            padding: 4px 10px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 11px;
        }}
        #focus-indicator .reset-btn:hover {{
            background: rgba(255,255,255,0.3);
        }}
    </style>
</head>
<body>
    <div class="container">
        <div id="graph-wrapper">
            <div id="graph"></div>

            <div id="toolbar">
                <div class="toolbar-section">
                    <button class="view-btn active" id="btn-radial" onclick="setLayout('radial')">Radial</button>
                    <button class="view-btn" id="btn-force" onclick="setLayout('force')">Force</button>
                </div>
                <div class="toolbar-divider"></div>
                <div class="toolbar-section">
                    <button class="view-btn" id="btn-2d" onclick="setDimension(2)">2D</button>
                    <button class="view-btn active" id="btn-3d" onclick="setDimension(3)">3D</button>
                </div>
            </div>

            <div id="focus-indicator">
                <span>Focused on: <strong id="focus-name"></strong></span>
                <button class="reset-btn" onclick="resetFocus()">Show All</button>
            </div>

            <div id="legend">
                <h3>Ecosystem Tiers</h3>
                <div class="legend-item">
                    <div class="legend-ring" style="border-color: #1a365d; background: rgba(26,54,93,0.3);">●</div>
                    <span class="legend-label">Central Hub</span>
                </div>
                <div class="legend-item">
                    <div class="legend-ring" style="border-color: #2f855a; background: rgba(47,133,90,0.2);">1</div>
                    <span class="legend-label">Core Industry Associations</span>
                </div>
                <div class="legend-item">
                    <div class="legend-ring" style="border-color: #3182ce; background: rgba(49,130,206,0.2);">2</div>
                    <span class="legend-label">Broader & Emerging Partners</span>
                </div>
                <div class="legend-item">
                    <div class="legend-ring" style="border-color: #805ad5; background: rgba(128,90,213,0.2);">3</div>
                    <span class="legend-label">Specialized SMEs</span>
                </div>
                <div class="legend-item">
                    <div class="legend-ring" style="border-color: #e53e3e; background: rgba(229,62,62,0.2);">4</div>
                    <span class="legend-label">Industry Members</span>
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
                    <p><strong>Explore the Ecosystem</strong></p>
                    <p>Click on any node to see details and connections. Double-click to focus on that entity's network.</p>
                    <p style="margin-top: 20px; font-size: 11px; color: #999;">
                        Drag to rotate • Scroll to zoom • Right-drag to pan
                    </p>
                </div>
                <div class="node-info" id="node-info">
                    <div class="node-header">
                        <img id="node-logo" class="node-logo" src="" alt="">
                        <div>
                            <div class="node-title" id="node-title"></div>
                            <div class="node-tier" id="node-tier"></div>
                        </div>
                    </div>
                    <div class="node-description" id="node-description"></div>
                    <div class="connections-header">Connected Entities</div>
                    <ul class="connection-list" id="connections"></ul>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Data
        const nodesData = {nodes_json};
        const linksData = {links_json};
        const groupsData = {groups_json};
        const tierNodes = {tier_nodes_json};

        // Configuration
        const RING_SPACING = 120;  // Distance between concentric rings
        const HUB_RADIUS = 0;      // Center position for hub

        // Create lookups
        const nodeMap = {{}};
        nodesData.forEach(node => {{ nodeMap[node.id] = node; }});

        const linksByNode = {{}};
        linksData.forEach(link => {{
            const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
            const targetId = typeof link.target === 'object' ? link.target.id : link.target;
            if (!linksByNode[sourceId]) linksByNode[sourceId] = [];
            if (!linksByNode[targetId]) linksByNode[targetId] = [];
            linksByNode[sourceId].push({{ nodeId: targetId, relationType: link.relationType }});
            linksByNode[targetId].push({{ nodeId: sourceId, relationType: link.relationType }});
        }});

        let graph;
        let selectedNode = null;
        let focusedNode = null;
        let currentLayout = 'radial';
        let currentDimension = 3;
        let sidebarVisible = true;

        // Calculate radial positions for nodes
        function calculateRadialPositions() {{
            const positions = {{}};
            const maxTier = Math.max(...Object.keys(tierNodes).map(Number));

            for (const [tier, nodeIds] of Object.entries(tierNodes)) {{
                const tierNum = parseInt(tier);
                const radius = tierNum === 0 ? HUB_RADIUS : tierNum * RING_SPACING;
                const count = nodeIds.length;

                nodeIds.forEach((nodeId, index) => {{
                    if (tierNum === 0) {{
                        // Hub at center
                        positions[nodeId] = {{ x: 0, y: 0, z: 0 }};
                    }} else {{
                        // Distribute evenly on ring with slight randomization for 3D depth
                        const angle = (2 * Math.PI * index) / count - Math.PI / 2;
                        const zOffset = (Math.random() - 0.5) * 30; // Slight 3D variation
                        positions[nodeId] = {{
                            x: radius * Math.cos(angle),
                            y: radius * Math.sin(angle),
                            z: zOffset
                        }};
                    }}
                }});
            }}
            return positions;
        }}

        // Apply radial layout
        function applyRadialLayout() {{
            const positions = calculateRadialPositions();
            const nodes = graph.graphData().nodes;
            const links = graph.graphData().links;

            // Set fixed positions for all nodes
            nodes.forEach(node => {{
                const pos = positions[node.id];
                if (pos) {{
                    node.x = pos.x;
                    node.y = pos.y;
                    node.z = pos.z;
                    node.fx = pos.x;
                    node.fy = pos.y;
                    node.fz = pos.z;
                }}
            }});

            // Re-set the graph data to apply positions
            graph.graphData({{ nodes: [...nodes], links: [...links] }});

            // Zoom to fit after a short delay
            setTimeout(() => {{
                graph.cameraPosition({{ x: 0, y: 0, z: 600 }}, {{ x: 0, y: 0, z: 0 }}, 1000);
            }}, 200);
        }}

        // Release force layout
        function applyForceLayout() {{
            const nodes = graph.graphData().nodes;
            nodes.forEach(node => {{
                node.fx = undefined;
                node.fy = undefined;
                node.fz = undefined;
            }});
            graph.graphData({{ nodes, links: graph.graphData().links }});
            graph.d3ReheatSimulation();
        }}

        function setLayout(layout) {{
            currentLayout = layout;
            document.getElementById('btn-radial').classList.toggle('active', layout === 'radial');
            document.getElementById('btn-force').classList.toggle('active', layout === 'force');

            if (layout === 'radial') {{
                applyRadialLayout();
            }} else {{
                applyForceLayout();
            }}
        }}

        function setDimension(dim) {{
            currentDimension = dim;
            document.getElementById('btn-2d').classList.toggle('active', dim === 2);
            document.getElementById('btn-3d').classList.toggle('active', dim === 3);
            graph.numDimensions(dim);

            if (dim === 2) {{
                graph.cameraPosition({{ x: 0, y: 0, z: 600 }}, {{ x: 0, y: 0, z: 0 }}, 1000);
            }}
        }}

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

            setTimeout(() => {{
                const wrapper = document.getElementById('graph-wrapper');
                graph.width(wrapper.offsetWidth).height(wrapper.offsetHeight);
            }}, 350);
        }}

        // Node click handling
        let lastClickTime = 0;
        let lastClickNode = null;
        const DOUBLE_CLICK_DELAY = 300;

        function handleNodeClick(node) {{
            const now = Date.now();

            // Always select on click
            selectNode(node);

            // Check for double-click
            if (lastClickNode === node && (now - lastClickTime) < DOUBLE_CLICK_DELAY) {{
                focusOnNode(node);
            }}

            lastClickNode = node;
            lastClickTime = now;
        }}

        function selectNode(node) {{
            selectedNode = node;

            // Post message to parent (for embed mode)
            if (window.parent !== window) {{
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
            }}

            // Update sidebar
            document.getElementById('placeholder').style.display = 'none';
            document.getElementById('node-info').classList.add('active');
            document.getElementById('node-title').textContent = node.name;
            document.getElementById('node-description').textContent = node.description || 'No description available.';

            const logoEl = document.getElementById('node-logo');
            logoEl.src = node.logo || '';
            logoEl.style.display = node.logo ? 'block' : 'none';

            const tierEl = document.getElementById('node-tier');
            tierEl.textContent = node.groupLabel || 'Unknown';
            tierEl.style.background = node.color;

            // Build connections
            const connections = linksByNode[node.id] || [];
            const connectionsList = document.getElementById('connections');
            connectionsList.innerHTML = '';

            // Sort connections by tier
            connections.sort((a, b) => {{
                const nodeA = nodeMap[a.nodeId];
                const nodeB = nodeMap[b.nodeId];
                return (nodeA?.tier || 99) - (nodeB?.tier || 99);
            }});

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
                li.onclick = () => navigateToNode(conn.nodeId);
                connectionsList.appendChild(li);
            }});

            // Highlight connected nodes
            updateHighlights(node);
        }}

        function updateHighlights(focusNode) {{
            const connectedIds = new Set([focusNode.id]);
            (linksByNode[focusNode.id] || []).forEach(conn => connectedIds.add(conn.nodeId));

            graph
                .nodeColor(n => {{
                    if (n.id === focusNode.id) return n.color;
                    if (connectedIds.has(n.id)) return n.color;
                    return '#333333';
                }})
                .nodeOpacity(n => {{
                    if (n.id === focusNode.id) return 1;
                    if (connectedIds.has(n.id)) return 0.9;
                    return 0.3;
                }})
                .linkOpacity(link => {{
                    const sId = typeof link.source === 'object' ? link.source.id : link.source;
                    const tId = typeof link.target === 'object' ? link.target.id : link.target;
                    return (sId === focusNode.id || tId === focusNode.id) ? 0.8 : 0.1;
                }});
        }}

        function focusOnNode(node) {{
            focusedNode = node;
            document.getElementById('focus-name').textContent = node.name;
            document.getElementById('focus-indicator').classList.add('active');

            // Filter to show only this node and its connections
            const connectedIds = new Set([node.id]);
            (linksByNode[node.id] || []).forEach(conn => connectedIds.add(conn.nodeId));

            const filteredNodes = nodesData.filter(n => connectedIds.has(n.id));
            const filteredLinks = linksData.filter(link => {{
                const sId = typeof link.source === 'object' ? link.source.id : link.source;
                const tId = typeof link.target === 'object' ? link.target.id : link.target;
                return sId === node.id || tId === node.id;
            }});

            graph.graphData({{ nodes: filteredNodes, links: filteredLinks }});

            if (currentLayout === 'radial') {{
                setTimeout(() => applyRadialLayout(), 100);
            }}

            graph.zoomToFit(500, 50);
        }}

        function resetFocus() {{
            focusedNode = null;
            document.getElementById('focus-indicator').classList.remove('active');

            graph.graphData({{ nodes: nodesData, links: linksData }});

            if (currentLayout === 'radial') {{
                setTimeout(() => applyRadialLayout(), 100);
            }}

            // Reset colors
            graph
                .nodeColor(n => n.color)
                .nodeOpacity(1)
                .linkOpacity(0.6);
        }}

        function navigateToNode(nodeId) {{
            const node = nodeMap[nodeId];
            if (node) {{
                selectNode(node);
                graph.cameraPosition(
                    {{ x: node.x, y: node.y, z: 300 }},
                    node,
                    500
                );
            }}
        }}

        function clearSelection() {{
            selectedNode = null;
            lastClickNode = null;

            if (window.parent !== window) {{
                window.parent.postMessage({{ type: 'nodeDeselected' }}, '*');
            }}

            document.getElementById('placeholder').style.display = 'block';
            document.getElementById('node-info').classList.remove('active');

            // Reset colors
            graph
                .nodeColor(n => n.color)
                .nodeOpacity(1)
                .linkOpacity(0.6);
        }}

        // Initialize
        function initGraph() {{
            const container = document.getElementById('graph');
            const wrapper = document.getElementById('graph-wrapper');

            graph = ForceGraph3D()(container)
                .width(wrapper.offsetWidth)
                .height(wrapper.offsetHeight)
                .graphData({{ nodes: nodesData, links: linksData }})
                .backgroundColor('rgba(0,0,0,0)')
                .nodeLabel(node => `<div style="background: rgba(0,0,0,0.8); padding: 6px 10px; border-radius: 4px; color: white; font-size: 12px;">${{node.name}}</div>`)
                .nodeVal(node => {{
                    // Size based on tier - hub biggest, tier 4 smallest
                    const tierSizes = {{ 0: 40, 1: 25, 2: 18, 3: 14, 4: 10 }};
                    return tierSizes[node.tier] || 12;
                }})
                .nodeRelSize(5)
                .nodeColor(node => node.color)
                .nodeOpacity(0.95)
                .linkColor(link => link.color)
                .linkWidth(link => link.width)
                .linkOpacity(0.6)
                .linkCurvature(0.2)  // Curved edges for better readability
                .linkDirectionalParticles(link => {{
                    // Particles on important connections
                    return link.edgeType === 'strategic_partner' ? 2 : 0;
                }})
                .linkDirectionalParticleWidth(2)
                .linkDirectionalParticleSpeed(0.005)
                .onNodeClick(handleNodeClick)
                .onBackgroundClick(clearSelection)
                .enableNodeDrag(false)  // Disable for radial layout
                .cooldownTicks(0);  // Start with no simulation - we position manually

            // Apply radial layout after initialization
            setTimeout(() => {{
                applyRadialLayout();
            }}, 500);

            // Handle resize
            window.addEventListener('resize', () => {{
                graph.width(wrapper.offsetWidth).height(wrapper.offsetHeight);
            }});
        }}

        // Check for embed mode
        function checkEmbedMode() {{
            const urlParams = new URLSearchParams(window.location.search);
            if (urlParams.get('embed') === 'true') {{
                document.getElementById('sidebar').style.display = 'none';
                document.getElementById('sidebar-toggle').style.display = 'none';
                document.getElementById('legend').style.display = 'none';
                setTimeout(() => {{
                    const wrapper = document.getElementById('graph-wrapper');
                    graph.width(wrapper.offsetWidth).height(wrapper.offsetHeight);
                }}, 100);
            }}
        }}

        // Start
        initGraph();
        checkEmbedMode();
    </script>
</body>
</html>'''

    return html


def generate_visualization(input_path: str, output_path: str) -> str:
    """Generate a radial visualization from JSON data."""
    data = load_json_data(input_path)
    metadata = data.get("metadata", {})
    title = metadata.get("title", "Knowledge Graph")

    print(f"Loaded graph: {len(data['nodes'])} nodes, {len(data['edges'])} edges")

    html = generate_radial_html(data, title)

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as f:
        f.write(html)

    print(f"Generated radial visualization: {output_file}")
    return str(output_file)


def main():
    parser = argparse.ArgumentParser(description="Generate radial knowledge graph visualization")
    parser.add_argument("--input", "-i", required=True, help="Input JSON file")
    parser.add_argument("--output", "-o", required=True, help="Output HTML file")
    args = parser.parse_args()
    generate_visualization(args.input, args.output)


if __name__ == "__main__":
    main()
