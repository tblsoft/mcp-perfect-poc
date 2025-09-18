from fastmcp import FastMCP, tool
import json
from pathlib import Path

mcp = FastMCP("file-json-mcp")

@tool()
def load_json(filename: str) -> dict:
    """
    Load and return the JSON contents of a file.
    
    Args:
        filename: Path to a JSON file.
    Returns:
        Parsed JSON object.
    """
    path = Path(filename)
    if not path.exists():
        return {"error": f"File not found: {filename}"}
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    mcp.run()
