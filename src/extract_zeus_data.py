#!/usr/bin/env python3
"""
Extract Zeus Memory decisions and CCE memories for visualization.
Generates JSON in network-ecosystem format.
"""

import json
import re
import psycopg2
from datetime import datetime

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

# Edge type styles
EDGE_TYPES = {
    "references": {"color": "#3182ce", "width": 2, "label": "References"},
    "informs": {"color": "#2f855a", "width": 2, "label": "Informs"},
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
    # Sanitize secrets first
    text = sanitize_secrets(text)
    # Remove newlines, extra spaces
    cleaned = ' '.join(text.split())
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len-3] + "..."
    return cleaned


def extract_data():
    """Extract decisions and memories from Zeus."""
    conn = psycopg2.connect(**conn_params)
    cur = conn.cursor()

    nodes = []
    edges = []
    node_ids = set()

    # 1. Get decisions from decisions table
    cur.execute("""
        SELECT decision_id, action, reasoning, confidence, agent_id, created_at
        FROM zeus_core.decisions
        WHERE tenant_id = %s
        ORDER BY created_at DESC
        LIMIT 100
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

    # 2. Get CCE memories - EXCLUDE CONFIDENTIAL CATEGORIES
    # Only include technical/operational content, not financial/business sensitive
    SAFE_CATEGORIES = [
        'technical', 'cce_setup', 'general', 'workspace-management',
        'implementation_plan', 'implementation_validation', 'prd-review',
        'collective_intelligence', 'hybrid_collective_intelligence',
        'local_p100_deployment', 'snowflake_search'
    ]
    # EXCLUDED (confidential): financial_analysis, cash_flow, tax_credit,
    # debt_service, holdco_structure, business, business_context, operational_plan

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
        LIMIT 100
    """, (TENANT_ID, tuple(SAFE_CATEGORIES)))

    memories = cur.fetchall()
    print(f"Found {len(memories)} CCE memories")

    for row in memories:
        memory_id, content, source, metadata, created_at = row
        node_id = str(memory_id)

        if node_id in node_ids:
            continue  # Skip duplicates

        node_ids.add(node_id)

        # Determine tier based on source
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

        nodes.append({
            "id": node_id,
            "label": clean_text(content, 50),
            "title": clean_text(content, 400),
            "tier": tier_map.get(source, 3),
            "group": source if source in GROUPS else "cce",
            "size": size_map.get(source, 15),
        })

        # Check for related_memory in metadata
        if metadata and isinstance(metadata, dict):
            related = metadata.get('related_memory')
            if related and related in node_ids:
                edges.append({
                    "source": node_id,
                    "target": related,
                    "type": "references"
                })

    # 3. Create hub node for Zeus Memory
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

    # 4. Connect all decision nodes to the hub
    for node in nodes:
        if node['group'] == 'decision' and node['id'] != hub_id:
            edges.append({
                "source": hub_id,
                "target": node['id'],
                "type": "informs"
            })

    # 5. Connect CCE decision logs to hub
    for node in nodes:
        if node['group'] == 'cce_decision_log' and node['id'] != hub_id:
            edges.append({
                "source": hub_id,
                "target": node['id'],
                "type": "informs"
            })

    # 6. Connect related sources together
    source_groups = {}
    for node in nodes:
        grp = node['group']
        if grp not in source_groups:
            source_groups[grp] = []
        source_groups[grp].append(node)

    # Connect failed approaches to successes (learning loop)
    failed = source_groups.get('cce_failed_approach', [])
    success = source_groups.get('cce_success_log', [])
    for f in failed[:10]:
        for s in success[:10]:
            edges.append({
                "source": f['id'],
                "target": s['id'],
                "type": "related"
            })

    # Connect research to decisions
    research = source_groups.get('cce_research', [])
    decisions = source_groups.get('decision', [])
    for r in research[:15]:
        # Connect to first few decisions
        for d in decisions[:5]:
            edges.append({
                "source": r['id'],
                "target": d['id'],
                "type": "informs"
            })

    cur.close()
    conn.close()

    return nodes, edges


def main():
    nodes, edges = extract_data()

    # Build visualization data
    data = {
        "metadata": {
            "title": "Zeus Memory Decision Graph",
            "description": "Visualization of decisions, learnings, and relationships in Zeus Memory",
            "source": "zeus_core database",
            "created": datetime.now().strftime("%Y-%m-%d"),
            "updated": datetime.now().strftime("%Y-%m-%d")
        },
        "groups": GROUPS,
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
