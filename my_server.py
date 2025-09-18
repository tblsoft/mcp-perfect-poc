from fastmcp import FastMCP
import httpx
from urllib.parse import urlencode
from typing import Any, Dict
import logging

mcp = FastMCP("My MCP Server")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("mcp-server")

@mcp.tool
def greet(name: str) -> str:
    logger.info("Tool called: greet(name=%r)", name)
    return f"Hello, {name}!"


@mcp.tool
def search_products(q: str) -> Dict[str, Any]:
    """
    Proxy a product search to Quasiris Search Cloud and return the JSON.
    
    Args:
        q: The search query string (mapped to ?q= ...).
    Returns:
        The parsed JSON response (or an {error: "..."} object).
    """
    
    logger.info("Tool called: search_products(q=%r)", q)
    if not isinstance(q, str) or not q.strip():
        return {"error": "Parameter 'q' must be a non-empty string."}

    params = {"q": q}
    url = f"https://qsc.quasiris.de/api/v1/search/ab/products?{urlencode(params)}"

    try:
        with httpx.Client(timeout=10000, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            # Expect JSON response from the upstream
            return resp.json()
    except httpx.HTTPStatusError as e:
        return {
            "error": "Upstream HTTP error",
            "status_code": e.response.status_code,
            "url": str(e.request.url),
            "body": e.response.text[:2000],  # avoid huge payloads
        }
    except httpx.RequestError as e:
        return {"error": f"Network error: {str(e)}"}
    except ValueError as e:
        # JSON decoding error
        return {"error": f"Invalid JSON from upstream: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}


if __name__ == "__main__":
    mcp.run(transport="http", port=8000)



