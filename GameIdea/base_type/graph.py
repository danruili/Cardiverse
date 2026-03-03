from typing import TypedDict, Union, Literal, Generic, TypeVar, Tuple
from pydantic import BaseModel, Field
import json
import uuid
import networkx as nx

NODE_TYPE = Literal[
    'entity',
]

class RelatedNode(BaseModel):
    node_id: str  # uuid to a BaseNode instance
    reasoning: str  # reasoning in edge
    
    # serialization
    def json_str(self):
        return json.dumps(self.model_dump())
    
def stringify_related_node_list(related_nodes: list[RelatedNode]) -> str:
    return "###".join([item.json_str() for item in related_nodes])

def parse_related_node_list(related_nodes_str: str) -> list[RelatedNode]:
    if related_nodes_str == "":
        return []
    elif isinstance(related_nodes_str, list):
        return [RelatedNode(**item) for item in related_nodes_str]
    elif isinstance(related_nodes_str, str):
        return [RelatedNode(**json.loads(item)) for item in related_nodes_str.split("###")]
    
    
    
class BaseNode(BaseModel):
    name: str
    description: str
    node_id: str = None
    color_label: Union[str, None] = None

    # for nodes that has been instantiated
    game_id: Union[str, None] = None
    depth: Union[int, None] = None  # the child of root node has depth 0

    # cache neighbor nodes and edges as RelatedNode instances
    upstream: list[RelatedNode] = Field(default_factory=list)
    downstream: list[RelatedNode] = Field(default_factory=list)  # downstream nodes are closer to the root node
    
    # use uuid for node_id when initializing
    def __init__(self, **data):
        # parse related nodes
        if "upstream" in data:
            data["upstream"] = parse_related_node_list(data["upstream"])
        if "downstream" in data:
            data["downstream"] = parse_related_node_list(data["downstream"])
        if not "depth" in data:
            data["depth"] = None
        super().__init__(**data)
        if self.node_id is None:
            self.node_id = uuid.uuid4().hex

    def embedding_str(self):
        return f"{self.description}"
    
    # hash
    def __hash__(self):
        return hash(self.node_id)
    

class BaseEdge(BaseModel):
    source_id: str
    target_id: str
    edge_type: str = None
    reasoning: str = None

class BaseGraph(BaseModel):
    name: str = None
    description: str = None
    nodes: list[BaseNode] = Field(default_factory=list)
    edges: list[BaseEdge] = Field(default_factory=list)

    def save(self, file_path: str):
        # save as json
        with open(file_path, "w") as f:
            f.write(self.model_dump_json(indent=4))

    def read(self, file_path: str):
        """
        Load the graph from a JSON file.
        """
        with open(file_path, "r", encoding='utf-8') as f:
            data = json.load(f)

        # Validate and populate the BaseGraph instance
        graph = BaseGraph(**data)
        self.name = graph.name
        self.description = graph.description
        self.nodes = graph.nodes
        self.edges = graph.edges
        return self
    
    def add_edge(
            self, 
            source: BaseNode, 
            target: BaseNode, 
            edge_type: str = None,
            reasoning: str = None
        ):
        edge = BaseEdge(source_id=source.node_id, target_id=target.node_id, edge_type=edge_type, reasoning=reasoning)
        self.edges.append(edge)
    
    def to_networkx(self) -> nx.DiGraph:
        """
        Converts a BaseGraph instance into a networkx directed graph.
        """
        # Create a directed graph
        nx_graph = nx.DiGraph()

        # Add nodes to the graph
        for node in self.nodes:
            nx_graph.add_node(
                node.node_id,
                name=node.name, 
                color_label=getattr(node, "color_label", None),
            )

        # Add edges to the graph
        for edge in self.edges:
            nx_graph.add_edge(
                edge.source_id, 
                edge.target_id, 
                color_label=getattr(edge, "edge_type", None),
            )

        return nx_graph

