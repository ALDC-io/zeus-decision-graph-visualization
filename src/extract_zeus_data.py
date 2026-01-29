#!/usr/bin/env python3
"""
Extract Zeus Memory decisions and CCE memories for visualization.
Generates JSON in network-ecosystem format.

Edge Generation Methods:
1. Metadata-based (category, source, agent_id, explicit references)
2. Temporal clustering (same session/day)
3. Vector similarity (pgvector embeddings)
4. Hub connections (structural)
"""

import json
import re
import psycopg2
from datetime import datetime, timedelta
from collections import defaultdict

# Database connection
conn_params = {
    'host': 'psql-zeus-memory-dev.postgres.database.azure.com',
    'port': 5432,
    'dbname': 'zeus_core',
    'user': 'zeus_admin',
    'password': 'ZeusMemory2024Db',
    'sslmode': 'require'
}

TENANT_ID = 'b513bc6e-ad51-4a11-bea3-e3b1a84d7b55'

# Group definitions with colors
GROUPS = {
    "decision": {"color": "#1a365d", "label": "Decisions"},
    "cce_decision_log": {"color": "#2f855a", "label": "CCE Decisions"},
    "cce_research": {"color": "#3182ce", "label": "Research"},
    "cce_failed_approach": {"color": "#e53e3e", "label": "Failed Approaches"},
    "cce_success_log": {"color": "#38a169", "label": "Successes"},
    "cce_system": {"color": "#805ad5", "label": "System Events"},
    "cce": {"color": "#d69e2e", "label": "CCE General"},
    "architecture": {"color": "#dd6b20", "label": "Architecture"},
}

# Edge type styles - expanded for new relationship types
EDGE_TYPES = {
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
    "temporal_context": {"color": "#fc8181", "width": 1, "label": "Temporal Context"},

    # Generic
    "related": {"color": "#a0aec0", "width": 1, "label": "Related"},
}

# Patterns that might contain secrets
SECRET_PATTERNS = [
    r'ntn_[a-zA-Z0-9]{40,}',  # Notion tokens
    r'sk-[a-zA-Z0-9]{32,}',   # OpenAI keys
    r'xoxb-[a-zA-Z0-9\-]+',   # Slack bot tokens
    r'xoxp-[a-zA-Z0-9\-]+',   # Slack user tokens
    r'ghp_[a-zA-Z0-9]{36}',   # GitHub tokens
    r'gho_[a-zA-Z0-9]{36}',   # GitHub OAuth tokens
    r'zm_[a-zA-Z0-9_]{30,}',  # Zeus Memory API keys
    r'AKIA[A-Z0-9]{16}',      # AWS access keys
    r'password["\']?\s*[:=]\s*["\'][^"\']+["\']',  # Password patterns
    r'api[_-]?key["\']?\s*[:=]\s*["\'][^"\']+["\']',  # API key patterns
]

# Safe categories (non-confidential)
SAFE_CATEGORIES = [
    'technical', 'cce_setup', 'general', 'workspace-management',
    'implementation_plan', 'implementation_validation', 'prd-review',
    'collective_intelligence', 'hybrid_collective_intelligence',
    'local_p100_deployment', 'snowflake_search'
]
# EXCLUDED (confidential): financial_analysis, cash_flow, tax_credit,
# debt_service, holdco_structure, business, business_context, operational_plan


def sanitize_secrets(text):
    """Remove potential secrets from text."""
    if not text:
        return text
    for pattern in SECRET_PATTERNS:
        text = re.sub(pattern, '[REDACTED]', text, flags=re.IGNORECASE)
    return text


def clean_text(text, max_len=80):
    """Clean text for display."""
    if not text:
        return "Untitled"
    text = sanitize_secrets(text)
    cleaned = ' '.join(text.split())
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len-3] + "..."
    return cleaned


