# Audit 09 — Real-Time Communication Layer

**Date:** 2026-04-08
**Scope:** Full data-flow path from `TradingPlatform.run()` to browser rendering. Protocol evaluation: Socket.IO vs raw WebSocket, SSE, WebTransport, gRPC-Web.

---

## 1. Current Architecture: Market-to-Browser Data Flow

### 1.1 The complete message path

```
TradingPlatform.run()                           # 1-second tick loop
  |
  v
BroadcastService.broadcast_to_websockets()      # fan-out layer
  |
  +---> emit_to_market(market_id, event, data)  # Socket.IO room broadcast
  |       |
  |       v
  |     sio.emit(event, sanitized, room=id)     # python-socketio AsyncServer
  |       |
  |       v
  |     Engine.IO frame -> WebSocket wire        # binary frame to browser
  |
  +---> websocket.send_json(message)            # legacy raw WS (parallel path)
```

Additionally, **per-trader unicast** messages follow a separate path:

```
HumanTrader.send_message_to_client()
  |
  v
sio.emit(event, sanitized, to=sid)              # targeted to single session
```

### 1.2 Three broadcast triggers

| Trigger | Source | Frequency |
|---------|--------|-----------|
| Timer tick | `TradingPlatform.run()` loop | Every 1 second |
| Order book change | `OrderHandler._process_order()` via `BroadcastService` | Per order event |
| Lifecycle events | `start_trading()`, `_end_trading_market()` | 3-5 per session |

### 1.3 Dual transport — Socket.IO + legacy raw WebSocket

The system maintains **two parallel broadcast paths**. `BroadcastService.broadcast_to_websockets()` (services.py:271-298) first emits via Socket.IO rooms, then iterates over a `self.websockets` set of raw Starlette WebSocket connections. `HumanTrader.send_message_to_client()` (human_trader.py:103-149) similarly checks for both `self._sio` and `self.websocket` and sends to whichever is available.

This dual-path architecture is technical debt from the Socket.IO migration. The raw WebSocket path still exists as a fallback but is no longer used by any frontend code — `front/src/socket.js` connects exclusively via Socket.IO.

### 1.4 Payload structure

Every `book_updated` event from `HumanTrader.send_message_to_client()` sends the **full trader state**: shares, cash, pnl, inventory, goal, goal_progress, order_book, initial_cash, initial_shares, sum_dinv, vwap, filled_orders, placed_orders. This is roughly 2-8 KB per message depending on order book depth and trade history length — sent on every single order book change to every human trader individually.

Room-level broadcasts from `BroadcastService.create_broadcast_message()` include: order_book snapshot, active_orders, full transaction history, spread, midpoint, transaction_price, timing metadata. These grow linearly with session activity.

### 1.5 Message sanitization

All outbound messages pass through `sanitize_websocket_message()` (websocket_utils.py), which recursively walks the entire payload dict to replace NaN/Inf floats and clean problematic strings. This is called on **every emit** — both room broadcasts and per-trader unicasts — adding CPU overhead proportional to payload size.

---

## 2. Protocol Evaluation: Is Socket.IO the Right Choice?

### 2.1 Candidates

| Protocol | Transport | Direction | Browser support | Maturity |
|----------|-----------|-----------|----------------|----------|
| **Socket.IO** (current) | WS + HTTP polling fallback | Bidirectional | 100% | Battle-tested, 10+ years |
| Raw WebSocket | WS (RFC 6455) | Bidirectional | 100% | Stable standard |
| Server-Sent Events (SSE) | HTTP/1.1 or HTTP/2 | Server-to-client only | 100% | Stable, simple |
| WebTransport | HTTP/3 (QUIC) | Bidirectional, multiplexed | ~75% (no Safari) | Emerging |
| gRPC-Web | HTTP/1.1 or HTTP/2 | Unary + server-stream only | Via proxy/envoy | Mature for microservices |

### 2.2 Socket.IO — why it was the right initial choice

Socket.IO provides several features this platform uses heavily:

