from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

class Socio(models.Model):
    """Modelo para gestionar socios/propietarios"""
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='socio')
    porcentaje_participacion = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        default=100
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    activo = models.BooleanField(default=True)
    
    class Meta:
        verbose_name_plural = "Socios"
        ordering = ['usuario__first_name']
    
    def __str__(self):
        return f"{self.usuario.get_full_name()} ({self.porcentaje_participacion}%)"


class Inmueble(models.Model):
    """Modelo para gestionar propiedades"""
    TIPOS = [
        ('PISO', 'Piso'),
        ('LOCAL', 'Local Comercial'),
        ('CASA', 'Casa'),
        ('GARAJE', 'Garaje'),
    ]
    
    nombre = models.CharField(max_length=255)
    tipo = models.CharField(max_length=20, choices=TIPOS, default='PISO')
    direccion = models.CharField(max_length=255)
    ciudad = models.CharField(max_length=100)
    codigo_postal = models.CharField(max_length=10)
    referencias_catastro = models.CharField(max_length=255, blank=True, null=True)
    
    # Datos fiscales
    renta_mensual = models.DecimalField(max_digits=10, decimal_places=2)
    socios = models.ManyToManyField(Socio, related_name='inmuebles', blank=True)
    
    # Configuración de impuestos
    iva_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('21.00'))
    irpf_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('19.00'))
    
    fecha_inicio_alquiler = models.DateField()
    fecha_fin_alquiler = models.DateField(blank=True, null=True)
    activo = models.BooleanField(default=True)
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['nombre']
        verbose_name_plural = "Inmuebles"
    
    def __str__(self):
        return f"{self.nombre} - {self.direccion}"
    
    @property
    def renta_anual_bruta(self):
        if self.renta_mensual is None:
            return Decimal('0')
        return self.renta_mensual * 12

    @property
    def iva_total(self):
        if self.renta_mensual is None:
            return Decimal('0')
        return self.renta_anual_bruta * (self.iva_porcentaje / 100)

    @property
    def irpf_total(self):
        if self.renta_mensual is None:
            return Decimal('0')
        return self.renta_anual_bruta * (self.irpf_porcentaje / 100)

    @property
    def renta_anual_neta(self):
        if self.renta_mensual is None:
            return Decimal('0')
        return self.renta_anual_bruta - self.irpf_total

    @property
    def gastos_totales(self):
        if not self.pk:  # Si aún no está guardado
            return Decimal('0')
        return sum([gasto.cantidad for gasto in self.gastos.all()]) or Decimal('0')

    @property
    def renta_neta_con_gastos(self):
        if self.renta_mensual is None:
            return Decimal('0')
        return self.renta_anual_neta - self.gastos_totales


class Gasto(models.Model):
    """Modelo para gastos deducibles de inmuebles"""
    CATEGORIAS = [
        ('MANTENIMIENTO', 'Mantenimiento'),
        ('REPARACION', 'Reparación'),
        ('SERVICIOS', 'Servicios (agua, luz, gas)'),
        ('SEGUROS', 'Seguros'),
        ('ADMINISTRATIVO', 'Gastos Administrativos'),
        ('OTRO', 'Otro'),
    ]
    
    inmueble = models.ForeignKey(Inmueble, on_delete=models.CASCADE, related_name='gastos')
    categoria = models.CharField(max_length=50, choices=CATEGORIAS)
    descripcion = models.CharField(max_length=255)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateField()
    factura_numero = models.CharField(max_length=100, blank=True, null=True)
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-fecha']
        verbose_name_plural = "Gastos"
    
    def __str__(self):
        return f"{self.inmueble.nombre} - {self.categoria} - {self.cantidad}€"


class Transaccion(models.Model):
    """Modelo para registrar ingresos/egresos"""
    TIPOS = [
        ('INGRESO', 'Ingreso'),
        ('GASTO', 'Gasto'),
    ]
    
    inmueble = models.ForeignKey(Inmueble, on_delete=models.CASCADE, related_name='transacciones')
    tipo = models.CharField(max_length=20, choices=TIPOS)
    descripcion = models.CharField(max_length=255)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateField()
    mes = models.DateField()  # Primer día del mes para agrupación
    
    es_bruto = models.BooleanField(default=True)  # True si es cantidad bruta, False si neta
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-fecha']
        verbose_name_plural = "Transacciones"
    
    def __str__(self):
        return f"{self.inmueble.nombre} - {self.tipo} - {self.cantidad}€"


class DeclaracionTrimestral(models.Model):
    """Modelo para tracking de declaraciones trimestrales (IVA, IRPF)"""
    TRIMESTRES = [
        ('Q1', 'Q1 (Enero-Marzo)'),
        ('Q2', 'Q2 (Abril-Junio)'),
        ('Q3', 'Q3 (Julio-Septiembre)'),
        ('Q4', 'Q4 (Octubre-Diciembre)'),
    ]
    
    socio = models.ForeignKey(Socio, on_delete=models.CASCADE, related_name='declaraciones')
    anio = models.IntegerField()
    trimestre = models.CharField(max_length=2, choices=TRIMESTRES)
    
    iva_total_ingreso = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    iva_total_gasto = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    iva_a_pagar = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    irpf_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    declarado = models.BooleanField(default=False)
    fecha_declaracion = models.DateField(blank=True, null=True)
    notas = models.TextField(blank=True)
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('socio', 'anio', 'trimestre')
        ordering = ['-anio', '-trimestre']
        verbose_name_plural = "Declaraciones Trimestrales"
    
    def __str__(self):
        return f"{self.socio.usuario.get_full_name()} - {self.anio} {self.trimestre}"