def extract_nodes(cur):
    """Extract all nodes (decisions + memories)."""
    nodes = []
    node_ids = set()
    node_metadata = {}  # Store metadata for edge generation

    # 1. Get decisions
    cur.execute("""
        SELECT decision_id, action, reasoning, confidence, agent_id, created_at
        FROM zeus_core.decisions
        WHERE tenant_id = %s
        ORDER BY created_at DESC
        LIMIT 200
    """, (TENANT_ID,))

    decisions = cur.fetchall()
    print(f"Found {len(decisions)} decisions")

    for row in decisions:
        decision_id, action, reasoning, confidence, agent_id, created_at = row
        node_id = str(decision_id)
        node_ids.add(node_id)

        nodes.append({
            "id": node_id,
            "label": clean_text(action, 50),
            "title": clean_text(action, 300) + (f"\n\nConfidence: {confidence}" if confidence else ""),
            "tier": 1,
            "group": "decision",
            "size": 25 + (int(confidence * 10) if confidence else 0),
        })

        node_metadata[node_id] = {
            "type": "decision",
            "agent_id": str(agent_id) if agent_id else None,
            "created_at": created_at,
            "category": None,
            "source": "decision",
        }

    # 2. Get CCE memories
    cur.execute("""
        SELECT memory_id, content, source, metadata, created_at
        FROM zeus_core.memories
        WHERE tenant_id = %s
          AND source IN ('cce_decision_log', 'cce_research', 'cce_failed_approach',
                        'cce_success_log', 'cce_system', 'cce')
          AND (
            metadata->>'category' IS NULL
            OR metadata->>'category' IN %s
          )
        ORDER BY created_at DESC
        LIMIT 200
    """, (TENANT_ID, tuple(SAFE_CATEGORIES)))

    memories = cur.fetchall()
    print(f"Found {len(memories)} CCE memories")

    tier_map = {
        'cce_decision_log': 1,
        'cce_research': 2,
        'cce_failed_approach': 3,
        'cce_success_log': 2,
        'cce_system': 4,
        'cce': 3,
    }

    size_map = {
        'cce_decision_log': 25,
        'cce_research': 20,
        'cce_failed_approach': 15,
        'cce_success_log': 20,
        'cce_system': 10,
        'cce': 15,
    }

    for row in memories:
        memory_id, content, source, metadata, created_at = row
        node_id = str(memory_id)

        if node_id in node_ids:
            continue

        node_ids.add(node_id)

        nodes.append({
            "id": node_id,
            "label": clean_text(content, 50),
            "title": clean_text(content, 400),
            "tier": tier_map.get(source, 3),
            "group": source if source in GROUPS else "cce",
            "size": size_map.get(source, 15),
        })

        meta = metadata if isinstance(metadata, dict) else {}
        node_metadata[node_id] = {
            "type": "memory",
            "agent_id": meta.get('agent_id'),
            "created_at": created_at,
            "category": meta.get('category'),
            "source": source,
            "related_memory": meta.get('related_memory'),
        }

    # 3. Create hub node
    hub_id = "zeus-memory-hub"
    nodes.insert(0, {
        "id": hub_id,
        "label": "Zeus Memory",
        "title": "Zeus Memory Hub - Central knowledge store for ALDC",
        "tier": 0,
        "group": "architecture",
        "size": 50,
    })
    node_ids.add(hub_id)
    node_metadata[hub_id] = {
        "type": "hub",
        "agent_id": None,
        "created_at": datetime.now(),
        "category": "hub",
        "source": "architecture",
    }

    return nodes, node_ids, node_metadata


