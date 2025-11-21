
# Proyecto ETL + API COVID-19 (Personalizado — master-shore-475019-i7)

**Resumen corto**  
Este repositorio contiene el pipeline ETL + API que implementaste en Google Cloud Platform (GCP) para procesar datos de COVID‑19 (Ministerio de Salud — Colombia). El proyecto está automatizado con Workflows y Cloud Scheduler, los datos se procesan con Dataproc (Spark/PySpark) y la API se sirve desde Cloud Run.

---

## Información del proyecto (específica tuya)
- **ID de proyecto GCP:** `master-shore-475019-i7`
- **Service account usada para pipeline / Cloud Run:** `covid19-pipeline-sa@master-shore-475019-i7.iam.gserviceaccount.com`
- **Buckets que usaste:**
  - RAW: `gs://covid19-raw-master-shore-475019-i7/ministerio/`
  - ARTIFACTS (scripts/jobs): `gs://covid19-artifacts-master-shore-475019-i7/jobs/`
  - TRUSTED / Parquet: `gs://covid19-trusted-master-shore-475019-i7/parquet/`
  - REFINED (mencionado en cargas): `gs://covid19-refined-master-shore-475019-i7/` *(si lo usaste)*
- **Workflow template:** `covid19-workflow`
- **Cloud Run service (API):** `covid-api`
  - Ejemplo de URL desplegada observada en logs: `https://covid-api-1043357486945.us-central1.run.app`
  - Nombre alternativo / preview: `https://covid-api-zoreft7ikq-uc.a.run.app`
- **BigQuery:** dataset `covid_dataset`, tabla `daily_cases` → `master-shore-475019-i7.covid_dataset.daily_cases`
- **PySpark job script (ETL) que subiste a artifacts:** `gs://covid19-artifacts-master-shore-475019-i7/jobs/etl_job.py`

---

## Qué contiene este README
1. Estructura del repo (qué archivos y dónde).
2. Cómo ejecutar (local / GCP) — comandos reproducibles.
3. Código clave (extractos) — ETL, app.py, Dockerfile, función trigger.
4. Pasos para reconstruir la imagen y redeploy de Cloud Run.
5. Comandos para debug y logs que usaste.
6. Checklist para la sustentación (video).
7. Troubleshooting (errores comunes que encontraste y cómo los resolviste).

---

## Estructura recomendada del repositorio (tuya)
```
project/
│── cloud_run/
│   ├── app.py                 # Flask API
│   ├── requirements.txt
│   ├── Dockerfile
│── gcp/
│   ├── cloud_functions/
│   │   └── trigger_dataproc/  # función trigger-dataproc
│   │       └── main.py
│── jobs/
│   ├── etl_job.py             # PySpark ETL (subido a GCS artifacts)
│── ingest/
│   └── ingest_script.py       # script para descargar raw del ministerio
│── README.md
```

---

## Código clave (extractos exactos que usaste)

### 1) `app.py` (Cloud Run — Flask)
```python
from flask import Flask, jsonify, request
from google.cloud import bigquery
import os

app = Flask(__name__)
client = bigquery.Client()

DATASET_TABLE = os.environ.get("BQ_TABLE", "master-shore-475019-i7.covid_dataset.daily_cases")

@app.route("/daily_cases")
def daily_cases():
    dept = request.args.get("departamento")

    query = f"SELECT * FROM `{DATASET_TABLE}`"

    if dept:
        # Soporta buscar por nombre (case-insensitive) o por código
        query += (
            " WHERE UPPER(departamento_nom) = UPPER('" + dept + "')"
            " OR departamento = '" + dept + "'"
        )

    query += " ORDER BY fecha_reporte_web DESC LIMIT 1000"

    query_job = client.query(query)
    rows = [dict(row) for row in query_job]
    return jsonify(rows)
```

> Nota: más adelante en logs detectaste que en la tabla el campo se llama `fecha_reporte_web` y no `fecha_reporte` (por eso hubo `Unrecognized name: fecha_reporte`). Ya adaptaste a `fecha_reporte_web`.

---

### 2) `Dockerfile` (para Cloud Run — el que usaste)
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["gunicorn", "-b", "0.0.0.0:8080", "app:app"]
```

---

### 3) `etl_job.py` (PySpark — extracto usado)
```python
from pyspark.sql import SparkSession
from pyspark.sql.functions import to_timestamp, col

def main():
    spark = SparkSession.builder.appName("covid-etl").getOrCreate()

    raw_path = "gs://covid19-raw-master-shore-475019-i7/ministerio/*"
    trusted_path = "gs://covid19-trusted-master-shore-475019-i7/parquet/"

    # Si tus archivos son JSON multiline:
    df = spark.read.option("multiline", "true").json(raw_path)

    # Normalización ejemplo (campo de fecha observado en tu tabla final)
    if "fecha_reporte_web" in df.columns:
        df = df.withColumn("fecha_reporte_web", to_timestamp(col("fecha_reporte_web")))

    # Escribir Parquet a trusted (overwrite para pruebas)
    df.write.mode("overwrite").parquet(trusted_path)

    spark.stop()

