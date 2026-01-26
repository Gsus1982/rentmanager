import json
from datetime import date, datetime
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login  # ✅ USAR authenticate()
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import (
    Sum, F, DecimalField, Q, Prefetch, Count,
    Case, When, Value, CharField, Exists, OuterRef
)
from django.db.models.functions import Coalesce, TruncMonth
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.contrib.postgres.aggregates import ArrayAgg
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.cache import cache_page
from django.views.generic import CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.core.cache import cache

from .models import Socio, Inmueble, Gasto
from .forms import InmuebleForm, GastoForm


# ============================================================================
# AUTENTICACIÓN
# ============================================================================

@require_http_methods(["GET", "POST"])
@csrf_protect
def login_view(request):
    """Vista de login segura"""
    if request.user.is_authenticated:
        return redirect('dashboard')

    error = None

    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        password = request.POST.get("password") or ""

        # Usar check_password() directamente (funciona en local y producción)
        from django.contrib.auth.models import User
        try:
            user = User.objects.get(username=username)
            if user.check_password(password) and user.is_active:
                login(request, user)
                next_url = request.GET.get("next") or request.POST.get("next")
                if next_url and (not next_url.startswith('/') or '//' in next_url):
                    next_url = None
                return redirect(next_url or 'dashboard')
            else:
                error = "Credenciales incorrectas"
        except User.DoesNotExist:
            error = "Credenciales incorrectas"

    return render(request, "login.html", {"error": error})

# ============================================================================
# HELPERS Y UTILIDADES - OPTIMIZADO PARA POSTGRESQL
# ============================================================================

def get_user_inmuebles(user):
    """
    Obtiene inmuebles según permisos del usuario
    Optimizado con Prefetch y select_related para reducir queries
    PostgreSQL: Usa EXISTS en lugar de IN para mejor performance
    """
    try:
        socio = Socio.objects.select_related('usuario').get(usuario=user)
        
        # Prefetch optimizado de gastos ordenados por fecha
        gastos_prefetch = Prefetch(
            'gastos',
            queryset=Gasto.objects.select_related('inmueble').order_by('-fecha')
        )
        
        # Prefetch de transacciones recientes
        transacciones_prefetch = Prefetch(
            'transacciones',
            queryset=None  # Ajusta según tu modelo de Transaccion
        )
        
        inmuebles = socio.inmuebles.select_related().prefetch_related(
            gastos_prefetch,
            'socios__usuario',  # Optimizar acceso a socios
        )
        return inmuebles, socio
        
    except Socio.DoesNotExist:
        if user.is_staff:
            gastos_prefetch = Prefetch(
                'gastos',
                queryset=Gasto.objects.select_related('inmueble').order_by('-fecha')
            )
            inmuebles = Inmueble.objects.select_related().prefetch_related(
                gastos_prefetch,
                'socios__usuario',
            )
            return inmuebles, None
        else:
            return Inmueble.objects.none(), None


def check_inmueble_permission(user, inmueble):
    """
    Verifica permisos de acceso al inmueble
    PostgreSQL: Usa EXISTS para consultas más eficientes
    """
    if user.is_staff:
        return True
    
    # EXISTS es más eficiente en PostgreSQL que contar o cargar objetos
    # Solo verifica la existencia sin cargar datos
    return Socio.objects.filter(
        usuario=user,
        inmuebles=inmueble
    ).exists()


def get_cache_key(user_id, key_name):
    """Genera claves de cache consistentes"""
    return f"user_{user_id}_{key_name}"


# ============================================================================
# DASHBOARD - CON AGREGACIONES POSTGRESQL
# ============================================================================

