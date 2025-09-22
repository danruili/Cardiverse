from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.core.node_parser import CodeSplitter
from tree_sitter_languages import get_parser
import os


class CodeSnippetRetriever:

    def __init__(self, directory_path):
        self.directory_path = os.path.join(directory_path, 'indexing')
        self.parser = get_parser('python')
        self.code_splitter = CodeSplitter(
            language="python",
            parser=self.parser,
        )
        self.index = None
        self.dense_retriever = None


    def build_index(self):
        # Split Documents using AST
        documents = SimpleDirectoryReader(self.directory_path, required_exts=[".py"]).load_data()
        nodes = self.code_splitter.get_nodes_from_documents(documents)

        # Dense Index
        self.index = VectorStoreIndex(nodes)
        self.dense_retriever = self.index.as_retriever()

        # raise errors if no documents found
        if not documents:
            raise ValueError(f"No .py documents found in directory: {self.directory_path}")

    def retrieve(self, query):
        # Dense Retrieval
        dense_result = self.dense_retriever.retrieve(query)
        return dense_result
    
    def retrieve_as_string(self, query):
        dense_result = self.retrieve(query)
        result_str = "Here are some example code from other games that might be helpful:\n\n"
        for i, doc in enumerate(dense_result):
            result_str += f"Document {i+1}, score: {doc.score}\n```python\n"
            result_str += doc.text + "\n```\n\n"
        return result_str
