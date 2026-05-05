# Guía de Backup y Restauración Automática para Odoo con Docker

Esta guía explica cómo usar el `docker-compose.yml` con servicios para:

- Levantar PostgreSQL y Odoo.
- Restaurar automáticamente una base de datos Odoo **solo cuando no exista**.
- Crear backups manuales con un solo comando.
- Borrar volúmenes para probar la restauración desde cero.

---

## 1. Estructura esperada del proyecto

Tu proyecto debería tener una estructura similar a esta:

```text
Restaurante_Odoo/
├── docker-compose.yml
├── addons/
├── backups/
│   ├── db_demo.dump
│   └── filestore/
│       └── odoo/
├── scripts/
└── README_BACKUP_RESTORE.md
```

La carpeta `backups` debe contener:

```text
backups/db_demo.dump
backups/filestore/odoo/
```

Donde:

- `db_demo.dump` es el respaldo de la base de datos PostgreSQL.
- `filestore/odoo/` contiene los archivos adjuntos, imágenes y recursos subidos a Odoo.
- `odoo` es el nombre de la base de datos creada desde el navegador de Odoo.

---

## 2. Levantar el proyecto normalmente

Para iniciar PostgreSQL, ejecutar el restore automático si corresponde y levantar Odoo:

```bash
docker compose up -d
```

Luego puedes entrar a Odoo desde:

```text
http://localhost:8070
```

---

## 3. ¿Cuándo se ejecuta el restore automático?

El servicio `restore` se ejecuta cuando haces:

```bash
docker compose up -d
```

Pero **no restaura siempre**.

Primero revisa si existe la base de datos:

```text
odoo
```

Si la base `odoo` ya existe, muestra algo como:

```text
La base odoo ya existe. No se restaura.
```

Si la base `odoo` no existe, busca el archivo:

```text
/backups/db_demo.dump
```

Y si existe, restaura la base y el filestore.

---

## 4. Hacer backup manual con Docker

Para generar un backup manual ejecuta:

```bash
docker compose --profile tools run --rm backup
```

Este comando genera o sobrescribe:

```text
backups/db_demo.dump
backups/filestore/odoo/
```

Este backup incluye:

- Base de datos PostgreSQL de Odoo.
- Filestore de Odoo.
- Imágenes, adjuntos y archivos internos asociados a la base `odoo`.

---

## 5. Ver logs del backup

Después de ejecutar el backup, puedes revisar los logs del servicio con:

```bash
docker compose logs backup
```

Aunque normalmente basta con revisar que existan estos archivos:

```bash
ls backups
ls backups/filestore/odoo
```

En Windows PowerShell puedes usar:

```powershell
dir backups
dir backups\filestore\odoo
```

---

## 6. Ver logs del restore

Para revisar qué hizo el servicio de restauración:

```bash
docker compose logs restore
```

Si quieres ver todos los logs en tiempo real:

```bash
docker compose logs -f
```

---

## 7. Probar restauración automática desde cero

Para probar que el restore automático funciona, debes simular una instalación limpia.

### Paso 1: Crear backup

Antes de borrar nada, genera un backup:

```bash
docker compose --profile tools run --rm backup
```

Verifica que exista:

```text
backups/db_demo.dump
backups/filestore/odoo/
```

### Paso 2: Apagar contenedores

```bash
docker compose down
```

Este comando apaga y elimina los contenedores, pero **no elimina los volúmenes**.

---

## 8. Listar volúmenes de Docker

Para ver los volúmenes existentes:

```bash
docker volume ls
```

Busca los volúmenes relacionados con tu proyecto. Normalmente tendrán nombres parecidos a:

```text
nombrecarpeta_odoo-db-data
nombrecarpeta_odoo-web-data
```

Por ejemplo, si tu carpeta se llama `Restaurante_Odoo`, podrían aparecer así:

```text
restaurante_odoo_odoo-db-data
restaurante_odoo_odoo-web-data
```

El nombre exacto depende del nombre de la carpeta del proyecto.

---

## 9. Borrar volúmenes para restaurar desde cero

Cuando identifiques los nombres reales de tus volúmenes, bórralos así:

```bash
docker volume rm nombrecarpeta_odoo-db-data nombrecarpeta_odoo-web-data
```

Ejemplo:

```bash
docker volume rm restaurante_odoo_odoo-db-data restaurante_odoo_odoo-web-data
```

Si Docker indica que un volumen está en uso, asegúrate de haber ejecutado primero:

```bash
docker compose down
```

---

## 10. Levantar nuevamente para que restaure solo

Después de borrar los volúmenes, levanta el proyecto:

```bash
docker compose up -d
```

Como la base `odoo` ya no existe, el servicio `restore` hará esto automáticamente:

```text
1. Espera a que PostgreSQL esté listo.
2. Revisa si existe la base odoo.
3. Como no existe, crea la base odoo.
4. Restaura backups/db_demo.dump.
5. Restaura backups/filestore/odoo/.
6. Luego inicia Odoo.
```

Para comprobarlo:

```bash
docker compose logs restore
```

---

## 11. Reiniciar Odoo

Para reiniciar solo Odoo:

```bash
docker compose restart odoo
```

Para reiniciar todo:

```bash
docker compose restart
```

---

## 12. Apagar todo

Para apagar los contenedores sin borrar volúmenes:

```bash
docker compose down
```

Esto mantiene los datos guardados en los volúmenes.

---

## 13. Apagar y borrar volúmenes en un solo comando

Si quieres borrar los contenedores y también los volúmenes del proyecto:

```bash
docker compose down -v
```

Cuidado: este comando elimina los datos de PostgreSQL y el filestore guardado en volúmenes.

Úsalo solo si ya tienes backup en:

```text
backups/db_demo.dump
backups/filestore/odoo/
```

---

## 14. Flujo recomendado de trabajo

### Levantar el sistema

```bash
docker compose up -d
```

### Trabajar normalmente en Odoo

Entra a:

```text
http://localhost:8070
```

### Crear backup cuando termines cambios importantes

```bash
docker compose --profile tools run --rm backup
```

### Apagar el sistema

```bash
docker compose down
```

---

## 15. Restaurar en otra máquina

Para mover el proyecto a otra computadora:

1. Copia toda la carpeta del proyecto.
2. Asegúrate de incluir:

```text
docker-compose.yml
addons/
backups/db_demo.dump
backups/filestore/odoo/
```

3. En la nueva máquina ejecuta:

```bash
docker compose up -d
```

Si no existen volúmenes previos, Docker restaurará automáticamente la base y el filestore.

---

## 16. Comandos rápidos

```bash
# Levantar proyecto
docker compose up -d

# Ver logs generales
docker compose logs -f

# Ver logs del restore
docker compose logs restore

# Crear backup manual
docker compose --profile tools run --rm backup

# Apagar contenedores
docker compose down

# Listar volúmenes
docker volume ls

# Borrar volúmenes específicos
docker volume rm nombrecarpeta_odoo-db-data nombrecarpeta_odoo-web-data

# Apagar y borrar volúmenes del proyecto
docker compose down -v

# Reiniciar Odoo
docker compose restart odoo
```

---

## 17. Nota importante

El restore automático **solo restaura si la base `odoo` no existe**.

Esto evita que cada vez que ejecutes:

```bash
docker compose up -d
```

se sobrescriban los cambios nuevos.

Si quieres forzar una restauración desde cero, debes borrar los volúmenes:

```bash
docker compose down -v
docker compose up -d
```

O borrar manualmente los volúmenes específicos del proyecto.
