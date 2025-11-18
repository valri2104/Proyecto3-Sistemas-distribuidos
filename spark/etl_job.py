from pyspark.sql import SparkSession
from pyspark.sql.functions import to_timestamp, col


def main():
    spark = SparkSession.builder.appName("covid-etl").getOrCreate()

    # Rutas (reemplaza <PREFIX> y <PROJECT_ID> si no usas variables)
    raw_path = "gs://covid19-raw-master-shore-475019-i7/ministerio/*"
    trusted_path = "gs://covid19-trusted-master-shore-475019-i7/parquet/"

    # Lee JSON/CSV del ministerio
    df = spark.read.option("multiline", "true").json(raw_path)  # usa .csv si es CSV

    # Ejemplo limpieza:
    if "fecha_reporte" in df.columns:
        df = df.withColumn("fecha_reporte", to_timestamp(col("fecha_reporte")))

    # (Opcional) Leer datos complementarios de Cloud SQL via JDBC
    # jdbc_url = "jdbc:postgresql://<CLOUD_SQL_IP>:5432/covid_aux"
    # props = {"user":"<DB_USER>", "password":"<DB_PWD>", "driver":"org.postgresql.Driver"}
    # df_aux = spark.read.jdbc(url=jdbc_url, table="tabla_complementaria", properties=props)
    # df = df.join(df_aux, on=["departamento_codigo"], how="left")

    # Escribir parquet a trusted
    df.write.mode("overwrite").parquet(trusted_path)

    spark.stop()


if __name__ == "__main__":
    main()
