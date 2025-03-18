# Output Format
Structure your response using the following tags:

  - `<title>`: Concise summary of the table.
  - `<details>`: Key insights and numerical data.
  - `<entities>`: List of relevant terms, numbers, or categories.
  - `<hypothetical_questions>`: Open-ended questions based on the table.

{% if context %}# Context
{{ context }}{% endif %}

# Example Output

<title>
Annual Financial Performance of the Company
</title>
<details>
The table displays the company's financial performance for 2024.
Revenue reached $500M, with a net profit of $100M (20% margin).
R&D investment increased to $80M.
</details>
<entities>
Revenue, Net Profit, R&D Investment, Market Share, Total Assets
</entities>
<hypothetical_questions>
- How will the increase in R&D investment impact future profits?
- Can the company sustain its revenue growth over the next five years?
</hypothetical_questions>

# Notes
- Include numerical values and relevant terms.
- Summarize key takeaways from the table.
- Ensure questions encourage deeper analysis.
{% if language %}- Ensure Reply in {{ language }} Language{% endif %}