def generate_metadata_edges(nodes, node_ids, node_metadata):
    """Generate edges based on metadata relationships."""
    edges = []
    edge_set = set()  # Track unique edges

    def add_edge(source, target, edge_type):
        """Add edge if not already exists."""
        key = tuple(sorted([source, target])) + (edge_type,)
        if key not in edge_set and source != target:
            edge_set.add(key)
            edges.append({
                "source": source,
                "target": target,
                "type": edge_type
            })

    # 1. Explicit references from metadata
    for node_id, meta in node_metadata.items():
        related = meta.get('related_memory')
        if related and related in node_ids:
            add_edge(node_id, related, "references")

    # 2. Same category connections
    category_groups = defaultdict(list)
    for node_id, meta in node_metadata.items():
        cat = meta.get('category')
        if cat:
            category_groups[cat].append(node_id)

    for category, members in category_groups.items():
        if len(members) > 1 and len(members) <= 20:  # Avoid huge clusters
            for i, m1 in enumerate(members):
                for m2 in members[i+1:min(i+4, len(members))]:  # Max 3 edges per node
                    add_edge(m1, m2, "same_category")

    # 3. Same agent connections
    agent_groups = defaultdict(list)
    for node_id, meta in node_metadata.items():
        agent = meta.get('agent_id')
        if agent:
            agent_groups[agent].append(node_id)

    for agent, members in agent_groups.items():
        if len(members) > 1 and len(members) <= 30:
            for i, m1 in enumerate(members):
                for m2 in members[i+1:min(i+3, len(members))]:
                    add_edge(m1, m2, "same_agent")

    # 4. Same source type - connect within groups (limited)
    source_groups = defaultdict(list)
    for node_id, meta in node_metadata.items():
        src = meta.get('source')
        if src:
            source_groups[src].append(node_id)

    # Connect failed approaches to successes (learning loop)
    failed = source_groups.get('cce_failed_approach', [])
    success = source_groups.get('cce_success_log', [])
    for f in failed[:15]:
        for s in success[:15]:
            add_edge(f, s, "related")

    # Connect research to decisions
    research = source_groups.get('cce_research', [])
    decisions = source_groups.get('decision', [])
    for r in research[:20]:
        for d in decisions[:10]:
            add_edge(r, d, "informs")

    print(f"Generated {len(edges)} metadata-based edges")
    return edges, edge_set


def generate_temporal_edges(node_ids, node_metadata, edge_set):
    """Generate edges based on temporal proximity."""
    edges = []

    def add_edge(source, target, edge_type):
        key = tuple(sorted([source, target])) + (edge_type,)
        if key not in edge_set and source != target:
            edge_set.add(key)
            edges.append({
                "source": source,
                "target": target,
                "type": edge_type
            })

    # Group by day
    day_groups = defaultdict(list)
    for node_id, meta in node_metadata.items():
        created = meta.get('created_at')
        if created and meta.get('type') != 'hub':
            day_key = created.date() if hasattr(created, 'date') else None
            if day_key:
                day_groups[day_key].append((node_id, created, meta.get('source')))

    # Connect nodes from same day with same source type
    for day, members in day_groups.items():
        # Group by source within the day
        source_day = defaultdict(list)
        for node_id, created, source in members:
            source_day[source].append((node_id, created))

        for source, items in source_day.items():
            if len(items) > 1:
                # Sort by time
                items.sort(key=lambda x: x[1])
                # Connect sequential items (max 2 connections per node)
                for i in range(len(items) - 1):
                    if i < 10:  # Limit edges
                        add_edge(items[i][0], items[i+1][0], "temporal_context")

    print(f"Generated {len(edges)} temporal edges")
    return edges


def generate_similarity_edges(cur, node_ids, node_metadata, edge_set, similarity_threshold=0.85, max_edges=200):
    """Generate edges based on vector similarity using pgvector."""
    edges = []

    def add_edge(source, target, edge_type, similarity):
        key = tuple(sorted([source, target])) + (edge_type,)
        if key not in edge_set and source != target:
            edge_set.add(key)
            edges.append({
                "source": source,
                "target": target,
                "type": edge_type,
                "weight": round(similarity, 3)
            })

    # Get memory IDs that are in our node set
    memory_ids = [nid for nid, meta in node_metadata.items()
                  if meta.get('type') == 'memory']

    if not memory_ids:
        print("No memory nodes for similarity calculation")
        return edges

    # Query for similar pairs using pgvector
    # Using embedding_voyage for similarity (or embedding_bge as fallback)
    try:
        # Convert string UUIDs to proper format for PostgreSQL
        uuid_list = [uuid for uuid in memory_ids if uuid != 'zeus-memory-hub']
        cur.execute("""
            WITH node_embeddings AS (
                SELECT memory_id, embedding_voyage
                FROM zeus_core.memories
                WHERE memory_id::text = ANY(%s)
                  AND embedding_voyage IS NOT NULL
            )
            SELECT
                m1.memory_id::text as source,
                m2.memory_id::text as target,
                1 - (m1.embedding_voyage <=> m2.embedding_voyage) as similarity
            FROM node_embeddings m1
            JOIN node_embeddings m2 ON m1.memory_id < m2.memory_id
            WHERE 1 - (m1.embedding_voyage <=> m2.embedding_voyage) > %s
            ORDER BY similarity DESC
            LIMIT %s
        """, (uuid_list, similarity_threshold, max_edges))

        similar_pairs = cur.fetchall()
        print(f"Found {len(similar_pairs)} similar memory pairs")

        for source, target, similarity in similar_pairs:
            if source in node_ids and target in node_ids:
                edge_type = "highly_similar" if similarity > 0.92 else "similar"
                add_edge(source, target, edge_type, similarity)

    except Exception as e:
        print(f"Warning: Similarity query failed: {e}")
        print("Continuing without similarity edges...")

    print(f"Generated {len(edges)} similarity edges")
    return edges


