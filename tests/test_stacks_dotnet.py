"""Los stacks .NET en capas: `dotnet-layered` (API REST) y `dotnet-mvc` (portal web).

Lo que se midio antes de este cambio, con el catalogo de diez stacks:

1. La plantilla de la API en capas y la del portal MVC se detectaban como
   `dotnet-hexagonal` (55%): era el unico stack .NET, y suma puntos en cualquier
   repo con un `.csproj`. Recibian la norma hexagonal, que no es la suya.
2. Con tres stacks del mismo lenguaje el puntaje no alcanza para decidir: el
   general suma en todos, y un empate lo resolvia el orden del disco.

Ahora el stack especifico declara su senal propia (`requires_any`), lo que lo
descarta (`anti_indicators`) y a que stack general desplaza (`supersedes`). Una
solucion hexagonal con vistas Razor sigue siendo hexagonal.

Las pruebas arman cada repo en una carpeta temporal: no dependen de las
plantillas de CALPIL, salvo las de la ultima clase, que se saltan si no estan.
"""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

import arquitectura  # noqa: E402
import stack  # noqa: E402

LAYERED, MVC, HEXAGONAL = "dotnet-layered", "dotnet-mvc", "dotnet-hexagonal"
PLANTILLAS = Path("/Users/alan/Documents/Git/CALPIL")
NET10 = "<Project><PropertyGroup><TargetFramework>net10.0</TargetFramework></PropertyGroup></Project>"


def escribir(ruta: Path, texto: str = "") -> Path:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(texto, encoding="utf-8")
    return ruta


def api_en_capas(repo: Path) -> Path:
    """Una API conforme a la norma: un proyecto, una carpeta por feature, una clase por capa."""
    api = repo / "src" / "Acme.Pagos.Api"
    escribir(repo / "Acme.Pagos.slnx", "<Solution />")
    escribir(repo / "Directory.Build.props", NET10)
    escribir(api / "Acme.Pagos.Api.csproj",
             '<Project Sdk="Microsoft.NET.Sdk.Web"><ItemGroup>'
             '<PackageReference Include="Dapper" /><PackageReference Include="Microsoft.Data.SqlClient" />'
             '</ItemGroup></Project>')
    escribir(api / "Program.cs", "var builder = WebApplication.CreateBuilder(args);\nbuilder.Services.AddPagos();\n")
    escribir(api / "Pagos" / "PagosController.cs",
             "using Microsoft.AspNetCore.Mvc;\nnamespace Acme.Pagos.Api.Pagos;\n"
             "public sealed class PagosController(PagoService service) : ControllerBase { }\n")
    escribir(api / "Pagos" / "PagoService.cs",
             "namespace Acme.Pagos.Api.Pagos;\n"
             "public sealed class PagoService(IPagoRepository repository, TimeProvider clock)\n"
             '{\n    public string Falta(Guid id) => $"el pago {id} no existe";\n}\n')
    escribir(api / "Pagos" / "IPagoRepository.cs",
             "namespace Acme.Pagos.Api.Pagos;\npublic interface IPagoRepository { }\n")
    escribir(api / "Pagos" / "PagoRepository.cs",
             "using System.Data;\nusing Acme.Pagos.Api.Platform.Database;\nusing Dapper;\n"
             "namespace Acme.Pagos.Api.Pagos;\n"
             "/// <summary>Nunca se interpola un valor: $\"... {id}\" esta prohibido.</summary>\n"
             "public sealed class PagoRepository(SqlConnectionFactory connections) : IPagoRepository\n{\n"
             '    private const string Columns = "id AS Id, monto AS Monto";\n'
             '    public string Buscar() => $"SELECT {Columns} FROM dbo.pagos WHERE id = @Id";\n}\n')
    escribir(api / "Platform" / "Database" / "SqlConnectionFactory.cs",
             "using Microsoft.Data.SqlClient;\nnamespace Acme.Pagos.Api.Platform.Database;\n"
             "public sealed class SqlConnectionFactory { }\n")
    escribir(repo / "db" / "migrations" / "0001_create_pagos.sql", "CREATE TABLE dbo.pagos (id uniqueidentifier);\n")
    escribir(repo / "tests" / "Acme.Pagos.Api.Tests" / "PagoServiceTests.cs", "public class PagoServiceTests { }\n")
    return repo


def portal_mvc(repo: Path) -> Path:
    """Un portal conforme a la norma: controllers delgados, vistas que solo presentan, datos por I*Api."""
    web = repo / "src" / "Acme.Portal.Web"
    escribir(repo / "Acme.Portal.slnx", "<Solution />")
    escribir(repo / "Directory.Build.props", NET10)
    escribir(web / "Acme.Portal.Web.csproj",
             '<Project Sdk="Microsoft.NET.Sdk.Web"><ItemGroup>'
             '<PackageReference Include="Microsoft.AspNetCore.Authentication.OpenIdConnect" />'
             '</ItemGroup></Project>')
    escribir(web / "Program.cs", "var builder = WebApplication.CreateBuilder(args);\n")
    escribir(web / "Controllers" / "PagosController.cs",
             "using Microsoft.AspNetCore.Mvc;\nnamespace Acme.Portal.Web.Controllers;\n"
             "public sealed class PagosController(IPagosApi api) : Controller { }\n")
    escribir(web / "Services" / "IPagosApi.cs",
             "namespace Acme.Portal.Web.Services;\npublic interface IPagosApi { }\n")
    escribir(web / "Services" / "PagosApiClient.cs",
             "namespace Acme.Portal.Web.Services;\n"
             "public sealed class PagosApiClient(HttpClient http) : IPagosApi { }\n")
    escribir(web / "Models" / "PagoViewModel.cs", "namespace Acme.Portal.Web.Models;\npublic sealed record PagoViewModel(string Titulo);\n")
    escribir(web / "Views" / "_ViewImports.cshtml", "@using Acme.Portal.Web.Models\n")
    escribir(web / "Views" / "Pagos" / "Index.cshtml",
             '@model PagoViewModel\n<h1>@Model.Titulo</h1>\n<script src="~/js/site.js"></script>\n')
    escribir(repo / "tests" / "Acme.Portal.Web.Tests" / "PagosPagesTests.cs", "public class PagosPagesTests { }\n")
    return repo


