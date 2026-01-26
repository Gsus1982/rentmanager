import json
from datetime import date
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, F, DecimalField, Q
from django.db.models.functions import Coalesce
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.views.generic import CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator

from .models import Socio, Inmueble, Gasto
from .forms import InmuebleForm, GastoForm


@require_http_methods(["GET", "POST"])
@csrf_protect
def login_view(request):
    """Vista de login segura - verifica credenciales directamente"""
    if request.user.is_authenticated:
        return redirect('dashboard')

    error = None

    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        password = request.POST.get("password") or ""

        # Buscar usuario y verificar contraseña directamente
        try:
            user = User.objects.get(username=username)
            if user.check_password(password) and user.is_active:
                login(request, user)
                next_url = request.GET.get("next") or request.POST.get("next")
                # Validar que next_url es seguro
                if next_url and not next_url.startswith('/'):
                    next_url = None
                return redirect(next_url or 'dashboard')
            else:
                error = "Credenciales incorrectas"
        except User.DoesNotExist:
            error = "Credenciales incorrectas"

    return render(request, "login.html", {"error": error})


def get_user_inmuebles(user):
    """Helper para obtener inmuebles según permisos del usuario"""
    try:
        socio = Socio.objects.get(usuario=user)
        inmuebles = socio.inmuebles.all()
        return inmuebles, socio
    except Socio.DoesNotExist:
        if user.is_staff:
            inmuebles = Inmueble.objects.all()
            return inmuebles, None
        else:
            return Inmueble.objects.none(), None


def check_inmueble_permission(user, inmueble):
    """Verifica si el usuario tiene permiso para acceder al inmueble"""
    if user.is_staff:
        return True
    
    try:
        socio = Socio.objects.get(usuario=user)
        return inmueble in socio.inmuebles.all()
    except Socio.DoesNotExist:
        return False


@login_required(login_url="login")
def dashboard(request):
    """Dashboard principal con resumen de datos optimizado"""
    
    # Obtener inmuebles con relaciones precargadas
    inmuebles, socio = get_user_inmuebles(request.user)
    inmuebles = inmuebles.filter(activo=True).select_related().prefetch_related('gastos')

    # Cálculos usando agregación SQL (más eficiente)
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
        )
    )

    renta_bruta_total = agregados['renta_bruta_total']
    gastos_totales = agregados['gastos_totales']

    # Calcular valores que requieren lógica personalizada
    renta_neta_total = Decimal('0')
    iva_total = Decimal('0')
    irpf_total = Decimal('0')
    
    inmuebles_data = []
    for inmueble in inmuebles:
        renta_neta_total += inmueble.renta_anual_neta
        iva_total += inmueble.iva_total
        irpf_total += inmueble.irpf_total
        
        inmuebles_data.append({
            'nombre': inmueble.nombre,
            'renta_bruta': str(inmueble.renta_anual_bruta),
            'renta_neta': str(inmueble.renta_anual_neta),
            'iva': str(inmueble.iva_total),
            'irpf': str(inmueble.irpf_total),
            'gastos': str(inmueble.gastos_totales),
        })

    context = {
        'inmuebles': inmuebles,
        'renta_bruta_total': renta_bruta_total,
        'renta_neta_total': renta_neta_total,
        'gastos_totales': gastos_totales,
        'iva_total': iva_total,
        'irpf_total': irpf_total,
        'inmuebles_json': json.dumps(inmuebles_data),
        'socio': socio,
        'num_inmuebles': inmuebles.count(),
    }

    return render(request, 'dashboard.html', context)


@login_required(login_url="login")
def inmuebles_list(request):
    """Listar todos los inmuebles con paginación"""
    inmuebles, _ = get_user_inmuebles(request.user)

    # Filtrado por tipo
    tipo_filter = request.GET.get('tipo')
    if tipo_filter and tipo_filter in dict(Inmueble.TIPOS):
        inmuebles = inmuebles.filter(tipo=tipo_filter)

    # Paginación
    paginator = Paginator(inmuebles.order_by('-id'), 20)  # 20 por página
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
    })


