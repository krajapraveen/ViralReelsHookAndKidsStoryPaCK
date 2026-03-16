"""
Direct image generation — bypasses emergentintegrations wrapper.
Calls litellm.image_generation directly with full parameter control (size, quality, model).
Preserves Emergent proxy routing for universal key users.
"""

import base64
import logging
import time
import requests
from typing import List, Optional

from litellm import image_generation

logger = logging.getLogger("image_gen_direct")

# Emergent proxy config (mirrored from emergentintegrations internals)
_EMERGENT_PROXY_URL = None


def _get_proxy_url() -> str:
    global _EMERGENT_PROXY_URL
    if _EMERGENT_PROXY_URL is None:
        try:
            from emergentintegrations.llm.utils import get_integration_proxy_url
            _EMERGENT_PROXY_URL = get_integration_proxy_url() + "/llm"
        except Exception:
            _EMERGENT_PROXY_URL = ""
    return _EMERGENT_PROXY_URL


def _is_emergent_key(api_key: str) -> bool:
    return api_key.startswith("sk-emergent-")


async def generate_image_direct(
    api_key: str,
    prompt: str,
    model: str = "gpt-image-1",
    quality: str = "low",
    size: Optional[str] = None,
    n: int = 1,
) -> List[bytes]:
    """
    Generate images via litellm with full parameter control.

    Args:
        api_key: OpenAI or Emergent universal key
        prompt: Image generation prompt
        model: Model name (gpt-image-1, dall-e-3, etc.)
        quality: low / medium / high (gpt-image-1) or standard / hd (dall-e-3)
        size: Image size (1024x1024, 1024x1536, 1536x1024, auto, or None for default)
        n: Number of images

    Returns:
        List of image bytes
    """
    # Quality normalization
    if model == "gpt-image-1":
        if quality == "standard":
            quality = "medium"
        elif quality == "hd":
            quality = "high"
    elif model == "dall-e-3":
        if quality in ("low", "medium"):
            quality = "standard"
        elif quality == "high":
            quality = "hd"

    params = {
        "model": f"openai/{model}",
        "prompt": prompt,
        "n": n,
        "api_key": api_key,
    }

    if model in ("dall-e-3", "gpt-image-1"):
        params["quality"] = quality

    # Size control — the key parameter the wrapper was missing
    if size:
        params["size"] = size

    # Emergent proxy routing
    if _is_emergent_key(api_key):
        proxy = _get_proxy_url()
        if proxy:
            params["api_base"] = proxy

    t0 = time.time()
    response = image_generation(**params)
    gen_ms = int((time.time() - t0) * 1000)

    # Convert response to bytes
    image_bytes_list = []
    for img in response.data:
        if hasattr(img, "b64_json") and img.b64_json:
            image_bytes_list.append(base64.b64decode(img.b64_json))
        elif hasattr(img, "url") and img.url:
            image_response = requests.get(img.url, timeout=30)
            image_bytes_list.append(image_response.content)
        else:
            raise RuntimeError(f"Unexpected image response format: {img}")

    logger.info(f"[IMG_DIRECT] Generated {len(image_bytes_list)} image(s) in {gen_ms}ms | model={model} quality={quality} size={size or 'default'}")
    return image_bytes_list
