#!/usr/bin/env python3
"""
Generate schema relationship graphs from Zeus Memory data.
Creates JSON visualization data showing table/column relationships.
"""

import json
import psycopg2
from datetime import datetime

conn_params = {
    'host': 'psql-zeus-memory-dev.postgres.database.azure.com',
    'port': 5432,
    'dbname': 'zeus_core',
    'user': 'zeus_admin',
    'password': 'ZeusMemory2024Db',
    'sslmode': 'require'
}

# Color palette for different table types
TABLE_COLORS = {
    "fact": "#1a365d",      # Dark blue - fact tables
    "dimension": "#2f855a", # Green - dimension tables
    "date": "#805ad5",      # Purple - date tables
    "measure": "#e53e3e",   # Red - measures
    "column": "#3182ce",    # Blue - columns
    "hub": "#dd6b20",       # Orange - hub/center
}


def get_schema_data(source_prefix):
    """Get all schema chunks from Zeus Memory."""
    conn = psycopg2.connect(**conn_params)
    cur = conn.cursor()

    # Get main schema record
    cur.execute("""
        SELECT content FROM zeus_core.memories
        WHERE source = %s LIMIT 1
    """, (source_prefix,))

    main_row = cur.fetchone()
    if not main_row:
        return None

    main_data = json.loads(main_row[0])

    # Get column chunks
    columns = []
    cur.execute("""
        SELECT content FROM zeus_core.memories
        WHERE source LIKE %s
        ORDER BY source
    """, (f"{source_prefix}_CHUNK_%",))

    for row in cur.fetchall():
        chunk_data = json.loads(row[0])
        if 'columns' in chunk_data:
            columns.extend(chunk_data['columns'])

    # Get measure chunks
    measures = []
    cur.execute("""
        SELECT content FROM zeus_core.memories
        WHERE source LIKE %s
        ORDER BY source
    """, (f"{source_prefix}_MEASURES_%",))

    for row in cur.fetchall():
        chunk_data = json.loads(row[0])
        if 'measures' in chunk_data:
            measures.extend(chunk_data['measures'])

    cur.close()
    conn.close()

    return {
        'main': main_data,
        'columns': columns,
        'measures': measures
    }