- **Rooms** — `sio.enter_room(sid, market_id)` and `sio.emit(event, data, room=market_id)` are the primary broadcast mechanism. Every market is a room. This would require manual implementation with raw WebSocket.
- **Structured events** — Named events (`book_updated`, `filled_order`, `time_update`) map directly to frontend handlers via `ROUTED_EVENTS`. Raw WebSocket only provides a single `onmessage` callback.
- **Automatic reconnection** — The client configures `reconnectionAttempts: 5` and `reconnectionDelay: 3000`, with a `reconnect` handler that re-joins the market room. This logic would need manual implementation with raw WebSocket.
- **Authentication on connect** — The `auth` dict on connection (`{lab_token, admin_token, prolific_pid}`) is a clean Socket.IO feature. Raw WebSocket requires auth via query params or a post-connect handshake.
- **Transport fallback** — `transports: ['websocket', 'polling']` provides HTTP long-polling fallback for restrictive networks (relevant for lab experiments at universities with proxy/firewall constraints).

### 2.3 Raw WebSocket — not worth the regression

Switching to raw WebSocket would remove the Socket.IO overhead (~2-5% per message for the Engine.IO framing layer) but require reimplementing:

- Room management (topic-based pub/sub)
- Connection lifecycle (heartbeat, disconnect detection)
- Reconnection with exponential backoff
- Transport negotiation and fallback
- Event multiplexing over a single connection

For a research platform with 50-100 users, the engineering cost far exceeds the performance gain. The Socket.IO overhead is negligible compared to the payload sizes being sent (2-8 KB per message).

### 2.4 SSE — wrong communication model

The platform requires **bidirectional** communication: browsers send `place_order`, `cancel_order`, and `mark_ready` events upstream. SSE is server-to-client only. While orders could be sent via HTTP POST alongside an SSE stream, this creates two separate connections, complicates error handling, and loses the transactional relationship between "send order" and "receive confirmation."

SSE would be appropriate if the platform were read-only (e.g., a market data viewer), but the interactive trading use case rules it out.

### 2.5 WebTransport — promising but premature

WebTransport offers genuine advantages for this use case:

- **No head-of-line blocking** — QUIC-based transport means a lost packet doesn't stall the entire stream. In a trading context, a delayed `time_update` wouldn't block a subsequent `filled_order`.
- **Multiplexed streams** — Different event types could use independent streams, allowing prioritization (e.g., trade confirmations over timer ticks).
- **Unreliable datagrams** — Timer updates could use unreliable delivery, reducing retransmission overhead.

However, critical blockers remain:

1. **Safari has zero support** as of April 2026. Lab experiments may include participants on macOS Safari.
2. **python-socketio does not support WebTransport as a transport** in its current ASGI mode. Socket.IO v4.7+ added WebTransport support, but only for the Node.js server. The Python server would need a separate HTTP/3 server (e.g., aioquic) running alongside the existing ASGI app.
3. **Deployment complexity** — WebTransport requires HTTP/3, which requires QUIC, which requires UDP port exposure. Firebase Hosting (the current deployment target at london-trader.web.app) proxies to Cloud Run, which does not support HTTP/3 for custom backends.
4. **Debugging tooling** — Browser DevTools WebTransport inspection is less mature than WebSocket frame inspection.

**Verdict:** Revisit in 12-18 months when Safari ships support and Python server libraries mature. Not viable for the current deployment.

### 2.6 gRPC-Web — wrong layer

gRPC-Web excels at typed RPC between microservices or between a browser client and a backend with strong schema contracts (Protocol Buffers). However:

- **No bidirectional streaming in browsers** — gRPC-Web only supports unary calls and server-streaming. Client-streaming and bidirectional streaming require a gRPC proxy (Envoy) and are not natively supported in browsers.
- **Operational overhead** — Requires an Envoy proxy sidecar, Protocol Buffer compilation, and a fundamentally different API design pattern.
- **Overkill** — The platform has ~6 upstream events and ~12 downstream events with simple JSON payloads. The schema enforcement and binary serialization of gRPC add complexity without proportional benefit at this scale.

gRPC would be relevant for the internal backend if the platform adopted a microservices architecture (e.g., separate order matching engine, trader management service), but not for the browser-facing communication layer.

---