def hexagonal_con_vistas(repo: Path) -> Path:
    """Solucion hexagonal cuya capa de presentacion sirve vistas Razor."""
    escribir(repo / "Acme.sln", "")
    for capa in ("Domain", "Application", "Infrastructure", "WebApi"):
        escribir(repo / "src" / capa / f"Acme.{capa}.csproj", '<Project Sdk="Microsoft.NET.Sdk" />')
    escribir(repo / "src" / "Domain" / "Pago.cs", "namespace Acme.Domain;\npublic sealed class Pago { }\n")
    escribir(repo / "src" / "WebApi" / "Program.cs", "var builder = WebApplication.CreateBuilder(args);\n")
    escribir(repo / "src" / "WebApi" / "Controllers" / "PagosController.cs", "public class PagosController { }\n")
    escribir(repo / "src" / "WebApi" / "Views" / "_ViewImports.cshtml", "@using Acme.WebApi\n")
    return repo


def verificador(stack_id: str):
    ruta = stack.STACKS_DIR / stack_id / "scripts" / "check-architecture.py"
    spec = importlib.util.spec_from_file_location("check_" + stack_id.replace("-", "_"), str(ruta))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def detectado(self, repo: Path) -> str:
        return stack.detectar_stack_directorio(repo)["stack"]


class DeteccionDeLaFamiliaTests(Base):
    def test_una_api_en_capas_es_dotnet_layered(self):
        res = stack.detectar_stack_directorio(api_en_capas(self.tmp / "api"))
        self.assertEqual(LAYERED, res["stack"])
        self.assertGreaterEqual(res["confidence"], 80)

    def test_un_portal_con_vistas_razor_es_dotnet_mvc(self):
        res = stack.detectar_stack_directorio(portal_mvc(self.tmp / "portal"))
        self.assertEqual(MVC, res["stack"])
        self.assertGreaterEqual(res["confidence"], 80)

    def test_el_general_no_queda_como_candidato_cuando_gana_el_especifico(self):
        res = stack.detectar_stack_directorio(api_en_capas(self.tmp / "api"))
        self.assertNotIn(HEXAGONAL, [c["stack"] for c in res["candidates"]])

    def test_una_solucion_hexagonal_con_vistas_sigue_siendo_hexagonal(self):
        self.assertEqual(HEXAGONAL, self.detectado(hexagonal_con_vistas(self.tmp / "hex")))

    def test_una_solucion_por_proyectos_con_api_sigue_siendo_hexagonal(self):
        repo = self.tmp / "hex"
        escribir(repo / "Acme.sln", "")
        for capa in ("Domain", "Application", "Infrastructure", "Api"):
            escribir(repo / "src" / f"Acme.{capa}" / f"Acme.{capa}.csproj", '<Project Sdk="Microsoft.NET.Sdk" />')
        escribir(repo / "src" / "Acme.Api" / "Program.cs", "var app = 1;\n")
        self.assertEqual(HEXAGONAL, self.detectado(repo))

    def test_un_repo_dotnet_sin_senal_propia_sigue_en_el_stack_general(self):
        repo = self.tmp / "worker"
        escribir(repo / "Acme.Worker.csproj", '<Project Sdk="Microsoft.NET.Sdk.Worker" />')
        escribir(repo / "Program.cs", "var host = 1;\n")
        self.assertEqual(HEXAGONAL, self.detectado(repo))

    def test_una_api_con_vistas_queda_en_el_stack_general(self):
        """La API en capas no sirve vistas y el portal no trae API: ninguna de las dos normas es la suya."""
        repo = api_en_capas(self.tmp / "mixto")
        escribir(repo / "src" / "Acme.Pagos.Api" / "Views" / "_ViewImports.cshtml", "")
        self.assertEqual(HEXAGONAL, self.detectado(repo))

    def test_un_portal_con_repositorios_queda_en_el_stack_general(self):
        """El portal no tiene acceso a datos: un MVC con repositorios no es el stack del portal."""
        repo = portal_mvc(self.tmp / "monolito")
        escribir(repo / "src" / "Acme.Portal.Web" / "Pagos" / "PagoRepository.cs", "public class PagoRepository { }\n")
        self.assertEqual(HEXAGONAL, self.detectado(repo))

    def test_api_y_portal_en_una_misma_solucion_quedan_en_el_stack_general(self):
        repo = api_en_capas(self.tmp / "solucion")
        portal_mvc(repo)
        self.assertEqual(HEXAGONAL, self.detectado(repo))

    def test_la_carpeta_de_un_proyecto_no_es_otro_repo(self):
        """Solucion con los proyectos en la raiz: cada carpeta, mirada sola, califica para otro stack .NET."""
        casos = {}
        hexagonal = self.tmp / "hexagonal"
        escribir(hexagonal / "Acme.sln", "")
        for capa in ("Domain", "Application", "Infrastructure"):
            escribir(hexagonal / f"Acme.{capa}" / f"Acme.{capa}.csproj", '<Project Sdk="Microsoft.NET.Sdk" />')
        escribir(hexagonal / "Acme.WebApi" / "Acme.WebApi.csproj", '<Project Sdk="Microsoft.NET.Sdk.Web" />')
        escribir(hexagonal / "Acme.WebApi" / "Program.cs", "var app = 1;\n")
        escribir(hexagonal / "Acme.WebApi" / "Views" / "_ViewImports.cshtml", "")
        casos[hexagonal] = HEXAGONAL
        self.assertEqual(MVC, self.detectado(hexagonal / "Acme.WebApi"), "sola, la carpeta parece un portal")

        en_capas = self.tmp / "en-capas"
        escribir(en_capas / "Acme.sln", "")
        escribir(en_capas / "Acme.Api" / "Acme.Api.csproj", '<Project Sdk="Microsoft.NET.Sdk.Web" />')
        escribir(en_capas / "Acme.Api" / "Program.cs", "var app = 1;\n")
        escribir(en_capas / "Acme.Api.Tests" / "Acme.Api.Tests.csproj", '<Project Sdk="Microsoft.NET.Sdk" />')
        casos[en_capas] = LAYERED
        self.assertEqual(HEXAGONAL, self.detectado(en_capas / "Acme.Api"), "sola, la carpeta cae en el general")

        for repo, esperado in casos.items():
            with self.subTest(repo=repo.name):
                self.assertEqual([(repo, esperado)],
                                 [(Path(d["path"]), d["stack"]) for d in stack.detectar_todos_los_destinos(repo)])

    def test_una_carpeta_de_otra_familia_sigue_siendo_otro_destino(self):
        repo = api_en_capas(self.tmp / "api")
        escribir(repo / "web" / "angular.json", "{}")
        escribir(repo / "web" / "package.json", json.dumps({"dependencies": {"@angular/core": "20.0.0"}}))
        escribir(repo / "web" / "src" / "app" / "app.routes.ts", "export const routes = [];\n")
        por_ruta = {Path(d["path"]).name: d["stack"] for d in stack.detectar_todos_los_destinos(repo)}
        self.assertEqual({"api": LAYERED, "web": "angular-product"}, por_ruta)

    def test_las_tres_plantillas_dotnet_son_marcas_de_repo(self):
        """Un servicio .NET dentro de una carpeta de microservicios se ve con cualquiera de los tres."""
        raiz = self.tmp / "micros"
        api_en_capas(raiz / "ms-pagos")
        portal_mvc(raiz / "portal")
        por_ruta = {Path(d["path"]).name: d["stack"] for d in stack.detectar_todos_los_destinos(raiz)}
        self.assertEqual({"ms-pagos": LAYERED, "portal": MVC}, por_ruta)


