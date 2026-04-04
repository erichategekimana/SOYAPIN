from pgvector.django import VectorField

class ChatMessage(TimestampMixin):
    user = models.ForeignKey('identity.User', on_delete=models.CASCADE)
    message = models.TextField()
    ai_response = models.TextField()
    embedding = VectorField(dimensions=1536, null=True)  # OpenAI ada-002
    
    class Meta:
        indexes = [
            HnswIndex(
                name='chat_embedding_idx',
                fields=['embedding'],
                opclasses=['vector_cosine_ops'],
                m=16, ef_construction=64
            )
        ]
    
    def find_similar_queries(self, limit: int = 5):
        """Semantic similarity search"""
        return ChatMessage.objects.annotate(
            similarity=CosineDistance('embedding', self.embedding)
        ).order_by('similarity')[:limit]