@login_required(login_url="login")
def dashboard(request):
    """
    Dashboard con agregaciones avanzadas usando PostgreSQL
    Optimizado con annotate, agregaciones y cache
    """
    
    # Intentar obtener datos del cache (5 minutos)
    cache_key = get_cache_key(request.user.id, 'dashboard_data')
    cached_data = cache.get(cache_key)
    
    if cached_data:
        return render(request, 'dashboard.html', cached_data)
    
    # Obtener inmuebles base
    inmuebles_base, socio = get_user_inmuebles(request.user)
    
    # Anotar cada inmueble con su suma de gastos (1 query en lugar de N)
    # PostgreSQL optimiza esta agregación muy eficientemente
    inmuebles = inmuebles_base.filter(activo=True).annotate(
        gastos_sum=Coalesce(
            Sum('gastos__cantidad', output_field=DecimalField()),
            Decimal('0'),
            output_field=DecimalField()
        ),
        num_gastos=Count('gastos')
    )

    # Agregaciones en una sola consulta SQL optimizada
    agregados = inmuebles.aggregate(
        renta_bruta_total=Coalesce(
            Sum(F('renta_mensual') * 12, output_field=DecimalField()), 
            Decimal('0'), 
            output_field=DecimalField()
        ),
        gastos_totales=Coalesce(
            Sum('gastos__cantidad', output_field=DecimalField()),
            Decimal('0'),
            output_field=DecimalField()
        ),
        total_inmuebles=Count('id', distinct=True)
    )

    renta_bruta_total = agregados['renta_bruta_total']
    gastos_totales = agregados['gastos_totales']
    num_inmuebles = agregados['total_inmuebles']

    # Usar only() para traer solo campos necesarios (reduce I/O)
    # PostgreSQL beneficia mucho de esto al reducir datos transferidos
    inmuebles_calc = inmuebles.only(
        'id', 'nombre', 'renta_mensual', 'tipo_iva', 'tipo_irpf', 'tipo'
    )
    
    renta_neta_total = Decimal('0')
    iva_total = Decimal('0')
    irpf_total = Decimal('0')
    
    inmuebles_data = []
    for inmueble in inmuebles_calc:
        renta_neta_total += inmueble.renta_anual_neta
        iva_total += inmueble.iva_total
        irpf_total += inmueble.irpf_total
        
        inmuebles_data.append({
            'nombre': inmueble.nombre,
            'tipo': inmueble.tipo,
            'renta_bruta': str(inmueble.renta_anual_bruta),
            'renta_neta': str(inmueble.renta_anual_neta),
            'iva': str(inmueble.iva_total),
            'irpf': str(inmueble.irpf_total),
            'gastos': str(inmueble.gastos_sum),  # Usar valor anotado
        })

    context = {
        'inmuebles': inmuebles_calc,
        'renta_bruta_total': renta_bruta_total,
        'renta_neta_total': renta_neta_total,
        'gastos_totales': gastos_totales,
        'iva_total': iva_total,
        'irpf_total': irpf_total,
        'inmuebles_json': json.dumps(inmuebles_data),
        'socio': socio,
        'num_inmuebles': num_inmuebles,
    }
    
    # Guardar en cache por 5 minutos
    cache.set(cache_key, context, 300)

    return render(request, 'dashboard.html', context)


# ============================================================================
# LISTADO DE INMUEBLES - CON BÚSQUEDA FULL-TEXT POSTGRESQL
# ============================================================================

@login_required(login_url="login")
def inmuebles_list(request):
    """
    Listado con búsqueda full-text usando PostgreSQL
    Implementa SearchVector para búsquedas eficientes
    """
    inmuebles, _ = get_user_inmuebles(request.user)

    # Filtrado por tipo con validación
    tipo_filter = request.GET.get('tipo')
    if tipo_filter and tipo_filter in dict(Inmueble.TIPOS):
        inmuebles = inmuebles.filter(tipo=tipo_filter)

    # Búsqueda de texto usando PostgreSQL Full-Text Search
    # Mucho más eficiente que ILIKE para grandes volúmenes
    search = request.GET.get('search', '').strip()
    if search:
        # Opción 1: Búsqueda simple con ILIKE (funcional pero lenta)
        # inmuebles = inmuebles.filter(
        #     Q(nombre__icontains=search) |
        #     Q(direccion__icontains=search)
        # )
        
        # Opción 2: Full-Text Search de PostgreSQL (RECOMENDADO)
        # Requiere crear índice GIN: CREATE INDEX idx_inmueble_search 
        # ON inmuebles USING GIN(to_tsvector('spanish', nombre || ' ' || COALESCE(direccion, '')));
        search_vector = SearchVector('nombre', 'direccion', config='spanish')
        search_query = SearchQuery(search, config='spanish')
        inmuebles = inmuebles.annotate(
            search=search_vector,
            rank=SearchRank(search_vector, search_query)
        ).filter(search=search_query).order_by('-rank')

    # Anotar con contadores para evitar queries adicionales
    inmuebles = inmuebles.annotate(
        total_gastos=Count('gastos'),
        suma_gastos=Coalesce(Sum('gastos__cantidad'), Decimal('0'))
    )

    # Defer campos grandes que no se muestran en el listado
    # PostgreSQL beneficia de esto al no transferir datos innecesarios
    inmuebles = inmuebles.defer('descripcion', 'notas')

    # Ordenamiento con validación
    order_by = request.GET.get('order', '-id')
    valid_orders = {
        'nombre': 'nombre',
        '-nombre': '-nombre',
        'renta': 'renta_mensual',
        '-renta': '-renta_mensual',
        'fecha': 'id',
        '-fecha': '-id',
        'gastos': 'suma_gastos',
        '-gastos': '-suma_gastos'
    }
    
    if order_by in valid_orders:
        inmuebles = inmuebles.order_by(valid_orders[order_by])
    else:
        inmuebles = inmuebles.order_by('-id')

    # Paginación eficiente
    paginator = Paginator(inmuebles, 20)
    page_number = request.GET.get('page', 1)
    
    try:
        page_obj = paginator.get_page(page_number)
    except Exception:
        page_obj = paginator.get_page(1)

    return render(request, 'inmuebles_list.html', {
        'page_obj': page_obj,
        'inmuebles': page_obj.object_list,
        'tipos': Inmueble.TIPOS,
        'tipo_filter': tipo_filter,
        'search': search,
        'order_by': order_by,
    })