class SupersedesTests(Base):
    """`detection.supersedes` vale para cualquier familia de stacks, no solo .NET."""

    def setUp(self):
        super().setUp()
        self.stacks = self.tmp / "stacks"
        original = stack.STACKS_DIR
        stack.STACKS_DIR = self.stacks
        self.addCleanup(setattr, stack, "STACKS_DIR", original)
        self.repo = self.tmp / "repo"
        escribir(self.repo / "app.cfg")
        for carpeta in ("a", "b", "c", "d"):
            (self.repo / carpeta).mkdir()

    def manifest(self, stack_id: str, **deteccion) -> None:
        escribir(self.stacks / stack_id / "manifest.json",
                 json.dumps({"id": stack_id, "name": stack_id,
                             "detection": {"files_any": ["app.cfg"], **deteccion}}))

    def test_el_especifico_gana_aunque_puntue_menos(self):
        self.manifest("fam-general", strong_indicators=["a", "b", "c", "d"])
        self.manifest("fam-especifico", requires_any=["marca.txt"], supersedes=["fam-general"])
        escribir(self.repo / "marca.txt")
        res = stack.detectar_stack_directorio(self.repo)
        self.assertEqual("fam-especifico", res["stack"])
        self.assertEqual(["fam-especifico"], [c["stack"] for c in res["candidates"]])

    def test_sin_su_senal_propia_el_especifico_no_desplaza_a_nadie(self):
        self.manifest("fam-general", strong_indicators=["a", "b", "c", "d"])
        self.manifest("fam-especifico", requires_any=["marca.txt"], supersedes=["fam-general"])
        self.assertEqual("fam-general", stack.detectar_stack_directorio(self.repo)["stack"])

    def test_la_familia_son_los_stacks_unidos_por_supersedes(self):
        self.manifest("fam-general")
        self.manifest("fam-uno", supersedes=["fam-general"])
        self.manifest("fam-dos", supersedes=["fam-general"])
        self.manifest("otro")
        self.assertEqual({"fam-general", "fam-uno", "fam-dos"}, stack.familia_de("fam-dos"))
        self.assertEqual({"otro"}, stack.familia_de("otro"))

    def test_dos_stacks_que_se_desplazan_entre_si_no_dejan_el_repo_sin_stack(self):
        self.manifest("fam-uno", supersedes=["fam-dos"])
        self.manifest("fam-dos", supersedes=["fam-uno"])
        self.assertIn(stack.detectar_stack_directorio(self.repo)["stack"], ("fam-uno", "fam-dos"))

    def test_un_empate_lo_decide_el_id_y_no_el_orden_del_disco(self):
        for stack_id in ("fam-zeta", "fam-alfa", "fam-medio"):
            self.manifest(stack_id)
        self.assertEqual("fam-alfa", stack.detectar_stack_directorio(self.repo)["stack"])


