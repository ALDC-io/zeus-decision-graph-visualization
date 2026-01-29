#!/usr/bin/env python3
"""
Zeus Memory Clustering - Phase 1

Clusters Zeus memories using the Leiden algorithm on a k-NN graph
built from pgvector embeddings.

This creates a hierarchical structure:
- Level 1: ~100-500 topic clusters
- Level 2: ~10-50 domain clusters
- Level 3: ~5-15 theme clusters

Usage:
    source venv/bin/activate
    python src/cluster_memories.py
"""

import os
import json
import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor
import igraph as ig
import leidenalg
from collections import defaultdict
from datetime import datetime

# Database connection
DB_CONFIG = {
    'host': 'psql-zeus-memory-dev.postgres.database.azure.com',
    'port': '5432',
    'database': 'zeus_core',
    'user': 'zeus_admin',
    'password': 'ZeusMemory2024Db',
    'sslmode': 'require'
}

TENANT_ID = os.environ.get('ZEUS_TENANT_ID', 'b513bc6e-ad51-4a11-bea3-e3b1a84d7b55')

# Clustering parameters
KNN_K = 15  # Number of nearest neighbors for graph construction
SIMILARITY_THRESHOLD = 0.7  # Minimum similarity to create edge
MAX_MEMORIES = 50000  # Limit for initial testing (increase for full run)


def get_db_connection():
    """Get database connection."""
    return psycopg2.connect(**DB_CONFIG)


def fetch_memories_with_embeddings(limit=MAX_MEMORIES):
    """Fetch memories that have embeddings."""
    print(f"Fetching up to {limit} memories with embeddings...")

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Get memories with voyage embeddings (1024 dimensions)
    cur.execute("""
        SELECT
            memory_id::text as id,
            content,
            source,
            metadata,
            metadata->>'category' as category,
            created_at,
            embedding_voyage
        FROM zeus_core.memories
        WHERE tenant_id = %s
          AND embedding_voyage IS NOT NULL
        ORDER BY created_at DESC
        LIMIT %s
    """, (TENANT_ID, limit))

    memories = cur.fetchall()
    cur.close()
    conn.close()

    print(f"Fetched {len(memories)} memories with embeddings")
    return memories


def parse_embedding(emb):
    """Parse embedding from various formats (list, string, numpy array)."""
    if emb is None:
        return None
    if isinstance(emb, (list, np.ndarray)):
        return np.array(emb, dtype=np.float32)
    if isinstance(emb, str):
        # Handle string representation like "[0.1, 0.2, ...]"
        emb = emb.strip('[]')
        return np.array([float(x) for x in emb.split(',')], dtype=np.float32)
    return None


def build_knn_graph(memories, k=KNN_K, threshold=SIMILARITY_THRESHOLD):
    """Build k-NN graph from memory embeddings using cosine similarity."""
    print(f"Building k-NN graph (k={k}, threshold={threshold})...")

    n = len(memories)

    # Extract and parse embeddings as numpy array
    print("  Parsing embeddings...")
    parsed_embeddings = []
    valid_indices = []
    for i, m in enumerate(memories):
        emb = parse_embedding(m['embedding_voyage'])
        if emb is not None and len(emb) == 1024:
            parsed_embeddings.append(emb)
            valid_indices.append(i)

    print(f"  Parsed {len(parsed_embeddings)} valid embeddings out of {n}")

    if len(parsed_embeddings) == 0:
        return [], [], []

    embeddings = np.array(parsed_embeddings)
    n_valid = len(embeddings)

    # Normalize for cosine similarity
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1  # Avoid division by zero
    embeddings_normalized = embeddings / norms

    # Build edges list
    edges = []
    weights = []

    # For each memory, find k nearest neighbors
    batch_size = 1000
    for start in range(0, n_valid, batch_size):
        end = min(start + batch_size, n_valid)
        batch = embeddings_normalized[start:end]

        # Compute similarities with all other memories
        similarities = np.dot(batch, embeddings_normalized.T)

        for i, row in enumerate(similarities):
            global_i = start + i

            # Get top-k neighbors (excluding self)
            row[global_i] = -1  # Exclude self
            top_k_indices = np.argsort(row)[-k:]

            for j in top_k_indices:
                sim = row[j]
                if sim >= threshold and global_i < j:  # Avoid duplicates
                    edges.append((global_i, j))
                    weights.append(float(sim))

        if (end) % 5000 == 0 or end == n_valid:
            print(f"  Processed {end}/{n_valid} memories...")

    print(f"Built graph with {n_valid} nodes and {len(edges)} edges")
    return edges, weights, valid_indices