# ============================================================================
# DETALLE DE INMUEBLE - CON ANÁLISIS TEMPORAL
# ============================================================================

@login_required(login_url="login")
def inmueble_detail(request, pk):
    """
    Detalle con análisis de gastos por periodo
    PostgreSQL: Usa TruncMonth y agregaciones temporales
    """
    # Optimizar carga inicial
    inmueble = get_object_or_404(
        Inmueble.objects.select_related().prefetch_related(
            'socios__usuario',
            Prefetch(
                'gastos',
                queryset=Gasto.objects.select_related().order_by('-fecha')
            )
        ),
        pk=pk
    )

    # Verificar permiso
    if not check_inmueble_permission(request.user, inmueble):
        messages.error(request, 'No tienes permiso para ver este inmueble')
        return redirect('inmuebles_list')

    # Gastos con agregación optimizada
    gastos = inmueble.gastos.all()
    
    # Agregación total
    gastos_agregado = gastos.aggregate(
        total=Coalesce(Sum('cantidad'), Decimal('0'), output_field=DecimalField()),
        promedio=Coalesce(Sum('cantidad') / Count('id'), Decimal('0'), output_field=DecimalField()),
        count=Count('id')
    )
    gastos_total = gastos_agregado['total']
    gastos_promedio = gastos_agregado['promedio']
    gastos_count = gastos_agregado['count']

    # Transacciones recientes (si existe el modelo)
    try:
        transacciones = inmueble.transacciones.all()[:10]
    except AttributeError:
        transacciones = []

    # Gastos por categoría con agregación
    gastos_por_categoria_query = gastos.values('categoria').annotate(
        total=Sum('cantidad'),
        count=Count('id')
    ).order_by('-total')
    
    gastos_por_categoria = {}
    for item in gastos_por_categoria_query:
        # Obtener display de categoría de forma eficiente
        categoria_display = dict(Gasto._meta.get_field('categoria').choices).get(
            item['categoria'], 
            item['categoria']
        )
        gastos_por_categoria[categoria_display] = {
            'total': item['total'],
            'count': item['count']
        }

    # Análisis temporal: gastos por mes (PostgreSQL TruncMonth)
    gastos_por_mes = gastos.annotate(
        mes=TruncMonth('fecha')
    ).values('mes').annotate(
        total=Sum('cantidad'),
        count=Count('id')
    ).order_by('mes')

    # Convertir a formato para gráficos
    gastos_mensuales_json = json.dumps([
        {
            'mes': item['mes'].strftime('%Y-%m') if item['mes'] else 'Sin fecha',
            'total': str(item['total']),
            'count': item['count']
        }
        for item in gastos_por_mes
    ])

    context = {
        'inmueble': inmueble,
        'gastos': gastos[:50],  # Limitar visualización inicial
        'gastos_total': gastos_total,
        'gastos_promedio': gastos_promedio,
        'gastos_count': gastos_count,
        'gastos_por_categoria': gastos_por_categoria,
        'gastos_json': json.dumps({k: str(v['total']) for k, v in gastos_por_categoria.items()}),
        'gastos_mensuales_json': gastos_mensuales_json,
        'transacciones': transacciones,
        'renta_neta': inmueble.renta_anual_neta,
        'renta_neta_con_gastos': inmueble.renta_neta_con_gastos,
    }

    return render(request, 'inmueble_detail.html', context)


# ============================================================================
# VISTAS CRUD - CON TRANSACCIONES ATÓMICAS
# ============================================================================

