from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.db.models import Q, Avg, Count
from django.views.decorators.csrf import csrf_protect
from .models import Alumno, Persona, Cursada, Carrera, PlanEstudio, Evaluacion

@csrf_protect
def buscador_view(request):
    if request.method == 'POST':
        query = request.POST.get('q', '').strip()
        carrera_id = request.POST.get('carrera', '').strip()
        situacion_filtro = request.POST.get('situacion', '').strip()
        asistencia_filtro = request.POST.get('asistencia', '').strip()
        orden_filtro = request.POST.get('orden', 'apellido').strip()
    else:
        query = ''
        carrera_id = ''
        situacion_filtro = ''
        asistencia_filtro = ''
        orden_filtro = 'apellido'

    if len(query) > 100:
        query = query[:100]

    alumnos = Alumno.objects.select_related('persona').prefetch_related(
        'cursadas__comision__plan_estudio__carrera',
        'cursadas__comision__plan_estudio__materia'
    ).all()

    # Búsqueda flexible por DNI con o sin puntos (ej: 46.647.745 o 46647745), Nombre, Apellido o Legajo
    if query:
        query_clean = query.replace('.', '').replace(' ', '').replace('-', '').replace(',', '')
        alumnos = alumnos.filter(
            Q(persona__dni__icontains=query) |
            Q(persona__dni__icontains=query_clean) |
            Q(persona__nombre__icontains=query) |
            Q(persona__apellido__icontains=query) |
            Q(legajo__icontains=query) |
            Q(legajo__icontains=query_clean)
        )

    # Filtro por Carrera
    if carrera_id:
        alumnos = alumnos.filter(cursadas__comision__plan_estudio__carrera__codigo_carrera=carrera_id).distinct()

    # Filtro por Situación Académica en alguna cursada
    if situacion_filtro in ['Promocionado', 'Final', 'Regular', 'Libre']:
        alumnos = alumnos.filter(cursadas__situacion_final=situacion_filtro).distinct()

    carreras = Carrera.objects.all().order_by('nombre_carrera')

    alumnos_list = []
    for al in alumnos:
        cursadas = al.cursadas.all()
        carreras_nombres = list(set([c.comision.plan_estudio.carrera.nombre_carrera for c in cursadas if c.comision and c.comision.plan_estudio]))
        
        asistencia_avg = cursadas.aggregate(Avg('porcentaje_asistencia'))['porcentaje_asistencia__avg'] or 0.0
        asistencia_avg = round(asistencia_avg, 1)

        if asistencia_filtro == 'alta' and asistencia_avg < 80.0:
            continue
        elif asistencia_filtro == 'media' and (asistencia_avg < 60.0 or asistencia_avg >= 80.0):
            continue
        elif asistencia_filtro == 'baja' and asistencia_avg >= 60.0:
            continue
        
        promocionadas = cursadas.filter(situacion_final='Promocionado').count()
        regulares = cursadas.filter(situacion_final='Regular').count()
        finales = cursadas.filter(situacion_final='Final').count()
        libres = cursadas.filter(situacion_final='Libre').count()

        alumnos_list.append({
            'alumno': al,
            'carreras': ", ".join(carreras_nombres) if carreras_nombres else "Sin Inscripción Registrada",
            'total_cursadas': cursadas.count(),
            'promocionadas': promocionadas,
            'regulares': regulares,
            'finales': finales,
            'libres': libres,
            'asistencia_avg': asistencia_avg,
        })

    if orden_filtro == 'asistencia_desc':
        alumnos_list.sort(key=lambda x: x['asistencia_avg'], reverse=True)
    elif orden_filtro == 'asistencia_asc':
        alumnos_list.sort(key=lambda x: x['asistencia_avg'], reverse=False)
    elif orden_filtro == 'promocionadas_desc':
        alumnos_list.sort(key=lambda x: x['promocionadas'], reverse=True)
    elif orden_filtro == 'nombre':
        alumnos_list.sort(key=lambda x: x['alumno'].persona.nombre)
    else:
        alumnos_list.sort(key=lambda x: x['alumno'].persona.apellido)

    context = {
        'query': query,
        'carrera_id': carrera_id,
        'situacion_filtro': situacion_filtro,
        'asistencia_filtro': asistencia_filtro,
        'orden_filtro': orden_filtro,
        'alumnos_list': alumnos_list[:100],
        'carreras': carreras,
        'total_resultados': len(alumnos_list),
        'total_alumnos_sistema': Alumno.objects.count()
    }
    return render(request, 'gestion/buscador.html', context)


