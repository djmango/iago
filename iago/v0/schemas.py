from v0.models import Content

k = {
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

query_k = {
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

query_k_temperature = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
        },
        "k": {
            "type": "integer",
            "inclusiveMinimum": 0,
        },
        "temperature": {
            "type": "integer",
            "inclusiveMinimum": 0,
            "inclusiveMaximum": 100
        }
    },
    "required": ["query"],
}

texts = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "texts": {
            "type": "array",
            "uniqueItems": True,
            "items": {
                "type": "string"
            }
        }
    },
    "required": ["texts"],
}

model_field_search = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "The string to search for"
        },
        "k": {
            "type": "integer",
            "description": "The number of results to return",
            "exclusiveMinimum": 0
        },
        "similarity_minimum": {
            "type": "integer",
            "description": "The minimum similarity between the query and the results",
            "exclusiveMinimum": 0,
            "inclusiveMaximum": 100
        },
        "fields": {
            "type": "array",
            "description": "The fields to return",
            "uniqueItems": True,
            "items": {
                "type": "string",
            }
        },
        "search_field": {
            "type": "string",
            "description": "The field to search in"
        }
    },
    "required": ["query", "k"],
}


embeds = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "embeds": {
            "type": "array",
            "uniqueItems": True,
            "items": {
                "type": "array"
            }
        }
    },
    "required": ["embeds"],
}


skills_adjacent = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "skills": {
            "type": "array",
            "uniqueItems": True,
            "items": {
                "type": "string"
            }
        },
        "k": {
            "type": "integer",
            "description": "The number of adjacent skills to return per skill",
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

content_via_search = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "searchtext": {
            "type": "string",
            "description": "The title or skills to search for",
        },
        "skills": {
            "type": "array",
            "description": "The skills to look for in content",
            "uniqueItems": True,
            "items": {
                "type": "string"
            }
        },
        "type": {
            "type": "array",
            "description": "The types of content to allow in result",
            "uniqueItems": True,
            "items": {
                "type": "string",
                "enum": vars(Content.types)["_member_names_"],
            }
        },
        "provider": {
            "type": "array",
            "description": "The providers whos content to allow in result",
            "uniqueItems": True,
            "items": {
                "type": "string",
                "enum": vars(Content.providers)["_member_names_"],
            }
        },
        "length": {
            "type": "array",
            "description": "Min and a max read length in seconds filter",
            "minItems": 2,
            "maxItems": 2,
            "uniqueItems": True,
            "items": {
                "type": "integer",
                "inclusiveMinimum": 0
            }
        },
        "k": {
            "type": "integer",
            "description": "The number of content pieces to return",
            "exclusiveMinimum": 0
        },
        "page": {
            "type": "integer",
            "description": "The page to return. Each page has k elements. Defaults to 0",
            "inclusiveMinimum": 0
        },
        "strict": {
            "type": "boolean",
            "description": "If true, only return content that matches ALL skills provided, assuming the skill exists in the database",
        },
        "fields": {
            "type": "array",
            "description": "The fields to return",
            "uniqueItems": True,
            "items": {
                "type": "string",
                "enum": [x.name for x in Content._meta.get_fields()],
            }
        }

    },
    "required": ["k"],
    "oneOf": [
        {"required": ["skills"]},
        {"required": ["searchtext"]}
    ]
}


