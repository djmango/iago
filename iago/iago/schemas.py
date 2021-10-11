messagesForLearnerSchema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "userProfile": {"type": "object"},
        "courseData": {"type": "object"},
    },
    "required": ["userProfile", "courseData"],
}