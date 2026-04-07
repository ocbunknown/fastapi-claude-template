---
name: api-client
description: Use when integrating an external HTTP API (Stripe, GitHub, Twilio, a payment provider, etc.) into the project. Enforces the Client + Service split — Client lives in infrastructure and returns raw vendor-shaped Pydantic responses, Service lives in application and maps raw responses to application `Result` types. Covers where to put ports, vendor enums, raw response DTOs, how to wire DI, and how to let a use case access a raw response when it genuinely needs one.
---

# Integrating an external HTTP API

An external API integration is **two objects**, not one:

1. **Client** (`infrastructure/http/clients/<vendor>/`) — thin HTTP wrapper. Returns **raw vendor-shaped Pydantic models** that mirror the API's JSON 1:1. No business logic, no transformation, no domain types.
2. **Service** (`application/v1/services/<vendor>.py`) — holds a Client via its port, calls it, and **maps raw responses into application `Result` types**. All business rules (enum mapping, filtering, multi-call orchestration) live here. The service **never** returns `Create*Type` / `Update*Type` — persistence shape is the use case's job.

Use cases depend on the **Service**. In rare cases (debug/proxy/admin) they can depend on the **Client port** directly. Examples below use a Stripe-shaped payment provider — substitute your vendor.

## Layer split

The project's rule (`CLAUDE.md`): `application/` **cannot** import from `infrastructure/`; `infrastructure/` **can** import from `application/`. Every type application-code reads must live in `application/`.

```
src/
├── application/
│   ├── common/interfaces/<vendor>/
│   │   ├── port.py              ← Protocol <Vendor>Client
│   │   ├── types.py             ← VENDOR enums/literals
│   │   └── responses.py         ← raw Pydantic DTOs (1:1 with API JSON)
│   ├── v1/results/<entity>.py   ← application Result (PaymentResult, …)
│   └── v1/services/<vendor>.py  ← <Vendor>Service: raw → Result
│
└── infrastructure/http/clients/<vendor>/
    ├── client.py                ← <Vendor>API(Client) — implements port structurally
    └── endpoints.py              ← StrEnum of URL paths
```

Raw response DTOs and vendor enums live in `application/` because the service in application reads them. They become **part of the port contract** — the same pattern as `JWT`/`TokenType`, `Cache`/`CacheKey`: the port owns its vocabulary.

## The Client — raw and dumb

Jobs: know the vendor's URL/auth, send HTTP, parse JSON into application-defined DTOs, translate HTTP errors into application exceptions. **Never** contains business branching or domain types.

```python
# src/infrastructure/http/clients/stripe/endpoints.py
from enum import StrEnum

class StripeEndpoints(StrEnum):
    CHARGES = "/v1/charges"
    CUSTOMERS = "/v1/customers"
```

```python
# src/infrastructure/http/clients/stripe/client.py
from enum import StrEnum
from typing import Optional, Unpack

from src.application.common.interfaces.stripe import responses as res
from src.application.common.interfaces.stripe.types import StripeChargeStatus, StripeCurrency
from src.infrastructure.http.clients.base import Client
from src.infrastructure.http.clients.stripe.endpoints import StripeEndpoints
from src.infrastructure.http.provider.aiohttp import ParamsType
from src.infrastructure.http.provider.base import AsyncProvider
from src.settings.core import StripeSettings


class StripeAPI(Client):
    __slots__ = ("_settings",)

    def __init__(
        self,
        settings: StripeSettings,
        provider: AsyncProvider | None = None,
        *,
        proxy: str | None = None,
        **options: Unpack[ParamsType],
    ) -> None:
        super().__init__(settings.base_url, provider, proxy=proxy, **options)
        self._settings = settings

    async def get_charge_by_id(self, charge_id: str) -> res.ChargeResponse:
        payload = await (
            await self._provider.make_request(
                "GET",
                self.endpoint_url(f"{StripeEndpoints.CHARGES}/{charge_id}"),
            )
        ).json()
        return res.ChargeResponse(**payload)

    async def list_charges(
        self,
        *,
        status: Optional[StripeChargeStatus] = None,
        currency: Optional[StripeCurrency] = None,
        limit: Optional[int] = None,
    ) -> list[res.ChargeResponse]:
        params = {
            k: v.value if isinstance(v, StrEnum) else v
            for k, v in {"status": status, "currency": currency, "limit": limit}.items()
            if v is not None
        }
        payload = await (
            await self._provider.make_request(
                "GET", self.endpoint_url(StripeEndpoints.CHARGES), params=params,
            )
        ).json()
        return [res.ChargeResponse(**item) for item in payload["data"]]
```