def run_leiden_clustering(n_nodes, edges, weights, resolution=1.0):
    """Run Leiden algorithm for community detection."""
    print(f"Running Leiden clustering (resolution={resolution})...")

    # Create igraph graph
    g = ig.Graph(n=n_nodes, edges=edges, directed=False)
    g.es['weight'] = weights

    # Run Leiden algorithm
    partition = leidenalg.find_partition(
        g,
        leidenalg.RBConfigurationVertexPartition,
        weights='weight',
        resolution_parameter=resolution
    )

    n_clusters = len(partition)
    modularity = partition.modularity

    print(f"Found {n_clusters} clusters (modularity: {modularity:.4f})")

    # Get cluster assignments
    cluster_assignments = partition.membership

    return cluster_assignments, n_clusters


def build_cluster_hierarchy(memories, l1_assignments):
    """Build hierarchical clusters by aggregating L1 clusters."""
    print("Building cluster hierarchy...")

    # Group memories by L1 cluster
    l1_clusters = defaultdict(list)
    for i, cluster_id in enumerate(l1_assignments):
        l1_clusters[cluster_id].append(i)

    # Compute centroid embeddings for L1 clusters
    l1_centroids = {}
    for cluster_id, member_indices in l1_clusters.items():
        cluster_embeddings = []
        for i in member_indices:
            emb = parse_embedding(memories[i]['embedding_voyage'])
            if emb is not None:
                cluster_embeddings.append(emb)
        if cluster_embeddings:
            embeddings = np.array(cluster_embeddings)
            centroid = np.mean(embeddings, axis=0)
            norm = np.linalg.norm(centroid)
            if norm > 0:
                centroid = centroid / norm  # Normalize
            l1_centroids[cluster_id] = centroid

    # Build L1-to-L1 similarity graph for L2 clustering
    n_l1 = len(l1_centroids)
    l1_ids = sorted(l1_centroids.keys())
    centroid_matrix = np.array([l1_centroids[cid] for cid in l1_ids])

    # k-NN on L1 centroids
    l1_edges = []
    l1_weights = []
    similarities = np.dot(centroid_matrix, centroid_matrix.T)

    for i in range(n_l1):
        for j in range(i + 1, n_l1):
            sim = similarities[i, j]
            if sim >= 0.6:  # Lower threshold for meta-clustering
                l1_edges.append((i, j))
                l1_weights.append(float(sim))

    # Run Leiden on L1 clusters to get L2
    if len(l1_edges) > 0:
        l2_assignments, n_l2 = run_leiden_clustering(
            n_l1, l1_edges, l1_weights, resolution=0.5
        )
    else:
        # Fallback: each L1 is its own L2
        l2_assignments = list(range(n_l1))
        n_l2 = n_l1

    # Map L1 cluster IDs to L2 cluster IDs
    l1_to_l2 = {l1_ids[i]: l2_assignments[i] for i in range(n_l1)}

    print(f"Created {n_l2} L2 clusters from {n_l1} L1 clusters")

    return l1_to_l2, n_l2


