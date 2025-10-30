from fastmcp import FastMCP, Context
import httpx
from urllib.parse import urlencode
from typing import Any, Dict
import logging
import os
import uuid
import requests
from datetime import datetime
import zoneinfo

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
    send a message to the qsc
    """

    msg_id = str(uuid.uuid4())

    doc = {
            "id": msg_id,
            "type" : "message",
            "message": message
    }

    r = send_to_qsc_with_doc_id(msg_id, doc);

    #ctx.info(f"QSC responded with {r.status}")

    return r


@mcp.tool
def add_to_cart(cartId: str, customerId: str, sku: str, ctx: Context) -> dict:
    """
    add the product with the sku to the cart

    cartId: a unique id to identify the cart
    customerId: a unique id to identify the customer
    sku: the sku of the product
    """

    msg_id = str(uuid.uuid4())

    doc = {
            "id": msg_id,
            "type": "addToCart",
            "cartId" : cartId,
            "sku" : sku,
            "customerId" : customerId
    }

    r = send_to_qsc_with_doc_id(msg_id, doc);

    #ctx.info(f"QSC responded with {r.status}")

    return r

def send_to_qsc(data: dict) -> dict:
    """
    Send a dict to QSC with an automatically generated UUID as id.
    """
    doc_id = str(uuid.uuid4())
    return _send_to_qsc_internal(doc_id, data)


def send_to_qsc_with_doc_id(doc_id: str, data: dict) -> dict:
    """
    Send a dict to QSC with a given id.
    If doc_id is empty or None, a UUID will be generated.
    """
    if not doc_id:
        doc_id = str(uuid.uuid4())
    return _send_to_qsc_internal(doc_id, data)


def _send_to_qsc_internal(doc_id: str, data: dict) -> dict:
    """
    Internal helper for sending data to QSC.
    """
    if not QSC_TOKEN:
        raise RuntimeError("Missing X_QSC_TOKEN environment variable")

    documents = [{
        "header": {
            "id": doc_id,
            "action": "update"
        },
        "payload": {
            "id": doc_id,
            "timestamp": datetime.now(zoneinfo.ZoneInfo("Europe/Berlin")).isoformat(),
            **data
        }
    }]

    try:
        with httpx.Client(timeout=10, follow_redirects=True) as client:
            resp = client.post(
                QSC_URL,
                json=documents,
                headers={
                    "Content-Type": "application/json",
                    "X-QSC-Token": QSC_TOKEN
                },
            )
            return {
                "id": doc_id,
                "status": resp.status_code,
                "ok": resp.is_success,
                "text": resp.text
            }
    except Exception as e:
        logger.error("Failed to send to QSC: %s", e)
        return {
                "id": doc_id,
                "status": 500,
                "ok": resp.is_success,
                "text": resp.text
            }


if __name__ == "__main__":
    mcp.run(transport="http", port=8000)



