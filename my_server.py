from fastmcp import FastMCP, Context
import httpx
from urllib.parse import urlencode
from typing import Any, Dict
import logging
import os
import uuid
import requests

mcp = FastMCP("My MCP Server")


QSC_URL = "https://qsc-dev.quasiris.de/api/v1/data/bulk/qsc/demo/messages"
QSC_TOKEN = os.environ.get("X_QSC_TOKEN") 

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("mcp-server")

@mcp.tool
def greet(name: str) -> str:
    logger.info("Tool called: greet(name=%r)", name)
    return f"Hello my friend from Quasiris, {name}!"


@mcp.tool
def search_products(q: str) -> Dict[str, Any]:
    """
    Proxy a product search to Quasiris Search Cloud and return the JSON.
    
    Args:
        q: The search query string (mapped to ?q= ...). - The search is optimized for searching keywords. Use only keywords for this parameter
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


@mcp.tool
def send_message(message: str, ctx: Context) -> dict:
    """
    This tool collect messages.
    """
    if not QSC_TOKEN:
        raise RuntimeError("X_QSC_TOKEN missing in environment")

    msg_id = str(uuid.uuid4())

    doc = [{
        "header": {
            "id": msg_id,
            "action": "update"
        },
        "payload": {
            "id": msg_id,
            "message": message
        }
    }]

    r = requests.post(
        QSC_URL,
        json=doc,
        headers={
            "Content-Type": "application/json",
            "X-QSC-Token": QSC_TOKEN
        },
        timeout=10
    )

    ctx.info(f"QSC responded with {r.status_code}")

    return {
        "id": msg_id,
        "status": r.status_code,
        "ok": r.ok,
        "text": r.text
    }


if __name__ == "__main__":
    mcp.run(transport="http", port=8000)



