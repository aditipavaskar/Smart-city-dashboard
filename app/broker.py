"""
InMemoryBroker — a topic-based pub/sub that mirrors the shape of a Kafka
producer/consumer API (produce(topic, message) / subscribe(topic) ->
async iterator) without requiring a running Kafka cluster for local dev
or grading.

Why this instead of aiokafka/confluent-kafka directly: the rest of the
codebase (sensors.py, websocket_manager.py, predictive.py) only ever calls
`broker.produce(...)` and `broker.subscribe(...)`. Swapping this for a real
Kafka-backed broker later is a one-file change — see the class docstring
below for exactly what to replace.
"""
from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from dataclasses import dataclass, field
from typing import AsyncIterator


@dataclass
class Message:
    topic: str
    payload: dict
    key: str | None = None

    def to_json(self) -> str:
        return json.dumps({"topic": self.topic, "key": self.key, "payload": self.payload})


class InMemoryBroker:
    """
    Drop-in replacement target: aiokafka.AIOKafkaProducer / AIOKafkaConsumer.

    To go to real Kafka in production:
      - produce() becomes `await self._producer.send_and_wait(topic, json)`
      - subscribe() becomes an AIOKafkaConsumer bound to `topic`, yielding
        deserialized messages from `async for msg in consumer`
      - Everything that calls broker.produce/subscribe is unchanged.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def produce(self, topic: str, payload: dict, key: str | None = None) -> None:
        message = Message(topic=topic, payload=payload, key=key)
        async with self._lock:
            queues = list(self._subscribers.get(topic, []))
        for q in queues:
            # Bounded queue: a slow consumer drops the oldest tick rather than
            # backing up the whole broker (same trade-off Kafka consumer lag
            # forces you to make in production).
            if q.full():
                try:
                    q.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            await q.put(message)

    async def subscribe(self, topic: str, maxsize: int = 100) -> AsyncIterator[Message]:
        q: asyncio.Queue = asyncio.Queue(maxsize=maxsize)
        async with self._lock:
            self._subscribers[topic].append(q)
        try:
            while True:
                msg = await q.get()
                yield msg
        finally:
            async with self._lock:
                if q in self._subscribers[topic]:
                    self._subscribers[topic].remove(q)


# Process-wide singleton. In a multi-worker deployment this is exactly the
# seam where you'd swap in a real Kafka cluster so all workers share state.
broker = InMemoryBroker()
