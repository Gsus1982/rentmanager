from django.contrib import admin
from .models import Socio, Inmueble, Gasto, Transaccion, DeclaracionTrimestral

@admin.register(Socio)
class SocioAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'porcentaje_participacion', 'activo', 'fecha_creacion']
    list_filter = ['activo', 'fecha_creacion']
    search_fields = ['usuario__first_name', 'usuario__last_name', 'usuario__email']
    readonly_fields = ['fecha_creacion']
    fieldsets = (
        ('Información del Socio', {
            'fields': ('usuario', 'porcentaje_participacion', 'activo')
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion',),
            'classes': ('collapse',)
        }),
    )

@admin.register(Inmueble)
class InmuebleAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'tipo', 'ciudad', 'renta_mensual', 'iva_porcentaje', 'irpf_porcentaje', 'activo']
    list_filter = ['tipo', 'ciudad', 'activo', 'fecha_creacion']
    search_fields = ['nombre', 'direccion', 'ciudad', 'referencias_catastro']
    readonly_fields = ['fecha_creacion', 'fecha_actualizacion']
    fieldsets = (
        ('Datos Básicos', {
            'fields': ('nombre', 'tipo', 'activo')
        }),
        ('Ubicación', {
            'fields': ('direccion', 'ciudad', 'codigo_postal', 'referencias_catastro')
        }),
        ('Datos Fiscales', {
            'fields': ('renta_mensual', 'iva_porcentaje', 'irpf_porcentaje')
        }),
        ('Periodo Alquiler', {
            'fields': ('fecha_inicio_alquiler', 'fecha_fin_alquiler')
        }),
        ('Socios', {
            'fields': ('socios',)
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Gasto)
class GastoAdmin(admin.ModelAdmin):
    list_display = ['inmueble', 'categoria', 'cantidad', 'fecha', 'factura_numero']
    list_filter = ['categoria', 'fecha', 'inmueble', 'fecha_creacion']
    search_fields = ['inmueble__nombre', 'descripcion', 'factura_numero']
    readonly_fields = ['fecha_creacion']
    date_hierarchy = 'fecha'
    fieldsets = (
        ('Información del Gasto', {
            'fields': ('inmueble', 'categoria', 'descripcion', 'cantidad')
        }),
        ('Documentación', {
            'fields': ('fecha', 'factura_numero')
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion',),
            'classes': ('collapse',)
        }),
    )

@admin.register(Transaccion)
class TransaccionAdmin(admin.ModelAdmin):
    list_display = ['inmueble', 'tipo', 'descripcion', 'cantidad', 'fecha', 'es_bruto']
    list_filter = ['tipo', 'fecha', 'inmueble', 'es_bruto']
    search_fields = ['inmueble__nombre', 'descripcion']
    readonly_fields = ['fecha_creacion']
    date_hierarchy = 'fecha'
    fieldsets = (
        ('Información de la Transacción', {
            'fields': ('inmueble', 'tipo', 'descripcion', 'cantidad')
        }),
        ('Clasificación', {
            'fields': ('es_bruto', 'fecha', 'mes')
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion',),
            'classes': ('collapse',)
        }),
    )

@admin.register(DeclaracionTrimestral)
class DeclaracionAdmin(admin.ModelAdmin):
    list_display = ['socio', 'anio', 'trimestre', 'iva_a_pagar', 'irpf_total', 'declarado']
    list_filter = ['anio', 'trimestre', 'declarado', 'socio']
    search_fields = ['socio__usuario__first_name', 'socio__usuario__last_name']
    readonly_fields = ['fecha_creacion']
    fieldsets = (
        ('Información', {
            'fields': ('socio', 'anio', 'trimestre', 'declarado')
        }),
        ('IVA', {
            'fields': ('iva_total_ingreso', 'iva_total_gasto', 'iva_a_pagar')
        }),
        ('IRPF', {
            'fields': ('irpf_total',)
        }),
        ('Declaración', {
            'fields': ('fecha_declaracion', 'notas')
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion',),
            'classes': ('collapse',)
        }),
    )
