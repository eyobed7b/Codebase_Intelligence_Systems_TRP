import os
import sys
import json
import tempfile

# ensure project root on path so `src` package is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from src.agents.hydrologist import Hydrologist


def write_file(tmpdir, name, content):
    path = os.path.join(tmpdir, name)
    with open(path, "w") as f:
        f.write(content)
    return path


def test_pandas_and_sqlalchemy(tmp_path):
    python_content = """
import pandas as pd
from sqlalchemy import create_engine

df = pd.read_csv('input.csv')
df.to_parquet('output.parquet')
engine = create_engine('sqlite://')
engine.execute('INSERT INTO tgt SELECT * FROM src')
"""
    write_file(tmp_path, "script.py", python_content)

    h = Hydrologist(str(tmp_path))
    h.analyze()
    results = h.get_results()
    ids = {n['id'] for n in results['nodes']}
    assert 'ds:input.csv' in ids
    assert 'ds:output.parquet' in ids
    # sql execution should have produced src and tgt datasets
    assert any('src' in n for n in ids)
    assert any('tgt' in n for n in ids)


def test_spark_patterns(tmp_path):
    python_content = """
from pyspark.sql import SparkSession
spark = SparkSession.builder.getOrCreate()
df = spark.read.csv('hdfs://data/table')
df.write.parquet('s3://bucket/out')
"""
    write_file(tmp_path, "spark.py", python_content)
    h = Hydrologist(str(tmp_path))
    h.analyze()
    results = h.get_results()
    ids = {n['id'] for n in results['nodes']}
    assert any('hdfs://data/table' in ds for ds in ids)
    assert any('s3://bucket/out' in ds for ds in ids)


def test_sql_file_and_cte(tmp_path):
    sql = """
WITH cte AS (SELECT * FROM base)
INSERT INTO target SELECT * FROM cte;
"""
    write_file(tmp_path, "query.sql", sql)
    h = Hydrologist(str(tmp_path))
    h.analyze()
    results = h.get_results()
    ids = {n['id'] for n in results['nodes']}
    assert 'ds:base' in ids
    assert 'ds:target' in ids


def test_notebook(tmp_path):
    nb = {
        "cells": [
            {"cell_type": "code", "source": ["import pandas as pd\n", "pd.read_csv('nb.csv')\n"]}
        ],
        "metadata": {},
        "nbformat": 4,
        "nbformat_minor": 2
    }
    path = write_file(tmp_path, "test.ipynb", json.dumps(nb))
    h = Hydrologist(str(tmp_path))
    h.analyze()
    results = h.get_results()
    ids = {n['id'] for n in results['nodes']}
    assert 'ds:nb.csv' in ids
