from crispy_forms.layout import Field, Row, Submit


class JustOneClickableSubmit(Submit):
    field_classes = "btn btn-primary cursor-pointer bg-blue-500 hover:bg-blue-700 text-white text-sm font-bold py-2 px-4 rounded float-right"

    def __init__(self, *, name="submit", value="Submit", **kwargs):
        onclick = """
            this.disabled = true;
            this.value = "Processing ...";
            this.form.requestSubmit();
        """
        super().__init__(name, value, onclick=onclick, **kwargs)


class EvenRow(Row):
    def __init__(self, *fields, **kwargs):

        new_fields = []
        for field in fields:
            if isinstance(field, str):
                field = Field(field, wrapper_class="flex-1")
            new_fields.append(field)

        kwargs.setdefault("css_class", "flex flex-row gap-2")
        super().__init__(*new_fields, **kwargs)
