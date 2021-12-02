messagesForLearnerSchema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "userProfile": {
            "type": "object",
            "items": {"learner_type": "string", "user_email": "string", "user_id": "integer"}
        },
        "courseData": {
            "type": "object",
            "items": {"location": "string"}
        },
    },
    "required": ["userProfile", "courseData"],
}

articleSubmissionSchema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "url": {
            "type": "string",
            "format": "uri"
        },
        "environment": {
            "type": "string",
            "enum": ["live", "test"],
        },
        "sync": {
            "type": "boolean",
        }
    },
    "required": ["url"],
}

querySubmissionSchema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
        },
        "text": {
            "type": "string",
        },
        "k": {
            "type": "integer"
        }
    },
    "required": ["query"],
}