class VerificadorLayeredTests(Base):
    def setUp(self):
        super().setUp()
        self.repo = api_en_capas(self.tmp / "api")
        self.api = self.repo / "src" / "Acme.Pagos.Api"
        self.check = verificador(LAYERED).check_dotnet_layered

    def errores(self) -> list[str]:
        return self.check(self.repo)[0]

    def assertInfraccion(self, texto: str):
        errores = self.errores()
        self.assertTrue(any(texto in e for e in errores), f"falta '{texto}' en {errores}")

    def test_la_api_conforme_no_tiene_infracciones_ni_avisos(self):
        self.assertEqual(([], []), self.check(self.repo))

    def test_un_controller_no_conoce_el_repositorio(self):
        escribir(self.api / "Pagos" / "PagosController.cs",
                 "public sealed class PagosController(IPagoRepository repository) { }\n")
        self.assertInfraccion("PagosController.cs: el controller solo conoce el service (referencia a IPagoRepository)")

    def test_un_controller_no_importa_la_capa_de_datos(self):
        escribir(self.api / "Pagos" / "PagosController.cs",
                 "using Dapper;\nusing Acme.Pagos.Api.Platform.Database;\npublic sealed class PagosController { }\n")
        self.assertInfraccion("el controller no toca la capa de datos (using Dapper)")
        self.assertInfraccion("el controller no toca la capa de datos (using Acme.Pagos.Api.Platform.Database)")

    def test_un_service_no_conoce_http_ni_sql(self):
        escribir(self.api / "Pagos" / "PagoService.cs",
                 "using Microsoft.AspNetCore.Http;\nusing Microsoft.Data.SqlClient;\n"
                 "public sealed class PagoService { int Codigo() => StatusCodes.Status404NotFound; }\n")
        self.assertInfraccion("el service no conoce HTTP ni SQL (using Microsoft.AspNetCore.Http)")
        self.assertInfraccion("el service no conoce HTTP ni SQL (using Microsoft.Data.SqlClient)")
        self.assertInfraccion("el service no conoce HTTP ni SQL (referencia a StatusCodes)")

    def test_un_repositorio_no_conoce_http_ni_services(self):
        escribir(self.api / "Pagos" / "PagoRepository.cs",
                 "using Microsoft.AspNetCore.Http;\n"
                 "public sealed class PagoRepository(PagoService service) : IPagoRepository { }\n")
        self.assertInfraccion("el repositorio no conoce HTTP (using Microsoft.AspNetCore.Http)")
        self.assertInfraccion("el repositorio no conoce HTTP ni services (referencia a PagoService)")

    def test_un_valor_interpolado_en_sql_es_infraccion(self):
        for literal in ('$"SELECT id FROM dbo.pagos WHERE id = \'{id}\'"',
                        '$@"DELETE FROM dbo.pagos WHERE id = {id}"',
                        '$"""\n        UPDATE dbo.pagos SET monto = {monto:F2}\n        """'):
            with self.subTest(literal=literal):
                escribir(self.api / "Pagos" / "PagoRepository.cs",
                         "public sealed class PagoRepository : IPagoRepository\n{\n"
                         f"    public string Sql(Guid id, decimal monto) => {literal};\n}}\n")
                self.assertInfraccion("interpolado; usa un parametro")

    def test_una_constante_del_repositorio_y_un_texto_que_no_es_sql_se_aceptan(self):
        escribir(self.api / "Pagos" / "PagoRepository.cs",
                 "public sealed class PagoRepository : IPagoRepository\n{\n"
                 '    private const string Columns = "id AS Id";\n'
                 '    public string Sql() => $"SELECT {Columns} FROM dbo.pagos WHERE id = @Id";\n'
                 '    public string Log(Guid id) => $"pago {id} leido";\n}\n')
        self.assertEqual([], self.errores())

    def test_una_carpeta_por_capa_es_infraccion(self):
        escribir(self.api / "Controllers" / "ClientesController.cs", "public sealed class ClientesController { }\n")
        self.assertInfraccion("src/Acme.Pagos.Api/Controllers/: carpeta por capa")

    def test_una_feature_no_usa_el_repositorio_de_otra(self):
        escribir(self.api / "Clientes" / "ClienteService.cs",
                 "public sealed class ClienteService(IPagoRepository pagos) { }\n")
        self.assertInfraccion("Clientes/ClienteService.cs: usa el repositorio de otra feature (IPagoRepository)")

    def test_platform_no_referencia_features(self):
        escribir(self.api / "Platform" / "Auditoria.cs",
                 "using Acme.Pagos.Api.Pagos;\npublic sealed class Auditoria { }\n")
        self.assertInfraccion("Platform/Auditoria.cs: Platform no referencia features (using Acme.Pagos.Api.Pagos)")

    def test_un_orm_es_infraccion(self):
        escribir(self.repo / "Directory.Packages.props",
                 '<Project><ItemGroup><PackageVersion Include="Microsoft.EntityFrameworkCore.SqlServer" Version="10.0.0" />'
                 "</ItemGroup></Project>")
        self.assertInfraccion("Directory.Packages.props: ORM prohibido ('Microsoft.EntityFrameworkCore.SqlServer')")

    def test_thread_sleep_en_pruebas_es_infraccion(self):
        escribir(self.repo / "tests" / "Acme.Pagos.Api.Tests" / "EsperaTests.cs",
                 "public class EsperaTests { void T() { Thread.Sleep(100); } }\n")
        self.assertInfraccion("EsperaTests.cs: 'Thread.Sleep' prohibido")

    def test_sin_composition_root_es_infraccion(self):
        (self.api / "Program.cs").unlink()
        self.assertInfraccion("Composition root ausente")

    def test_un_comentario_no_es_una_referencia(self):
        escribir(self.api / "Pagos" / "PagosController.cs",
                 "/// <summary>No usa IPagoRepository ni SqlConnection.</summary>\n"
                 "// using Dapper;\npublic sealed class PagosController(PagoService service) { }\n")
        self.assertEqual([], self.errores())

    def test_lo_que_no_se_pudo_medir_se_dice(self):
        repo = self.tmp / "vacio"
        escribir(repo / "src" / "Acme.Api" / "Program.cs", "var app = 1;\n")
        errores, avisos = self.check(repo)
        self.assertEqual([], errores)
        self.assertTrue(any("NO se midieron" in a for a in avisos), avisos)


