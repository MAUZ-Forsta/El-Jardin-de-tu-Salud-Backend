# El Jardín de tu Salud — Backend

API FastAPI con PostgreSQL, SQLAlchemy y Alembic. Están implementados el registro, las sesiones y el catálogo de productos físicos. Carrito, pedidos, pagos, inventario y cursos aún no tienen endpoints.

## Preparación

Requiere Python 3.11 a 3.14 y PostgreSQL. Instalar desde `pyproject.toml`, que contiene las dependencias de la aplicación y las herramientas de desarrollo:

```bash
python -m venv venv
source venv/bin/activate
python -m pip install -e '.[dev]'
cp .env.example .env
```

Editar `.env` con las URL de PostgreSQL correspondientes. `APP_DEBUG` debe ser `true` o `false`; se usa ese nombre para evitar conflictos con la variable genérica `DEBUG` del entorno. `TEST_DATABASE_URL` debe apuntar exclusivamente a `tia_richrad_test` y ser distinta de `DATABASE_URL`. La aplicación acepta orígenes CORS explícitos; en producción exige HTTPS, `APP_DEBUG=false` y `SESSION_COOKIE_SECURE=true`.

`requirements.txt` es una lista anterior que no reproduce todas las dependencias. Usar `pyproject.toml` para instalar.

## Ejecución y API

```bash
python -m uvicorn app.main:create_app --factory --reload
```

| Método | Ruta | Función |
| --- | --- | --- |
| GET | `/health` | Estado del servicio |
| POST | `/api/v1/auth/register` | Registro de clientes |
| POST | `/api/v1/auth/login` | Crea sesión y cookie HttpOnly; devuelve token CSRF |
| GET | `/api/v1/auth/me` | Devuelve el usuario de la sesión |
| POST | `/api/v1/auth/csrf` | Rota el token CSRF |
| POST | `/api/v1/auth/logout` | Revoca la sesión y elimina la cookie |
| GET | `/api/v1/products` | Lista productos físicos activos; búsqueda `q`, `limit` y `offset` |
| GET | `/api/v1/products/{id}` | Detalle activo y productos relacionados |
| GET | `/api/v1/admin/products` | Lista productos físicos, incluidos los inactivos; solo ADMIN |
| GET | `/api/v1/admin/products/{id}` | Detalle administrativo; solo ADMIN |
| POST | `/api/v1/admin/products` | Crea un producto inactivo; ADMIN, origen y CSRF |
| PATCH | `/api/v1/admin/products/{id}` | Edita o activa/desactiva; ADMIN, origen y CSRF |

`login`, `csrf` y `logout` exigen un `Origin` presente en `CORS_ORIGINS`. `logout` exige además `X-CSRF-Token`. La cookie viaja con las solicitudes del navegador; el frontend debe usar credenciales y conservar el token CSRF recibido. La documentación OpenAPI está disponible en `/docs` fuera de producción.

El frontend React todavía usa autenticación simulada; integrar estas rutas con sus formularios y estado de sesión es trabajo pendiente.

El catálogo no almacena stock ni permite comprar. `stock_available: null` expresa que la disponibilidad aún no se conoce; publicar un producto no garantiza existencias. Las categorías físicas del contrato difieren de las categorías actuales del prototipo React y requieren una adaptación explícita en la integración. El contrato completo está en [Catálogo de productos](<../El-Jardin-de-tu-Salud-Docs/Reports/Development/API/Catálogo de productos.md>).

## Migraciones y pruebas

La cadena Alembic es `fbb92a483cb4` (baseline), `ee44ed5d90be` (usuarios y perfiles), `9b5b0c3d4e6f` (sesiones), `c7e4a91f2b35` (catálogo). `python -m alembic upgrade head` modifica la base indicada por `DATABASE_URL`; verificarla antes de ejecutar el comando.

Para actualizar **solo** la base de pruebas, usar el script que comprueba el nombre `tia_richrad_test` y que ambas URL sean diferentes:

```bash
python -m scripts.migrate_test_db
python -m pytest
ruff check app tests alembic/versions scripts
python -m compileall -q app tests alembic/versions
```

En la verificación del 18 de noviembre de 2026, la suite completa terminó con **54 aprobadas y una advertencia de Starlette**. Las pruebas de base usan `tia_richrad_test`; `tests/test_database.py` contiene un auxiliar de migración, no un caso de pytest.

## Alcance pendiente

El perfil aún carece de teléfono, direcciones y preferencias; también faltan recuperación de contraseña y permisos para otros recursos administrativos. Los requisitos y decisiones del proyecto están en el repositorio hermano [El-Jardin-de-tu-Salud-Docs](../El-Jardin-de-tu-Salud-Docs/README.md).
