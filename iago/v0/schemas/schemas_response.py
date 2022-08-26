"""
json-schemas for the responses of the API endpoints.
"""
from iago.settings import MODEL_VECTOR_SIZE

transform = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "vectors": {
            "type": "array",
            "description": "List of embeddings corresponding to the input strings.", 
            "items": {
                "type": "array",
                "description": "An embedding vector.",
                "minItems": MODEL_VECTOR_SIZE,
                "maxItems": MODEL_VECTOR_SIZE,
                "items": {
                    "type": "number",
                }
            }
        }
    },
    "required": ["k"],
}