import networkx as nx

def find_company_groups(db):
    """
    Returns list[set[str]] of company entity_ids
    """

    ownerships = db.query_df("""
    SELECT owner_id, owned_id
    FROM ownerships
    WHERE
        control_level = 'beneficial'
        OR (
            role = 'Засновник'
            AND share_percent >= 50
        )
    """)

    B = nx.Graph()

    for _, row in ownerships.iterrows():
        B.add_node(row["owner_id"], bipartite="owner")
        B.add_node(row["owned_id"], bipartite="company")
        B.add_edge(row["owner_id"], row["owned_id"])

    companies = [
        n for n, d in B.nodes(data=True)
        if d.get("bipartite") == "company"
    ]

    G = nx.bipartite.projected_graph(B, companies)

    return [
        g for g in nx.connected_components(G)
        if len(g) > 1
    ]