## 3. Scalability Analysis: 50-100 Concurrent Users

### 3.1 Connection load

Socket.IO connections are lightweight. Each connection is an asyncio transport object with ~50 KB of memory overhead. For 100 concurrent connections:

- **Memory**: ~5 MB for connection state (negligible)
- **File descriptors**: 100 sockets (well within OS defaults of 1024-65535)
- **Heartbeat overhead**: Socket.IO default ping interval is 25 seconds. 100 connections = 4 pings/second of background traffic.

**Assessment: No concern.** python-socketio with ASGI can handle 10,000+ concurrent connections on a single process. 100 users is trivially within capacity.

### 3.2 Message throughput

The real scalability concern is **broadcast fan-out**. Every order book change triggers:

1. **Room broadcast** via `emit_to_market()` — one message serialized and sent to N room members
2. **Per-trader unicast** via `send_to_traders()` — iterates over all connected traders, calling `trader.on_message_from_system()` on each
3. **Per-trader client emit** — each `HumanTrader.send_message_to_client()` sends an individualized payload to that trader's socket

For a market with 5 human traders and 10 algo traders:
- Each order event triggers: 1 room broadcast + 15 `on_message_from_system` calls + 5 individual `sio.emit` calls
- With 10 orders/second (moderate activity): **210 emit calls/second**
- With full payload sanitization on each: **210 recursive dict walks/second**

For 20 parallel markets (the target parallelism): **4,200 emit calls/second** across all markets.

**Assessment: Manageable but approaching the point where optimization matters.** The `sanitize_websocket_message()` cost is the bottleneck — it walks entire payloads including the growing transaction history on every call.

### 3.3 Payload growth problem

`create_broadcast_message()` includes `"history": self.transaction_manager.transactions` — the **entire transaction history** of the session. In a 5-minute trading session with active markets, this can reach 50-200 transactions. Combined with the full order book snapshot, payloads grow from ~2 KB at session start to ~15-30 KB by session end.

This means later broadcasts are 5-15x more expensive to serialize, sanitize, and transmit than early ones. Over a session, total bandwidth per human participant for book updates alone:

- Start: 2 KB x 10 updates/sec = 20 KB/s
- End: 20 KB x 10 updates/sec = 200 KB/s

For 100 simultaneous human participants: **up to 20 MB/s outbound** at peak. This is feasible on cloud infrastructure but wasteful — most of the payload is unchanged between consecutive messages.

### 3.4 The dual-broadcast redundancy

The `broadcast_to_websockets()` and `send_to_traders()` calls happen **in sequence** on the same data. For human traders, this means they receive the same information twice:

1. Once via the Socket.IO room broadcast (from `broadcast_to_websockets`)
2. Once via `send_to_traders` -> `on_message_from_system` -> `send_message_to_client` (individual emit)

The frontend receives both but only meaningfully processes one. This doubles the per-human message rate unnecessarily.

---

## 4. Latency Analysis

### 4.1 Measurement: server-to-browser latency

The critical latency path is: **order placed -> order book updated -> all participants see the new book state**.

Estimated latency breakdown for a single order event:

| Stage | Time | Notes |
|-------|------|-------|
| Order processing + matching | <1 ms | In-memory order book, single asyncio lock |
| Broadcast message construction | 1-3 ms | Dict construction + `create_broadcast_message` |
| `sanitize_websocket_message()` | 1-5 ms | Recursive walk of full payload |
| Socket.IO serialization | <1 ms | JSON.stringify equivalent |
| Engine.IO framing | <0.1 ms | Minimal overhead |
| Network transit (same region) | 5-20 ms | Cloud Run -> browser |
| Network transit (cross-Atlantic) | 80-150 ms | UK server, global participants |
| Frontend processing | 1-3 ms | Vue reactivity update |
| **Total (same region)** | **~10-30 ms** | |
| **Total (cross-region)** | **~90-160 ms** | |

### 4.2 Is this fast enough?

For this platform's use case — a **research experiment** where human traders make decisions on 1-10 second timescales — yes. The key requirements:

