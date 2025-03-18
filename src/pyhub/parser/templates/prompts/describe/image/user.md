# Output Format
<title>...</title>
<details>...</details>
<entities>...</entities>
<hypothetical_questions>...</hypothetical_questions>

{% if context %}# Context
{{ context }}{% endif %}

# Requirements
- Provide a short, descriptive title for the image.
- Clearly summarize the main details.
- Identify and list key entities or objects.
- Pose hypothetical questions that explore deeper implications or ideas.
{% if language %}- Ensure Reply in {{ language }} Language{% endif %}