@login_required(login_url="login")
def inmueble_detail(request, pk):
    """Detalle de un inmueble con resumen económico"""
    inmueble = get_object_or_404(Inmueble, pk=pk)

    # Verificar permiso
    if not check_inmueble_permission(request.user, inmueble):
        messages.error(request, 'No tienes permiso para ver este inmueble')
        return redirect('inmuebles_list')

    # Optimizar consultas
    gastos = inmueble.gastos.all()
    gastos_agregado = gastos.aggregate(
        total=Coalesce(Sum('cantidad'), Decimal('0'), output_field=DecimalField())
    )
    gastos_total = gastos_agregado['total']

    transacciones = inmueble.transacciones.all()[:10]  # Últimas 10

    # Gastos por categoría usando agregación
    gastos_por_categoria_query = gastos.values('categoria').annotate(
        total=Sum('cantidad')
    ).order_by('categoria')
    
    gastos_por_categoria = {}
    for item in gastos_por_categoria_query:
        categoria_display = dict(Gasto._meta.get_field('categoria').choices).get(
            item['categoria'], 
            item['categoria']
        )
        gastos_por_categoria[categoria_display] = item['total']

    context = {
        'inmueble': inmueble,
        'gastos': gastos,
        'gastos_total': gastos_total,
        'gastos_por_categoria': gastos_por_categoria,
        'gastos_json': json.dumps({k: str(v) for k, v in gastos_por_categoria.items()}),
        'transacciones': transacciones,
        'renta_neta': inmueble.renta_anual_neta,
        'renta_neta_con_gastos': inmueble.renta_neta_con_gastos,
    }

    return render(request, 'inmueble_detail.html', context)


class InmuebleCreateView(LoginRequiredMixin, CreateView):
    """Crear nuevo inmueble"""
    model = Inmueble
    form_class = InmuebleForm
    template_name = 'inmueble_form.html'
    success_url = reverse_lazy('inmuebles_list')
    login_url = 'login'

    def form_valid(self, form):
        # Guardar primero para obtener el ID
        self.object = form.save()
        
        # Asignar socio actual si existe
        try:
            socio = Socio.objects.get(usuario=self.request.user)
            if socio not in self.object.socios.all():
                self.object.socios.add(socio)
        except Socio.DoesNotExist:
            # Si no es socio, verificar que sea staff
            if not self.request.user.is_staff:
                messages.error(self.request, 'No tienes permiso para crear inmuebles')
                return redirect('inmuebles_list')
        
        messages.success(self.request, f'Inmueble "{self.object.nombre}" creado exitosamente')
        return redirect(self.get_success_url())


class InmuebleUpdateView(LoginRequiredMixin, UpdateView):
    """Actualizar inmueble"""
    model = Inmueble
    form_class = InmuebleForm
    template_name = 'inmueble_form.html'
    login_url = 'login'

    def dispatch(self, request, *args, **kwargs):
        """Verificar permisos antes de procesar"""
        inmueble = self.get_object()
        if not check_inmueble_permission(request.user, inmueble):
            messages.error(request, 'No tienes permiso para editar este inmueble')
            return redirect('inmuebles_list')
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        messages.success(self.request, f'Inmueble "{self.object.nombre}" actualizado')
        return reverse_lazy('inmueble_detail', kwargs={'pk': self.object.pk})


