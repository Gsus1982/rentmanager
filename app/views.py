import json
from datetime import date
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, F, DecimalField
from django.db.models.functions import Coalesce
from django.views.decorators.http import require_http_methods
from django.views.generic import CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.http import JsonResponse

from .models import Socio, Inmueble, Gasto
from .forms import InmuebleForm, GastoForm


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    error = None

    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        password = request.POST.get("password") or ""

        
        user = authenticate(username=username, password=password)

        if user is not None and user.is_active:
            login(request, user)
            next_url = request.GET.get("next") or request.POST.get("next")
            return redirect(next_url or 'dashboard')
        else:
            error = "Usuario o contraseña incorrectos"

    return render(request, "login.html", {"error": error})


@login_required(login_url="login")
def dashboard(request):
    """Dashboard principal con resumen de datos"""

    # Obtener datos del usuario (si es socio)
    try:
        socio = Socio.objects.get(usuario=request.user)
        inmuebles = socio.inmuebles.filter(activo=True)
    except Socio.DoesNotExist:
        # Si es admin, mostrar todos los inmuebles
        inmuebles = Inmueble.objects.filter(activo=True)
        socio = None

    # Cálculos globales
    renta_bruta_total = inmuebles.aggregate(
        total=Coalesce(Sum(F('renta_mensual') * 12), Decimal('0'), output_field=DecimalField())
    )['total']

    renta_neta_total = sum([i.renta_anual_neta for i in inmuebles])

    gastos_totales = Gasto.objects.filter(inmueble__in=inmuebles).aggregate(
        total=Coalesce(Sum('cantidad'), Decimal('0'), output_field=DecimalField())
    )['total']

    iva_total = sum([i.iva_total for i in inmuebles])
    irpf_total = sum([i.irpf_total for i in inmuebles])

    # Datos para gráficos
    inmuebles_data = []
    for inmueble in inmuebles:
        inmuebles_data.append({
            'nombre': inmueble.nombre,
            'renta_bruta': float(inmueble.renta_anual_bruta),
            'renta_neta': float(inmueble.renta_anual_neta),
            'iva': float(inmueble.iva_total),
            'irpf': float(inmueble.irpf_total),
            'gastos': float(inmueble.gastos_totales),
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
    """Listar todos los inmuebles"""
    try:
        socio = Socio.objects.get(usuario=request.user)
        inmuebles = socio.inmuebles.all()
    except Socio.DoesNotExist:
        inmuebles = Inmueble.objects.all()

    # Filtrado por tipo
    tipo_filter = request.GET.get('tipo')
    if tipo_filter:
        inmuebles = inmuebles.filter(tipo=tipo_filter)

    return render(request, 'inmuebles_list.html', {
        'inmuebles': inmuebles,
        'tipos': Inmueble.TIPOS
    })


@login_required(login_url="login")
def inmueble_detail(request, pk):
    """Detalle de un inmueble con resumen económico"""
    inmueble = get_object_or_404(Inmueble, pk=pk)

    # Verificar permiso
    try:
        socio = Socio.objects.get(usuario=request.user)
        if inmueble not in socio.inmuebles.all() and not request.user.is_staff:
            messages.error(request, 'No tienes permiso para ver este inmueble')
            return redirect('inmuebles_list')
    except Socio.DoesNotExist:
        if not request.user.is_staff:
            messages.error(request, 'No tienes permiso para ver este inmueble')
            return redirect('inmuebles_list')

    gastos = inmueble.gastos.all()
    gastos_total = gastos.aggregate(Sum('cantidad'))['cantidad__sum'] or Decimal('0')

    transacciones = inmueble.transacciones.all()[:10]  # Últimas 10

    # Gastos por categoría
    gastos_por_categoria = {}
    for gasto in gastos:
        cat = gasto.get_categoria_display()
        if cat not in gastos_por_categoria:
            gastos_por_categoria[cat] = Decimal('0')
        gastos_por_categoria[cat] += gasto.cantidad

    context = {
        'inmueble': inmueble,
        'gastos': gastos,
        'gastos_total': gastos_total,
        'gastos_por_categoria': gastos_por_categoria,
        'gastos_json': json.dumps({k: float(v) for k, v in gastos_por_categoria.items()}),
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
        response = super().form_valid(form)
        # Asignar socio actual si existe
        try:
            socio = Socio.objects.get(usuario=self.request.user)
            if socio not in form.instance.socios.all():
                form.instance.socios.add(socio)
        except Socio.DoesNotExist:
            pass
        messages.success(self.request, f'Inmueble "{form.instance.nombre}" creado exitosamente')
        return response


class InmuebleUpdateView(LoginRequiredMixin, UpdateView):
    """Actualizar inmueble"""
    model = Inmueble
    form_class = InmuebleForm
    template_name = 'inmueble_form.html'
    login_url = 'login'

    def get_success_url(self):
        messages.success(self.request, f'Inmueble "{self.object.nombre}" actualizado')
        return reverse_lazy('inmueble_detail', kwargs={'pk': self.object.pk})


class InmuebleDeleteView(LoginRequiredMixin, DeleteView):
    """Eliminar inmueble"""
    model = Inmueble
    template_name = 'inmueble_confirm_delete.html'
    success_url = reverse_lazy('inmuebles_list')
    login_url = 'login'

    def delete(self, request, *args, **kwargs):
        inmueble = self.get_object()
        messages.success(request, f'Inmueble "{inmueble.nombre}" eliminado')
        return super().delete(request, *args, **kwargs)


class GastoCreateView(LoginRequiredMixin, CreateView):
    """Crear gasto para inmueble"""
    model = Gasto
    form_class = GastoForm
    template_name = 'gasto_form.html'
    login_url = 'login'

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

    def get_success_url(self):
        messages.success(self.request, 'Gasto actualizado')
        return reverse_lazy('inmueble_detail', kwargs={'pk': self.object.inmueble.pk})


class GastoDeleteView(LoginRequiredMixin, DeleteView):
    """Eliminar gasto"""
    model = Gasto
    template_name = 'gasto_confirm_delete.html'
    login_url = 'login'

    def get_success_url(self):
        messages.success(self.request, 'Gasto eliminado')
        return reverse_lazy('inmueble_detail', kwargs={'pk': self.object.inmueble.pk})


@login_required(login_url="login")
def api_dashboard_data(request):
    """API endpoint para datos del dashboard (JSON)"""
    try:
        socio = Socio.objects.get(usuario=request.user)
        inmuebles = socio.inmuebles.filter(activo=True)
    except Socio.DoesNotExist:
        inmuebles = Inmueble.objects.filter(activo=True)

    data = {
        'inmuebles': [],
        'resumen': {
            'renta_bruta_total': float(sum([i.renta_anual_bruta for i in inmuebles])),
            'renta_neta_total': float(sum([i.renta_anual_neta for i in inmuebles])),
            'gastos_total': float(sum([i.gastos_totales for i in inmuebles])),
            'iva_total': float(sum([i.iva_total for i in inmuebles])),
            'irpf_total': float(sum([i.irpf_total for i in inmuebles])),
        }
    }

    for inmueble in inmuebles:
        data['inmuebles'].append({
            'id': inmueble.id,
            'nombre': inmueble.nombre,
            'tipo': inmueble.tipo,
            'renta_mensual': float(inmueble.renta_mensual),
            'renta_anual_bruta': float(inmueble.renta_anual_bruta),
            'renta_anual_neta': float(inmueble.renta_anual_neta),
            'iva': float(inmueble.iva_total),
            'irpf': float(inmueble.irpf_total),
            'gastos': float(inmueble.gastos_totales),
        })

    return JsonResponse(data)


@login_required(login_url="login")
def reportes(request):
    """Vista de reportes"""
    try:
        socio = Socio.objects.get(usuario=request.user)
        inmuebles = socio.inmuebles.all()
    except Socio.DoesNotExist:
        inmuebles = Inmueble.objects.all()

    # Resumen anual
    renta_total = sum([i.renta_anual_bruta for i in inmuebles])
    impuestos_total = sum([i.iva_total + i.irpf_total for i in inmuebles])
    gastos_total = sum([i.gastos_totales for i in inmuebles])

    context = {
        'inmuebles': inmuebles,
        'renta_total': renta_total,
        'impuestos_total': impuestos_total,
        'gastos_total': gastos_total,
        'neto_total': renta_total - impuestos_total - gastos_total,
    }

    return render(request, 'reportes.html', context)
