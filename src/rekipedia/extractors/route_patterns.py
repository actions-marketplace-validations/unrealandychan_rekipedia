"""Framework-aware route pattern definitions for rekipedia extractors.

Each entry maps a framework to a list of regex patterns that identify
HTTP route handler registrations in source code.

Route symbol names are formatted as ``"METHOD /path"``
(e.g. ``"GET /users/{id}"``). When the method cannot be determined the
name is just the path string.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# ── HTTP method normalisation ─────────────────────────────────────────────────

_HTTP_METHODS = frozenset({"get", "post", "put", "patch", "delete", "head", "options", "any", "all"})


def normalise_method(raw: str) -> str:
    """Return an upper-case HTTP method, or '*' for catch-all registrations."""
    low = raw.lower()
    if low in ("any", "all", "use"):
        return "*"
    return low.upper() if low in _HTTP_METHODS else raw.upper()


# ── Pattern dataclass ─────────────────────────────────────────────────────────

@dataclass
class RoutePattern:
    """A regex pattern that matches a route registration line."""
    framework: str
    regex: re.Pattern
    method_group: int | None = None   # capture group index for HTTP method
    path_group: int = 1               # capture group index for path


# ── Python route patterns ─────────────────────────────────────────────────────

PYTHON_ROUTE_PATTERNS: list[RoutePattern] = [
    # Flask / Quart:  @app.route('/path', methods=['GET', 'POST'])
    RoutePattern(
        framework="flask",
        regex=re.compile(
            r"""@\w+\.route\(\s*['"]([^'"]+)['"](?:[^)]*methods\s*=\s*\[([^\]]+)\])?""",
            re.IGNORECASE,
        ),
        method_group=2,
        path_group=1,
    ),
    # Flask shorthand: @app.get('/path'), @bp.post('/path')
    RoutePattern(
        framework="flask",
        regex=re.compile(
            r"""@\w+\.(get|post|put|patch|delete|head|options)\(\s*['"]([^'"]+)['"]""",
            re.IGNORECASE,
        ),
        method_group=1,
        path_group=2,
    ),
    # FastAPI / APIRouter:  @router.get('/path'), @app.post('/users/{id}')
    RoutePattern(
        framework="fastapi",
        regex=re.compile(
            r"""@\w+\.(get|post|put|patch|delete|head|options|websocket)\(\s*['"]([^'"]+)['"]""",
            re.IGNORECASE,
        ),
        method_group=1,
        path_group=2,
    ),
    # Django urlpatterns:  path('users/', view)  /  re_path(r'^users/', view)
    RoutePattern(
        framework="django",
        regex=re.compile(
            r"""(?:^|\s)(?:re_)?path\(\s*r?['"]([^'"]+)['"]""",
            re.IGNORECASE,
        ),
        method_group=None,
        path_group=1,
    ),
    # Django url() legacy
    RoutePattern(
        framework="django",
        regex=re.compile(
            r"""(?:^|\s)url\(\s*r?['"]([^'"]+)['"]""",
            re.IGNORECASE,
        ),
        method_group=None,
        path_group=1,
    ),
    # Starlette / generic add_route:  app.add_route('/path', handler, methods=['GET'])
    RoutePattern(
        framework="starlette",
        regex=re.compile(
            r"""\.add_route\(\s*['"]([^'"]+)['"](?:[^)]*methods\s*=\s*\[([^\]]+)\])?""",
            re.IGNORECASE,
        ),
        method_group=2,
        path_group=1,
    ),
]


# ── TypeScript / JavaScript route patterns ───────────────────────────────────

TYPESCRIPT_ROUTE_PATTERNS: list[RoutePattern] = [
    # Express / Fastify / Hapi:  router.get('/path', ...) / app.post('/path', ...)
    RoutePattern(
        framework="express",
        regex=re.compile(
            r"""(?:router|app|server)\.(get|post|put|patch|delete|head|options|all|use)\(\s*['"`]([^'"`]+)['"`]""",
            re.IGNORECASE,
        ),
        method_group=1,
        path_group=2,
    ),
    # Next.js API routes: export default handler — infer from file path (handled in extractor)
    # Koa:  router.get('/path', ...)
    RoutePattern(
        framework="koa",
        regex=re.compile(
            r"""router\.(get|post|put|patch|delete|head|options)\(\s*['"`]([^'"`]+)['"`]""",
            re.IGNORECASE,
        ),
        method_group=1,
        path_group=2,
    ),
    # NestJS decorators:  @Get('/path'), @Post('/users/:id')
    RoutePattern(
        framework="nestjs",
        regex=re.compile(
            r"""@(Get|Post|Put|Patch|Delete|Head|Options|All)\(\s*['"`]([^'"`]*)['"`]\)""",
        ),
        method_group=1,
        path_group=2,
    ),
    # NestJS controller with no path arg:  @Get()
    RoutePattern(
        framework="nestjs",
        regex=re.compile(
            r"""@(Get|Post|Put|Patch|Delete|Head|Options|All)\(\s*\)""",
        ),
        method_group=1,
        path_group=None,  # type: ignore[arg-type]  # path falls back to ""
    ),
]


# ── Go route patterns ─────────────────────────────────────────────────────────

GO_ROUTE_PATTERNS: list[RoutePattern] = [
    # Gin:  r.GET("/path", handler)  /  group.POST("/path", ...)
    RoutePattern(
        framework="gin",
        regex=re.compile(
            r"""\w+\.(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS|Any)\(\s*"([^"]+)"""
        ),
        method_group=1,
        path_group=2,
    ),
    # Echo:  e.GET("/path", handler)
    RoutePattern(
        framework="echo",
        regex=re.compile(
            r"""\w+\.(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS|Any)\(\s*"([^"]+)"""
        ),
        method_group=1,
        path_group=2,
    ),
    # Chi / gorilla/mux:  r.Get("/path", handler)
    RoutePattern(
        framework="chi",
        regex=re.compile(
            r"""\w+\.(Get|Post|Put|Patch|Delete|Head|Options|Handle)\(\s*"([^"]+)"""
        ),
        method_group=1,
        path_group=2,
    ),
    # net/http ServeMux:  mux.HandleFunc("/path", handler)
    RoutePattern(
        framework="net/http",
        regex=re.compile(
            r"""(?:mux|http|router|r)\s*\.HandleFunc\(\s*"([^"]+)"""
        ),
        method_group=None,
        path_group=1,
    ),
    # net/http Handle:  http.Handle("/path", ...)
    RoutePattern(
        framework="net/http",
        regex=re.compile(
            r"""http\.Handle\(\s*"([^"]+)"""
        ),
        method_group=None,
        path_group=1,
    ),
]


# ── Rust route patterns ───────────────────────────────────────────────────────

RUST_ROUTE_PATTERNS: list[RoutePattern] = [
    # Axum:  .route("/path", get(handler))  /  .route("/path", post(handler).put(handler))
    RoutePattern(
        framework="axum",
        regex=re.compile(
            r"""\.route\(\s*"([^"]+)"\s*,\s*(get|post|put|patch|delete|head|options|any)\s*\(""",
            re.IGNORECASE,
        ),
        method_group=2,
        path_group=1,
    ),
    # Actix-web:  web::get().to(...) via .route("/path", web::get().to(handler))
    RoutePattern(
        framework="actix-web",
        regex=re.compile(
            r"""\.route\(\s*"([^"]+)"\s*,\s*web::(get|post|put|patch|delete|head|options)\(\)""",
            re.IGNORECASE,
        ),
        method_group=2,
        path_group=1,
    ),
    # Actix-web macros:  #[get("/path")], #[post("/users/{id}")]
    RoutePattern(
        framework="actix-web",
        regex=re.compile(
            r"""#\[(get|post|put|patch|delete|head|options)\s*\(\s*"([^"]+)"\s*\)\]""",
            re.IGNORECASE,
        ),
        method_group=1,
        path_group=2,
    ),
    # Rocket macros:  #[get("/path")], #[post("/path")]
    RoutePattern(
        framework="rocket",
        regex=re.compile(
            r"""#\[(get|post|put|patch|delete|head|options)\s*\(\s*"([^"]+)"\s*(?:,|\))""",
            re.IGNORECASE,
        ),
        method_group=1,
        path_group=2,
    ),
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _clean_path(raw: str | None) -> str:
    if not raw:
        return "/"
    # strip regex anchors from Django patterns
    cleaned = raw.strip().lstrip("^").rstrip("$")
    if not cleaned.startswith("/"):
        cleaned = "/" + cleaned
    return cleaned


def _parse_methods_list(raw: str | None) -> list[str]:
    """Parse ``['GET', 'POST']`` style string into list of methods."""
    if not raw:
        return []
    return [m.strip().strip("'\"") for m in raw.split(",") if m.strip().strip("'\"")]


def extract_routes_from_line(
    line: str,
    patterns: list[RoutePattern],
) -> list[tuple[str, str]]:
    """Return list of (route_name, framework) tuples matched in *line*.

    Route name format: ``"METHOD /path"`` or ``"/path"`` (when method unknown).
    """
    results: list[tuple[str, str]] = []
    for pat in patterns:
        m = pat.regex.search(line)
        if not m:
            continue
        # path
        if pat.path_group and pat.path_group <= len(m.groups()):
            raw_path = m.group(pat.path_group)
        else:
            raw_path = None
        path = _clean_path(raw_path)

        # method
        if pat.method_group and pat.method_group <= len(m.groups()):
            raw_method = m.group(pat.method_group)
        else:
            raw_method = None

        if raw_method:
            methods_list = _parse_methods_list(raw_method) or [raw_method]
            for meth in methods_list:
                norm = normalise_method(meth)
                results.append((f"{norm} {path}", pat.framework))
        else:
            results.append((path, pat.framework))

    return results
