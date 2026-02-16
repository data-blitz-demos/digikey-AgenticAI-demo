from __future__ import annotations

"""
Property of Data-Blitz Inc.
Author: Paul Harvener

Pydantic request/response models used by the demo APIs.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class QueryIntent(BaseModel):
    keywords: str = Field(..., description="Search phrase to match products")
    limit: int = Field(default=8, ge=1, le=20)
    in_stock_only: bool = True
    min_quantity: Optional[int] = Field(default=None, ge=0)
    max_unit_price: Optional[float] = Field(default=None, gt=0)
    sort_preference: Literal["relevance", "price_low", "stock_high"] = "relevance"


class ProductResult(BaseModel):
    id: str
    manufacturer: str
    manufacturer_part_number: str
    name: str
    description: str
    category: str
    unit_price: float
    quantity_available: int
    product_url: str
    datasheet_url: str
    recommendation_score: float
    fit_reason: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=2, max_length=600)


class ChatResponse(BaseModel):
    mode: str
    intent: QueryIntent
    products: list[ProductResult]
    answer: str
    warning: Optional[str] = None


class DirectSearchRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=250)
    limit: int = Field(default=12, ge=1, le=25)


class DirectSearchProduct(BaseModel):
    id: Optional[str] = None
    manufacturer: str
    manufacturer_part_number: str
    name: str
    description: str
    category: str
    unit_price: Optional[float] = None
    quantity_available: Optional[int] = None
    product_url: Optional[str] = None
    datasheet_url: Optional[str] = None
    recommendation_score: Optional[float] = None
    fit_reason: Optional[str] = None


class DirectSearchResponse(BaseModel):
    source: str
    query: str
    products: list[DirectSearchProduct]
    warning: Optional[str] = None
