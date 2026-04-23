# WebSockets

WebSockets provide real-time, low-latency email event streaming over a persistent connection. No public URL required.

## When to Use

- Local development (no ngrok needed)
- Client-side applications
- When you need bidirectional communication
- Lower latency than webhooks

For production with public endpoints, [webhooks.md](webhooks.md) may be simpler.

## Comparison

| Feature    | Webhook                | WebSocket         |
| ---------- | ---------------------- | ----------------- |
| Setup      | Requires public URL    | No external tools |
| Connection | HTTP request per event | Persistent        |
| Latency    | HTTP round-trip        | Instant streaming |
| Firewall   | Must expose port       | Outbound only     |

## TypeScript SDK

### Basic Usage

```typescript
import { AgentMailClient, AgentMail } from "agentmail";

const client = new AgentMailClient({ apiKey: process.env.AGENTMAIL_API_KEY });

async function main() {
  const socket = await client.websockets.connect();

  socket.on("open", () => {
    console.log("Connected");
    socket.sendSubscribe({
      type: "subscribe",
      inboxIds: ["agent@agentmail.to"],
    });
  });

  socket.on("message", (event: AgentMail.MessageReceivedEvent) => {
    if (event.type === "message.received") {
      console.log("From:", event.message.from_);
      console.log("Subject:", event.message.subject);
    }
  });

  socket.on("close", (event) => console.log("Disconnected:", event.code));
  socket.on("error", (error) => console.error("Error:", error));
}

main();
```

### React Hook

```typescript
import { useEffect, useState } from "react";
import { AgentMailClient, AgentMail } from "agentmail";

function useAgentMailWebSocket(apiKey: string, inboxIds: string[]) {
  const [lastMessage, setLastMessage] =
    useState<AgentMail.MessageReceivedEvent | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    const client = new AgentMailClient({ apiKey });
    let socket: Awaited<ReturnType<typeof client.websockets.connect>>;

    async function connect() {
      socket = await client.websockets.connect();

      socket.on("open", () => {
        setIsConnected(true);
        socket.sendSubscribe({ type: "subscribe", inboxIds });
      });

      socket.on("message", (event) => {
        if (event.type === "message.received") {
          setLastMessage(event);
        }
      });

      socket.on("close", () => setIsConnected(false));
    }

    connect();
    return () => socket?.close();
  }, [apiKey, inboxIds.join(",")]);

  return { lastMessage, isConnected };
}
```

## Python SDK

### Sync Usage

```python
from agentmail import AgentMail, Subscribe, Subscribed, MessageReceivedEvent

client = AgentMail(api_key="YOUR_API_KEY")

with client.websockets.connect() as socket:
    # Subscribe to inboxes
    socket.send_subscribe(Subscribe(inbox_ids=["agent@agentmail.to"]))

    # Process events
    for event in socket:
        if isinstance(event, Subscribed):
            print(f"Subscribed to: {event.inbox_ids}")
        elif isinstance(event, MessageReceivedEvent):
            print(f"From: {event.message.from_}")
            print(f"Subject: {event.message.subject}")
```

### Async Usage

```python
import asyncio
from agentmail import AsyncAgentMail, Subscribe, MessageReceivedEvent

client = AsyncAgentMail(api_key="YOUR_API_KEY")

async def main():
    async with client.websockets.connect() as socket:
        await socket.send_subscribe(Subscribe(inbox_ids=["agent@agentmail.to"]))

        async for event in socket:
            if isinstance(event, MessageReceivedEvent):
                print(f"New: {event.message.subject}")

asyncio.run(main())
```

### Event Handler Pattern

```python
import threading
from agentmail import AgentMail, Subscribe, EventType

client = AgentMail(api_key="YOUR_API_KEY")

with client.websockets.connect() as socket:
    socket.on(EventType.OPEN, lambda _: print("Connected"))
    socket.on(EventType.MESSAGE, lambda msg: print("Received:", msg))
    socket.on(EventType.CLOSE, lambda _: print("Disconnected"))
    socket.on(EventType.ERROR, lambda err: print("Error:", err))

    socket.send_subscribe(Subscribe(inbox_ids=["agent@agentmail.to"]))

    # Run listener in background thread
    listener = threading.Thread(target=socket.start_listening, daemon=True)
    listener.start()
    listener.join()
```

## Subscribe Options

Filter events by inbox, pod, or event type.

```typescript
socket.sendSubscribe({
  type: "subscribe",
  inboxIds: ["agent@agentmail.to"],
  eventTypes: ["message.received", "message.sent"],
});

// By pods
socket.sendSubscribe({
  type: "subscribe",
  podIds: ["pod_123", "pod_456"],
});
```

```python
from agentmail import Subscribe

# By inboxes
Subscribe(inbox_ids=["inbox1@agentmail.to", "inbox2@agentmail.to"])

# By pods
Subscribe(pod_ids=["pod_123", "pod_456"])

# By event types
Subscribe(
    inbox_ids=["agent@agentmail.to"],
    event_types=["message.received", "message.sent"]
)
```

## Event Types

| Event                  | TypeScript Type                    | Python Class             |
| ---------------------- | ---------------------------------- | ------------------------ |
| Subscription confirmed | `AgentMail.Subscribed`             | `Subscribed`             |
| New email received     | `AgentMail.MessageReceivedEvent`   | `MessageReceivedEvent`   |
| Email sent             | `AgentMail.MessageSentEvent`       | `MessageSentEvent`       |
| Email delivered        | `AgentMail.MessageDeliveredEvent`  | `MessageDeliveredEvent`  |
| Email bounced          | `AgentMail.MessageBouncedEvent`    | `MessageBouncedEvent`    |
| Spam complaint         | `AgentMail.MessageComplainedEvent` | `MessageComplainedEvent` |
| Email rejected         | `AgentMail.MessageRejectedEvent`   | `MessageRejectedEvent`   |
| Domain verified        | `AgentMail.DomainVerifiedEvent`    | `DomainVerifiedEvent`    |

## Message Properties

The `event.message` object contains:

| Property      | Description                   |
| ------------- | ----------------------------- |
| `inbox_id`    | Inbox that received the email |
| `message_id`  | Unique message ID             |
| `thread_id`   | Conversation thread ID        |
| `from_`       | Sender email address          |
| `to`          | Recipients list               |
| `subject`     | Subject line                  |
| `text`        | Plain text body               |
| `html`        | HTML body (if present)        |
| `attachments` | List of attachments           |

## Error Handling

```typescript
import { AgentMailClient, AgentMailError } from "agentmail";

try {
  const socket = await client.websockets.connect();
  // ...
} catch (err) {
  if (err instanceof AgentMailError) {
    console.error(`API error: ${err.statusCode} - ${err.message}`);
  } else {
    console.error("Connection error:", err);
  }
}
```

```python
from agentmail import AsyncAgentMail, Subscribe, MessageReceivedEvent
from agentmail.core.api_error import ApiError

client = AsyncAgentMail(api_key="YOUR_API_KEY")

async def main():
    try:
        async with client.websockets.connect() as socket:
            await socket.send_subscribe(Subscribe(inbox_ids=["agent@agentmail.to"]))

            async for event in socket:
                if isinstance(event, MessageReceivedEvent):
                    await process_email(event.message)

    except ApiError as e:
        print(f"API error: {e.status_code} - {e.body}")
    except Exception as e:
        print(f"Connection error: {e}")
```
