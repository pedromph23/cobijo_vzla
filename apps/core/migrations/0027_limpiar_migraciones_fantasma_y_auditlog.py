"""
Limpieza de restos de una versión temprana del proyecto:

1. Elimina de `django_migrations` las entradas fantasma:
   - core/0004_parametrosmodelo_parametros_p_gte_1_and_more
   - core/0005_auditlog
   Sus números 0004 y 0005 colisionan con las migraciones actuales
   (0004_registroauditoria, 0005_registroversion).

2. Dropea la tabla huérfana `core_auditlog`:
   - No está en models.py.
   - No hay referencias en el código.
   - Contiene 2 filas de pruebas manuales del 2026-09-30.

Contexto:
Ambas provienen del commit 2e5ef0a ("feat: agrega auditoria y validaciones
de integridad"). Fueron reemplazadas por RegistroAuditoria y RegistroVersion
pero nunca se limpiaron sus metadatos ni su tabla.

Riesgos:
- Bajo. Cero referencias en código y cero FKs entrantes.
- Reversible: recrea la tabla y las entradas de django_migrations.

Idempotente: si ya se limpió, no hace nada.
"""

from django.db import migrations


FORWARD_SQL = """
-- 1. Eliminar las entradas fantasma de django_migrations.
DELETE FROM django_migrations
WHERE app = 'core'
  AND name IN (
      '0004_parametrosmodelo_parametros_p_gte_1_and_more',
      '0005_auditlog'
  );

-- 2. Dropear la tabla huérfana core_auditlog.
DROP TABLE IF EXISTS core_auditlog CASCADE;
"""


REVERSE_SQL = """
-- Recrear la tabla core_auditlog (schema inferido del estado original).
CREATE TABLE IF NOT EXISTS core_auditlog (
    id bigserial PRIMARY KEY,
    fecha_hora timestamp with time zone NOT NULL DEFAULT NOW(),
    accion character varying(50) NOT NULL,
    modelo character varying(150),
    objeto_id character varying(100),
    objeto_repr character varying(200),
    descripcion text,
    ip inet,
    metodo_http character varying(10),
    ruta character varying(500),
    user_agent text,
    datos_anteriores jsonb,
    datos_nuevos jsonb,
    resultado character varying(20),
    usuario_id integer
);

-- Re-insertar las entradas de django_migrations si no existen.
INSERT INTO django_migrations (app, name, applied)
SELECT 'core', t.name, NOW()
FROM (VALUES
    ('0004_parametrosmodelo_parametros_p_gte_1_and_more'),
    ('0005_auditlog')
) AS t(name)
WHERE NOT EXISTS (
    SELECT 1 FROM django_migrations
    WHERE app = 'core' AND name = t.name
);
"""


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0026_eliminar_parroquia_huerfana'),
    ]

    operations = [
        migrations.RunSQL(
            sql=FORWARD_SQL,
            reverse_sql=REVERSE_SQL,
            state_operations=[],
        ),
    ]
