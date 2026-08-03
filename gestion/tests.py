from django.test import TestCase, Client
from django.urls import reverse
from gestion.models import Persona, Alumno, Carrera, Materia, PlanEstudio, Comision, Cursada

class BuscadorAlumnosTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.persona = Persona.objects.create(
            dni="40375138",
            nombre="Emiliano Gabriel",
            apellido="Acosta",
            mail="emiliano.acosta@alumnos.isft188.edu.ar"
        )
        self.alumno = Alumno.objects.create(
            persona=self.persona,
            legajo="LEG-40375138"
        )
        self.carrera = Carrera.objects.create(
            codigo_carrera="LOGISTICA",
            nombre_carrera="Técnico Superior en Logística"
        )
        self.materia = Materia.objects.create(
            codigo_materia="LOG_101",
            nombre_materia="Sistemas de Información en Logística"
        )
        self.plan = PlanEstudio.objects.create(
            carrera=self.carrera,
            materia=self.materia,
            anio_carrera=3
        )
        self.comision = Comision.objects.create(
            codigo_comision="COM_LOG_2025",
            plan_estudio=self.plan,
            anio_lectivo=2025
        )
        self.cursada = Cursada.objects.create(
            comision=self.comision,
            alumno=self.alumno,
            porcentaje_asistencia=95.0,
            situacion_final="Promocionado"
        )

    def test_buscador_view_renders_correctly(self):
        response = self.client.get(reverse('gestion:buscador'))
        self.assertEqual(response.status_code, 200)

    def test_busqueda_post_por_dni(self):
        response = self.client.post(reverse('gestion:buscador'), {'q': '40375138'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Acosta, Emiliano Gabriel")

    def test_busqueda_post_por_dni_con_puntos(self):
        response = self.client.post(reverse('gestion:buscador'), {'q': '40.375.138'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Acosta, Emiliano Gabriel")

    def test_busqueda_post_por_nombre(self):
        response = self.client.post(reverse('gestion:buscador'), {'q': 'Emiliano'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "40375138")

    def test_busqueda_post_por_apellido(self):
        response = self.client.post(reverse('gestion:buscador'), {'q': 'Acosta'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "40375138")

    def test_api_alumno_detalle_json(self):
        response = self.client.get(reverse('gestion:alumno_detalle_json', kwargs={'dni': '40.375.138'}))
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertEqual(json_data['personal']['dni'], '40375138')
        self.assertEqual(json_data['personal']['nombre'], 'Emiliano Gabriel')
        self.assertEqual(json_data['personal']['apellido'], 'Acosta')
        self.assertEqual(len(json_data['cursadas']), 1)
        self.assertEqual(json_data['cursadas'][0]['situacion'], 'Promocionado')
