from __future__ import annotations

"""
Property of Data-Blitz Inc.
Author: Paul Harvener

API entrypoint for the DigiKey AI demo web application.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.ai_assistant import QueryInterpreter
from app.catalog import CatalogService
from app.models import (
    ChatRequest,
    ChatResponse,
    DirectSearchProduct,
    DirectSearchRequest,
    DirectSearchResponse,
    ProductResult,
    QueryIntent,
)

load_dotenv()

catalog = CatalogService()
interpreter = QueryInterpreter()


# Args:
#   _: FastAPI
#     The application instance injected by FastAPI lifespan handling.
# Returns:
#   async context manager
#     Startup/shutdown lifecycle manager that initializes catalog state.
@asynccontextmanager
async def lifespan(_: FastAPI):
    startup_warning = catalog.initialize()
    app.state.startup_warning = startup_warning
    yield


app = FastAPI(title="DigiKey AI Equipment Advisor", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# Args:
#   item: DirectSearchProduct
#     Product payload from direct search endpoint flow.
#   rank: int
#     Zero-based position of the result in returned list.
# Returns:
#   ProductResult
#     Normalized ProductResult used by chat response rendering/summarization.
def _direct_to_product_result(item: DirectSearchProduct, rank: int) -> ProductResult:
    return ProductResult(
        id=item.id or item.manufacturer_part_number or f"product-{rank}",
        manufacturer=item.manufacturer,
        manufacturer_part_number=item.manufacturer_part_number,
        name=item.name,
        description=item.description,
        category=item.category,
        unit_price=float(item.unit_price) if item.unit_price is not None else 0.0,
        quantity_available=int(item.quantity_available) if item.quantity_available is not None else 0,
        product_url=item.product_url or "",
        datasheet_url=item.datasheet_url or "",
        recommendation_score=float(item.recommendation_score) if item.recommendation_score is not None else 0.75,
        fit_reason=item.fit_reason or "Result sourced from mock catalog.",
    )


# Args:
#   query: str
#     Query phrase used for mock/elasticsearch search.
#   limit: int
#     Maximum results requested.
# Returns:
#   tuple[list[DirectSearchProduct], str | None]
#     Mock catalog products normalized into DirectSearchProduct and optional warning.
def _query_mock_products(query: str, limit: int) -> tuple[list[DirectSearchProduct], str | None]:
    intent = QueryIntent(
        keywords=query,
        limit=limit,
        in_stock_only=False,
        min_quantity=None,
        max_unit_price=None,
        sort_preference="relevance",
    )
    fallback_products, fallback_warning = catalog.search(intent)
    mapped = [
        DirectSearchProduct(
            id=product.id,
            manufacturer=product.manufacturer,
            manufacturer_part_number=product.manufacturer_part_number,
            name=product.name,
            description=product.description,
            category=product.category,
            unit_price=product.unit_price,
            quantity_available=product.quantity_available,
            product_url=product.product_url,
            datasheet_url=product.datasheet_url,
            recommendation_score=product.recommendation_score,
            fit_reason=product.fit_reason,
        )
        for product in fallback_products
    ]
    return mapped, fallback_warning


# Args:
#   products: list[ProductResult]
#     Candidate results to filter.
#   intent: QueryIntent
#     Constraint payload extracted from user request.
# Returns:
#   list[ProductResult]
#     Filtered products honoring stock/quantity/price constraints.
def _apply_intent_constraints(products: list[ProductResult], intent: QueryIntent) -> list[ProductResult]:
    filtered = products
    if intent.in_stock_only:
        filtered = [p for p in filtered if (p.quantity_available or 0) > 0]
    if intent.min_quantity is not None:
        filtered = [p for p in filtered if (p.quantity_available or 0) >= intent.min_quantity]
    if intent.max_unit_price is not None:
        filtered = [p for p in filtered if (p.unit_price or 0.0) <= intent.max_unit_price]
    return filtered[: intent.limit]


# Args:
#   None
# Returns:
#   FileResponse
#     The static HTML page for the demo UI.
@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


# Args:
#   None
# Returns:
#   dict[str, str]
#     Health payload including service status and active catalog mode.
@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "mode": catalog.mode}


# Args:
#   request: ChatRequest
#     Natural-language assistant request payload from the UI.
# Returns:
#   ChatResponse
#     Interpreted intent, ranked products, summary answer, and optional warnings.
# Notes:
#   This endpoint runs AI-assisted intent parsing and queries the mock catalog.
@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    intent = interpreter.interpret(request.message)
    direct_products, query_warning = _query_mock_products(
        query=intent.keywords,
        limit=intent.limit,
    )
    source_label = "mock_catalog"
    products = [_direct_to_product_result(item, idx) for idx, item in enumerate(direct_products)]
    products = _apply_intent_constraints(products, intent)
    answer = interpreter.summarize(intent, products, source_label)

    warning_parts = []
    if app.state.startup_warning:
        warning_parts.append(app.state.startup_warning)
    if query_warning:
        warning_parts.append(query_warning)

    return ChatResponse(
        mode=source_label,
        intent=intent,
        products=products,
        answer=answer,
        warning=" ".join(warning_parts) if warning_parts else None,
    )


# Args:
#   request: DirectSearchRequest
#     Header search query and requested result limit.
# Returns:
#   DirectSearchResponse
#     Mock-catalog search results with optional warning context.
# Notes:
#   This endpoint powers the top header search bar for direct catalog lookup.
@app.post("/api/digikey-search", response_model=DirectSearchResponse)
def digikey_search(request: DirectSearchRequest) -> DirectSearchResponse:
    products, warning = _query_mock_products(
        query=request.query,
        limit=request.limit,
    )
    return DirectSearchResponse(
        source="mock_catalog",
        query=request.query,
        products=products,
        warning=warning,
    )
