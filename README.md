
# Proyecto ETL + API COVID-19 (Personalizado — master-shore-475019-i7)

Este proyecto implementa un pipeline completo y automatizado para la ingesta, transformación, almacenamiento y exposición vía API de datos del COVID-19 en Colombia utilizando Google Cloud Platform (GCP).

---

## Información del proyecto (en mi caso):
- **ID de proyecto GCP:** `master-shore-475019-i7`
- **Service account usada para pipeline / Cloud Run:** `covid19-pipeline-sa@master-shore-475019-i7.iam.gserviceaccount.com`
- **Buckets que usaste:**
  - RAW: `gs://covid19-raw-master-shore-475019-i7/ministerio/`
  - ARTIFACTS (scripts/jobs): `gs://covid19-artifacts-master-shore-475019-i7/jobs/`
  - TRUSTED / Parquet: `gs://covid19-trusted-master-shore-475019-i7/parquet/`
  - REFINED (mencionado en cargas): `gs://covid19-refined-master-shore-475019-i7/` 
- **Workflow template:** `covid19-workflow`
- **Cloud Run service (API):** `covid-api`
  - URL desplegada observada en logs: `https://covid-api-1043357486945.us-central1.run.app`
  - Nombre alternativo / preview: `https://covid-api-zoreft7ikq-uc.a.run.app`
- **BigQuery:** dataset `covid_dataset`, tabla `daily_cases` → `master-shore-475019-i7.covid_dataset.daily_cases`
- **PySpark job script (ETL) que subí a artifacts:** `gs://covid19-artifacts-master-shore-475019-i7/jobs/etl_job.py`

---

## Información del proyecto (para replicar):
- **ID de proyecto GCP:** `<ID proyecto>`
- **Service account usada para pipeline / Cloud Run:** `covid19-pipeline-sa@<ID proyecto>.iam.gserviceaccount.com`
- **Buckets que usaste:**
  - RAW: `gs://covid19-raw-<ID proyecto>`
  - ARTIFACTS (scripts/jobs): `gs://covid19-artifacts-<ID proyecto>/jobs/`
  - TRUSTED / Parquet: `gs://covid19-trusted-<ID proyecto>/parquet/`
  - REFINED (mencionado en cargas): `gs://covid19-refined-<ID proyecto>/` 
- **Workflow template:** `covid19-workflow`
- **BigQuery:** dataset `covid_dataset`, tabla `daily_cases` → `<ID proyecto>.covid_dataset.daily_cases`
- **PySpark job script (ETL) que se sube a artifacts:** `gs://covid19-artifacts-<ID proyecto>/jobs/etl_job.py`

---

## Arquitectura general
```
        ┌─────────────────────────┐
        │    Cloud Scheduler      │  (cada día)
        └──────────────┬──────────┘
                       │ invoca
        ┌──────────────▼──────────┐
        │       Workflows         │
        │  (orquesta el pipeline) │
        └──────────────┬──────────┘
                       │
   ┌───────────────────▼───────────────────┐
   │      Cloud Function (ingesta)         │
   │    Descarga datos → RAW bucket        │
   └───────────────────┬───────────────────┘
                       │
        ┌──────────────▼─────────────┐
        │       ETL PySpark          │
        │ Lee RAW → limpia → TRUSTED │
        └──────────────┬─────────────┘
                       │
       ┌───────────────▼──────────────┐
       │            BigQuery          │
       │Tabla: covid_dataset.daily_cases
       └───────────────┬──────────────┘
                       │ consulta
          ┌────────────▼────────────┐
          │       Cloud Run API     │
          │  Endpoint: /daily_cases │
          └─────────────────────────┘

```

## Estructura del repositorio 
```
project3-covid/
│── gcp/
│   ├── cloud_functions/
│   │   ├── trigger_dataproc/  
│   │   |   └── main.py
│   │   |   └── requirements.txt
│   |   └── ingest_ministerio/  
│   │       └── main.py            # script para descargar raw del ministerio
│   │       └── requirements.txt
|   └── cloud_run/
|        └── api/
│            ├── app.py                 # Flask API
│            ├── requirements.txt
│            └── Dockerfile
│── jobs/
│   ├── etl_job.py             # PySpark ETL (subido a GCS artifacts)
│   └── analytics_job.py
│── sql/
│   └── init_data.sql
│── terraform/
│   ├── main.tf
|   ├── variables.tf
|   └── outputs.tf
│── README.md
```

---

## Comandos más útiles 

