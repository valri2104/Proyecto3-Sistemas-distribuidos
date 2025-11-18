import os
import functions_framework
from google.cloud import dataproc_v1

PROJECT_ID = os.environ.get("PROJECT_ID")
REGION = os.environ.get("REGION", "us-central1")
TEMPLATE = os.environ.get("TEMPLATE_NAME", "covid19-workflow")


@functions_framework.http
def trigger_dataproc(request):
    client = dataproc_v1.WorkflowTemplateServiceClient(
        client_options={"api_endpoint": f"{REGION}-dataproc.googleapis.com:443"}
    )

    parent = f"projects/{PROJECT_ID}/regions/{REGION}"

    response = client.instantiate_workflow_template(
        name=f"{parent}/workflowTemplates/{TEMPLATE}"
    )

    return "Workflow instantiated", 200
