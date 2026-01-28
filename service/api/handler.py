"""API Lambda handler using AWS Lambda Powertools."""

from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import APIGatewayHttpResolver
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.utilities.typing import LambdaContext

from service.api.routes import expenses, report

logger = Logger()
tracer = Tracer()
app = APIGatewayHttpResolver()

# Register routes
app.include_router(expenses.router, prefix='/expense')
app.include_router(report.router, prefix='/report')


@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_HTTP)
@tracer.capture_lambda_handler
def handler(event: dict, context: LambdaContext) -> dict:
    """Lambda handler entry point."""
    return app.resolve(event, context)
