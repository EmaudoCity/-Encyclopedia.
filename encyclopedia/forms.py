from django import forms


class EntryForm(forms.Form):
    title = forms.RegexField(
        regex=r"\A\w[\w .()'-]*\Z",
        max_length=120,
        strip=True,
        error_messages={
            "invalid": "Start with a letter or number and use only letters, numbers, spaces, dots, parentheses, apostrophes, underscores, or hyphens."
        },
    )
    content = forms.CharField(widget=forms.Textarea(attrs={"rows": 20}), strip=False)
