from v0.models import Content

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


jobSkillMatchSchema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "jobtitle": {
            "type": "string",
        },
        "k": {
            "type": "integer"
        }
    },
    "required": ["jobtitle"],
}

queryKSchema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
        },
        "k": {
            "type": "integer",
            "inclusiveMinimum": 0,
        }
    },
    "required": ["query"],
}


kSchema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "k": {
            "type": "integer",
            "inclusiveMinimum": 0,
        }
    },
    "required": ["k"],
}

textsSchema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "texts": {
            "type": "array",
            "items": {
                "type": "string"
            }
        }
    },
    "required": ["texts"],
}


embedsSchema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "embeds": {
            "type": "array",
            "items": {
                "type": "array"
            }
        }
    },
    "required": ["embeds"],
}

searchContentSchema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "skills": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },
        "type": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": vars(Content.types)['_member_names_'],
                # "enum": ["article", "video", "pdf"]
            }
        },
        "length": {
            "type": "array",
            "minContains": 2,
            "maxContains": 2,
            "uniqueItems": True,
            "items": {
                "type": "integer",
                "inclusiveMinimum": 0
            }
        },
        "k": {
            "type": "integer",
            "description": "The number of content pieces to return.",
            "exclusiveMinimum": 0
        },
        "page": {
            "type": "integer",
            "inclusiveMinimum": 0
        },
        "strict": {
            "type": "boolean"
        }

    },
    "required": ["skills", "type"],
}


adjacentSkillsSchema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "skills": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },
        "k": {
            "type": "integer",
            "description": "The number of adjacent skills to return per skill.",
            "exclusiveMinimum": 0
        },
        "temperature": {
            "type": "integer",
            "inclusiveMinimum": 0,
            "inclusiveMaximum": 100
        }

    },
    "required": ["skills"],
}

recomendContentSchema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "title": {
            "type": "string",
            "description": "A free-form job title.",
        },
        "position": {
            "type": "string",
            "description": "A free-form job position.",
        },
        "lastconsumedcontent": {
            "type": "array",
            "items": {
                "type": "string",
                "description": "The unique identifier for a content piece.",
                "format": "uuid"
            }
        },
        "k": {
            "type": "integer",
            "description": "The number of recommendations to return.",
            "exclusiveMinimum": 0
        },
        "weights": {
            "type": "array",
            "description": "The weight of the position and the content history. For example, provided [0.5, 1] means content history is twice as heavy as position in the recomendation.",
            "items": {
                "type": "number",
                "inclusiveMinimum": 0,
                "inclusiveMaximum": 1,
                "length": 2
            }
        },
        "temperature": {
            "type": "integer",
            "inclusiveMinimum": 0,
            "inclusiveMaximum": 100
        }
    },
    "required": ["position", "lastconsumedcontent", "k"]
}
