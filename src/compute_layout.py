#!/usr/bin/env python3
"""
Zeus Memory Layout Computation - Phase 2

Pre-computes (x, y) positions for clustered memories using ForceAtlas2.
Creates layouts at multiple hierarchy levels for semantic zoom.

Usage:
    source venv/bin/activate
    python src/compute_layout.py
"""

import json
import numpy as np
from pathlib import Path
from fa2_modified import ForceAtlas2
import networkx as nx
from collections import defaultdict
from datetime import datetime


def load_clustering_results(filepath="data/clustering_results.json"):
    """Load clustering results from Phase 1."""
    print(f"Loading clustering results from {filepath}...")
    with open(filepath, 'r') as f:
        data = json.load(f)
    print(f"Loaded {len(data['memories'])} memories in {len(data['clusters']['l1'])} L1 clusters")
    return data


def build_cluster_graph(clustering_data, level='l1'):
    """Build a NetworkX graph of cluster centroids for layout computation."""
    print(f"Building {level.upper()} cluster graph...")

    if level == 'l1':
        # Build graph of L1 clusters
        clusters = clustering_data['clusters']['l1']

        # Create nodes for each cluster
        G = nx.Graph()
        for cluster_id, info in clusters.items():
            G.add_node(cluster_id, size=info['size'])

        # Create edges between clusters that share similar memories
        # (approximated by looking at memories assigned to adjacent cluster IDs)
        memory_clusters = {m['id']: m['cluster_l1'] for m in clustering_data['memories']}

        # Simple heuristic: connect clusters with sequential IDs (they were likely similar)
        cluster_ids = sorted([int(c) for c in clusters.keys()])
        for i, cid in enumerate(cluster_ids[:-1]):
            next_cid = cluster_ids[i + 1]
            # Connect if clusters are "close" in ID space (heuristic for similarity)
            if next_cid - cid < 10:
                G.add_edge(str(cid), str(next_cid), weight=1.0)

        print(f"Built L1 graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    elif level == 'l2':
        # Build graph of L2 clusters
        clusters = clustering_data['clusters']['l2']

        G = nx.Graph()
        for cluster_id, info in clusters.items():
            G.add_node(cluster_id, size=info['total_size'])

        # Connect L2 clusters that share L1 sub-clusters
        cluster_ids = sorted([int(c) for c in clusters.keys()])
        for i, cid in enumerate(cluster_ids[:-1]):
            next_cid = cluster_ids[i + 1]
            if next_cid - cid < 5:
                G.add_edge(str(cid), str(next_cid), weight=1.0)

        print(f"Built L2 graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    return G


def compute_forceatlas2_layout(G, iterations=1000, scale_ratio=10.0):
    """Compute ForceAtlas2 layout for a graph."""
    print(f"Computing ForceAtlas2 layout ({iterations} iterations)...")

    if G.number_of_nodes() == 0:
        return {}

    # Initialize ForceAtlas2
    forceatlas2 = ForceAtlas2(
        # Behavior alternatives
        outboundAttractionDistribution=True,
        linLogMode=False,
        adjustSizes=False,
        edgeWeightInfluence=1.0,

        # Performance
        jitterTolerance=1.0,
        barnesHutOptimize=True,
        barnesHutTheta=1.2,

        # Tuning
        scalingRatio=scale_ratio,
        strongGravityMode=False,
        gravity=1.0,

        # Verbose
        verbose=True
    )

    # Get positions
    positions = forceatlas2.forceatlas2_networkx_layout(
        G,
        pos=None,
        iterations=iterations
    )

    print(f"Computed positions for {len(positions)} nodes")
    return positions


def compute_memory_positions(clustering_data, l1_positions):
    """Compute positions for individual memories based on their cluster positions."""
    print("Computing memory positions from cluster centroids...")

    memory_positions = {}

    # Group memories by L1 cluster
    cluster_memories = defaultdict(list)
    for mem in clustering_data['memories']:
        cluster_memories[str(mem['cluster_l1'])].append(mem['id'])

    # Position memories around their cluster centroid
    for cluster_id, mem_ids in cluster_memories.items():
        if cluster_id not in l1_positions:
            continue

        cx, cy = l1_positions[cluster_id]
        n = len(mem_ids)

        # Distribute memories in a circle around centroid
        for i, mem_id in enumerate(mem_ids):
            if n == 1:
                memory_positions[mem_id] = (cx, cy)
            else:
                angle = 2 * np.pi * i / n
                radius = min(20, np.sqrt(n) * 2)  # Scale radius with cluster size
                x = cx + radius * np.cos(angle)
                y = cy + radius * np.sin(angle)
                memory_positions[mem_id] = (x, y)

    print(f"Computed positions for {len(memory_positions)} memories")
    return memory_positions


def save_layout_results(clustering_data, l1_positions, l2_positions, memory_positions, output_path):
    """Save layout results to JSON."""
    print(f"Saving layout results to {output_path}...")

    results = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "total_memories": len(memory_positions),
            "l1_clusters": len(l1_positions),
            "l2_clusters": len(l2_positions),
        },
        "positions": {
            "l1_clusters": {k: {"x": v[0], "y": v[1]} for k, v in l1_positions.items()},
            "l2_clusters": {k: {"x": v[0], "y": v[1]} for k, v in l2_positions.items()},
            "memories": {k: {"x": v[0], "y": v[1]} for k, v in memory_positions.items()},
        },
        "clusters": clustering_data['clusters'],
    }

    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"Saved layout for {len(memory_positions)} memories")
    return results


def main():
    print("=" * 60)
    print("Zeus Memory Layout Computation - Phase 2")
    print("=" * 60)

    # Load clustering results
    clustering_data = load_clustering_results()

    # Build and layout L2 clusters (high level)
    G_l2 = build_cluster_graph(clustering_data, level='l2')
    l2_positions = compute_forceatlas2_layout(G_l2, iterations=500, scale_ratio=50.0)

    # Build and layout L1 clusters (detailed)
    G_l1 = build_cluster_graph(clustering_data, level='l1')
    l1_positions = compute_forceatlas2_layout(G_l1, iterations=1000, scale_ratio=20.0)

    # Compute individual memory positions
    memory_positions = compute_memory_positions(clustering_data, l1_positions)

    # Save results
    output_path = "data/layout_results.json"
    save_layout_results(
        clustering_data, l1_positions, l2_positions, memory_positions, output_path
    )

    print("\n" + "=" * 60)
    print("LAYOUT COMPUTATION COMPLETE")
    print("=" * 60)
    print(f"L2 cluster positions: {len(l2_positions)}")
    print(f"L1 cluster positions: {len(l1_positions)}")
    print(f"Memory positions: {len(memory_positions)}")
    print(f"Results saved to: {output_path}")


if __name__ == "__main__":
    main()