- **Order book freshness**: Traders need to see the current book state within ~100 ms of a change. Current architecture delivers this.
- **Trade confirmation**: Traders need to know their order was filled within ~200 ms. The per-trader unicast path provides this.
- **Timer accuracy**: The 1-second timer tick is adequate for sessions measured in minutes.

This is NOT a high-frequency trading platform. Sub-millisecond latency is irrelevant. The current approach is well within acceptable bounds for the research context.

### 4.3 Where latency could become a problem

The `_time_update_loop` in `socketio_server.py` spawns **one asyncio task per connected client** that emits every 1 second. With 100 clients, that's 100 independent tasks all firing within the same 1-second window. If the event loop is congested from order processing, these can bunch up and create visible timer jitter on the frontend.

A single room-level broadcast (`sio.emit('time_update', data, room=market_id)`) would replace 100 individual emits with 1 call, letting Socket.IO handle the fan-out internally.

---

## 5. Reliability: Reconnection, Ordering, Delivery

### 5.1 Reconnection handling

**Current implementation:**

```js
// socket.js
reconnectionAttempts: 5,
reconnectionDelay: 3000,

_socket.io.on('reconnect', () => {
  socketState.connected = true
  if (_lastJoinedTrader) {
    _socket.emit('join_market', { trader_id: _lastJoinedTrader })
  }
})
```

This is **partially correct** but has gaps:

- **Room re-join works** — the reconnect handler re-emits `join_market`, which triggers the full `join_market` flow on the backend including `connect_to_socketio()`.
- **5 attempts is low** — a brief network interruption (e.g., laptop sleep, WiFi dropout in a lab) could exhaust all 5 attempts in 15 seconds. Recommended: 10-20 attempts with exponential backoff.
- **No state recovery** — after reconnection, the client has no way to request a "catch-up" snapshot of what it missed. If 3 orders were placed during the disconnection, the client's order book is stale until the next broadcast. Since broadcasts include full state, the next `book_updated` event will fix this — but there could be a gap of up to 1 second.
- **No user notification** — the `connect_error` handler sets `socketState.connected = false` but does not surface the error to the UI. The `showErrorAlert` ref in `TradingDashboard.vue` exists but is never triggered by connection issues.

### 5.2 Message ordering

Socket.IO over WebSocket guarantees **in-order delivery** within a single connection (TCP provides this). Messages are processed sequentially by the asyncio event loop on the server side, and the single WebSocket frame stream preserves ordering on the client side.

**Risk**: The parallel `broadcast_to_websockets()` + `send_to_traders()` paths could deliver the room broadcast and the individual unicast in different orders, but since they carry the same data (or the unicast is a superset), this is not a correctness issue — just a minor inefficiency.

### 5.3 Delivery guarantees

Socket.IO provides **at-most-once** delivery by default. If a message is sent while the client is disconnected, it is lost. Socket.IO v4+ has a connection state recovery feature that can buffer messages during brief disconnections, but it is **not enabled** in the current configuration.

For this platform, at-most-once is acceptable because:

- Full state is included in every broadcast (order book, positions, PnL), so any missed message is implicitly corrected by the next one.
- The 1-second timer tick acts as a natural heartbeat and state synchronization point.
- Order confirmations are sent via the unicast path to the specific trader, and if missed, the trader's local state will be corrected on the next `book_updated` broadcast.

**However**, if a `filled_order` event is lost, the trader may not realize their order was filled until the next book update. For a research experiment this is tolerable; for a production trading platform it would not be.

### 5.4 Disconnect detection

Socket.IO's Engine.IO layer sends periodic pings (default: every 25 seconds, timeout after 20 seconds). If a client disappears without a clean disconnect (e.g., browser crash, network loss), the server detects it after ~45 seconds. The `disconnect` handler removes the session and broadcasts an updated trader count.

This 45-second detection window means a crashed participant's slot is not freed for nearly a minute. For lab experiments where all participants must be present, this can cause confusion.

---

## 6. Recommendation

### Keep Socket.IO. Optimize the usage, not the protocol.

Socket.IO is the correct choice for this platform at its current and foreseeable scale (50-100 concurrent users, 20 parallel markets). Switching protocols would introduce significant engineering effort with minimal benefit. The performance bottlenecks are in **what is being sent**, not **how it is being sent**.