class InmuebleDeleteView(LoginRequiredMixin, DeleteView):
    """Eliminar inmueble (soft delete)"""
    model = Inmueble
    template_name = 'inmueble_confirm_delete.html'
    success_url = reverse_lazy('inmuebles_list')
    login_url = 'login'

    def dispatch(self, request, *args, **kwargs):
        """Verificar permisos antes de procesar"""
        inmueble = self.get_object()
        if not check_inmueble_permission(request.user, inmueble):
            messages.error(request, 'No tienes permiso para eliminar este inmueble')
            return redirect('inmuebles_list')
        return super().dispatch(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        inmueble = self.get_object()
        nombre = inmueble.nombre
        
        # Soft delete: marcar como inactivo
        inmueble.activo = False
        inmueble.save()
        
        messages.success(request, f'Inmueble "{nombre}" desactivado')
        return redirect(self.success_url)


class GastoCreateView(LoginRequiredMixin, CreateView):
    """Crear gasto para inmueble"""
    model = Gasto
    form_class = GastoForm
    template_name = 'gasto_form.html'
    login_url = 'login'

    def dispatch(self, request, *args, **kwargs):
        """Verificar permisos del inmueble"""
        inmueble = get_object_or_404(Inmueble, pk=self.kwargs['inmueble_pk'])
        if not check_inmueble_permission(request.user, inmueble):
            messages.error(request, 'No tienes permiso para agregar gastos a este inmueble')
            return redirect('inmuebles_list')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['inmueble'] = get_object_or_404(Inmueble, pk=self.kwargs['inmueble_pk'])
        return context

    def form_valid(self, form):
        form.instance.inmueble_id = self.kwargs['inmueble_pk']
        messages.success(self.request, 'Gasto registrado exitosamente')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('inmueble_detail', kwargs={'pk': self.kwargs['inmueble_pk']})


class GastoUpdateView(LoginRequiredMixin, UpdateView):
    """Actualizar gasto"""
    model = Gasto
    form_class = GastoForm
    template_name = 'gasto_form.html'
    login_url = 'login'

    def dispatch(self, request, *args, **kwargs):
        """Verificar permisos del inmueble asociado"""
        gasto = self.get_object()
        if not check_inmueble_permission(request.user, gasto.inmueble):
            messages.error(request, 'No tienes permiso para editar este gasto')
            return redirect('inmuebles_list')
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        messages.success(self.request, 'Gasto actualizado')
        return reverse_lazy('inmueble_detail', kwargs={'pk': self.object.inmueble.pk})


class GastoDeleteView(LoginRequiredMixin, DeleteView):
    """Eliminar gasto"""
    model = Gasto
    template_name = 'gasto_confirm_delete.html'
    login_url = 'login'

    def dispatch(self, request, *args, **kwargs):
        """Verificar permisos del inmueble asociado"""
        gasto = self.get_object()
        if not check_inmueble_permission(request.user, gasto.inmueble):
            messages.error(request, 'No tienes permiso para eliminar este gasto')
            return redirect('inmuebles_list')
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        messages.success(self.request, 'Gasto eliminado')
        return reverse_lazy('inmueble_detail', kwargs={'pk': self.object.inmueble.pk})


@login_required(login_url="login")
def api_dashboard_data(request):
    """API endpoint para datos del dashboard (JSON)"""
    inmuebles, _ = get_user_inmuebles(request.user)
    inmuebles = inmuebles.filter(activo=True).select_related().prefetch_related('gastos')

    # Calcular resumen
    renta_bruta_total = Decimal('0')
    renta_neta_total = Decimal('0')
    gastos_total = Decimal('0')
    iva_total = Decimal('0')
    irpf_total = Decimal('0')

    inmuebles_list = []
    for inmueble in inmuebles:
        renta_bruta_total += inmueble.renta_anual_bruta
        renta_neta_total += inmueble.renta_anual_neta
        gastos_total += inmueble.gastos_totales
        iva_total += inmueble.iva_total
        irpf_total += inmueble.irpf_total

        inmuebles_list.append({
            'id': inmueble.id,
            'nombre': inmueble.nombre,
            'tipo': inmueble.tipo,
            'renta_mensual': str(inmueble.renta_mensual),
            'renta_anual_bruta': str(inmueble.renta_anual_bruta),
            'renta_anual_neta': str(inmueble.renta_anual_neta),
            'iva': str(inmueble.iva_total),
            'irpf': str(inmueble.irpf_total),
            'gastos': str(inmueble.gastos_totales),
        })

    data = {
        'inmuebles': inmuebles_list,
        'resumen': {
            'renta_bruta_total': str(renta_bruta_total),
            'renta_neta_total': str(renta_neta_total),
            'gastos_total': str(gastos_total),
            'iva_total': str(iva_total),
            'irpf_total': str(irpf_total),
        }
    }

    return JsonResponse(data)


@login_required(login_url="login")
def reportes(request):
    """Vista de reportes optimizada"""
    inmuebles, _ = get_user_inmuebles(request.user)
    inmuebles = inmuebles.select_related().prefetch_related('gastos')

    # Calcular totales
    renta_total = Decimal('0')
    impuestos_total = Decimal('0')
    gastos_total = Decimal('0')

    for inmueble in inmuebles:
        renta_total += inmueble.renta_anual_bruta
        impuestos_total += inmueble.iva_total + inmueble.irpf_total
        gastos_total += inmueble.gastos_totales

    context = {
        'inmuebles': inmuebles,
        'renta_total': renta_total,
        'impuestos_total': impuestos_total,
        'gastos_total': gastos_total,
        'neto_total': renta_total - impuestos_total - gastos_total,
    }

    return render(request, 'reportes.html', context)
