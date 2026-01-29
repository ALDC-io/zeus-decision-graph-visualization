#!/usr/bin/env python3
"""
Network Graph Visualization Generator - 3D Version

Generates interactive 3D network visualizations with:
- True 3D space with orbit controls (rotate, zoom, pan)
- Toggle between 2D and 3D views
- Click-to-show info panel
- Navigation through connected nodes
- Nodes positioned by tier in spherical shells

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

    # Prepare nodes JSON with 3D positions based on tier
    nodes_list = []
    tier_counts = {}  # Track count per tier for positioning

    for node in data["nodes"]:
        node_id = node["id"]
        group = node.get("group", "default")
        tier = node.get("tier", 0)
        group_info = groups.get(group, {"color": "#888888", "label": group})

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
        })

    # Prepare links JSON with relationship type labels
    # Default edge styles - can be overridden by data
    edge_styles = {
        "references": {"color": "#3182ce", "width": 2, "label": "References"},
        "informs": {"color": "#2f855a", "width": 2, "label": "Informs"},
        "related": {"color": "#a0aec0", "width": 1, "label": "Related"},
        "strategic_partner": {"color": "#2f855a", "width": 3, "label": "Strategic Partner"},
        "emerging_partner": {"color": "#3182ce", "width": 2, "label": "Emerging Partner"},
        "sme_expert": {"color": "#805ad5", "width": 2, "label": "SME Expert"},
        "collaboration": {"color": "#a0aec0", "width": 1, "label": "Collaboration"},
        "member": {"color": "#718096", "width": 1, "label": "Association Member"},
        "direct_partner": {"color": "#e53e3e", "width": 2, "label": "Direct Partner"},
        "supply_chain": {"color": "#dd6b20", "width": 1, "label": "Supply Chain"},
    }

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
        })

    nodes_json = json.dumps(nodes_list)
    links_json = json.dumps(links_list)
    groups_json = json.dumps(groups)

    # Generate dynamic legend items from groups
    legend_items_html = ""
    for group_id, group_info in groups.items():
        color = group_info.get("color", "#888888")
        label = group_info.get("label", group_id)
        legend_items_html += f'''<label class="legend-item"><input type="checkbox" checked data-group="{group_id}"><span class="legend-color" style="background:{color}"></span> {label}</label>\n                    '''

    # Get description from metadata
    description = data.get("metadata", {}).get("description", "Click a node to explore")

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
            margin-bottom: 20px;
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
            transition: all 0.2s;
            border-left: 4px solid #e0e0e0;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .connection-item:hover {{
            background: #e8f4fd;
            border-left-color: #3182ce;
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
        #legend {{
            position: absolute;
            bottom: 20px;
            left: 20px;
            background: rgba(255, 255, 255, 0.95);
            padding: 15px 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.3);
            z-index: 10000;
            pointer-events: auto;
        }}
        .legend-title {{
            font-size: 12px;
            font-weight: 600;
            color: #666;
            margin-bottom: 10px;
            text-transform: uppercase;
        }}
        .legend-items {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px 20px;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            font-size: 11px;
            color: #333;
            cursor: pointer;
            padding: 4px 8px;
            border-radius: 4px;
            transition: all 0.2s;
        }}
        .legend-item:hover {{
            background: rgba(0,0,0,0.05);
        }}
        .legend-item.disabled {{
            opacity: 0.4;
        }}
        .legend-item input {{
            margin-right: 6px;
            cursor: pointer;
        }}
        .legend-color {{
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 6px;
        }}
        .filter-controls {{
            margin-top: 10px;
            padding-top: 10px;
            border-top: 1px solid #e0e0e0;
            display: flex;
            gap: 10px;
        }}
        .filter-btn {{
            font-size: 10px;
            padding: 4px 8px;
            border: 1px solid #ccc;
            background: white;
            border-radius: 4px;
            cursor: pointer;
        }}
        .filter-btn:hover {{
            background: #f0f0f0;
        }}
        #view-toggle {{
            position: absolute;
            top: 20px;
            left: 20px;
            background: rgba(255, 255, 255, 0.95);
            padding: 10px 15px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.3);
            z-index: 10000;
            pointer-events: auto;
            display: flex;
            gap: 10px;
        }}
        .view-btn {{
            padding: 8px 16px;
            border: 2px solid #1a365d;
            background: white;
            color: #1a365d;
            font-weight: 600;
            font-size: 12px;
            cursor: pointer;
            border-radius: 6px;
            transition: all 0.2s;
        }}
        .view-btn.active {{
            background: #1a365d;
            color: white;
        }}
        .view-btn:hover:not(.active) {{
            background: #e8f4fd;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div id="graph-wrapper">
            <div id="graph"></div>
            <div id="view-toggle">
                <button class="view-btn active" id="btn-3d" onclick="setView('3d')">3D</button>
                <button class="view-btn" id="btn-2d" onclick="setView('2d')">2D</button>
            </div>
            <div id="legend">
                <div class="legend-title">Filter by Type (click to toggle)</div>
                <div class="legend-items">
                    {legend_items_html}
                </div>
                <div class="filter-controls">
                    <button class="filter-btn" onclick="showAll()">Show All</button>
                    <button class="filter-btn" onclick="hideAll()">Hide All</button>
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
                    <div class="node-description" id="node-description"></div>
                    <div class="connections-header">Connected Nodes</div>
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

        // Double-click detection
        let lastClickTime = 0;
        let lastClickNode = null;
        const DOUBLE_CLICK_DELAY = 300;

        function handleNodeClick(node) {{
            const now = Date.now();
            if (lastClickNode === node && (now - lastClickTime) < DOUBLE_CLICK_DELAY) {{
                // Double click detected
                focusNodeIn2D(node);
                lastClickNode = null;
                lastClickTime = 0;
            }} else {{
                // Single click
                lastClickNode = node;
                lastClickTime = now;
                // Delay single-click action to check for double-click
                setTimeout(() => {{
                    if (lastClickNode === node) {{
                        selectNodeOnly(node);
                    }}
                }}, DOUBLE_CLICK_DELAY);
            }}
        }}

        // Track which groups are visible - initialize from data
        const allGroups = Object.keys(groupsData);
        const visibleGroups = new Set(allGroups);

        // Attach event listeners to legend checkboxes
        document.querySelectorAll('#legend input[type="checkbox"]').forEach(cb => {{
            cb.addEventListener('change', function() {{
                const group = this.dataset.group;
                if (this.checked) {{
                    visibleGroups.add(group);
                }} else {{
                    visibleGroups.delete(group);
                }}
                applyFilters();
            }});
        }});

        function showAll() {{
            allGroups.forEach(g => visibleGroups.add(g));
            updateCheckboxes();
            applyFilters();
        }}

        function hideAll() {{
            visibleGroups.clear();
            updateCheckboxes();
            applyFilters();
        }}

        function updateCheckboxes() {{
            document.querySelectorAll('#legend input[type="checkbox"]').forEach(cb => {{
                const group = cb.dataset.group;
                cb.checked = visibleGroups.has(group);
            }});
        }}

        function applyFilters() {{
            const filteredNodes = nodesData.filter(node => visibleGroups.has(node.group));
            const filteredNodeIds = new Set(filteredNodes.map(n => n.id));

            const filteredLinks = linksData.filter(link => {{
                const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
                const targetId = typeof link.target === 'object' ? link.target.id : link.target;
                return filteredNodeIds.has(sourceId) && filteredNodeIds.has(targetId);
            }});

            graph.graphData({{
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
                }});

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
        }}

        // Single click - just select and populate sidebar
        function selectNodeOnly(node) {{
            selectedNode = node;

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
            document.getElementById('node-description').textContent = node.description || 'No description available.';

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
                li.addEventListener('click', function(e) {{
                    e.preventDefault();
                    e.stopPropagation();
                    const targetNode = graph.graphData().nodes.find(n => n.id === conn.nodeId);
                    if (targetNode) {{
                        selectNodeOnly(targetNode);
                        // Pan to the node
                        graph.cameraPosition(
                            {{ x: targetNode.x, y: targetNode.y, z: 300 }},
                            targetNode,
                            500
                        );
                    }}
                }});
                connectionsList.appendChild(li);
            }});

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

            graph.graphData({{
                nodes: filteredNodes,
                links: filteredLinks
            }});

            // Switch to 2D and center
            setView('2d');

            // Update sidebar
            selectNode(graph.graphData().nodes.find(n => n.id === node.id));

            // Fit view after a short delay
            setTimeout(() => {{
                graph.zoomToFit(500, 50);
            }}, 100);
        }}

        // Initialize
        initGraph();
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
