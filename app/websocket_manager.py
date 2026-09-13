"""
Streams broker topics to a connected WebSocket client, scoped to the
domains their role is permitted to see (app.config.ROLES).

A role like "city_admin" needs to fan in several broker topics (one per
domain, plus the shared alerts topic) onto a single WebSocket connection.
We do that with one asyncio task per subscribed topic, all writing to the
same socket, plus one task reading from the socket purely to notice a
client-initiated disconnect. Whichever task finishes first (usually the
disconnect) triggers cancellation of the rest.
"""
from __future__ import annotations

import asyncio

from fastapi import WebSocket

from app.broker import broker
from app.config import ALERTS_TOPIC, DOMAINS, ROLES


async def _forward_domain_topic(ws: WebSocket, domain: str) -> None:
    topic = DOMAINS[domain]["topic"]
    async for message in broker.subscribe(topic):
        await ws.send_json({"type": "reading", **message.payload})


async def _forward_alerts_topic(ws: WebSocket, allowed_domains: set[str]) -> None:
    async for message in broker.subscribe(ALERTS_TOPIC):
        if message.payload.get("domain") in allowed_domains:
            await ws.send_json({"type": "alert", **message.payload})


async def _watch_for_disconnect(ws: WebSocket) -> None:
    # We don't expect the (mostly read-only) dashboard client to send
    # anything meaningful, but awaiting receive() is how FastAPI's
    # WebSocket surfaces a client-initiated close.
    while True:
        await ws.receive_text()


async def stream_for_role(ws: WebSocket, role: str) -> None:
    allowed_domains = set(ROLES[role]["domains"])

    tasks = [asyncio.create_task(_forward_domain_topic(ws, d)) for d in allowed_domains]
    tasks.append(asyncio.create_task(_forward_alerts_topic(ws, allowed_domains)))
    tasks.append(asyncio.create_task(_watch_for_disconnect(ws)))

    try:
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    finally:
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