**`StripeAPI` does NOT inherit from the `StripeClient` protocol.** Python's `Protocol` is structural — matching method signatures make `StripeAPI` satisfy `StripeClient` automatically. Explicit inheritance is redundant and complicates `__slots__`/MRO. Inherit only from `Client`.

## The port

```python
# src/application/common/interfaces/stripe/port.py
from typing import Optional, Protocol

from src.application.common.interfaces.stripe import responses as res
from src.application.common.interfaces.stripe.types import StripeChargeStatus, StripeCurrency


class StripeClient(Protocol):
    async def get_charge_by_id(self, charge_id: str) -> res.ChargeResponse: ...

    async def list_charges(
        self,
        *,
        status: Optional[StripeChargeStatus] = None,
        currency: Optional[StripeCurrency] = None,
        limit: Optional[int] = None,
    ) -> list[res.ChargeResponse]: ...
```

Keep the port small — only methods the service (or raw-access use case) actually calls. If filters grow big, take a DTO instead of 20 keyword args.

## Raw response DTOs

Pydantic models that mirror the vendor's JSON field-for-field. Use `alias_generator=to_camel` only if the vendor sends camelCase. Mark fields `Optional` unless guaranteed — vendors drop fields without notice. `extra="ignore"` so new vendor fields never break deserialization.

```python
# src/application/common/interfaces/stripe/responses.py
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class BaseResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class ChargeResponse(BaseResponse):
    id: Optional[str] = None
    amount: Optional[int] = None          # minor units (cents)
    currency: Optional[str] = None
    status: Optional[str] = None
    paid: Optional[bool] = None
    refunded: Optional[bool] = None
    captured: Optional[bool] = None
    customer: Optional[str] = None
    description: Optional[str] = None
    created: Optional[datetime] = None
```

The vocabulary is the **vendor's**: `captured`, `refunded`, minor units. These models never pretend to be domain objects.

## Vendor enums

```python
# src/application/common/interfaces/stripe/types.py
from enum import StrEnum


class StripeChargeStatus(StrEnum):
    SUCCEEDED = "succeeded"
    PENDING = "pending"
    FAILED = "failed"


class StripeCurrency(StrEnum):
    USD = "usd"
    EUR = "eur"
    GBP = "gbp"
```

**NOT a duplicate** of any domain enum in `database/models/types.py` (e.g. `PaymentStatusEnum`). The vendor enum describes "what the vendor sends on the wire"; the domain enum describes "how we model the concept internally". They usually diverge — the domain has values the vendor doesn't (`REFUNDED` inferred from flags) or vice versa. The service bridges them.

**Stays in `infrastructure/`**: HTTP method literals, auth scheme literals, `aiohttp.ClientTimeout`/`ClientSession`, URL path enums. Rule: does application-code outside the port reference it? No → keep in infra.

## The Service — ACL

The service is the **Anti-Corruption Layer** (Evans, DDD ch.14). It depends on the **port** (`StripeClient`), not the concrete class. It returns application `Result` types and knows nothing about databases, ownership, or persistence shapes.

```python
# src/application/v1/results/payment.py
from decimal import Decimal
from typing import Optional

from src.application.v1.results.base import Result
from src.database.psql.models.types import PaymentStatusEnum


class PaymentResult(Result):
    external_id: str
    amount: Decimal
    currency: str
    status: PaymentStatusEnum
    description: Optional[str] = None
```

