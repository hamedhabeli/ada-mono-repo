import os
from neo4j import GraphDatabase
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance

class CloudEpistemicMemory:
    def __init__(self):
        # اتصال به Qdrant Cloud (Vector DB)
        self.qdrant = QdrantClient(
            url=os.getenv("QDRANT_URL"), 
            api_key=os.getenv("QDRANT_API_KEY")
        )
        self.collection_name = "ada_epistemic_events"
        
        # ایجاد کالکشن در صورت عدم وجود
        if not self.qdrant.collection_exists(self.collection_name):
            self.qdrant.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=768, distance=Distance.COSINE)
            )

        # اتصال به Neo4j AuraDB (Graph DB)
        self.neo4j_driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI"),
            auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
        )

    def store_contradiction(self, problem: str, hypothesis: str, unsat_core: list):
        core_str = " AND ".join(unsat_core)
        doc_id = abs(hash(problem + core_str)) % (10 ** 8) # شناسه عددی برای Qdrant
        
        # ذخیره در Qdrant (بدون نیاز به مدل امبدینگ محلی، از FastEmbed داخلی Qdrant استفاده میکنیم)
        text_payload = f"Problem: {problem} | Failed: {hypothesis} | Core: {core_str}"
        # Embed the text using the Qdrant client's built-in `embed` method
        embedding = self.qdrant.embed.embed(text_payload)
        self.qdrant.upsert(
            collection_name=self.collection_name,
            points=[PointStruct(id=doc_id, vector=embedding, payload={"text": text_payload, "type": "contradiction"})]
        )
        
        # ذخیره در Neo4j
        query = """
        MERGE (p:Problem {text: $problem})
        MERGE (h:Hypothesis {text: $hypothesis})
        MERGE (u:UnsatCore {text: $core})
        MERGE (p)-[:GENERATED]->(h)-[:LED_TO_CONTRADICTION]->(u)
        """
        with self.neo4j_driver.session() as session:
            session.run(query, problem=problem, hypothesis=hypothesis, core=core_str)

    def store_meta_axiom(self, problem: str, unsat_core: list, meta_axiom: str):
        core_str = " AND ".join(unsat_core)
        query = """
        MATCH (u:UnsatCore {text: $core})
        MERGE (m:MetaAxiom {text: $axiom})
        MERGE (u)-[:RESOLVED_BY]->(m)
        """
        with self.neo4j_driver.session() as session:
            session.run(query, core=core_str, axiom=meta_axiom)

memory_db = CloudEpistemicMemory()