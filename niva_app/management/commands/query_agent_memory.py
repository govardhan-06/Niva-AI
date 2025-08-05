from django.core.management.base import BaseCommand
from django.db import connection
from django.db.models import F
from django.db.models.expressions import RawSQL
from django.db.models.functions import Cast
from django.db.models import FloatField
from pgvector.django import CosineDistance

from niva_app.models.memory import Memory
from niva_app.models.rag import Document
from google import genai
from pydantic import BaseModel, Field
from typing import List
import uuid
import os

gemini_client=genai.Client(api_key=os.getenv("GOOGLE_GEMINI_API_KEY"))

class SearchResult(BaseModel):
    content: str = Field(..., description="The content of the search result")
    relevance: float = Field(..., description="A score from 0 to 1 indicating how relevant this result is to the query")


class SearchResults(BaseModel):
    results: List[SearchResult] = Field(..., description="A list of search results")
    summary: str = Field(..., description="A brief summary of the search results")


class QueryResponse(BaseModel):
    answer: str = Field(..., description="A concise answer to the query based on the search results")
    explanation: str = Field(...,
                           description="A detailed explanation of the answer, including relevant information from the search results")
    confidence: float = Field(..., description="A score from 0 to 1 indicating the confidence in the answer")


def inspect_memory(memory_id: str):
    """Inspect the documents stored for a given memory using Django ORM"""
    doc_count = Document.objects.filter(memory_id=memory_id).count()

    print(f"Memory contains {doc_count} documents.")

    if doc_count > 0:
        sample_size = min(5, doc_count)
        sample_docs = Document.objects.filter(
            memory_id=memory_id
        ).order_by('?')[:sample_size]

        print(f"Sample of {sample_size} documents:")
        for i, doc in enumerate(sample_docs, 1):
            print(f"Document {i}:")
            print(f"Content: {doc.content[:100]}...")
            print(f"Created: {doc.created_at}")
            print("---")


def query_memory(query: str, memory_id: str, k: int = 5) -> QueryResponse:
    """
    Query documents using vector similarity search with Django ORM.
    Using the pgvector <=> operator for cosine similarity.
    """
    query_embedding = gemini_client.models.embed_content(
        model="gemini-embedding-exp-03-07",
        contents=query,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY")
    )

    similar_docs = (
        Document.objects
        .filter(memory_id=memory_id)
        .annotate(
            similarity=1 - CosineDistance(
                "embedding",
                query_embedding
            )
        )
        .order_by("-similarity")  # Order by highest similarity first
        .values('content', 'created_at', 'similarity')
        [:k]
    )

    if not similar_docs:
        print(f"No documents found for query: '{query}' in memory: '{memory_id}'")
        print("Inspecting memory:")
        inspect_memory(memory_id)
        return QueryResponse(
            answer="No information found.",
            explanation="The search did not return any relevant documents for this query. The memory may be empty or not contain relevant information.",
            confidence=0.0
        )

    results = [
        SearchResult(
            content=doc['content'],
            relevance=doc['similarity']
        )
        for doc in similar_docs
    ]

    results_text = "\n".join([
        f"Content: {r.content}\nRelevance: {r.relevance:.3f}"
        for r in results
    ])

    prompt = f"""
    Query: {query}

    Search Results:
    {results_text}

    Instructions:
    1. Provide a concise answer to the query based ONLY on the information given in the search results above.
    2. If the search results don't contain enough information to fully answer the query, explicitly state this and explain what information is missing.
    3. Do not make up or infer any information that is not directly stated in the search results.
    4. If the search results are not relevant to the query, state that you cannot answer based on the given information.
    5. Provide an explanation of your answer, citing specific parts of the search results.
    6. Assign a confidence score (0-1) to your answer based on how well the search results support it.
    """

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        config=types.GenerateContentConfig(
            system_instruction="You are a helpful assistant that answers queries based strictly on the given search results. You do not make up information or use external knowledge. If the search results are insufficient to answer the query, you clearly state this.",
            response_mime_type="application/json",
            response_schema=QueryResponse
        ),
        contents=prompt
    )

    return response


class Command(BaseCommand):
    help = 'Query a memory and its associated documents using memory ID'

    def add_arguments(self, parser):
        parser.add_argument('memory_id', type=str, help='UUID of the memory to query')

    def handle(self, *args, **options):
        try:
            memory_id = uuid.UUID(options['memory_id'])
        except ValueError:
            self.stdout.write(self.style.ERROR(f"Invalid memory ID format. Please provide a valid UUID."))
            return

        try:
            memory = Memory.objects.get(id=memory_id)
        except Memory.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Memory with ID '{memory_id}' does not exist."))
            # List available memories to help user
            available_memories = Memory.objects.all()[:5]
            if available_memories:
                self.stdout.write("\nAvailable memories:")
                for m in available_memories:
                    self.stdout.write(f"ID: {m.id} - URL: {m.url}")
            return

        self.stdout.write(self.style.SUCCESS(f"Found memory: {memory.url} (ID: {memory.id})"))
        doc_count = memory.documents.count()

        if doc_count == 0:
            self.stdout.write(self.style.WARNING(f"No documents found in memory '{memory_id}'."))
            return

        self.stdout.write(self.style.SUCCESS(
            f"Memory details:\n"
            f"URL: {memory.url}\n"
            f"Created: {memory.created_at}\n"
            f"Document count: {doc_count}"
        ))

        self.stdout.write("Enter your queries. Type 'exit' to quit.")

        while True:
            query = input("Enter your query: ")
            if query.lower() == 'exit':
                break

            try:
                query_response = query_memory(query, str(memory.id))
                self.stdout.write(self.style.SUCCESS(f"Query Results:"))
                self.stdout.write(f"Answer: {query_response.answer}")
                self.stdout.write(f"Explanation: {query_response.explanation}")
                self.stdout.write(f"Confidence: {query_response.confidence:.3f}")
                self.stdout.write("---")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing query: {str(e)}"))
                self.stdout.write(self.style.ERROR("Traceback:"))
                import traceback
                self.stdout.write(traceback.format_exc())

        self.stdout.write(self.style.SUCCESS("Query session ended."))