```python
# src/application/v1/services/stripe.py
from dataclasses import dataclass
from decimal import Decimal

from src.application.common.interfaces.stripe import responses as res
from src.application.common.interfaces.stripe.port import StripeClient
from src.application.common.interfaces.stripe.types import StripeChargeStatus
from src.application.v1.results.payment import PaymentResult
from src.database.psql.models.types import PaymentStatusEnum


@dataclass(slots=True)
class StripeService:
    client: StripeClient

    async def fetch_successful_charges(self, *, limit: int = 100) -> list[PaymentResult]:
        raw = await self.client.list_charges(status=StripeChargeStatus.SUCCEEDED, limit=limit)
        return [self._to_payment(c) for c in raw if c.id]

    def _to_payment(self, charge: res.ChargeResponse) -> PaymentResult:
        return PaymentResult(
            external_id=charge.id or "",
            amount=Decimal(charge.amount or 0) / Decimal(100),  # minor → major
            currency=(charge.currency or "").upper(),
            status=self._infer_status(charge),
            description=charge.description,
        )

    @staticmethod
    def _infer_status(charge: res.ChargeResponse) -> PaymentStatusEnum:
        if charge.refunded:
            return PaymentStatusEnum.REFUNDED
        if charge.status == StripeChargeStatus.SUCCEEDED and charge.captured:
            return PaymentStatusEnum.COMPLETED
        if charge.status == StripeChargeStatus.PENDING:
            return PaymentStatusEnum.PENDING
        return PaymentStatusEnum.FAILED
```

What's **not** here:
- No `user_uuid` / ownership params — that's a use-case concern.
- No `CreatePaymentType` import — persistence shape is unknown to the service.
- No `self.database` — a service that opens transactions is a mini-use-case, not an ACL.

## The use case

Takes `PaymentResult` from the service, attaches ownership, reshapes into `CreatePaymentType`, persists. The **only** place where all three vocabularies meet.

```python
# src/application/v1/usecases/payments/sync_stripe.py
from dataclasses import dataclass

import uuid_utils.compat as uuid

from src.application.common.interfaces.usecase import UseCase
from src.application.common.request import Request
from src.application.v1.results import SyncResult
from src.application.v1.results.payment import PaymentResult
from src.application.v1.services.stripe import StripeService
from src.database.psql import DBGateway
from src.database.psql.types.payment import CreatePaymentType


class SyncStripePaymentsRequest(Request):
    user_uuid: uuid.UUID
    limit: int = 100


@dataclass(slots=True)
class SyncStripePaymentsUseCase(UseCase[SyncStripePaymentsRequest, SyncResult]):
    database: DBGateway
    stripe: StripeService

    async def __call__(self, request: SyncStripePaymentsRequest) -> SyncResult:
        payments = await self.stripe.fetch_successful_charges(limit=request.limit)
        rows = [self._to_row(p, request.user_uuid) for p in payments]
        async with self.database:
            created = await self.database.payment.bulk_create(rows)
        return SyncResult(count=len(created))

    @staticmethod
    def _to_row(payment: PaymentResult, user_uuid: uuid.UUID) -> CreatePaymentType:
        return {
            "external_id": payment.external_id,
            "amount": payment.amount,
            "currency": payment.currency,
            "status": payment.status,
            "description": payment.description,
            "user_uuid": user_uuid,
        }
```

Three-vocabulary separation:

| Layer | Reads | Writes |
|---|---|---|
| Client | HTTP/JSON | `res.ChargeResponse` (vendor) |
| Service | `res.ChargeResponse` | `PaymentResult` (application) |
| Use case | `PaymentResult` | `CreatePaymentType` (persistence) |
| Repository | `CreatePaymentType` | ORM row |

No layer sees two vocabularies except on its own translation boundary.

## DI wiring

```python
# src/infrastructure/provider.py
@provide
def stripe_client(self, provider: AiohttpProvider, settings: Settings) -> StripeClient:
    return StripeAPI(settings=settings.stripe, provider=provider)

# src/application/provider.py
stripe_service = provide(StripeService, scope=Scope.REQUEST)
```

Return type of the infra provider is the **port** (`StripeClient`), not `StripeAPI`. Dishka resolves `StripeClient` through the port — use case code asks for the port, gets the concrete class.

## Raw response in a use case — rare legal path

When the use case is a pure passthrough (debug endpoint echoing raw vendor data, admin proxy, raw-log pipeline) and has **no** business transformation, inject the **client port directly** — skip the service entirely. Don't invent a service with a single wrapper method just for symmetry.

```python
@dataclass(slots=True)
class DebugFetchChargeUseCase(UseCase[DebugFetchChargeRequest, res.ChargeResponse]):
    stripe: StripeClient   # ← port directly

    async def __call__(self, request: DebugFetchChargeRequest) -> res.ChargeResponse:
        return await self.stripe.get_charge_by_id(request.charge_id)
```

Guardrails: keep it **rare** (>2-3 such use cases → extract a service); expose only via `admin/` or `internal/` audiences; never via `public/`/`user/`.

