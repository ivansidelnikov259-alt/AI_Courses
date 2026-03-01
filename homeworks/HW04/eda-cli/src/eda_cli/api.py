# Файл: src/eda_cli/api.py
from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Dict, Any, Optional

import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

# === ИМПОРТЫ ИЗ НАШЕГО ПРОЕКТА HW03 ===
from .core import (
    summarize_dataset,
    missing_table,
    compute_quality_flags,
    DatasetSummary,
)
# === КОНЕЦ ИМПОРТОВ ===

app = FastAPI(
    title="EDA Quality Service",
    description="HTTP-сервис для оценки качества датасетов поверх eda-cli",
    version="0.1.0",
)

# === БАЗОВЫЙ ЭНДПОИНТ ИЗ СЕМИНАРА ===
@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Проверка работоспособности сервиса."""
    return {
        "status": "healthy",
        "service": "eda-quality-service",
        "version": "0.1.0",
    }


@app.post("/quality")
async def quality_check(data: Dict[str, Any]) -> Dict[str, Any]:
    """Оценка качества датасета на основе переданных метрик."""
    start_time = time.time()
    
    # Извлекаем параметры (пример из семинара)
    n_rows = data.get("n_rows", 0)
    max_missing_share = data.get("max_missing_share", 0.0)
    has_constant_columns = data.get("has_constant_columns", False)
    
    # Простейшая логика предсказания (можно доработать)
    ok_for_model = (
        n_rows > 100 and 
        max_missing_share < 0.3 and 
        not has_constant_columns
    )
    
    # Простой расчет качества (пример)
    quality_score = 1.0
    if max_missing_share > 0.5:
        quality_score -= 0.3
    if has_constant_columns:
        quality_score -= 0.2
    if n_rows < 100:
        quality_score -= 0.1
    quality_score = max(0.0, min(1.0, quality_score))
    
    latency_ms = (time.time() - start_time) * 1000
    
    return {
        "ok_for_model": ok_for_model,
        "quality_score": round(quality_score, 3),
        "latency_ms": round(latency_ms, 2),
        "flags": {
            "n_rows_sufficient": n_rows >= 100,
            "missing_acceptable": max_missing_share < 0.3,
            "no_constant_columns": not has_constant_columns,
        }
    }


@app.post("/quality-from-csv")
async def quality_from_csv(
    file: UploadFile = File(...),
    min_rows: int = 50,
    max_missing_threshold: float = 0.5,
) -> Dict[str, Any]:
    """Оценка качества датасета из CSV-файла."""
    start_time = time.time()
    
    # Проверка расширения файла
    if not file.filename or not file.filename.lower().endswith('.csv'):
        raise HTTPException(
            status_code=400,
            detail="Файл должен быть в формате CSV"
        )
    
    try:
        # Чтение CSV
        contents = await file.read()
        df = pd.read_csv(pd.io.common.BytesIO(contents))
        
        # Проверка на пустой датасет
        if df.empty:
            raise HTTPException(
                status_code=400,
                detail="CSV файл пуст или не содержит данных"
            )
        
        # Используем логику из нашего проекта HW03
        summary: DatasetSummary = summarize_dataset(df)
        missing_df = missing_table(df)
        flags = compute_quality_flags(summary, missing_df)
        
        # Определяем, подходит ли датасет для модели
        ok_for_model = (
            summary.n_rows >= min_rows and
            flags.get("max_missing_share", 1.0) < max_missing_threshold and
            not flags.get("too_many_missing", True) and
            not flags.get("has_constant_columns", False)  # Используем нашу новую эвристику
        )
        
        latency_ms = (time.time() - start_time) * 1000
        
        return {
            "ok_for_model": ok_for_model,
            "quality_score": round(flags.get("quality_score", 0.0), 3),
            "latency_ms": round(latency_ms, 2),
            "dataset_info": {
                "n_rows": summary.n_rows,
                "n_cols": summary.n_cols,
            },
            "flags": flags,  # Включаем ВСЕ флаги из HW03
        }
        
    except pd.errors.EmptyDataError:
        raise HTTPException(
            status_code=400,
            detail="CSV файл пуст или не содержит данных"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка обработки файла: {str(e)}"
        )
# === КОНЕЦ БАЗОВЫХ ЭНДПОИНТОВ ===


# === НОВЫЙ ЭНДПОИНТ ДЛЯ HW04 (ОБЯЗАТЕЛЬНЫЙ) ===
@app.post("/quality-flags-from-csv")
async def quality_flags_from_csv(
    file: UploadFile = File(...),
    high_cardinality_threshold: int = 50,
    zero_values_threshold: float = 0.3,
) -> Dict[str, Any]:
    """
    Возвращает полный набор флагов качества из CSV-файла.
    Включает все эвристики, добавленные в HW03.
    """
    start_time = time.time()
    
    # Проверка файла
    if not file.filename or not file.filename.lower().endswith('.csv'):
        raise HTTPException(
            status_code=400,
            detail="Файл должен быть в формате CSV"
        )
    
    try:
        # Чтение CSV
        contents = await file.read()
        df = pd.read_csv(pd.io.common.BytesIO(contents))
        
        if df.empty:
            raise HTTPException(
                status_code=400,
                detail="CSV файл пуст"
            )
        
        # Используем логику из HW03
        summary: DatasetSummary = summarize_dataset(df)
        missing_df = missing_table(df)
        
        # === ВЫЗЫВАЕМ НАШУ ФУНКЦИЮ ИЗ HW03 ===
        flags = compute_quality_flags(summary, missing_df)
        # === КОНЕЦ ВЫЗОВА ===
        
        # Дополнительная проверка на дубликаты ID (если есть колонка 'user_id' или 'id')
        has_id_duplicates = False
        if 'user_id' in df.columns:
            has_id_duplicates = df['user_id'].duplicated().any()
        elif 'id' in df.columns:
            has_id_duplicates = df['id'].duplicated().any()
        
        # Добавляем эту проверку в флаги
        flags["has_suspicious_id_duplicates"] = has_id_duplicates
        
        # Проверка на много нулей в числовых колонках
        has_many_zeros = False
        numeric_cols = df.select_dtypes(include='number').columns
        for col in numeric_cols:
            zero_share = (df[col] == 0).sum() / len(df)
            if zero_share > zero_values_threshold:
                has_many_zeros = True
                break
        
        flags["has_many_zero_values"] = has_many_zeros
        flags["zero_values_threshold"] = zero_values_threshold
        flags["high_cardinality_threshold"] = high_cardinality_threshold
        
        latency_ms = (time.time() - start_time) * 1000
        
        return {
            "flags": flags,  # Все флаги из compute_quality_flags + дополнительные
            "additional_flags": {
                "has_suspicious_id_duplicates": has_id_duplicates,
                "has_many_zero_values": has_many_zeros,
                "zero_values_threshold": zero_values_threshold,
                "high_cardinality_threshold": high_cardinality_threshold,
            },
            "latency_ms": round(latency_ms, 2),
            "dataset_info": {
                "n_rows": summary.n_rows,
                "n_cols": summary.n_cols,
                "file_name": file.filename,
            }
        }
        
    except pd.errors.EmptyDataError:
        raise HTTPException(status_code=400, detail="CSV файл пуст")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка обработки файла: {str(e)}"
        )
# === КОНЕЦ НОВОГО ЭНДПОИНТА ===


# === ДОПОЛНИТЕЛЬНЫЙ ЭНДПОИНТ (ОПЦИОНАЛЬНО) ===
@app.post("/report-from-csv")
async def report_from_csv(
    file: UploadFile = File(...),
    max_hist_columns: int = 6,
    top_k_categories: int = 5,
    out_dir: str = "api_reports",
) -> Dict[str, Any]:
    """
    Генерирует полный EDA-отчёт из CSV-файла.
    Использует параметры из HW03.
    """
    try:
        # Чтение CSV
        contents = await file.read()
        df = pd.read_csv(pd.io.common.BytesIO(contents))
        
        if df.empty:
            raise HTTPException(status_code=400, detail="CSV файл пуст")
        
        # Создаем директорию для отчёта
        report_dir = Path(out_dir) / f"report_{uuid.uuid4().hex[:8]}"
        report_dir.mkdir(parents=True, exist_ok=True)
        
        # Сохраняем CSV для обработки CLI
        temp_csv = report_dir / "temp_data.csv"
        df.to_csv(temp_csv, index=False)
        
        # Здесь можно было бы вызвать CLI команду,
        # но для простоты делаем базовую обработку
        
        summary = summarize_dataset(df)
        missing_df = missing_table(df)
        flags = compute_quality_flags(summary, missing_df)
        
        # Сохраняем базовую информацию
        import json
        report_info = {
            "dataset_info": {
                "n_rows": summary.n_rows,
                "n_cols": summary.n_cols,
                "file_name": file.filename,
            },
            "quality_flags": flags,
            "report_settings": {
                "max_hist_columns": max_hist_columns,
                "top_k_categories": top_k_categories,
                "out_dir": str(report_dir),
            },
            "report_files": [
                str(report_dir / "dataset_info.json"),
                str(report_dir / "temp_data.csv"),
            ]
        }
        
        # Сохраняем JSON с информацией
        with open(report_dir / "dataset_info.json", "w") as f:
            json.dump(report_info, f, indent=2, default=str)
        
        # Удаляем временный CSV
        temp_csv.unlink()
        
        return {
            "status": "report_generated",
            "report_dir": str(report_dir),
            "message": f"Отчёт сгенерирован в {report_dir}",
            "dataset_info": report_info["dataset_info"],
            "quality_score": flags.get("quality_score", 0.0),
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка генерации отчёта: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)