class VerificadorMvcTests(Base):
    def setUp(self):
        super().setUp()
        self.repo = portal_mvc(self.tmp / "portal")
        self.web = self.repo / "src" / "Acme.Portal.Web"
        self.check = verificador(MVC).check_dotnet_mvc

    def errores(self) -> list[str]:
        return self.check(self.repo)[0]

    def assertInfraccion(self, texto: str):
        errores = self.errores()
        self.assertTrue(any(texto in e for e in errores), f"falta '{texto}' en {errores}")

    def test_el_portal_conforme_no_tiene_infracciones_ni_avisos(self):
        self.assertEqual(([], []), self.check(self.repo))

    def test_un_controller_no_usa_http_client(self):
        escribir(self.web / "Controllers" / "PagosController.cs",
                 "public sealed class PagosController(HttpClient http) { }\n")
        self.assertInfraccion("PagosController.cs: el controller llega a los datos solo por una interfaz I*Api "
                              "(referencia a HttpClient)")

    def test_un_controller_no_usa_el_cliente_concreto(self):
        escribir(self.web / "Controllers" / "PagosController.cs",
                 "public sealed class PagosController(PagosApiClient api) { }\n")
        self.assertInfraccion("(referencia a PagosApiClient)")

    def test_una_vista_solo_presenta(self):
        casos = {"@inject IPagosApi Api\n": "@inject",
                 "<p>@Html.Raw(Model.Titulo)</p>\n": "Html.Raw",
                 "<script>alert(1)</script>\n": "<script>",
                 "<style>p { color: red }</style>\n": "<style",
                 '<p style="color: red">x</p>\n': 'style="',
                 '<button onclick="borrar()">x</button>\n': 'onclick="'}
        for cuerpo, hallado in casos.items():
            with self.subTest(hallado=hallado):
                escribir(self.web / "Views" / "Pagos" / "Index.cshtml", cuerpo)
                self.assertInfraccion(f"Views/Pagos/Index.cshtml: la vista solo presenta; sin servicios, "
                                      f"HTML crudo ni codigo en linea ({hallado})")

    def test_un_script_con_src_y_un_comentario_razor_se_aceptan(self):
        escribir(self.web / "Views" / "Pagos" / "Index.cshtml",
                 '@* nunca @Html.Raw ni <style> *@\n<script src="~/js/site.js"></script>\n')
        self.assertEqual([], self.errores())

    def test_un_paquete_de_acceso_a_datos_es_infraccion(self):
        escribir(self.web / "Acme.Portal.Web.csproj",
                 '<Project Sdk="Microsoft.NET.Sdk.Web"><ItemGroup><PackageReference Include="Dapper" />'
                 "</ItemGroup></Project>")
        self.assertInfraccion("Acme.Portal.Web.csproj: el portal no tiene acceso a datos (paquete 'Dapper')")

    def test_un_using_de_acceso_a_datos_es_infraccion(self):
        escribir(self.web / "Services" / "Atajo.cs", "using Microsoft.Data.SqlClient;\npublic sealed class Atajo { }\n")
        self.assertInfraccion("Services/Atajo.cs: el portal no tiene acceso a datos (using Microsoft.Data.SqlClient)")

    def test_la_csp_no_admite_codigo_en_linea(self):
        escribir(self.web / "Platform" / "SecurityHeadersMiddleware.cs",
                 "public sealed class SecurityHeadersMiddleware\n{\n"
                 "    const string Csp = \"default-src 'self'; script-src 'self' 'unsafe-inline'\";\n}\n")
        self.assertInfraccion("la CSP no admite 'unsafe-inline'")

    def test_platform_no_dibuja_vistas_de_una_feature(self):
        escribir(self.web / "Platform" / "Limite.cs",
                 'public sealed class Limite { string v = "~/Views/Pagos/Index.cshtml"; }\n')
        self.assertInfraccion("Platform/Limite.cs: Platform no conoce features (vista ~/Views/Pagos/)")

    def test_platform_no_usa_modelos_de_una_feature(self):
        escribir(self.web / "Platform" / "Limite.cs",
                 "using Acme.Portal.Web.Models;\npublic sealed class Limite { PagoViewModel m; }\n")
        self.assertInfraccion("Platform/Limite.cs: Platform no conoce features (modelo PagoViewModel de Pagos)")

    def test_platform_no_referencia_controllers(self):
        escribir(self.web / "Platform" / "Ruta.cs",
                 "public sealed class Ruta { string n = nameof(PagosController); }\n")
        self.assertInfraccion("Platform/Ruta.cs: Platform no conoce features (controller PagosController)")

    def test_platform_usa_vistas_compartidas_modelos_transversales_y_rutas(self):
        escribir(self.web / "Models" / "MantencionViewModel.cs",
                 "namespace Acme.Portal.Web.Models;\npublic sealed record MantencionViewModel(string Mensaje);\n")
        escribir(self.web / "Platform" / "Mantencion.cs",
                 "using Acme.Portal.Web.Models;\n"
                 "public sealed class Mantencion(MantencionViewModel aviso)\n"
                 '{ string v = "~/Views/Shared/Mantencion.cshtml"; string e = "/Pagos/Error"; }\n')
        self.assertEqual([], self.errores())

    def test_thread_sleep_en_pruebas_es_infraccion(self):
        escribir(self.repo / "tests" / "Acme.Portal.Web.Tests" / "EsperaTests.cs",
                 "public class EsperaTests { void T() { Thread.Sleep(100); } }\n")
        self.assertInfraccion("EsperaTests.cs: 'Thread.Sleep' prohibido")

    def test_las_librerias_de_wwwroot_no_se_miden(self):
        escribir(self.web / "wwwroot" / "lib" / "demo" / "Views" / "ejemplo.cshtml", "<script>alert(1)</script>\n")
        self.assertEqual([], self.errores())

    def test_lo_que_no_se_pudo_medir_se_dice(self):
        repo = self.tmp / "vacio"
        escribir(repo / "src" / "Acme.Web" / "Program.cs", "var app = 1;\n")
        errores, avisos = self.check(repo)
        self.assertEqual([], errores)
        self.assertTrue(any("NO se midieron" in a for a in avisos), avisos)


