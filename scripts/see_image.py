"""Use MiMo vision API to describe UI screenshots."""
import sys
import os
import base64
import json
import requests


def describe_image(image_path: str, prompt: str, api_key: str, base_url: str = None) -> str:
    """Send image to MiMo API and return description."""
    if base_url is None:
        if api_key.startswith("tp-"):
            base_url = "https://token-plan-cn.xiaomimimo.com/v1"
        else:
            base_url = "https://api.xiaomimimo.com/v1"

    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()

    headers = {
        "api-key": api_key,
        "Content-Type": "application/json",
    }

    data = {
        "model": "mimo-v2.5",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64}"},
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
        "max_completion_tokens": 2000,
    }

    resp = requests.post(
        f"{base_url}/chat/completions",
        headers=headers,
        json=data,
        timeout=120,
    )

    if resp.status_code != 200:
        return f"API Error {resp.status_code}: {resp.text[:300]}"

    result = resp.json()
    return result["choices"][0]["message"]["content"]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("image_path")
    parser.add_argument("prompt", nargs="?", default=(
        "请详细描述这个UI截图的布局和视觉效果。"
        "重点说：1)整体布局结构 2)卡片/区域是否有可见的背景色和边框"
        "3)文字是否清晰可读 4)颜色对比度 5)整体视觉质量评价。用中文回答。"
    ))
    parser.add_argument("--output", "-o", default=None)
    args = parser.parse_args()

    api_key = os.environ.get("MIMO_API_KEY", "")
    if not api_key:
        print("ERROR: MIMO_API_KEY not set")
        sys.exit(1)

    result = describe_image(args.image_path, args.prompt, api_key)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(result)
        print("Saved to " + args.output)
    else:
        print(result)
