from django import forms
from .models import Inmueble, Gasto, Transaccion
from datetime import date

class InmuebleForm(forms.ModelForm):
    class Meta:
        model = Inmueble
        fields = [
            'nombre', 'tipo', 'direccion', 'ciudad', 'codigo_postal',
            'referencias_catastro', 'renta_mensual', 'iva_porcentaje',
            'irpf_porcentaje', 'fecha_inicio_alquiler', 'fecha_fin_alquiler', 'socios'
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del inmueble (ej: Piso Centro)'
            }),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'direccion': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Dirección completa'
            }),
            'ciudad': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ciudad'
            }),
            'codigo_postal': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'CP'
            }),
            'referencias_catastro': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Opcional'
            }),
            'renta_mensual': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': '800.00'
            }),
            'iva_porcentaje': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'value': '21.00'
            }),
            'irpf_porcentaje': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'value': '19.00'
            }),
            'fecha_inicio_alquiler': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'fecha_fin_alquiler': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'socios': forms.CheckboxSelectMultiple(attrs={
                'class': 'form-check-input'
            }),
        }


class GastoForm(forms.ModelForm):
    class Meta:
        model = Gasto
        fields = ['categoria', 'descripcion', 'cantidad', 'fecha', 'factura_numero']
        widgets = {
            'categoria': forms.Select(attrs={'class': 'form-control'}),
            'descripcion': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Descripción del gasto'
            }),
            'cantidad': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': '150.00'
            }),
            'fecha': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'factura_numero': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de factura (opcional)'
            }),
        }


class TransaccionForm(forms.ModelForm):
    class Meta:
        model = Transaccion
        fields = ['tipo', 'descripcion', 'cantidad', 'fecha', 'es_bruto', 'mes']
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'descripcion': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Descripción'
            }),
            'cantidad': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'fecha': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'mes': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'es_bruto': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
