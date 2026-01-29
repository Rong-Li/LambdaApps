# Authentication (iOS + API Gateway)

## Current State

The API has **no authentication** today. Any client that knows the API URL can call it. This is fine for local or internal use only.

## Recommended: Cognito User Pools + JWT Authorizer

For an **iOS mobile app** calling API Gateway, the standard AWS approach is:

1. **Amazon Cognito User Pools** – User sign‑in (email/password, social, etc.). Cognito issues **JWT** (ID token / access token).
2. **API Gateway JWT Authorizer** – API Gateway validates the JWT before invoking your Lambda. Invalid or missing token → 401.
3. **iOS app** – Sends the token in the `Authorization` header on every request.

```
┌─────────────────┐     Authorization: Bearer <jwt>     ┌──────────────────┐     ┌─────────────────┐
│   iOS App       │────────────────────────────────────▶│  API Gateway     │────▶│  Lambda (API)   │
│   (Cognito SDK) │◀─── JWT from Cognito sign‑in ────────│  JWT Authorizer  │     │  (only if OK)   │
└─────────────────┘                                     └──────────────────┘     └─────────────────┘
```

### Why this fits iOS

- Cognito has an **iOS SDK** (and Amplify) for sign‑in and token refresh.
- JWTs are short‑lived; refresh is handled by the SDK.
- Validation happens in **API Gateway**; your Lambda only runs when the token is valid.
- You can pass **user identity** (e.g. `sub`) into the Lambda via the authorizer context.

### What you need to set up

| Step | Where | What |
|------|--------|------|
| 1 | **Cognito** | Create a User Pool. Configure app client (e.g. no client secret for mobile). Note **User Pool ID** and **region**. |
| 2 | **API Gateway** | Create a **JWT authorizer** for the HTTP API: issuer = `https://cognito-idp.{region}.amazonaws.com/{userPoolId}`, audience = your app client ID. Attach this authorizer to your routes (or the whole API). |
| 3 | **iOS** | Use **Amplify Auth** or **AWS SDK** to sign in, get the ID or access token, and send it as `Authorization: Bearer <token>` on each request. |

No code changes are required inside the Lambda for “is this request allowed?” – API Gateway enforces that. You only need to **read the user id** from the request when you want to scope data (e.g. by `sub`). A small helper for that is in `service/api/auth.py` (see below).

---

## Request format (once authorizer is on)

| Header | Value |
|--------|--------|
| `Authorization` | `Bearer <JWT>` (ID token or access token from Cognito) |

If the authorizer is attached and the token is missing or invalid, API Gateway returns **401 Unauthorized** and does not call the Lambda.

---

## Reading the current user in Lambda

After you attach a JWT authorizer, API Gateway passes decoded claims into the request context. Use the helper in `service.api.auth` to get the current user id (Cognito `sub`) so you can scope expenses or reports by user when you add multi‑tenancy.

---

## Alternatives (brief)

| Option | Pros | Cons |
|--------|------|------|
| **Cognito + JWT** | Native AWS, good for mobile, no custom token logic | Requires Cognito and API Gateway config |
| **Lambda authorizer** | Any JWT (e.g. Auth0, Firebase) | Extra Lambda, more moving parts |
| **API Key** | Very simple | Not ideal for mobile (key can be extracted); better for server‑to‑server |

For an iOS app, **Cognito + JWT authorizer** is the recommended path.