class NormalizacionMultiLLMTests(Base):
    """Las reglas y skills llegan a los tres directorios de host, y el contrato a AGENTS.md."""

    CASOS = ((LAYERED, api_en_capas, "add-persistence"), (MVC, portal_mvc, "add-page"))

    def test_normalizar_deja_paridad_completa_en_los_dos_stacks(self):
        for stack_id, armar, skill in self.CASOS:
            with self.subTest(stack=stack_id):
                repo = armar(self.tmp / stack_id)
                res = stack.normalizar_repositorio(repo)
                self.assertEqual(stack_id, res["stack"])
                for host in (".claude", ".agents", ".gemini"):
                    for regla in ("architecture.md", "dependencies.md", "security.md", "testing.md"):
                        self.assertTrue((repo / host / "rules" / regla).is_file(), f"{host}/rules/{regla}")
                    self.assertTrue((repo / host / "skills" / skill / "SKILL.md").is_file(), f"{host}/skills/{skill}")
                self.assertIn("trigger: always_on", (repo / ".gemini" / "rules" / "architecture.md").read_text("utf-8"))
                self.assertIn(f"`{stack_id}`", (repo / "AGENTS.md").read_text(encoding="utf-8"))
                self.assertTrue((repo / "scripts" / "check-architecture.py").is_file())

                diag = stack.verificar_cumplimiento(repo)
                self.assertEqual([], diag["findings"])
                self.assertTrue(diag["full_multi_llm_parity"])
                self.assertEqual(["claude-code", "openai-codex/hermes/grok/kimi", "gemini-cli/agy"],
                                 diag["hosts_active"])

    def test_el_verificador_instalado_en_el_repo_es_el_de_su_stack(self):
        for stack_id, armar, _ in self.CASOS:
            with self.subTest(stack=stack_id):
                repo = armar(self.tmp / stack_id)
                stack.normalizar_repositorio(repo)
                self.assertEqual((stack.STACKS_DIR / stack_id / "scripts" / "check-architecture.py").read_bytes(),
                                 (repo / "scripts" / "check-architecture.py").read_bytes())

    def test_las_skills_del_manifest_son_las_que_existen_en_el_stack(self):
        for stack_id in (LAYERED, MVC):
            with self.subTest(stack=stack_id):
                declaradas = stack.cargar_manifest(stack_id)["normative"]["skills"]
                self.assertEqual(sorted(declaradas), sorted(stack._skills_del_stack(stack_id)))
                self.assertEqual(9, len(declaradas))

    def test_el_layout_no_marca_como_heredado_el_repo_conforme(self):
        for stack_id, armar, _ in self.CASOS:
            with self.subTest(stack=stack_id):
                repo = armar(self.tmp / stack_id)
                lay = arquitectura.layout_de(stack_id)
                rutas = arquitectura.rutas_en_disco(repo)
                self.assertGreater(sum(1 for r in rutas if lay.en_alcance(r)), 0)
                self.assertEqual({}, arquitectura.heredados_por_unidad(lay, rutas))


class RepoRecienCreadoTests(Base):
    """Un proyecto nuevo salido de la plantilla: `git init` y todavia ningun commit."""

    def test_un_repo_git_sin_nada_versionado_se_mide_por_lo_que_hay_en_disco(self):
        repo = api_en_capas(self.tmp / "api")
        escribir(repo / "src" / "Acme.Pagos.Api" / "Suelto.cs", "public sealed class Suelto { }\n")
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        lay = arquitectura.layout_de(LAYERED)
        rutas = arquitectura.rutas_en_disco(repo)
        self.assertIn("src/Acme.Pagos.Api/Pagos/PagoService.cs", rutas)
        self.assertEqual({"src/Acme.Pagos.Api": ["src/Acme.Pagos.Api/Suelto.cs"]},
                         arquitectura.heredados_por_unidad(lay, rutas))

    def test_con_archivos_versionados_lo_que_no_esta_en_git_no_cuenta(self):
        repo = api_en_capas(self.tmp / "api")
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        subprocess.run(["git", "add", "src/Acme.Pagos.Api/Program.cs"], cwd=repo, check=True)
        self.assertEqual(["src/Acme.Pagos.Api/Program.cs"], arquitectura.rutas_en_disco(repo))