def create_graph_json(schema_data, client_name):
    """Convert schema data to visualization JSON format."""
    main = schema_data['main']
    columns = schema_data['columns']
    measures = schema_data['measures']

    # Extract tables from schema definition
    tables = main.get('schema', {}).get('definition', {}).get('tables', [])

    nodes = []
    edges = []

    # Create hub node (the dataset)
    dataset_name = main.get('schema', {}).get('capacity_options', {}).get('dataset_name', f"{client_name} Dataset")
    nodes.append({
        "id": "hub",
        "label": dataset_name,
        "tier": 0,
        "group": "hub",
        "title": f"{client_name} Analytics Dataset\nTables: {len(tables)}\nColumns: {len(columns)}\nMeasures: {len(measures)}",
        "size": 50
    })

    # Create table nodes
    table_columns = {}  # Track columns per table
    for col in columns:
        locator = col.get('column_locator', '')
        # Parse table name from locator: 'Table Name'[Column Name]
        if "'" in locator:
            table_name = locator.split("'")[1]
            if table_name not in table_columns:
                table_columns[table_name] = []
            table_columns[table_name].append(col)

    # Determine table types based on naming conventions
    for table_name in tables:
        table_id = table_name.lower().replace(' ', '_').replace('(', '').replace(')', '')

        # Classify table type
        if 'date' in table_name.lower():
            group = "date"
            tier = 2
        elif table_name in ['Spend', 'Flight', 'Order', 'Order Line', 'Campaign']:
            group = "fact"
            tier = 1
        else:
            group = "dimension"
            tier = 2

        col_count = len(table_columns.get(table_name, []))

        nodes.append({
            "id": f"table_{table_id}",
            "label": table_name,
            "tier": tier,
            "group": group,
            "title": f"{table_name}\n{col_count} columns",
            "size": 20 + min(col_count * 2, 20)
        })

        # Connect table to hub
        edges.append({
            "source": "hub",
            "target": f"table_{table_id}",
            "type": "contains"
        })

    # Create measure nodes (grouped)
    if measures:
        # Group measures by their likely table association
        measure_tables = {}
        for measure in measures:
            locator = measure.get('column_locator', '')
            if "'" in locator:
                table_name = locator.split("'")[1]
                if table_name not in measure_tables:
                    measure_tables[table_name] = []
                measure_tables[table_name].append(measure)

        for table_name, table_measures in measure_tables.items():
            table_id = table_name.lower().replace(' ', '_').replace('(', '').replace(')', '')
            measure_node_id = f"measures_{table_id}"

            nodes.append({
                "id": measure_node_id,
                "label": f"{table_name} Measures",
                "tier": 3,
                "group": "measure",
                "title": f"{len(table_measures)} calculated measures for {table_name}",
                "size": 15 + min(len(table_measures), 15)
            })

            # Connect measures to their table
            edges.append({
                "source": f"table_{table_id}",
                "target": measure_node_id,
                "type": "has_measures"
            })

    # Create edges between related tables (based on common column patterns)
    # Look for foreign key-like relationships
    for col in columns:
        col_name = col.get('column_name', '').lower()
        locator = col.get('column_locator', '')

        if "'" in locator:
            source_table = locator.split("'")[1]
            source_id = f"table_{source_table.lower().replace(' ', '_').replace('(', '').replace(')', '')}"

            # Look for ID columns that might reference other tables
            for table_name in tables:
                table_lower = table_name.lower().replace(' ', '_')
                if f"{table_lower}_id" in col_name or f"{table_lower}id" in col_name:
                    target_id = f"table_{table_lower.replace('(', '').replace(')', '')}"
                    if source_id != target_id:
                        edges.append({
                            "source": source_id,
                            "target": target_id,
                            "type": "references"
                        })

    # Build final JSON structure
    groups = {
        "hub": {"color": TABLE_COLORS["hub"], "label": "Dataset"},
        "fact": {"color": TABLE_COLORS["fact"], "label": "Fact Tables"},
        "dimension": {"color": TABLE_COLORS["dimension"], "label": "Dimension Tables"},
        "date": {"color": TABLE_COLORS["date"], "label": "Date Tables"},
        "measure": {"color": TABLE_COLORS["measure"], "label": "Measures"},
    }

    edge_types = {
        "contains": {"color": "#718096", "width": 2, "label": "Contains"},
        "has_measures": {"color": "#e53e3e", "width": 1, "label": "Has Measures"},
        "references": {"color": "#3182ce", "width": 2, "label": "References"},
    }

    return {
        "metadata": {
            "title": f"{client_name} Data Schema",
            "description": f"Schema visualization for {dataset_name} - {len(tables)} tables, {len(columns)} columns, {len(measures)} measures",
            "source": "Zeus Memory / Eclipse API",
            "created": datetime.now().strftime("%Y-%m-%d"),
            "updated": datetime.now().strftime("%Y-%m-%d")
        },
        "groups": groups,
        "edge_types": edge_types,
        "nodes": nodes,
        "edges": edges
    }


def main():
    schemas = [
        ("F92_SCHEMA", "Fusion92"),
        ("ALDC_SCHEMA", "ALDC Internal"),
        ("GEP_SCHEMA", "GEP (Global Export Platform)")
    ]

    output_dir = "data/examples"

    for source_prefix, client_name in schemas:
        print(f"\nProcessing {client_name}...")

        schema_data = get_schema_data(source_prefix)
        if not schema_data:
            print(f"  No data found for {source_prefix}")
            continue

        graph_json = create_graph_json(schema_data, client_name)

        output_file = f"{output_dir}/{source_prefix.lower()}_graph.json"
        with open(output_file, 'w') as f:
            json.dump(graph_json, f, indent=2)

        print(f"  Generated {output_file}")
        print(f"  - Nodes: {len(graph_json['nodes'])}")
        print(f"  - Edges: {len(graph_json['edges'])}")


if __name__ == "__main__":
    main()
