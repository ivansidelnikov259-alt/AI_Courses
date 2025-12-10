from __future__ import annotations

import io
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Импортируем функции из нашего ядра
from .core import (
    DatasetSummary,
    compute_quality_flags,
    missing_table,
    summarize_dataset,
    top_categories,
    correlation_matrix,
    flatten_summary_for_print,
)

app = FastAPI(
    title="EDA Quality API",
    description="HTTP-сервис для оценки качества датасетов на базе eda-cli",
    version="0.1.0",
)

# ========== МОДЕЛИ ДЛЯ ЗАПРОСОВ/ОТВЕТОВ ==========

class QualityRequest(BaseModel):
    """Модель запроса для эндпоинта /quality"""
    n_rows: int
    n_cols: int
    max_missing_share: float
    has_constant_columns: bool = False
    has_high_cardinality_categoricals: bool = False
    has_suspicious_id_duplicates: bool = False
    has_many_zero_values: bool = False


class QualityResponse(BaseModel):
    """Модель ответа для эндпоинтов качества"""
    ok_for_model: bool
    quality_score: float
    latency_ms: float
    flags: Dict[str, Any]
    request_id: str


class QualityFlagsResponse(BaseModel):
    """Модель ответа для эндпоинта /quality-flags-from-csv"""
    flags: Dict[str, Any]
    summary_stats: Dict[str, Any]
    latency_ms: float
    request_id: str


class HealthResponse(BaseModel):
    """Модель ответа для эндпоинта /health"""
    status: str
    version: str
    timestamp: float


# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

def _read_csv_from_upload(file: UploadFile) -> pd.DataFrame:
    """Читает CSV из загруженного файла"""
    try:
        contents = file.file.read()
        text = contents.decode("utf-8")
        return pd.read_csv(io.StringIO(text))
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Не удалось прочитать CSV: {str(e)}"
        )
    finally:
        file.file.close()


def _compute_quality_for_df(df: pd.DataFrame) -> Dict[str, Any]:
    """Вычисляет качество для DataFrame"""
    start_time = time.time()
    
    summary = summarize_dataset(df)
    missing_df = missing_table(df)
    flags = compute_quality_flags(summary, missing_df, df)
    
    latency_ms = (time.time() - start_time) * 1000
    
    return {
        "flags": flags,
        "summary": summary,
        "missing_df": missing_df,
        "latency_ms": latency_ms,
    }


# ========== СУЩЕСТВУЮЩИЕ ЭНДПОИНТЫ (из семинара) ==========

@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Проверка здоровья сервиса"""
    return HealthResponse(
        status="ok",
        version="0.1.0",
        timestamp=time.time(),
    )


@app.post("/quality", response_model=QualityResponse)
async def quality(request: QualityRequest) -> QualityResponse:
    """
    Оценка качества на основе параметров
    
    Использует эвристики из HW03 для предсказания,
    подходит ли датасет для обучения модели.
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    # В реальном проекте здесь может быть ML-модель
    # Сейчас используем простые правила на основе эвристик HW03
    
    score = 1.0
    
    # Эвристики из HW03
    if request.n_rows < 100:
        score -= 0.2
    if request.n_cols > 100:
        score -= 0.1
    if request.max_missing_share > 0.5:
        score -= 0.3
    if request.has_constant_columns:
        score -= 0.1
    if request.has_high_cardinality_categoricals:
        score -= 0.1
    if request.has_suspicious_id_duplicates:
        score -= 0.15
    if request.has_many_zero_values:
        score -= 0.1
    
    score = max(0.0, min(1.0, score))
    
    ok_for_model = score > 0.6
    
    flags = {
        "too_few_rows": request.n_rows < 100,
        "too_many_columns": request.n_cols > 100,
        "too_many_missing": request.max_missing_share > 0.5,
        "has_constant_columns": request.has_constant_columns,
        "has_high_cardinality_categoricals": request.has_high_cardinality_categoricals,
        "has_suspicious_id_duplicates": request.has_suspicious_id_duplicates,
        "has_many_zero_values": request.has_many_zero_values,
        "max_missing_share": request.max_missing_share,
    }
    
    latency_ms = (time.time() - start_time) * 1000
    
    return QualityResponse(
        ok_for_model=ok_for_model,
        quality_score=score,
        latency_ms=latency_ms,
        flags=flags,
        request_id=request_id,
    )