class VersionMinimaTests(Base):
    """La version de .NET se lee donde este: en cada .csproj o en Directory.Build.props."""

    def auditar(self, repo: Path, stack_id: str) -> dict:
        with mock.patch.object(stack, "_herramienta_disponible", return_value=False):
            return stack.auditar_seguridad_y_versiones(repo, stack_id)

    def test_una_version_vieja_en_directory_build_props_se_avisa(self):
        for stack_id, armar in ((LAYERED, api_en_capas), (MVC, portal_mvc)):
            with self.subTest(stack=stack_id):
                repo = armar(self.tmp / stack_id)
                escribir(repo / "Directory.Build.props", NET10.replace("net10.0", "net8.0"))
                res = self.auditar(repo, stack_id)
                self.assertTrue(any("net8.0" in w and "net10.0.0" in w for w in res["warnings"]), res["warnings"])
                self.assertEqual("/dotnet/aspnetcore.docs", res["context7_library"])
                self.assertIn("--include-transitive", res["audit_command"])

    def test_la_version_de_la_norma_no_avisa(self):
        res = self.auditar(api_en_capas(self.tmp / "api"), LAYERED)
        self.assertEqual([], [w for w in res["warnings"] if "inferior" in w])

    def test_la_version_minima_misma_no_avisa_en_el_stack_hexagonal(self):
        """`net8.0` contra el minimo `8.0.0`: (8, 0) < (8, 0, 0) avisaba de la version que se pide."""
        repo = self.tmp / "hex"
        escribir(repo / "src" / "Acme.Domain" / "Acme.Domain.csproj", NET10.replace("net10.0", "net8.0"))
        self.assertEqual([], self.auditar(repo, HEXAGONAL)["warnings"])

    def test_el_stack_hexagonal_conserva_su_lectura_del_csproj(self):
        repo = self.tmp / "hex"
        escribir(repo / "src" / "Acme.Domain" / "Acme.Domain.csproj",
                 "<Project><PropertyGroup><TargetFramework>net6.0</TargetFramework></PropertyGroup></Project>")
        res = self.auditar(repo, HEXAGONAL)
        self.assertTrue(any("net6.0" in w for w in res["warnings"]), res["warnings"])


class PlantillasOficialesTests(unittest.TestCase):
    """La plantilla ES la norma: se detecta como su stack y su arquitectura esta en verde."""

    CASOS = ((LAYERED, "calpil-dotnet-layered-template"), (MVC, "calpil-dotnet-mvc-template"),
             (HEXAGONAL, "calpil-dotnet-hexagonal-template"))

    def test_cada_plantilla_dotnet_se_detecta_como_su_stack(self):
        for stack_id, carpeta in self.CASOS:
            repo = PLANTILLAS / carpeta
            if not repo.is_dir():
                continue  # la plantilla no esta en esta maquina
            with self.subTest(stack=stack_id):
                res = stack.detectar_stack_directorio(repo)
                self.assertEqual(stack_id, res["stack"])
                self.assertGreaterEqual(res["confidence"], 80)

    def test_cada_plantilla_cumple_su_propia_norma(self):
        for stack_id, carpeta in self.CASOS:
            repo = PLANTILLAS / carpeta
            if not repo.is_dir():
                continue
            with self.subTest(stack=stack_id):
                diag = stack.verificar_cumplimiento(repo)
                self.assertEqual([], [f for f in diag["findings"] if not f.startswith("Copias desactualizadas")])
                self.assertTrue(diag["architecture_ok"])
                self.assertEqual([], diag["architecture_warnings"])
                self.assertTrue(diag["rules_ok"])
                self.assertTrue(diag["skills_ok"])


if __name__ == "__main__":
    unittest.main()


def raiz_multirepo(raiz: Path) -> Path:
    """La raiz de un proyecto multi-repo: una solucion local y el codigo solo en sus repos y worktrees."""
    escribir(raiz / "Proyecto.local.slnx", "<Solution />")
    api_en_capas(raiz / "api")
    (raiz / "api" / ".git").mkdir()
    portal_mvc(raiz / "web")
    (raiz / "web" / ".git").mkdir()
    escribir(raiz / "api-wt" / "1-pagos" / ".git", "gitdir: /otro/lugar/.git/worktrees/1-pagos\n")
    api_en_capas(raiz / "api-wt" / "1-pagos")
    return raiz


class StackDeclaradoTests(Base):
    """El contrato AGENTS.md que genera el arnes declara el stack del repo y manda sobre la heuristica.

    Lo que se midio antes del cambio: la raiz de DEREC (una solucion local `.slnx`, ignorada por git,
    y el codigo solo en `api/`, `web/`, `sync/` y sus worktrees) se detectaba como `dotnet-hexagonal`
    en cada arranque. `estado.py` le volvia a instalar la norma hexagonal aunque el usuario le
    hubiera puesto la MVC con `normalizar --stack dotnet-mvc`.
    """

    def test_sin_contrato_la_raiz_multirepo_cae_en_el_stack_general(self):
        self.assertEqual(HEXAGONAL, self.detectado(raiz_multirepo(self.tmp / "raiz")))

    def test_el_contrato_que_deja_normalizar_declara_el_stack(self):
        raiz = raiz_multirepo(self.tmp / "raiz")
        stack.normalizar_repositorio(raiz, MVC)
        res = stack.detectar_stack_directorio(raiz)
        self.assertEqual(MVC, res["stack"])
        self.assertEqual(100, res["confidence"])
        self.assertTrue(any("AGENTS.md" in i for i in res["indicators"]), res["indicators"])

    def test_el_contrato_manda_aunque_la_heuristica_diga_otro_stack(self):
        repo = api_en_capas(self.tmp / "api")
        stack.normalizar_repositorio(repo, MVC)
        self.assertEqual(MVC, self.detectado(repo))

    def test_un_agents_md_del_usuario_no_declara_nada(self):
        raiz = raiz_multirepo(self.tmp / "raiz")
        escribir(raiz / "AGENTS.md", "# Contrato del equipo\n\n> **Stack Tecnológico:** `dotnet-mvc`  \n")
        self.assertEqual(HEXAGONAL, self.detectado(raiz))

    def test_un_stack_declarado_que_no_existe_no_cuenta(self):
        raiz = raiz_multirepo(self.tmp / "raiz")
        escribir(raiz / "AGENTS.md", "# AGENTS.md — Contrato Operativo y Normativo (Otro)\n\n"
                                     "> **Stack Tecnológico:** `cobol-zos`  \n")
        self.assertEqual(HEXAGONAL, self.detectado(raiz))

    def test_la_raiz_declarada_mvc_no_mide_el_codigo_de_sus_repos(self):
        raiz = raiz_multirepo(self.tmp / "raiz")
        stack.normalizar_repositorio(raiz, MVC)
        diag = stack.verificar_cumplimiento(raiz, MVC)
        self.assertTrue(diag["architecture_ok"], diag["architecture_errors"])

    def test_la_deteccion_se_puede_serializar(self):
        """`stack.py detectar --json` caia con 'Circular reference detected': el ganador se contenia a si mismo."""
        for armar in (api_en_capas, raiz_multirepo):
            with self.subTest(repo=armar.__name__):
                json.dumps(stack.detectar_stack_directorio(armar(self.tmp / armar.__name__)))


