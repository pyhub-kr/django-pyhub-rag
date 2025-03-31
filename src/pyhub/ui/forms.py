from django import forms


class CrispyLayoutAwareModelForm(forms.ModelForm):
    """
    crispy layout에 명시되지 않은 필드에 대해서 유효성 검사 에러가 발생하면 Form 화면에 보여지는 에러가 없어서 혼란스러울 수 있습니다.
    명시되지 않은 필드에 대해서 non field errors로서 처리합니다.
    """

    def full_clean(self):
        super().full_clean()

        if hasattr(self, "helper") and hasattr(self.helper, "layout"):
            extra_errored_fields = (
                set(self.errors.keys()) - set(self.get_layout_field_names(self.helper.layout)) - {"__all__"}
            )
            if extra_errored_fields:
                for field_name in extra_errored_fields:
                    field_label = self.fields[field_name].label
                    e = forms.ValidationError(f"{field_label} : {' '.join(self.errors[field_name])}")
                    self.add_error(None, e)

    @classmethod
    def get_layout_field_names(cls, layout) -> list[str]:
        field_names = []

        if hasattr(layout, "fields"):
            # Layout or compound field with nested fields
            for field in layout.fields:
                field_names.extend(cls.get_layout_field_names(field))
        else:
            # Base field - just return the field name
            field_names.append(str(layout))

        return field_names