### Priority optimizations (within Socket.IO)

| Priority | Change | Impact | Effort |
|----------|--------|--------|--------|
| **P0** | Remove legacy raw WebSocket path from `BroadcastService` | Eliminates dead code, simplifies broadcast logic | Small |
| **P0** | Deduplicate room broadcast + per-trader unicast | Cuts human trader message rate in half | Medium |
| **P1** | Stop including full transaction history in every broadcast | Reduces late-session payloads by 5-15x | Medium |
| **P1** | Replace per-client `_time_update_loop` tasks with room-level broadcast | Replaces N tasks with 1 per market | Small |
| **P1** | Increase `reconnectionAttempts` to 15, add exponential backoff | Better resilience for lab network issues | Small |
| **P2** | Cache `sanitize_websocket_message()` for unchanged sub-dicts | Reduces CPU cost of repeated sanitization | Medium |
| **P2** | Enable Socket.IO connection state recovery (`connectionStateRecovery`) | Buffers messages during brief disconnects | Small |
| **P2** | Surface connection errors in UI via `showErrorAlert` | Better UX during network issues | Small |
| **P3** | Add `/admin` namespace for observer connections | Separates admin traffic from trader traffic | Large |

### When to reconsider

Re-evaluate the protocol choice if any of these conditions arise:

1. **Scale exceeds 1,000 concurrent users** — at this point, consider a managed WebSocket service (e.g., Ably, AWS API Gateway WebSocket) rather than self-hosted Socket.IO.
2. **Sub-10ms latency becomes a research requirement** — if the experiment design requires measuring human reaction times to price changes at high precision, the current architecture's 10-30ms server-to-browser path may need profiling and optimization.
3. **Safari ships WebTransport support** — once browser coverage reaches ~95%, WebTransport becomes a viable upgrade path, particularly if Socket.IO's Python server adds native WebTransport transport support.
4. **The platform becomes multi-region** — if experiments span multiple continents simultaneously, a CDN-backed WebSocket service or WebTransport (with its superior handling of lossy connections) would provide better experience than a single-region Socket.IO server.

---

## Sources

- [WebSocket vs WebTransport: When to Use Which](https://websocket.org/comparisons/webtransport/)
- [WebSocket vs HTTP, SSE, MQTT, WebRTC & More (2026)](https://websocket.org/comparisons/)
- [Socket.IO vs WebSocket: Performance & Use Case Guide](https://ably.com/topic/socketio-vs-websocket)
- [WebSockets vs SSE vs Long-Polling vs WebRTC vs WebTransport](https://rxdb.info/articles/websockets-sse-polling-webrtc-webtransport.html)
- [Socket.IO: Complete Guide (2026 Edition)](https://dev.to/abanoubkerols/socketio-the-complete-guide-to-building-real-time-web-applications-2026-edition-c7h)
- [FOSDEM 2026: Intro to WebTransport](https://www.infoq.com/news/2026/03/fosdem-webtransport-vs-websocket/)
- [What it really takes to scale Socket.IO in production](https://ably.com/topic/scaling-socketio)
- [WebSocket vs gRPC: Browser Apps vs Microservices](https://websocket.org/comparisons/grpc/)
- [gRPC vs WebSocket: Key differences](https://ably.com/topic/grpc-vs-websocket)
- [Modern HTTP Stack in 2026: HTTP/3, gRPC, WebSockets](https://hemaks.org/posts/modern-http-stack-in-2026-http3-grpc-websockets-and-when-to-use-what/)
- [WebTransport browser support (Can I Use)](https://caniuse.com/webtransport)
- [python-socketio ASGI documentation](https://python-socketio.readthedocs.io/en/latest/server.html)
- [SSE vs WebSockets: Comparing Real-Time Communication Protocols](https://softwaremill.com/sse-vs-websockets-comparing-real-time-communication-protocols/)
- [Server-Sent Events Beat WebSockets for 95% of Real-Time Apps](https://dev.to/polliog/server-sent-events-beat-websockets-for-95-of-real-time-apps-heres-why-a4l)