@csrf_protect
def alumno_detalle_json(request, dni):
    dni_clean = str(dni).replace('.', '').replace(' ', '').replace('-', '').strip()[:20]
    persona = get_object_or_404(Persona, dni=dni_clean)
    alumno = get_object_or_404(Alumno, persona=persona)
    
    cursadas_qs = Cursada.objects.filter(alumno=alumno).select_related(
        'comision__plan_estudio__carrera',
        'comision__plan_estudio__materia'
    ).prefetch_related('evaluaciones', 'comision__docentes_asignados__docente__persona')

    carreras_dict = {}
    total_asistencia = 0
    total_notas = 0
    cant_notas = 0

    cursadas_data = []
    for c in cursadas_qs:
        materia_name = c.comision.plan_estudio.materia.nombre_materia if c.comision and c.comision.plan_estudio else "Materia Indefinida"
        carrera_name = c.comision.plan_estudio.carrera.nombre_carrera if c.comision and c.comision.plan_estudio else "Sin Carrera"
        anio_carrera = c.comision.plan_estudio.anio_carrera if c.comision and c.comision.plan_estudio else 1

        if carrera_name not in carreras_dict:
            carreras_dict[carrera_name] = 0
        carreras_dict[carrera_name] += 1

        docentes_list = [f"{d.docente.persona.apellido}, {d.docente.persona.nombre}" for d in c.comision.docentes_asignados.all()]
        docentes_str = ", ".join(docentes_list) if docentes_list else "Sin Asignar"

        evals_data = []
        nota_final_val = None
        for ev in c.evaluaciones.all():
            evals_data.append({
                'instancia': ev.instancia,
                'nota': float(ev.nota) if ev.nota is not None else None,
                'fecha': ev.fecha.strftime('%d/%m/%Y') if ev.fecha else ''
            })
            if ev.nota is not None:
                total_notas += float(ev.nota)
                cant_notas += 1
                if ev.instancia == 'Nota Final':
                    nota_final_val = float(ev.nota)

        asist = float(c.porcentaje_asistencia)
        total_asistencia += asist

        cursadas_data.append({
            'id_cursada': c.id_cursada,
            'carrera': carrera_name,
            'materia': materia_name,
            'anio_carrera': anio_carrera,
            'comision': c.comision.codigo_comision if c.comision else '-',
            'docentes': docentes_str,
            'asistencia': round(asist, 1),
            'situacion': c.situacion_final,
            'nota_final': nota_final_val,
            'evaluaciones': evals_data
        })

    cant_cursadas = len(cursadas_data)
    asistencia_promedio = round(total_asistencia / cant_cursadas, 1) if cant_cursadas > 0 else 0.0
    promedio_notas = round(total_notas / cant_notas, 2) if cant_notas > 0 else "N/A"

    data = {
        'personal': {
            'dni': persona.dni,
            'nombre': persona.nombre,
            'apellido': persona.apellido,
            'nombre_completo': f"{persona.apellido}, {persona.nombre}",
            'legajo': alumno.legajo or f"LEG-{persona.dni}",
            'mail': persona.mail or 'Sin registrar',
            'domicilio': persona.domicilio or 'Sin registrar',
            'telefono': persona.telefono or 'Sin registrar'
        },
        'resumen_academico': {
            'carreras': list(carreras_dict.keys()),
            'total_materias_cursadas': cant_cursadas,
            'asistencia_promedio': asistencia_promedio,
            'promedio_notas': promedio_notas,
            'aprobadas_promocionadas': sum(1 for c in cursadas_data if c['situacion'] == 'Promocionado'),
            'a_final': sum(1 for c in cursadas_data if c['situacion'] == 'Final'),
            'regulares': sum(1 for c in cursadas_data if c['situacion'] == 'Regular'),
            'libres': sum(1 for c in cursadas_data if c['situacion'] == 'Libre'),
        },
        'cursadas': cursadas_data
    }
    return JsonResponse(data)


@csrf_protect
def imprimir_estado_academico(request, dni):
    dni_clean = str(dni).replace('.', '').replace(' ', '').replace('-', '').strip()[:20]
    persona = get_object_or_404(Persona, dni=dni_clean)
    alumno = get_object_or_404(Alumno, persona=persona)
    cursadas = Cursada.objects.filter(alumno=alumno).select_related(
        'comision__plan_estudio__carrera',
        'comision__plan_estudio__materia'
    ).prefetch_related('evaluaciones')

    context = {
        'persona': persona,
        'alumno': alumno,
        'cursadas': cursadas,
    }
    return render(request, 'gestion/imprimir_analitico.html', context)
