"""Simple template engine for non-Django environments."""

import re
from typing import Any, Dict


class SimpleTemplate:
    """Simple template implementation for non-Django environments."""

    def __init__(self, template_string: str):
        self.template_string = template_string

    def render(self, context: Dict[str, Any]) -> str:
        """Render the template with the given context."""
        result = self.template_string

        # Simple variable replacement
        for key, value in context.items():
            result = result.replace(f"{{{{ {key} }}}}", str(value))

        # Handle for loops (simple implementation)
        for_pattern = r"{{% for (\w+) in (\w+) %}}(.*?){{% endfor %}}"
        matches = re.findall(for_pattern, result, re.DOTALL)

        for var_name, list_name, loop_content in matches:
            if list_name in context and isinstance(context[list_name], list):
                loop_results = []
                for item in context[list_name]:
                    loop_result = loop_content
                    # Replace variable references
                    if hasattr(item, "name"):
                        loop_result = loop_result.replace(f"{{{{ {var_name}.name }}}}", item.name)
                    if hasattr(item, "description"):
                        loop_result = loop_result.replace(f"{{{{ {var_name}.description }}}}", item.description)
                    loop_results.append(loop_result.strip())

                full_pattern = f"{{% for {var_name} in {list_name} %}}{loop_content}{{% endfor %}}"
                result = result.replace(full_pattern, "\n".join(loop_results))

        # Handle if statements
        if_pattern = r"{{% if (\w+) %}}(.*?){{% endif %}}"
        matches = re.findall(if_pattern, result, re.DOTALL)

        for var_name, if_content in matches:
            if var_name in context and context[var_name]:
                result = result.replace(f"{{% if {var_name} %}}{if_content}{{% endif %}}", if_content)
            else:
                result = result.replace(f"{{% if {var_name} %}}{if_content}{{% endif %}}", "")

        return result
