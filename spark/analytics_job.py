from pyspark.sql import SparkSession
from pyspark.sql.functions import col


def main():
    spark = SparkSession.builder.appName("covid-analytics").getOrCreate()

    trusted_path = "gs://covid19-trusted-master-shore-475019-i7/parquet/"
    refined_path = "gs://covid19-refined-master-shore-475019-i7/daily_cases/"

    df = spark.read.parquet(trusted_path)

    # ejemplo: agregación diaria por departamento
    if (
        "nuevos" in df.columns
        and "departamento" in df.columns
        and "fecha_reporte" in df.columns
    ):
        agg = (
            df.groupBy("departamento", "fecha_reporte")
            .sum("nuevos")
            .withColumnRenamed("sum(nuevos)", "nuevos_diarios")
        )
        agg.write.mode("overwrite").parquet(refined_path)
    else:
        df.write.mode("overwrite").parquet(refined_path)

    spark.stop()


if __name__ == "__main__":
    main()