## The one rule for service + client dependencies

> **A use case depends on *either* the service *or* the client port — never both. If you want both, add a method to the service.**

Three cases:

1. **Service exists** → use case only injects the service. Anything the use case needs (transformed, raw, combination) is a method on the service. The service internally calls the client — that's its `client: <Vendor>Client` field's whole reason to exist.
2. **No service** (pure passthrough) → use case injects the port directly.
3. **Anti-pattern** — use case dataclass with both `stripe_service: StripeService` and `stripe_client: StripeClient` fields. Two overlapping dependencies, no single place where "all vendor calls live". Caches/retries/logging added to the service silently skip calls that went around it.

If the use case needs both transformed and raw (e.g. persist + dump raw to audit log), add a method to the service that returns a tuple — the use case keeps a single dependency.

## Import direction

| From | To | Allowed? |
|---|---|---|
| `application/v1/services/<vendor>.py` | `application/common/interfaces/<vendor>/` | yes |
| `application/v1/usecases/...` | `application/v1/services/<vendor>.py` | yes |
| `application/v1/usecases/...` | `application/common/interfaces/<vendor>/` | yes (raw-access only) |
| `application/v1/usecases/...` | `infrastructure/http/clients/<vendor>/` | **no** |
| `infrastructure/http/clients/<vendor>/` | `application/common/interfaces/<vendor>/` | yes |
| `infrastructure/http/clients/<vendor>/` | `application/v1/services/<vendor>.py` | **no** |
| `application/common/interfaces/<vendor>/` | `infrastructure/` | **no** |

## Anti-patterns

| ❌ | Why it breaks | ✅ |
|---|---|---|
| Client returns `dict[str, Any]` | Vendor field changes break use cases silently; no IDE completion | Typed Pydantic from `application/common/interfaces/<vendor>/responses.py` |
| Client contains domain branching (`if user.is_premium: ...`) | Business logic in infra; can't swap client | Move branching to service |
| Service imports `StripeAPI` concrete class | Layer violation; untestable without real HTTP | Depend on `StripeClient` Protocol |
| DI provider returns concrete `StripeAPI` instead of port | Intent hidden; fragile resolution | Provider signature `-> StripeClient` |
| Service returns `list[CreatePaymentType]` / any persistence TypedDict | Anemic — service becomes an `INSERT`-param generator; couples ACL to DB schema | Return `list[PaymentResult]`; use case reshapes before `bulk_create` |
| Service accepts `user_uuid` / ownership as param | Ownership is use-case concern; service shouldn't know "whose charges" | Remove; use case attaches during `Result` → `CreateType` mapping |
| Client inherits both `Client` and `Protocol` (`class StripeAPI(Client, StripeClient):`) | Protocol is structural — inheritance redundant, complicates `__slots__`/MRO | `class StripeAPI(Client):` only |
| Use case dataclass has both service and client port fields | Two overlapping deps; no single place for cross-cutting concerns | Add method to service; remove client field |
| `aiohttp.ClientTimeout`/`ClientSession` in port signature | Infra type in application — hard layer violation | Accept plain `float`/`int`; client converts internally |
| Unifying `StripeChargeStatus` with `PaymentStatusEnum` | Vendor vocabulary contaminates domain | Keep separate; bridge in `_infer_status` |
| Vendor raw responses flowing to `public/` endpoint | Public API coupled to vendor wire format | Expose only via `admin/`/`internal/` |

## Checklist for a new vendor

1. `application/common/interfaces/<vendor>/` — `port.py`, `types.py`, `responses.py`, `__init__.py`.
2. `application/v1/results/<entity>.py` — `<Entity>Result` the service will return.
3. `infrastructure/http/clients/<vendor>/` — `client.py` (inherits `Client` **only**), `endpoints.py`.
4. `application/v1/services/<vendor>.py` — `@dataclass(slots=True)` with `client: <Vendor>Client`. Methods return `Result`, **never** `Create*Type`. No ownership params.
5. `infrastructure/provider.py` — `@provide` returning the **port type**.
6. `application/provider.py` — `@provide` for the service (or add to `ServiceGateway`).
7. Use case depends on the service (normal) or the port (raw-access). Use case does `Result` → `Create*Type` mapping.
8. Tests: unit-test the service with a fake client (plain class satisfying the Protocol structurally); integration-test the real client against `aioresponses`.