def generate_cluster_labels(memories, cluster_assignments, sample_size=5):
    """Generate labels for clusters based on content samples."""
    print("Generating cluster labels...")

    # Group memories by cluster
    clusters = defaultdict(list)
    for i, cluster_id in enumerate(cluster_assignments):
        clusters[cluster_id].append(memories[i])

    labels = {}
    for cluster_id, members in clusters.items():
        # Get sample of memory types and content
        sample = members[:sample_size]
        types = [m['category'] for m in sample]

        # Extract key terms from content (simple approach)
        words = []
        for m in sample:
            content = m['content'][:200] if m['content'] else ""
            words.extend(content.split()[:10])

        # Most common type
        type_counts = defaultdict(int)
        for t in types:
            type_counts[t] += 1
        primary_type = max(type_counts.keys(), key=lambda x: type_counts[x])

        # Simple label: type + size
        labels[cluster_id] = {
            "primary_type": primary_type,
            "size": len(members),
            "sample_words": words[:20],
        }

    return labels


def save_clustering_results(memories, l1_assignments, l1_to_l2, labels, output_path):
    """Save clustering results to JSON."""
    print(f"Saving results to {output_path}...")

    results = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "total_memories": len(memories),
            "l1_clusters": len(set(l1_assignments)),
            "l2_clusters": len(set(l1_to_l2.values())),
            "parameters": {
                "knn_k": KNN_K,
                "similarity_threshold": SIMILARITY_THRESHOLD,
            }
        },
        "memories": [],
        "clusters": {
            "l1": {},
            "l2": {},
        }
    }

    # Memory assignments
    for i, memory in enumerate(memories):
        l1_id = l1_assignments[i]
        l2_id = l1_to_l2.get(l1_id, 0)

        results["memories"].append({
            "id": memory['id'],
            "category": memory['category'],
            "cluster_l1": l1_id,
            "cluster_l2": l2_id,
            "content_preview": (memory['content'][:100] + "...") if memory['content'] else "",
        })

    # Cluster info
    for cluster_id, label_info in labels.items():
        results["clusters"]["l1"][str(cluster_id)] = label_info

    # L2 cluster info
    l2_clusters = defaultdict(list)
    for l1_id, l2_id in l1_to_l2.items():
        l2_clusters[l2_id].append(l1_id)

    for l2_id, l1_ids in l2_clusters.items():
        total_size = sum(labels.get(l1_id, {}).get("size", 0) for l1_id in l1_ids)
        results["clusters"]["l2"][str(l2_id)] = {
            "l1_clusters": l1_ids,
            "total_size": total_size,
        }

    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    print(f"Saved clustering for {len(memories)} memories")
    return results


def main():
    print("=" * 60)
    print("Zeus Memory Clustering - Phase 1")
    print("=" * 60)


    # Fetch memories
    memories = fetch_memories_with_embeddings(limit=MAX_MEMORIES)

    if len(memories) < 10:
        print("Not enough memories with embeddings to cluster")
        return

    # Build k-NN graph
    edges, weights, valid_indices = build_knn_graph(memories)

    if len(edges) == 0:
        print("No edges created - try lowering similarity threshold")
        return

    # Filter to only valid memories
    valid_memories = [memories[i] for i in valid_indices]
    print(f"Using {len(valid_memories)} memories with valid embeddings")

    # Run L1 clustering (fine-grained topics)
    l1_assignments, n_l1 = run_leiden_clustering(
        len(valid_memories), edges, weights, resolution=1.0
    )

    # Build L2 hierarchy (domains)
    l1_to_l2, n_l2 = build_cluster_hierarchy(valid_memories, l1_assignments)

    # Generate labels
    labels = generate_cluster_labels(valid_memories, l1_assignments)

    # Save results
    output_path = "data/clustering_results.json"
    os.makedirs("data", exist_ok=True)
    results = save_clustering_results(
        valid_memories, l1_assignments, l1_to_l2, labels, output_path
    )

    print("\n" + "=" * 60)
    print("CLUSTERING COMPLETE")
    print("=" * 60)
    print(f"Total memories: {len(memories)}")
    print(f"L1 clusters (topics): {n_l1}")
    print(f"L2 clusters (domains): {n_l2}")
    print(f"Results saved to: {output_path}")

    # Show sample clusters
    print("\nSample L1 clusters:")
    for cluster_id in list(labels.keys())[:5]:
        info = labels[cluster_id]
        print(f"  Cluster {cluster_id}: {info['size']} memories, type={info['primary_type']}")


if __name__ == "__main__":
    main()