class SubRepoNoSeMideTests(Base):
    """Un sub-repo o un worktree (carpeta con su propio `.git`) es otro repo: el verificador no lo mide."""

    CASOS = ((MVC, "check_dotnet_mvc", "Controllers/XController.cs",
              "public sealed class XController(HttpClient http) { }\n"),
             (LAYERED, "check_dotnet_layered", "Pagos/PagosController.cs",
              "public sealed class PagosController(IPagoRepository repository) { }\n"),
             (HEXAGONAL, "check_dotnet_architecture", "Domain/Pago.cs",
              "using Dapper;\nnamespace Acme.Domain;\npublic sealed class Pago { }\n"))

    def armar(self, stack_id: str) -> Path:
        repo = self.tmp / stack_id
        if stack_id == MVC:
            return portal_mvc(repo)
        if stack_id == LAYERED:
            return api_en_capas(repo)
        escribir(repo / "Acme.sln", "")
        escribir(repo / "src" / "WebApi" / "Program.cs", "var builder = WebApplication.CreateBuilder(args);\n")
        return repo

    def test_el_codigo_de_un_sub_repo_o_de_un_worktree_no_se_mide(self):
        for stack_id, funcion, rel, codigo in self.CASOS:
            check = getattr(verificador(stack_id), funcion)
            repo = self.armar(stack_id)
            base = check(repo)[0]
            for nombre, git in (("sub-repo", "dir"), ("worktree", "archivo")):
                with self.subTest(stack=stack_id, carpeta=nombre):
                    otro = repo / nombre
                    if git == "dir":
                        (otro / ".git").mkdir(parents=True)
                    else:
                        escribir(otro / ".git", "gitdir: /otro/lugar\n")
                    escribir(otro / "src" / "Otro.Api" / rel, codigo)
                    self.assertEqual(base, check(repo)[0])

    def test_la_misma_carpeta_sin_git_si_se_mide(self):
        for stack_id, funcion, rel, codigo in self.CASOS:
            with self.subTest(stack=stack_id):
                check = getattr(verificador(stack_id), funcion)
                repo = self.armar(stack_id)
                base = check(repo)[0]
                escribir(repo / "suelto" / "src" / "Otro.Api" / rel, codigo)
                self.assertNotEqual(base, check(repo)[0])

    def test_una_raiz_sin_codigo_propio_avisa_y_no_infringe(self):
        raiz = raiz_multirepo(self.tmp / "raiz")
        for stack_id, funcion, _, _ in self.CASOS:
            with self.subTest(stack=stack_id):
                errores, avisos = getattr(verificador(stack_id), funcion)(raiz)
                self.assertEqual([], errores)
                self.assertTrue(any("Sin codigo .NET propio" in a for a in avisos), avisos)

    def test_un_repo_con_codigo_propio_sigue_exigiendo_su_composition_root(self):
        raiz = raiz_multirepo(self.tmp / "raiz")
        escribir(raiz / "src" / "Suelto" / "Suelto.cs", "public sealed class Suelto { }\n")
        for stack_id, funcion, _, _ in self.CASOS:
            with self.subTest(stack=stack_id):
                errores = getattr(verificador(stack_id), funcion)(raiz)[0]
                self.assertTrue(any("omposition" in e and "ausente" in e for e in errores), errores)

    def test_lo_que_git_ignora_no_se_mide(self):
        for stack_id, funcion, rel, codigo in self.CASOS:
            with self.subTest(stack=stack_id):
                check = getattr(verificador(stack_id), funcion)
                repo = self.armar(stack_id)
                subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
                escribir(repo / ".gitignore", "/.local-dev/\n/Suelto.local.cs\n")
                base = check(repo)[0]
                escribir(repo / ".local-dev" / "src" / "Otro.Api" / rel, codigo)
                escribir(repo / "Suelto.local.cs", codigo)
                self.assertEqual(base, check(repo)[0])
                escribir(repo / "local-dev" / "src" / "Otro.Api" / rel, codigo)
                self.assertNotEqual(base, check(repo)[0])

    def test_una_raiz_con_solo_codigo_ignorado_y_sus_repos_avisa_y_no_infringe(self):
        raiz = raiz_multirepo(self.tmp / "raiz")
        subprocess.run(["git", "init", "-q"], cwd=raiz, check=True)
        escribir(raiz / ".gitignore", "/.local-dev/\n/*.local.slnx\n")
        escribir(raiz / ".local-dev" / "init-db.cs", "using System.Data;\npublic static class InitDb { }\n")
        for stack_id, funcion, _, _ in self.CASOS:
            with self.subTest(stack=stack_id):
                errores, avisos = getattr(verificador(stack_id), funcion)(raiz)
                self.assertEqual([], errores)
                self.assertTrue(any("Sin codigo .NET propio" in a for a in avisos), avisos)