class InmuebleCreateView(LoginRequiredMixin, CreateView):
    """Crear inmueble con transacción atómica"""
    model = Inmueble
    form_class = InmuebleForm
    template_name = 'inmueble_form.html'
    success_url = reverse_lazy('inmuebles_list')
    login_url = 'login'

    @transaction.atomic  # PostgreSQL: Asegura atomicidad
    def form_valid(self, form):
        # Guardar inmueble
        self.object = form.save()
        
        # Asignar socio si existe
        try:
            socio = Socio.objects.select_for_update().get(usuario=self.request.user)
            if socio not in self.object.socios.all():
                self.object.socios.add(socio)
        except Socio.DoesNotExist:
            if not self.request.user.is_staff:
                messages.error(self.request, 'No tienes permiso para crear inmuebles')
                return redirect('inmuebles_list')
        
        # Invalidar cache del usuario
        cache_key = get_cache_key(self.request.user.id, 'dashboard_data')
        cache.delete(cache_key)
        
        messages.success(self.request, f'Inmueble "{self.object.nombre}" creado exitosamente')
        return redirect(self.get_success_url())


class InmuebleUpdateView(LoginRequiredMixin, UpdateView):
    """Actualizar inmueble"""
    model = Inmueble
    form_class = InmuebleForm
    template_name = 'inmueble_form.html'
    login_url = 'login'

    def dispatch(self, request, *args, **kwargs):
        inmueble = self.get_object()
        if not check_inmueble_permission(request.user, inmueble):
            messages.error(request, 'No tienes permiso para editar este inmueble')
            return redirect('inmuebles_list')
        return super().dispatch(request, *args, **kwargs)

    @transaction.atomic
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Invalidar cache
        cache_key = get_cache_key(self.request.user.id, 'dashboard_data')
        cache.delete(cache_key)
        
        messages.success(self.request, f'Inmueble "{self.object.nombre}" actualizado')
        return response

    def get_success_url(self):
        return reverse_lazy('inmueble_detail', kwargs={'pk': self.object.pk})


class InmuebleDeleteView(LoginRequiredMixin, DeleteView):
    """Soft delete de inmueble"""
    model = Inmueble
    template_name = 'inmueble_confirm_delete.html'
    success_url = reverse_lazy('inmuebles_list')
    login_url = 'login'

    def dispatch(self, request, *args, **kwargs):
        inmueble = self.get_object()
        if not check_inmueble_permission(request.user, inmueble):
            messages.error(request, 'No tienes permiso para eliminar este inmueble')
            return redirect('inmuebles_list')
        return super().dispatch(request, *args, **kwargs)

    @transaction.atomic
    def delete(self, request, *args, **kwargs):
        inmueble = self.get_object()
        nombre = inmueble.nombre
        
        # Soft delete
        inmueble.activo = False
        inmueble.save(update_fields=['activo'])
        
        # Invalidar cache
        cache_key = get_cache_key(request.user.id, 'dashboard_data')
        cache.delete(cache_key)
        
        messages.success(request, f'Inmueble "{nombre}" desactivado')
        return redirect(self.success_url)


class GastoCreateView(LoginRequiredMixin, CreateView):
    """Crear gasto"""
    model = Gasto
    form_class = GastoForm
    template_name = 'gasto_form.html'
    login_url = 'login'

    def dispatch(self, request, *args, **kwargs):
        inmueble = get_object_or_404(Inmueble, pk=self.kwargs['inmueble_pk'])
        if not check_inmueble_permission(request.user, inmueble):
            messages.error(request, 'No tienes permiso para agregar gastos')
            return redirect('inmuebles_list')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['inmueble'] = get_object_or_404(Inmueble, pk=self.kwargs['inmueble_pk'])
        return context

    @transaction.atomic
    def form_valid(self, form):
        form.instance.inmueble_id = self.kwargs['inmueble_pk']
        response = super().form_valid(form)
        
        # Invalidar cache
        cache_key = get_cache_key(self.request.user.id, 'dashboard_data')
        cache.delete(cache_key)
        
        messages.success(self.request, 'Gasto registrado exitosamente')
        return response

    def get_success_url(self):
        return reverse_lazy('inmueble_detail', kwargs={'pk': self.kwargs['inmueble_pk']})


class GastoUpdateView(LoginRequiredMixin, UpdateView):
    """Actualizar gasto"""
    model = Gasto
    form_class = GastoForm
    template_name = 'gasto_form.html'
    login_url = 'login'

    def dispatch(self, request, *args, **kwargs):
        gasto = self.get_object()
        if not check_inmueble_permission(request.user, gasto.inmueble):
            messages.error(request, 'No tienes permiso para editar este gasto')
            return redirect('inmuebles_list')
        return super().dispatch(request, *args, **kwargs)

    @transaction.atomic
    def form_valid(self, form):
        response = super().form_valid(form)
        cache_key = get_cache_key(self.request.user.id, 'dashboard_data')
        cache.delete(cache_key)
        messages.success(self.request, 'Gasto actualizado')
        return response

    def get_success_url(self):
        return reverse_lazy('inmueble_detail', kwargs={'pk': self.object.inmueble.pk})