if __name__ == "__main__":
    main()
```

---

### 4) Cloud Function `trigger_dataproc` (en `gcp/cloud_functions/trigger_dataproc/main.py`)
**Importante**: la función en el archivo debe llamarse exactamente lo que espera `functions-framework` si despliegas con nombre por defecto; tú resolviste que el entry point es `trigger_dataproc` (evita `-` en nombre de función).

```python
import os
from google.cloud import dataproc_v1

PROJECT_ID = os.environ.get("PROJECT_ID")
REGION = os.environ.get("REGION", "us-central1")
TEMPLATE = os.environ.get("TEMPLATE_NAME", "covid19-workflow")

def trigger_dataproc(request):
    client = dataproc_v1.WorkflowTemplatesClient(
        client_options={"api_endpoint": f"{REGION}-dataproc.googleapis.com:443"}
    )
    parent = f"projects/{PROJECT_ID}/regions/{REGION}"
    response = client.instantiate_workflow_template(
        name=f"{parent}/workflowTemplates/{TEMPLATE}"
    )
    return "Workflow instantiated", 200
```

**Error que encontraste:** `MissingTargetException: File /workspace/main.py is expected to contain a function named 'trigger-dataproc'. Found: 'trigger_dataproc' instead.`  
**Solución:** al desplegar con `gcloud functions deploy trigger-dataproc ...` el framework esperaba una función Python llamada `trigger-dataproc` (no válida como nombre de función). Desplegaste correctamente con `--entry-point=trigger_dataproc` o renombraste el target en el comando o cambiaste la configuración.

---

## Comandos más útiles que ejecutaste (paso a paso)

### Dataproc — crear workflow-managed cluster / template
> Ejemplo que arrojó error por flags incompatibles, la opción recomendada es usar `--worker-machine-type` en vez de `--machine-type`:
```bash
gcloud dataproc workflow-templates set-managed-cluster covid19-workflow \
  --region=us-central1 \
  --cluster-name=covid19-ephemeral-cluster \
  --zone=us-central1-a \
  --single-node \
  --worker-machine-type=n1-standard-2 \
  --image-version=2.1-debian11
```

### Añadir jobs al workflow (nota: debes especificar `--step-id`)
```bash
gcloud dataproc workflow-templates add-job pyspark gs://covid19-artifacts-master-shore-475019-i7/jobs/etl_job.py \
  --step-id=etl-step \
  --workflow-template=covid19-workflow \
  --region=us-central1
```

### Instanciar workflow (ejecución completa que crea cluster ephemerally)
```bash
gcloud dataproc workflow-templates instantiate covid19-workflow --region=us-central1
```

### Subir imagen (opciones)
- Construir y subir con Cloud Build (necesitas Dockerfile en el dir o especificar `--tag` con contexto):
```bash
gcloud builds submit --tag gcr.io/master-shore-475019-i7/covid-api .
```
(si recibes `Dockerfile required when specifying --tag` asegúrate de ejecutar el comando desde la carpeta que contiene Dockerfile o pasar `--source .`).

- O desplegar desde fuente directo a Cloud Run (no necesitas construir imagen manualmente):
```bash
gcloud run deploy covid-api --source . --region=us-central1 --set-env-vars BQ_TABLE=master-shore-475019-i7.covid_dataset.daily_cases
```

### Permisos (lo ejecutaste y funcionó)
Dar permisos BigQuery al service account de Cloud Run:
```bash
gcloud projects add-iam-policy-binding master-shore-475019-i7 \
  --member="serviceAccount:covid19-pipeline-sa@master-shore-475019-i7.iam.gserviceaccount.com" \
  --role="roles/bigquery.dataViewer"

gcloud projects add-iam-policy-binding master-shore-475019-i7 \
  --member="serviceAccount:covid19-pipeline-sa@master-shore-475019-i7.iam.gserviceaccount.com" \
  --role="roles/bigquery.user"
```

Dar storage admin (si tu pipeline necesita escribir en buckets):
```bash
gcloud projects add-iam-policy-binding master-shore-475019-i7 \
  --member="serviceAccount:covid19-pipeline-sa@master-shore-475019-i7.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"
