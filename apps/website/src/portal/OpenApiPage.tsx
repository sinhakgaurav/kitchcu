import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { BrandNavMark } from "../components/BrandNavMark";
import { APP_POSITIONING_SHORT } from "../shared/brand";

declare global {
  interface Window {
    SwaggerUIBundle?: (options: Record<string, unknown>) => { destroy?: () => void };
  }
}

const OPENAPI_URL = "/openapi.json";
const SWAGGER_UI_CSS = "https://unpkg.com/swagger-ui-dist@5.17.14/swagger-ui.css";
const SWAGGER_UI_BUNDLE = "https://unpkg.com/swagger-ui-dist@5.17.14/swagger-ui-bundle.js";

function loadStylesheet(href: string): Promise<void> {
  return new Promise((resolve, reject) => {
    if (document.querySelector(`link[href="${href}"]`)) {
      resolve();
      return;
    }
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = href;
    link.onload = () => resolve();
    link.onerror = () => reject(new Error(`Failed to load ${href}`));
    document.head.appendChild(link);
  });
}

function loadScript(src: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const existing = document.querySelector(`script[src="${src}"]`);
    if (existing && window.SwaggerUIBundle) {
      resolve();
      return;
    }
    const script = document.createElement("script");
    script.src = src;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error(`Failed to load ${src}`));
    document.body.appendChild(script);
  });
}

export function OpenApiPage() {
  const hostRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [pathCount, setPathCount] = useState<number | null>(null);

  useEffect(() => {
    let destroyed = false;
    let uiInstance: { destroy?: () => void } | null = null;

    async function boot() {
      setLoading(true);
      setError(null);
      try {
        const meta = await fetch(OPENAPI_URL);
        if (!meta.ok) {
          throw new Error(
            `OpenAPI schema unavailable (${meta.status}). Start the Docker stack so the gateway can aggregate service specs.`,
          );
        }
        const schema = await meta.json();
        if (destroyed) return;
        // Swagger OAuth resolves tokenUrl against servers[0]. A cached
        // http:// host from the gateway (TLS terminator) is mixed content.
        schema.servers = [{ url: window.location.origin, description: "same origin" }];
        setPathCount(Object.keys(schema.paths || {}).length);

        await loadStylesheet(SWAGGER_UI_CSS);
        await loadScript(SWAGGER_UI_BUNDLE);
        if (destroyed || !hostRef.current || !window.SwaggerUIBundle) {
          throw new Error("Swagger UI failed to initialize");
        }
        hostRef.current.innerHTML = "";
        const mount = document.createElement("div");
        mount.id = "swagger-ui-mount";
        hostRef.current.appendChild(mount);
        uiInstance = window.SwaggerUIBundle({
          spec: schema,
          dom_id: "#swagger-ui-mount",
          deepLinking: true,
          persistAuthorization: true,
          displayRequestDuration: true,
          tryItOutEnabled: true,
          filter: true,
          docExpansion: "list",
          defaultModelsExpandDepth: 1,
          // Keep in sync with services/gateway/app/openapi_aggregate.py
          requestInterceptor: (req: { url?: string; method?: string; headers?: Record<string, string> }) => {
            try {
              const origin = window.location.origin;
              let raw = String(req.url || "");
              if (raw.startsWith("//")) raw = `${window.location.protocol}${raw}`;
              const parsed = new URL(raw, origin);
              let path = `${parsed.pathname}${parsed.search}${parsed.hash}`;
              if (parsed.hostname === "api" && path.startsWith("/v1/")) path = `/api${path}`;
              if (path.startsWith("/api/") || path.startsWith("/openapi")) {
                req.url = `${origin}${path}`;
              } else if (parsed.protocol === "http:" && origin.startsWith("https://")) {
                parsed.protocol = "https:";
                req.url = parsed.href;
              }
              if (String(req.method || "GET").toUpperCase() === "GET" && req.headers) {
                delete req.headers["Content-Type"];
                delete req.headers["content-type"];
              }
            } catch {
              /* keep original url */
            }
            return req;
          },
        });
        document.addEventListener(
          "click",
          (event) => {
            const target = event.target;
            if (!(target instanceof Element) || !target.closest("button.execute")) {
              return;
            }
            window.setTimeout(() => {
              document
                .querySelector(".live-responses-table")
                ?.scrollIntoView({ behavior: "smooth", block: "center" });
            }, 600);
          },
          true,
        );
      } catch (err) {
        if (!destroyed) {
          setError(err instanceof Error ? err.message : "Failed to load OpenAPI explorer");
        }
      } finally {
        if (!destroyed) setLoading(false);
      }
    }

    void boot();
    return () => {
      destroyed = true;
      uiInstance?.destroy?.();
    };
  }, []);

  return (
    <div className="openapi-page">
      <header className="openapi-page__bar">
        <div className="openapi-page__bar-inner container">
          <Link to="/" className="openapi-page__brand">
            <BrandNavMark height={28} />
            <span className="openapi-page__product">
              {" "}
              <em>OpenAPI</em>
            </span>
          </Link>
          <p className="openapi-page__claim">{APP_POSITIONING_SHORT}</p>
          <nav className="openapi-page__links">
            <a href="/openapi.json" target="_blank" rel="noreferrer">
              openapi.json
            </a>
            <a href="/docs" target="_blank" rel="noreferrer">
              Gateway /docs
            </a>
            <a href="/redoc" target="_blank" rel="noreferrer">
              ReDoc
            </a>
            <Link to="/" className="btn btn--ghost btn--sm">
              Portal home
            </Link>
          </nav>
        </div>
      </header>

      <section className="openapi-page__intro container">
        <h1>Public API reference</h1>
        <p>
          Live OpenAPI contract aggregated by the API Gateway. Every operation includes a{" "}
          <strong>summary</strong>, detailed <strong>description</strong> (auth, request body, expected
          success response), typed schemas with field descriptions/examples, and documented error
          responses (<code>400</code>/<code>401</code>/<code>403</code>/<code>404</code>/<code>422</code>
          ). Public operations have no padlock — use <em>Try it out</em> without
          Authorize. Padlocked operations: click <strong>Authorize</strong> and use{" "}
          <em>OAuth2Password</em> (phone + OTP, or admin email + password) or paste an{" "}
          <code>access_token</code> into HTTPBearer.
          {pathCount != null ? (
            <>
              {" "}
              Currently exposing <strong>{pathCount}</strong> paths.
            </>
          ) : null}{" "}
          Human index: see repo <code>docs/API.md</code>.
        </p>
      </section>

      {loading ? <p className="openapi-page__status container">Loading schema…</p> : null}
      {error ? (
        <div className="openapi-page__error container" role="alert">
          <p>{error}</p>
          <p>
            Ensure <code>docker compose up -d</code> is running, then open{" "}
            <a href="/openapi.json">gateway OpenAPI</a> directly.
          </p>
        </div>
      ) : null}

      <div className="openapi-page__swagger" ref={hostRef} />
    </div>
  );
}