class GastoDeleteView(LoginRequiredMixin, DeleteView):
    """Eliminar gasto"""
    model = Gasto
    template_name = 'gasto_confirm_delete.html'
    login_url = 'login'

    def dispatch(self, request, *args, **kwargs):
        gasto = self.get_object()
        if not check_inmueble_permission(request.user, gasto.inmueble):
            messages.error(request, 'No tienes permiso para eliminar este gasto')
            return redirect('inmuebles_list')
        return super().dispatch(request, *args, **kwargs)

    @transaction.atomic
    def delete(self, request, *args, **kwargs):
        inmueble_pk = self.object.inmueble.pk
        response = super().delete(request, *args, **kwargs)
        
        cache_key = get_cache_key(self.request.user.id, 'dashboard_data')
        cache.delete(cache_key)
        
        messages.success(self.request, 'Gasto eliminado')
        return response

    def get_success_url(self):
        return reverse_lazy('inmueble_detail', kwargs={'pk': self.object.inmueble.pk})


# ============================================================================
# API Y REPORTES
# ============================================================================

@login_required(login_url="login")
@cache_page(60 * 5)  # Cache de 5 minutos
def api_dashboard_data(request):
    """API endpoint optimizado"""
    inmuebles, _ = get_user_inmuebles(request.user)
    inmuebles = inmuebles.filter(activo=True).only(
        'id', 'nombre', 'tipo', 'renta_mensual', 'tipo_iva', 'tipo_irpf'
    ).annotate(
        gastos_sum=Coalesce(Sum('gastos__cantidad'), Decimal('0'))
    )

    # Calcular en una sola iteración
    inmuebles_list = []
    totales = {
        'renta_bruta': Decimal('0'),
        'renta_neta': Decimal('0'),
        'gastos': Decimal('0'),
        'iva': Decimal('0'),
        'irpf': Decimal('0'),
    }

    for inmueble in inmuebles:
        totales['renta_bruta'] += inmueble.renta_anual_bruta
        totales['renta_neta'] += inmueble.renta_anual_neta
        totales['gastos'] += inmueble.gastos_sum
        totales['iva'] += inmueble.iva_total
        totales['irpf'] += inmueble.irpf_total

        inmuebles_list.append({
            'id': inmueble.id,
            'nombre': inmueble.nombre,
            'tipo': inmueble.tipo,
            'renta_mensual': str(inmueble.renta_mensual),
            'renta_anual_bruta': str(inmueble.renta_anual_bruta),
            'renta_anual_neta': str(inmueble.renta_anual_neta),
            'iva': str(inmueble.iva_total),
            'irpf': str(inmueble.irpf_total),
            'gastos': str(inmueble.gastos_sum),
        })

    data = {
        'inmuebles': inmuebles_list,
        'resumen': {k: str(v) for k, v in totales.items()}
    }

    return JsonResponse(data)


@login_required(login_url="login")
def reportes(request):
    """
    Reportes con análisis temporal
    PostgreSQL: Aprovecha agregaciones por fecha
    """
    inmuebles, _ = get_user_inmuebles(request.user)
    
    # Anotar con totales
    inmuebles = inmuebles.annotate(
        gastos_sum=Coalesce(Sum('gastos__cantidad'), Decimal('0')),
        num_gastos=Count('gastos')
    ).only('id', 'nombre', 'renta_mensual', 'tipo_iva', 'tipo_irpf', 'tipo')

    # Calcular totales en una iteración
    totales = {
        'renta': Decimal('0'),
        'impuestos': Decimal('0'),
        'gastos': Decimal('0'),
    }

    for inmueble in inmuebles:
        totales['renta'] += inmueble.renta_anual_bruta
        totales['impuestos'] += inmueble.iva_total + inmueble.irpf_total
        totales['gastos'] += inmueble.gastos_sum

    context = {
        'inmuebles': inmuebles,
        'renta_total': totales['renta'],
        'impuestos_total': totales['impuestos'],
        'gastos_total': totales['gastos'],
        'neto_total': totales['renta'] - totales['impuestos'] - totales['gastos'],
    }

    return render(request, 'reportes.html', context)