```

### Logs y depuración (comandos que usaste)
- Leer logs Cloud Run (mostraste muchas líneas):
```bash
gcloud run services logs read covid-api --region=us-central1
```

- Ver driver output de jobs Dataproc (ya lo hiciste):
```bash
gsutil cat gs://dataproc-staging-us-central1-1043357486945-ncd2wmd2/google-cloud-dataproc-metainfo/<run-id>/jobs/etl-step-*/driveroutput.000000000
```

---

## Cómo reconstruir la imagen y redeploy después de cambiar código (pasos precisos que funcionan)

1. Desde la carpeta `cloud_run/` (donde está `Dockerfile` y `app.py`):

```bash
# construir y subir
gcloud builds submit --tag gcr.io/master-shore-475019-i7/covid-api .
# desplegar la imagen en Cloud Run
gcloud run deploy covid-api --image gcr.io/master-shore-475019-i7/covid-api --region=us-central1 --platform managed --set-env-vars BQ_TABLE=master-shore-475019-i7.covid_dataset.daily_cases --service-account=covid19-pipeline-sa@master-shore-475019-i7.iam.gserviceaccount.com
```

2. Alternativa (deploy desde fuente):
```bash
gcloud run deploy covid-api --source . --region=us-central1 --set-env-vars BQ_TABLE=master-shore-475019-i7.covid_dataset.daily_cases
```

3. Confirmar nuevo URL y probar:
```bash
gcloud run services describe covid-api --region=us-central1 --format="value(status.url)"
curl "https://<SERVICE_URL>/daily_cases?departamento=5"
```

---

## Checklist para la sustentación (video demo) — exactamente lo que mostraste y debes mostrar

1. Mostrar **buckets** en la consola (RAW y TRUSTED).  
2. Mostrar **archivo raw** (ej. `gs://covid19-raw-master-shore-475019-i7/ministerio/<file>`).  
3. Ejecutar manualmente (o mostrar ejecución pasada) de **Workflow** y que se creen clusters efímeros.  
4. Mostrar salida de logs del job Dataproc (driveroutput).  
5. Confirmar parquet en `gs://covid19-trusted-master-shore-475019-i7/parquet/`.  
6. Mostrar tabla `covid_dataset.daily_cases` en BigQuery (esquema y muestra de filas).  
   - En tus pruebas buscaste por `departamento` tanto por código (ej. `5`) como por nombre (`ANTIOQUIA`) — muestra ambas consultas.  
7. Desplegar/mostrar **Cloud Run** y el endpoint.  
8. Probar API con `curl` (ej.: `?departamento=5` y `?departamento=ANTIOQUIA`) y mostrar resultados.  
9. Mostrar **Cloud Scheduler** y la job que invoca la Cloud Function `trigger-dataproc` (OIDC service account).  
10. Explicar los permisos IAM que configuraste y por qué (BigQuery viewer, Storage admin, etc.).  
11. Explicar decisiones de diseño (por qué Parquet, por qué Dataproc, por qué Cloud Run).  
12. Mostrar screenshots o la terminal con los comandos que corriste (logs reproducibles).  

---

## Troubleshooting (errores que tuviste y soluciones)

- **Error**: `unrecognized arguments: --machine-type=n1-standard-2`  
  **Causa / Fix**: Usa `--worker-machine-type` en lugar de `--machine-type` en `gcloud dataproc workflow-templates set-managed-cluster`.

- **Error**: `argument --step-id: Must be specified.` al agregar job al workflow.  
  **Fix**: Siempre incluye `--step-id=<id>` para cada job que agregues.

- **Error**: functions-framework espera `trigger-dataproc` pero encontraste `trigger_dataproc`.  
  **Fix**: Usa `--entry-point=trigger_dataproc` o asegura que el nombre de la función en el archivo coincida con el entry point.

- **Error**: Cloud Run 500 por BigQuery `403 Access Denied`.  
  **Fix**: Dale permisos BigQuery al service account del servicio Cloud Run (`roles/bigquery.dataViewer`, `roles/bigquery.user`).

- **Error**: `Unrecognized name: fecha_reporte`  
  **Fix**: Revisaste esquema en BigQuery y usaste el campo real `fecha_reporte_web` en tus queries.

---

## Comandos útiles finales (resumen rápido)

- Instanciar workflow:  
  `gcloud dataproc workflow-templates instantiate covid19-workflow --region=us-central1`

- Revisar jobs Dataproc:  
  `gcloud dataproc jobs list --region=us-central1 --project=master-shore-475019-i7`

- Leer logs Cloud Run:  
  `gcloud run services logs read covid-api --region=us-central1`

- Rebuild + deploy image:  
  `gcloud builds submit --tag gcr.io/master-shore-475019-i7/covid-api .`  
  `gcloud run deploy covid-api --image gcr.io/master-shore-475019-i7/covid-api --region=us-central1 --set-env-vars BQ_TABLE=master-shore-475019-i7.covid_dataset.daily_cases`

- Probar API:  
  `curl "https://covid-api-1043357486945.us-central1.run.app/daily_cases?departamento=5"`

---

## Notas finales / Recomendaciones
- En la sustentación, antes de grabar, **verifica** que:
  - El service account esté activo y tenga permisos.
  - El Workflow se pueda ejecutar (usa un run manual desde `gcloud` o la consola).
  - Los buckets tengan los datos esperados.
  - Cloud Run esté desplegado en la última versión del código.

- Para la reproducibilidad, añade un pequeño `docs/deploy.md` con los comandos exactos que usaste (puedo generarlo si quieres).

---

# Fin — README personalizado para tu proyecto
Si quieres, ahora:
- Puedo generar un archivo `README.md` descargable (ya lo estoy guardando aquí).
- O crear también `docs/deploy.md` y `CHECKLIST_SUSTENTACION.md` listos para descargar.