@app.post("/quality-from-csv", response_model=QualityResponse)
async def quality_from_csv(
    file: UploadFile = File(..., description="CSV файл для анализа"),
    sep: str = Form(","),
    encoding: str = Form("utf-8"),
) -> QualityResponse:
    """
    Оценка качества датасета из CSV-файла
    
    Использует функции из core.py для вычисления
    эвристик качества, добавленных в HW03.
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    try:
        # Читаем CSV
        df = _read_csv_from_upload(file)
        
        if df.empty:
            raise HTTPException(
                status_code=400,
                detail="CSV файл пустой"
            )
        
        # Вычисляем качество
        result = _compute_quality_for_df(df)
        flags = result["flags"]
        summary = result["summary"]
        
        # Определяем, подходит ли для модели
        ok_for_model = flags["quality_score"] > 0.6
        
        # Формируем полный набор флагов для ответа
        full_flags = {
            "too_few_rows": flags["too_few_rows"],
            "too_many_columns": flags["too_many_columns"],
            "too_many_missing": flags["too_many_missing"],
            "has_constant_columns": flags["has_constant_columns"],
            "has_high_cardinality_categoricals": flags["has_high_cardinality_categoricals"],
            "has_suspicious_id_duplicates": flags["has_suspicious_id_duplicates"],
            "has_many_zero_values": flags["has_many_zero_values"],
            "max_missing_share": flags["max_missing_share"],
            "quality_score": flags["quality_score"],
        }
        
        return QualityResponse(
            ok_for_model=ok_for_model,
            quality_score=flags["quality_score"],
            latency_ms=result["latency_ms"],
            flags=full_flags,
            request_id=request_id,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Внутренняя ошибка сервера: {str(e)}"
        )


# ========== НОВЫЙ ЭНДПОИНТ ДЛЯ HW04 ==========

@app.post("/quality-flags-from-csv", response_model=QualityFlagsResponse)
async def quality_flags_from_csv(
    file: UploadFile = File(..., description="CSV файл для анализа"),
    sep: str = Form(","),
    encoding: str = Form("utf-8"),
    include_summary_stats: bool = Form(True, description="Включать статистику датасета"),
) -> QualityFlagsResponse:
    """
    Возвращает полный набор флагов качества из CSV файла
    
    Этот эндпоинт специально создан для HW04 и использует
    все эвристики качества, добавленные в HW03.
    
    В отличие от /quality-from-csv, возвращает ТОЛЬКО флаги
    без решения о пригодности для модели.
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    try:
        # Читаем CSV
        df = _read_csv_from_upload(file)
        
        if df.empty:
            raise HTTPException(
                status_code=400,
                detail="CSV файл пустой"
            )
        
        # Вычисляем качество
        result = _compute_quality_for_df(df)
        flags = result["flags"]
        summary = result["summary"]
        missing_df = result["missing_df"]
        
        # Формируем полный набор флагов для ответа
        full_flags = {
            # Основные флаги из исходной реализации
            "too_few_rows": flags["too_few_rows"],
            "too_many_columns": flags["too_many_columns"],
            "too_many_missing": flags["too_many_missing"],
            
            # ========== НОВЫЕ ФЛАГИ ИЗ HW03 ==========
            "has_constant_columns": flags["has_constant_columns"],
            "has_high_cardinality_categoricals": flags["has_high_cardinality_categoricals"],
            "has_suspicious_id_duplicates": flags["has_suspicious_id_duplicates"],
            "has_many_zero_values": flags["has_many_zero_values"],
            
            # Дополнительные метрики
            "max_missing_share": flags["max_missing_share"],
            "quality_score": flags["quality_score"],
        }
        
        # Статистика датасета
        summary_stats = {}
        if include_summary_stats:
            summary_stats = {
                "n_rows": summary.n_rows,
                "n_cols": summary.n_cols,
                "numeric_columns": sum(1 for c in summary.columns if c.is_numeric),
                "categorical_columns": sum(1 for c in summary.columns if not c.is_numeric),
                "total_missing": missing_df["missing_count"].sum() if not missing_df.empty else 0,
                "columns_with_missing": (missing_df["missing_count"] > 0).sum() if not missing_df.empty else 0,
            }
        
        latency_ms = (time.time() - start_time) * 1000
        
        return QualityFlagsResponse(
            flags=full_flags,
            summary_stats=summary_stats,
            latency_ms=latency_ms,
            request_id=request_id,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Внутренняя ошибка сервера: {str(e)}"
        )


# ========== ДОПОЛНИТЕЛЬНЫЙ ЭНДПОИНТ (опционально) ==========

@app.post("/dataset-summary-from-csv")
async def dataset_summary_from_csv(
    file: UploadFile = File(..., description="CSV файл для анализа"),
    sep: str = Form(","),
    encoding: str = Form("utf-8"),
    top_k_categories: int = Form(5, description="Количество топ-категорий"),
):
    """
    Расширенная сводка по датасету из CSV
    
    Возвращает детальную информацию:
    - общую статистику
    - пропуски по колонкам
    - топ-категории
    - корреляционную матрицу
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    try:
        # Читаем CSV
        df = _read_csv_from_upload(file)
        
        if df.empty:
            raise HTTPException(
                status_code=400,
                detail="CSV файл пустой"
            )
        
        # Вычисляем различные метрики
        summary = summarize_dataset(df)
        missing_df = missing_table(df)
        flags = compute_quality_flags(summary, missing_df, df)
        top_cats = top_categories(df, top_k=top_k_categories)
        corr_matrix = correlation_matrix(df)
        
        # Форматируем результаты
        summary_list = []
        for col in summary.columns:
            summary_list.append({
                "name": col.name,
                "dtype": col.dtype,
                "non_null": col.non_null,
                "missing": col.missing,
                "missing_share": col.missing_share,
                "unique": col.unique,
                "is_numeric": col.is_numeric,
            })
        
        # Форматируем пропуски
        missing_list = []
        if not missing_df.empty:
            for idx, row in missing_df.iterrows():
                missing_list.append({
                    "column": idx,
                    "missing_count": int(row["missing_count"]),
                    "missing_share": float(row["missing_share"]),
                })
        
        # Форматируем топ-категории
        top_cats_formatted = {}
        for col_name, table in top_cats.items():
            top_cats_formatted[col_name] = table.to_dict(orient="records")
        
        # Форматируем корреляционную матрицу
        corr_formatted = {}
        if not corr_matrix.empty:
            corr_formatted = {
                "columns": corr_matrix.columns.tolist(),
                "matrix": corr_matrix.values.tolist(),
            }
        
        latency_ms = (time.time() - start_time) * 1000
        
        return JSONResponse({
            "request_id": request_id,
            "latency_ms": latency_ms,
            "summary": {
                "n_rows": summary.n_rows,
                "n_cols": summary.n_cols,
                "columns": summary_list,
            },
            "missing": missing_list,
            "top_categories": top_cats_formatted,
            "correlation": corr_formatted,
            "quality_flags": flags,
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Внутренняя ошибка сервера: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)