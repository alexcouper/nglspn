export async function register() {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    const { NodeSDK } = await import("@opentelemetry/sdk-node");
    const { OTLPTraceExporter } = await import(
      "@opentelemetry/exporter-trace-otlp-http"
    );

    const endpoint = process.env.OTEL_EXPORTER_OTLP_ENDPOINT;
    if (!endpoint) {
      return;
    }

    const sdk = new NodeSDK({
      serviceName: process.env.OTEL_SERVICE_NAME || "web-ui",
      traceExporter: new OTLPTraceExporter({
        url: `${endpoint.replace(/\/v1\/traces$/, "")}/v1/traces`,
      }),
    });

    sdk.start();
  }
}