def generate_hub_edges(nodes, edge_set):
    """Generate hub connections for structure."""
    edges = []
    hub_id = "zeus-memory-hub"

    def add_edge(source, target, edge_type):
        key = tuple(sorted([source, target])) + (edge_type,)
        if key not in edge_set and source != target:
            edge_set.add(key)
            edges.append({
                "source": source,
                "target": target,
                "type": edge_type
            })

    # Connect decisions and decision logs to hub
    for node in nodes:
        if node['group'] in ('decision', 'cce_decision_log') and node['id'] != hub_id:
            add_edge(hub_id, node['id'], "informs")

    print(f"Generated {len(edges)} hub edges")
    return edges


def extract_data():
    """Extract all data and generate edges using multiple methods."""
    conn = psycopg2.connect(**conn_params)
    cur = conn.cursor()

    # Extract nodes
    nodes, node_ids, node_metadata = extract_nodes(cur)

    # Generate edges using all methods
    all_edges = []
    edge_set = set()

    # 1. Metadata-based edges
    metadata_edges, edge_set = generate_metadata_edges(nodes, node_ids, node_metadata)
    all_edges.extend(metadata_edges)

    # 2. Temporal edges
    temporal_edges = generate_temporal_edges(node_ids, node_metadata, edge_set)
    all_edges.extend(temporal_edges)

    # 3. Similarity edges (vector-based)
    similarity_edges = generate_similarity_edges(cur, node_ids, node_metadata, edge_set)
    all_edges.extend(similarity_edges)

    # 4. Hub edges (structural)
    hub_edges = generate_hub_edges(nodes, edge_set)
    all_edges.extend(hub_edges)

    cur.close()
    conn.close()

    # Summary
    print(f"\n--- Edge Summary ---")
    edge_types = defaultdict(int)
    for e in all_edges:
        edge_types[e['type']] += 1
    for etype, count in sorted(edge_types.items(), key=lambda x: -x[1]):
        print(f"  {etype}: {count}")

    return nodes, all_edges


def main():
    nodes, edges = extract_data()

    # Build visualization data
    data = {
        "metadata": {
            "title": "Zeus Memory Knowledge Graph",
            "description": "Knowledge graph of decisions, learnings, and relationships in Zeus Memory",
            "source": "zeus_core database",
            "created": datetime.now().strftime("%Y-%m-%d"),
            "updated": datetime.now().strftime("%Y-%m-%d"),
            "edge_methods": ["metadata", "temporal", "similarity", "hub"]
        },
        "groups": GROUPS,
        "edge_types": EDGE_TYPES,
        "nodes": nodes,
        "edges": edges
    }

    # Write output
    output_path = "data/examples/zeus_decisions.json"
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2, default=str)

    print(f"\nGenerated {output_path}")
    print(f"  Nodes: {len(nodes)}")
    print(f"  Edges: {len(edges)}")
    print(f"  Groups: {list(GROUPS.keys())}")


if __name__ == "__main__":
    main()
