from __future__ import annotations

import json
import math
import os
import urllib.parse
import urllib.request
from typing import Any

GEOAPIFY_BASE_URL = "https://api.geoapify.com/v1/geocode"
NZ_COUNTRY_FILTER = "countrycode:nz"


class AddressService:
    """Geoapify-backed address lookup helpers / 基于 Geoapify 的地址查询封装。"""

    @staticmethod
    def _api_key() -> str:
        return os.getenv("GEOAPIFY_API_KEY", "").strip()

    @staticmethod
    def _fetch_json(path: str, params: dict[str, Any]) -> dict[str, Any] | None:
        api_key = AddressService._api_key()
        if not api_key:
            return None
        query = {"apiKey": api_key, "format": "json", **params}
        url = f"{GEOAPIFY_BASE_URL}/{path}?{urllib.parse.urlencode(query)}"
        try:
            with urllib.request.urlopen(url, timeout=8) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception:
            return None

    @staticmethod
    def _map_result(item: dict[str, Any]) -> dict[str, Any] | None:
        address = (item.get("formatted") or item.get("address_line1") or "").strip()
        lat = item.get("lat")
        lng = item.get("lon")
        if not address:
            return None
        return {
            "address": address,
            "lat": lat,
            "lng": lng,
            # Backward-compatible keys kept empty / 兼容旧逻辑保留空键
            "nztm_x": None,
            "nztm_y": None,
        }

    @staticmethod
    def autocomplete(query: str, max_results: int = 8) -> list[dict[str, Any]]:
        """Return matching addresses via Geoapify autocomplete.
        / 通过 Geoapify 返回地址自动补全结果。"""
        query = query.strip()
        if len(query) < 3:
            return []
        data = AddressService._fetch_json(
            "autocomplete",
            {
                "text": query,
                "limit": max_results,
                "filter": NZ_COUNTRY_FILTER,
            },
        )
        if not data:
            return []
        results: list[dict[str, Any]] = []
        for item in data.get("results", []):
            mapped = AddressService._map_result(item)
            if mapped:
                results.append(mapped)
        return results

    @staticmethod
    def geocode(address: str) -> dict[str, Any] | None:
        """Resolve a single address to coordinates.
        / 将单个地址解析为坐标。"""
        address = address.strip()
        if not address:
            return None
        data = AddressService._fetch_json(
            "search",
            {
                "text": address,
                "limit": 1,
                "filter": NZ_COUNTRY_FILTER,
            },
        )
        if not data:
            return None
        for item in data.get("results", []):
            mapped = AddressService._map_result(item)
            if mapped:
                return mapped
        return None

    @staticmethod
    def reverse_geocode(lat: float, lng: float, max_radius_m: int = 200) -> dict[str, Any] | None:
        """Find the nearest address for a WGS84 lat/lng point.
        / 根据 WGS84 经纬度查找最近地址。"""
        data = AddressService._fetch_json(
            "reverse",
            {
                "lat": lat,
                "lon": lng,
                "limit": 1,
                "filter": NZ_COUNTRY_FILTER,
            },
        )
        if not data:
            return None
        for item in data.get("results", []):
            mapped = AddressService._map_result(item)
            if not mapped:
                continue
            distance_m = item.get("distance")
            if distance_m is not None and distance_m > max_radius_m:
                return None
            return mapped
        return None


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Return distance in metres between two WGS84 lat/lng points.
    / 返回两个 WGS84 经纬度点之间的距离（米）。"""
    r = 6_371_000.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlng / 2) ** 2
    )
    return r * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
