"""Form Bootstrap untuk membuat dan mengedit data Pot."""

from django import forms

from .models import Pot


class PotForm(forms.ModelForm):
    class Meta:
        model = Pot
        fields = [
            "kode_pot",
            "jenis_tanaman",
            "tanggal_tanam",
            "fase_pertumbuhan",
            "device_terpasang",
            "keterangan",
        ]
        widgets = {
            "tanggal_tanam": forms.DateInput(attrs={"type": "date"}),
            "keterangan": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = (
                "form-select" if isinstance(field.widget, forms.Select) else "form-control"
            )
        self.fields["device_terpasang"].required = False
        if self.instance and self.instance.pk:
            # Kode pot adalah primary key, sehingga tidak diubah saat edit.
            self.fields["kode_pot"].disabled = True