### Dataproc — crear workflow-managed cluster / template
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
Para añadir `etl_step`:
```bash
gcloud dataproc workflow-templates add-job pyspark gs://covid19-artifacts-<ID proyecto>/jobs/etl_job.py \
  --step-id=etl-step \
  --workflow-template=covid19-workflow \
  --region=us-central1
```

Para añadir `analytics_step`:
```bash
gcloud dataproc workflow-templates add-job pyspark gs://covid19-artifacts-<ID proyecto>/jobs/etl_job.py \
  --step-id=analytics-step \
  --workflow-template=covid19-workflow \
  --region=us-central1
```

### Instanciar workflow (ejecución completa que crea cluster ephemerally)
```bash
gcloud dataproc workflow-templates instantiate covid19-workflow --region=us-central1
```

### Subir imagen 
- Construir y subir con Cloud Build (necesitas Dockerfile en el dir o especificar `--tag` con contexto):
```bash
gcloud builds submit --tag gcr.io/<ID proyecto>/covid-api .
```
(si recibes `Dockerfile required when specifying --tag` asegúrate de ejecutar el comando desde la carpeta que contiene Dockerfile o pasar `--source .`).

- O desplegar desde fuente directo a Cloud Run (no necesitas construir imagen manualmente):
```bash
gcloud run deploy covid-api --source . --region=us-central1 --set-env-vars BQ_TABLE=<ID proyecto>.covid_dataset.daily_cases
```

### Permisos 
Dar permisos BigQuery al service account de Cloud Run:
```bash
gcloud projects add-iam-policy-binding <ID proyecto> \
  --member="serviceAccount:covid19-pipeline-sa@m<ID proyecto>.iam.gserviceaccount.com" \
  --role="roles/bigquery.dataViewer"

gcloud projects add-iam-policy-binding <ID proyecto> \
  --member="serviceAccount:covid19-pipeline-sa@<ID proyecto>.iam.gserviceaccount.com" \
  --role="roles/bigquery.user"
```

Dar storage admin (si tu pipeline necesita escribir en buckets):
```bash
gcloud projects add-iam-policy-binding <ID proyecto> \
  --member="serviceAccount:covid19-pipeline-sa@<ID proyecto>.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"
```

### Logs y depuración 
- Leer logs Cloud Run:
```bash
gcloud run services logs read covid-api --region=us-central1
```

- Ver driver output de jobs Dataproc:
```bash
gsutil cat gs://dataproc-staging-us-central1-1043357486945-ncd2wmd2/google-cloud-dataproc-metainfo/<run-id>/jobs/etl-step-*/driveroutput.000000000
```

---

## Cómo reconstruir la imagen y redeploy después de cambiar código 

1. Desde la carpeta `cloud_run/api` (donde está `Dockerfile` y `app.py`):

```bash
# construir y subir
gcloud builds submit --tag gcr.io/<ID proyecto>/covid-api .
# desplegar la imagen en Cloud Run
gcloud run deploy covid-api --image gcr.io/<ID proyecto>/covid-api --region=us-central1 --platform managed --set-env-vars BQ_TABLE=<ID proyecto>.covid_dataset.daily_cases --service-account=covid19-pipeline-sa@<ID proyecto>.iam.gserviceaccount.com
```

2. Alternativa (deploy desde fuente):
```bash
gcloud run deploy covid-api --source . --region=us-central1 --set-env-vars BQ_TABLE=<ID proyecto>.covid_dataset.daily_cases
```

3. Confirmar nuevo URL y probar:
```bash
gcloud run services describe covid-api --region=us-central1 --format="value(status.url)"
curl "https://<SERVICE_URL>/daily_cases?departamento=5"
```

---

## Comandos útiles finales 

- Instanciar workflow:  
  `gcloud dataproc workflow-templates instantiate covid19-workflow --region=us-central1`

- Revisar jobs Dataproc:  
  `gcloud dataproc jobs list --region=us-central1 --project=<ID proyecto>`

- Leer logs Cloud Run:  
  `gcloud run services logs read covid-api --region=us-central1`

- Rebuild + deploy image:  
  `gcloud builds submit --tag gcr.io/<ID proyecto>/covid-api .`  
  `gcloud run deploy covid-api --image gcr.io/<ID proyecto>/covid-api --region=us-central1 --set-env-vars BQ_TABLE=<ID proyecto>.covid_dataset.daily_cases`

- Probar API:  
  `curl "https://covid-api-1043357486945.us-central1.run.app/daily_cases?departamento=5"`

---


# Créditos
Valeria Cardona Urrea
Sistemas distribuidos
