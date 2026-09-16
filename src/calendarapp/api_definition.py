import java

OpenAPIDefinition = java.type("io.swagger.v3.oas.annotations.OpenAPIDefinition")
Info = java.type("io.swagger.v3.oas.annotations.info.Info")


@OpenAPIDefinition(
    info=Info(
        title="calendar",
        version="0.1.0",
        description="Pyronaut Calendar API: events, categories, agenda and iCalendar export",
    )
)
class ApiDefinition:
    """Carries the OpenAPI metadata; Swagger UI is served at /swagger-ui/index.html."""