content_via_adjacent_skills = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "skills": {
            "type": "array",
            "description": "The skills to look for in content",
            "uniqueItems": True,
            "items": {
                "type": "string"
            }
        },
        "type": {
            "type": "array",
            "description": "The types of content to allow in result",
            "uniqueItems": True,
            "items": {
                "type": "string",
                "enum": vars(Content.types)["_member_names_"],
            }
        },
        "provider": {
            "type": "array",
            "description": "The providers whos content to allow in result",
            "uniqueItems": True,
            "items": {
                "type": "string",
                "enum": vars(Content.providers)["_member_names_"],
            }
        },
        "length": {
            "type": "array",
            "description": "Min and a max read length in seconds filter",
            "minItems": 2,
            "maxItems": 2,
            "uniqueItems": True,
            "items": {
                "type": "integer",
                "inclusiveMinimum": 0
            }
        },
        "k": {
            "type": "integer",
            "description": "The number of content pieces to return",
            "exclusiveMinimum": 0
        },
        "page": {
            "type": "integer",
            "description": "The page to return. Each page has k elements. Defaults to 0",
            "inclusiveMinimum": 0
        },
        "fields": {
            "type": "array",
            "description": "The fields to return",
            "uniqueItems": True,
            "items": {
                "type": "string",
                "enum": [x.name for x in Content._meta.get_fields()],
            }
        }
    },
    "required": ["skills", "k"]
}

content_via_recommendation = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "title": {
            "type": "string",
            "description": "A free-form job title",
        },
        "position": {
            "type": "string",
            "description": "A free-form job position",
        },
        "lastconsumedcontent": {
            "type": "array",
            "description": "The content pieces that the user has consumed",
            "uniqueItems": True,
            # "minItems": 1, i guess we have to keep these valid because i keep getting empty requests - will handle it on iago side, send random recommendation idk
            "items": {
                "type": "string",
                "description": "The unique identifier for a content piece",
                "format": "uuid"
            }
        },
        "k": {
            "type": "integer",
            "description": "The number of recommendations to return",
            "exclusiveMinimum": 0
        },
        "page": {
            "type": "integer",
            "description": "The page to return. Each page has k elements. Defaults to 0",
            "inclusiveMinimum": 0
        },
        "type": {
            "type": "array",
            "description": "The types of content to allow in result",
            "uniqueItems": True,
            "items": {
                "type": "string",
                "enum": vars(Content.types)["_member_names_"],
            }
        },
        "provider": {
            "type": "array",
            "description": "The providers to allow in result",
            "items": {
                "type": "string",
                "enum": vars(Content.providers)["_member_names_"],
            }
        },
        "length": {
            "type": "array",
            "description": "Min and a max read length in seconds filter",
            "minItems": 2,
            "maxItems": 2,
            "uniqueItems": True,
            "items": {
                "type": "integer",
                "inclusiveMinimum": 0
            }
        },
        "weights": {
            "type": "array",
            "description": "The weight of the position and the content history. For example, provided [0.5, 1] means content history is twice as heavy as position in the recomendation",
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
        },
        "fields": {
            "type": "array",
            "description": "The fields to return",
            "uniqueItems": True,
            "items": {
                "type": "string",
                "enum": [x.name for x in Content._meta.get_fields()],
            }
        }
    },
    "required": ["k"],
    "anyOf": [
        {"required": ["position"]},
        {"required": ["lastconsumedcontent"]}
    ]
}


content_via_title = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "The content title to search for",
        },
        "type": {
            "type": "array",
            "description": "The types of content to allow in result",
            "uniqueItems": True,
            "items": {
                "type": "string",
                "enum": vars(Content.types)["_member_names_"],
            }
        },
        "provider": {
            "type": "array",
            "description": "The providers whos content to allow in result",
            "uniqueItems": True,
            "items": {
                "type": "string",
                "enum": vars(Content.providers)["_member_names_"],
            }
        },
        "length": {
            "type": "array",
            "description": "Min and a max read length in seconds filter",
            "minItems": 2,
            "maxItems": 2,
            "uniqueItems": True,
            "items": {
                "type": "integer",
                "inclusiveMinimum": 0
            }
        },
        "k": {
            "type": "integer",
            "description": "The number of content pieces to return",
            "exclusiveMinimum": 0
        },
        "page": {
            "type": "integer",
            "description": "The page to return. Each page has k elements. Defaults to 0",
            "inclusiveMinimum": 0
        },
        "fields": {
            "type": "array",
            "description": "The fields to return",
            "uniqueItems": True,
            "items": {
                "type": "string",
                "enum": [x.name for x in Content._meta.get_fields()],
            }
        }

    },
    "required": ["query", "k"],
}