from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from doctorly.api.routes.health import router as health_router
from doctorly.api.routes.appointments import router as appointments_router
from doctorly.api.routes.auth import router as auth_router
from doctorly.api.routes.doctors import router as doctors_router
from doctorly.api.routes.staff import router as staff_router
from doctorly.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    provider = TracerProvider(
        resource=Resource.create({"service.name": settings.otel_service_name})
    )
    if settings.otel_exporter_otlp_endpoint:
        provider.add_span_processor(
            BatchSpanProcessor(
                OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint)
            )
        )
    trace.set_tracer_provider(provider)

    app = FastAPI(title="Doctorly API")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(doctors_router)
    app.include_router(appointments_router)
    app.include_router(staff_router)
    FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
    return app


app = create_app()
