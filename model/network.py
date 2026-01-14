import networkx as nx


def make_scale_free_network(n: int, m: int, seed: int | None = None) -> nx.Graph:
    """
    Barabási–Albert (scale-free) network:
    - n: number of nodes
    - m: number of edges to attach from a new node to existing nodes
    """
    if m < 1 or m >= n:
        raise ValueError("In Barabási–Albert, require 1 <= m < n.")
    return nx.barabasi_albert_graph(n=n, m=m, seed=seed)
