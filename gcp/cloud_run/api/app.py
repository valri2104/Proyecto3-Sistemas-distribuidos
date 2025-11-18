from flask import Flask, jsonify, request
from google.cloud import bigquery
import os

app = Flask(__name__)
client = bigquery.Client()

DATASET_TABLE = os.environ.get("BQ_TABLE", "<PROJECT_ID>.covid_dataset.daily_cases")


@app.route("/daily_cases")
def daily_cases():
    dept = request.args.get("departamento")
    sql = f"SELECT * FROM `{DATASET_TABLE}`"

    if dept:
        sql += f" WHERE LOWER(departamento_nom) = LOWER('{dept}')"

    sql += " ORDER BY fecha_reporte_web DESC LIMIT 1000"

    query_job = client.query(sql)
    rows = [dict(row) for row in query_job]
    return jsonify(rows)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
