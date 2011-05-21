from django import forms

class ManagementForm(forms.Form):
    """
    ``ManagementForm`` is used to keep track of how many form instances
    are displayed on the page. If adding new forms via javascript, you should
    increment the count field of this form as well.
    """
    current_step = forms.CharField(widget=forms.HiddenInput)
