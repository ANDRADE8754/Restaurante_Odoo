# Comandos Odoo + Docker — Restaurante Casa Vieja

Referencia rápida. Todos los comandos se ejecutan desde la raíz del proyecto.

URL local: `http://localhost:8070`

---

## Levantar / apagar

```bash
# Levantar (PostgreSQL + restore automático si la BD no existe + Odoo)
docker compose up -d

# Reiniciar solo Odoo
docker compose restart odoo

# Apagar conservando datos
docker compose down

# Apagar y borrar volúmenes (PIERDES la BD y el filestore — solo si tienes backup)
docker compose down -v
```

---

## Backup y restore

```bash
# Crear backup -> ./backups/db_demo.dump + ./backups/filestore/odoo/
docker compose --profile tools run --rm backup

# El restore es automático al hacer `docker compose up -d` SI la BD `odoo` no existe.
# Para forzar restore desde cero:
docker compose down -v
docker compose up -d
```

---

## Aplicar cambios en addons

Cada vez que modifiques código de un módulo personalizado, ejecuta lo que aplique según el cambio:

| Tipo de cambio | Comando |
|---|---|
| Solo Python (modelos, métodos, lógica) | `docker compose restart odoo` |
| XML (vistas, menús, security.xml) o CSV (ir.model.access.csv) | upgrade del módulo (ver abajo) |
| Manifest `__manifest__.py` (nuevas dependencias / archivos data) | upgrade del módulo |
| Addon nuevo (carpeta nueva en `addons/`) | install (ver abajo) |

### Upgrade de uno o varios módulos (aplica cambios XML / CSV / manifest)

```bash
docker stop proyectoDAS
docker run --rm `
  --network restaurante_odoo_default `
  -v restaurante_odoo_odoo-web-data:/var/lib/odoo `
  -v "${PWD}\addons:/mnt/extra-addons" `
  odoo:18 odoo --stop-after-init -d odoo `
  -u restaurant_casa_vieja_base,restaurant_delivery_orders `
  --db_host=db --db_user=odoo --db_password=odoo
docker start proyectoDAS
```

Cambia la lista después de `-u` por los módulos que tocaste. Para upgrade de TODOS los personalizados:

```
-u restaurant_casa_vieja_base,restaurant_delivery_orders,restaurant_table_reservations,restaurant_dish_customization
```

### Instalar un addon nuevo (primera vez)

Mismo comando pero con `-i` en vez de `-u`:

```bash
docker stop proyectoDAS
docker run --rm `
  --network restaurante_odoo_default `
  -v restaurante_odoo_odoo-web-data:/var/lib/odoo `
  -v "${PWD}\addons:/mnt/extra-addons" `
  odoo:18 odoo --stop-after-init -d odoo `
  -i nombre_modulo `
  --db_host=db --db_user=odoo --db_password=odoo
docker start proyectoDAS
```

> **Importante:** detener `proyectoDAS` antes del `docker run` evita conflictos en el filestore.

---

## Logs

```bash
# Logs en vivo de Odoo
docker logs -f proyectoDAS

# Últimas 100 líneas
docker logs --tail 100 proyectoDAS

# Logs del restore (después de un up)
docker compose logs restore

# Logs del backup
docker compose logs backup
```

---

## Borrar / desinstalar

```bash
# Listar volúmenes del proyecto
docker volume ls

# Borrar un volumen específico (contenedores apagados primero)
docker compose down
docker volume rm restaurante_odoo_odoo-db-data restaurante_odoo_odoo-web-data
```

Desinstalar un módulo: hacerlo desde la UI (Apps → ⋮ → Uninstall). Para desinstalar por shell:

```bash
docker exec -it proyectoDAS odoo shell -d odoo --db_host=db --db_user=odoo --db_password=odoo
# dentro del shell:
#   self.env['ir.module.module'].search([('name','=','nombre_modulo')]).button_immediate_uninstall()
#   self.env.cr.commit()
#   exit()
```

---

## Flujo de trabajo recomendado

1. `docker compose up -d` para arrancar.
2. Trabajar en Odoo (`http://localhost:8070`).
3. Si modificas addons → upgrade del módulo (ver tabla arriba).
4. Antes de un cambio grande o al terminar el día → `docker compose --profile tools run --rm backup`.
5. `docker compose down` al cerrar.
