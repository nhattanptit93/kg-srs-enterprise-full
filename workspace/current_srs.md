# Software Requirements Specification
## FoodSwift — Food Delivery Platform

**Version:** 1.0
**Date:** 2025-01-15
**Author:** SRS Agent (Automated)
**Document ID:** SRS-FOODSWIFT-001

---

### Revision History

| Version | Date | Description | Author |
|---------|------|-------------|--------|
| 1.0 | 2025-01-15 | Initial generation from knowledge graph | SRS Agent |

---

## Table of Contents

1. Introduction
   1.1 Purpose
   1.2 Scope
   1.3 Definitions, Acronyms, and Abbreviations
   1.4 References
2. Overall Description
   2.1 Product Perspective
   2.2 Product Functions (Summary)
   2.3 User Classes and Characteristics
   2.4 Operating Environment
   2.5 Design and Implementation Constraints
   2.6 Assumptions and Dependencies
3. System Features (Functional Requirements)
   3.1 Account Management & Authentication
   3.2 Restaurant Discovery & Browsing
   3.3 Cart Management
   3.4 Order Placement & Lifecycle
   3.5 Payment Processing
   3.6 Order Dispatch & Delivery Tracking
   3.7 Notifications
   3.8 Cancellation & Refund
   3.9 Ratings, Reviews, and Disputes
   3.10 Admin & Restaurant Operations
4. External Interface Requirements
5. Non-Functional Requirements
6. Data Requirements
7. Appendices

---

## 1. Introduction

### 1.1 Purpose

This Software Requirements Specification (SRS) defines the functional and non-functional requirements of **FoodSwift**, a multi-sided food delivery platform connecting customers, restaurants, and delivery drivers. The document is intended for:

- Software engineers and architects implementing the system
- QA engineers designing verification test suites
- Product managers and business stakeholders
- Operations and compliance teams
- Third-party integration partners (payment, mapping, messaging)

### 1.2 Scope

**Product Name:** FoodSwift Food Delivery Platform.

**What the system does:**
- Enables customers to discover restaurants, browse menus, place orders, pay digitally or via cash-on-delivery (COD), and track deliveries in real time.
- Enables restaurant staff to receive, confirm, prepare, and dispatch orders.
- Enables delivery drivers to accept assignments, navigate to pickup/dropoff locations, and complete deliveries.
- Enables administrators to onboard restaurants, resolve disputes, and oversee platform integrity.
- Integrates with external payment gateways (VNPay, Momo, Stripe), mapping services (Google Maps, Mapbox), push notification services (FCM, APNs), and SMS/Email services.

**What the system does NOT do:**
- Does not store raw card data (PCI-DSS Level 1 redirect/tokenization model).
- Does not provide in-house mapping or routing computation; relies on external providers.
- Does not employ drivers (they are independent contractors).
- Does not produce or fulfill food (restaurants do).

**Benefits and Objectives:**
- Reduce order placement to confirmation latency to under 30 seconds.
- Achieve ETA accuracy of ±3 minutes for 90% of deliveries.
- Provide 99.9% platform availability.
- Enable secure, auditable financial transactions with ≥7 years retention.

### 1.3 Definitions, Acronyms, and Abbreviations

| Term | Definition |
|------|-----------|
| Account | Authentication record linking a user identity to credentials and sessions |
| ABAC | Attribute-Based Access Control |
| APNs | Apple Push Notification service |
| COD | Cash On Delivery — payment in cash to driver upon delivery |
| Customer | End-user placing food orders via mobile app |
| Dispatcher | Internal subsystem matching orders to available drivers |
| Driver | Independent contractor who picks up and delivers orders |
| ETA | Estimated Time of Arrival |
| FCM | Firebase Cloud Messaging |
| GDPR | General Data Protection Regulation |
| HMAC | Hash-based Message Authentication Code |
| Idempotency Key | Unique client-supplied token preventing duplicate processing of the same request |
| MFA | Multi-Factor Authentication |
| MTBF | Mean Time Between Failures |
| MTTR | Mean Time To Recovery |
| OTP | One-Time Password |
| PCI-DSS | Payment Card Industry Data Security Standard |
| PII | Personally Identifiable Information |
| RBAC | Role-Based Access Control |
| Refund Tier | Authorization level required to approve a refund based on monetary threshold |
| SLA | Service Level Agreement |
| SRS | Software Requirements Specification |
| TBD | To Be Determined |
| VND | Vietnamese Dong (currency) |
| WCAG | Web Content Accessibility Guidelines |

### 1.4 References

- IEEE Std 830-1998 — IEEE Recommended Practice for Software Requirements Specifications
- ISO/IEC/IEEE 29148:2018 — Systems and software engineering — Life cycle processes — Requirements engineering
- PCI-DSS v4.0 — Payment Card Industry Data Security Standard
- WCAG 2.1 Level AA — Web Content Accessibility Guidelines
- GDPR (EU 2016/679) and Vietnam's Decree 13/2023/ND-CP on Personal Data Protection
- OWASP Application Security Verification Standard (ASVS) v4.0

---

## 2. Overall Description

### 2.1 Product Perspective

FoodSwift is a cloud-hosted, mobile-first marketplace consisting of:

- **Customer mobile application** (iOS, Android)
- **Restaurant operations app** (tablet-optimized)
- **Driver mobile application** (Android primary, iOS supported)
- **Admin web console** (browser-based)
- **Backend API services** (RESTful + WebSocket for real-time tracking)
- **Internal subsystems**: Order Dispatcher, ETA Calculator
- **External dependencies**: Payment Gateways (VNPay, Momo, Stripe), Map Service (Google Maps / Mapbox), Push Notification Service (FCM, APNs), SMS/Email Service

**System Context (textual diagram):**

```
[Customer App] ─┐
[Restaurant App] ┼─→ [API Gateway] ─→ [Core Services] ─┬─→ [PostgreSQL]
[Driver App] ───┤                                       ├─→ [Redis Cache]
[Admin Console] ┘                                       └─→ [Audit Store]
                                                                 │
                External: [Payment Gateway] [Map Service] [FCM/APNs] [SMS/Email]
```

### 2.2 Product Functions (Summary)

The platform shall provide the following major function groups (detailed in Section 3):

- F1: Account registration, OTP verification, login/logout, session management
- F2: Restaurant discovery, search, filtering, and menu browsing
- F3: Cart creation and management (single-restaurant constraint)
- F4: Order placement, lifecycle state management, and ETA calculation
- F5: Payment authorization, capture, COD handling, and HMAC-verified webhook processing
- F6: Driver dispatch, real-time location tracking, and masked communication
- F7: Multi-channel notifications (push, SMS, email)
- F8: Order cancellation and tiered refund authorization
- F9: Ratings, reviews (with profanity filter), and dispute management
- F10: Restaurant onboarding, menu administration, and admin operations

### 2.3 User Classes and Characteristics

| User Class | Description | Technical Proficiency | Frequency | Privilege |
|-----------|-------------|----------------------|-----------|-----------|
| Customer | End-user ordering food | Low to medium | Daily to weekly | Self-service over own data |
| Restaurant Staff | Receives and confirms orders | Low to medium | Continuous during operating hours | Restaurant-scoped operations |
| Delivery Driver | Picks up and delivers orders | Low to medium | Continuous when on shift | Delivery-scoped operations |
| Admin | Manages platform | High | Daily | Platform-wide privileged access |
| Payment Gateway | External system | N/A (system actor) | On-demand per transaction | Authenticated webhook callbacks |
| Map Service | External system | N/A | On-demand for routing/ETA | Read-only API consumer |
| Push Notification Service | External system | N/A | On-demand per event | Outbound API consumer |
| SMS/Email Service | External system | N/A | On-demand per OTP/notification | Outbound API consumer |

### 2.4 Operating Environment

- **Customer / Driver mobile clients:** iOS 14+ and Android 9+ (API level 28+).
- **Restaurant client:** Android 10+ tablet (10-inch class) or iPad iOS 14+.
- **Admin console browsers:** Latest two major versions of Chrome, Edge, Firefox, Safari.
- **Backend:** Linux-based container orchestration (Kubernetes) on a major cloud (AWS, GCP, or Azure).
- **Database:** PostgreSQL 14+; Redis 6+ for caching and session storage.
- **Network:** TLS 1.2+ for all client-server communication; WebSocket Secure (WSS) for live tracking.

### 2.5 Design and Implementation Constraints

- **DC-1:** No raw card data shall be stored on platform infrastructure (PCI-DSS scope minimization).
- **DC-2:** All state-mutating API endpoints shall accept an `Idempotency-Key` header with a 24-hour replay window.
- **DC-3:** All inbound webhooks (payment gateway callbacks) shall require HMAC-SHA256 signature verification before processing.
- **DC-4:** Refund authorization shall follow a tiered model based on VND amount thresholds (see REQ-F-082).
- **DC-5:** OTP delivery and verification shall use SMS/Email service; OTP secrets shall not be logged.
- **DC-6:** Driver phone numbers shared with customers shall be masked via virtual numbers.
- **DC-7:** Audit logs for financial transactions shall be retained for ≥ 7 years.
- **DC-8:** All UI shall support Vietnamese (vi-VN) and English (en-US) at minimum.

### 2.6 Assumptions and Dependencies

- **A-1:** External payment gateways (VNPay, Momo, Stripe) provide ≥ 99.5% availability.
- **A-2:** Map service provides geocoding, routing, and travel-time APIs with documented rate limits.
- **A-3:** Push notification service (FCM/APNs) device tokens are valid and refreshed by client SDKs.
- **A-4:** Customers possess a phone number capable of receiving SMS for OTP.
- **A-5:** Drivers' devices have GPS hardware and grant location permission to the driver app.
- **A-6:** Restaurant staff devices remain online during operating hours; offline order receipt is out of scope for v1.

---

## 3. System Features (Functional Requirements)

---

### 3.1 Account Management & Authentication

**Description and Priority**
Manages registration, OTP verification, login, session lifecycle, and account state transitions for all user classes.
- Priority: Essential
- Stability: Fixed

#### REQ-F-001: Customer Registration with Phone Number
**Description:** The system shall allow a customer to register an account using a unique phone number, name, email, password, and preferred language.
**Rationale:** Establishes verifiable identity for ordering and payment.
**Inputs:** phoneNumber (E.164 format), name, email, password, preferredLanguage (vi/en).
**Processing:**
1. Validate phoneNumber uniqueness against `Account` records.
2. Validate password meets policy (≥ 10 chars, mixed case, digit, symbol).
3. Hash password using Argon2id (memory ≥ 64MB, iterations ≥ 3).
4. Create `Account` record in state `pending_verification`.
5. Trigger OTP generation (REQ-F-003).
**Outputs:** accountId returned to client; OTP sent via SMS/Email service.
**Error Handling:** Return 409 Conflict if phoneNumber already registered; 400 Bad Request on validation failure.
**Priority:** Essential
**Source:** Customer entity; HAS Account; REQUIRES OTP Verification.
**Acceptance Criteria:**
- AC1: Given a new phone number, When the customer submits valid registration data, Then an account is created in `pending_verification` state and an OTP is dispatched within 30 seconds.
- AC2: Given an existing phone number, When registration is submitted, Then the system returns HTTP 409 with error code `PHONE_ALREADY_REGISTERED`.

#### REQ-F-002: Multi-Role Account Provisioning
**Description:** The system shall provision accounts for four user types: customer (self-service), restaurant staff (admin-provisioned), delivery driver (admin-provisioned with vehicle verification), and admin (admin-provisioned).
**Rationale:** Different user classes require different onboarding flows and trust levels.
**Inputs:** userType, identity payload, provisioning actor.
**Processing:** Apply user-type-specific validation; route through onboarding workflow.
**Outputs:** Provisioned account record.
**Error Handling:** Return 403 Forbidden if a non-admin attempts to provision staff/driver/admin.
**Priority:** Essential
**Source:** Customer/Restaurant Staff/Driver/Admin → HAS Account.
**Acceptance Criteria:**
- AC1: Given an admin actor, When provisioning a driver with valid vehicle registration, Then a driver account is created in `offline` lifecycle state.

#### REQ-F-003: OTP Generation and Delivery
**Description:** The system shall generate a 6-digit numeric OTP, store it with `expiresAt = now + 5 minutes`, and dispatch it via the SMS/Email service.
**Rationale:** Phone verification prevents fraudulent registrations.
**Inputs:** phoneNumber, deliveryChannel (SMS or email).
**Processing:**
1. Generate cryptographically secure 6-digit OTP.
2. Persist in `otp_verification` with attemptCount = 0, state = `sent`.
3. Invoke SMS/Email service.
**Outputs:** otpId, deliveryStatus.
**Error Handling:** If SMS/Email service returns failure, mark state = `failed` and surface retry option to client.
**Priority:** Essential
**Source:** OTP Verification entity; SMS/Email PRODUCES OTP.
**Acceptance Criteria:**
- AC1: Given a registration request, When OTP is generated, Then the SMS/Email service shall receive the request such that 95% of OTPs reach the recipient within 30 seconds.
- AC2: Given an OTP older than 5 minutes, When the customer submits it, Then the system rejects it with error `OTP_EXPIRED`.

#### REQ-F-004: OTP Verification with Attempt Limiting
**Description:** The system shall verify a submitted OTP against the stored record, enforcing maximum 5 attempts before locking the account for 30 minutes.
**Rationale:** Prevents brute-force attacks on OTP.
**Inputs:** phoneNumber, submitted OTP code.
**Processing:**
1. Locate active OTP record.
2. If `attemptCount >= 5`, lock the account (state = `locked`) for 30 minutes; return error.
3. Compare codes via constant-time comparison.
4. On match, set OTP state = `verified`; set Account state = `active`.
5. On mismatch, increment attemptCount.
**Outputs:** Verification status; account activation event.
**Error Handling:** Return 429 Too Many Requests when attempt limit exceeded.
**Priority:** Essential
**Source:** OTP constraints (max 5 attempts, 5-min expiry); Account lifecycle.
**Acceptance Criteria:**
- AC1: Given 5 failed attempts, When the 6th attempt is made, Then the account is locked for 30 minutes and a security audit log entry is created.
- AC2: Given a valid OTP within 5 minutes, When verified, Then Account state transitions from `pending_verification` to `active`.

#### REQ-F-005: OTP Resend Throttling
**Description:** The system shall allow at most 3 OTP resends per phone number per rolling 60-minute window.
**Rationale:** Prevents SMS abuse and cost inflation.
**Inputs:** phoneNumber.
**Processing:** Count resends in last 60 minutes; if ≥ 3, reject with error `OTP_RESEND_LIMIT_EXCEEDED`.
**Outputs:** New OTP or rejection.
**Error Handling:** Return 429 with retry-after header.
**Priority:** Essential
**Source:** OTP constraint (max 3 resends/hour).
**Acceptance Criteria:**
- AC1: Given 3 resends within the past hour, When a 4th is requested, Then the system returns HTTP 429.

#### REQ-F-006: User Login with Credentials
**Description:** The system shall authenticate users via phoneNumber + password (customers) or email + password (staff/admin/drivers) and issue a session token.
**Rationale:** Authenticated access to platform features.
**Inputs:** identifier, password.
**Processing:**
1. Locate Account; if state ≠ `active`, reject.
2. Verify password against stored hash (Argon2id).
3. Create `Session` with cryptographically random token, expiresAt = now + 30 days, deviceInfo captured.
4. Update Account.lastLoginAt.
**Outputs:** sessionToken, account profile.
**Error Handling:** Return 401 Unauthorized; do not disclose whether identifier or password was wrong.
**Priority:** Essential
**Source:** Account → Session HAS (1:N).
**Acceptance Criteria:**
- AC1: Given valid credentials, When login is attempted, Then a session token valid for 30 days is returned and stored.
- AC2: Given an account in `locked` state, When login is attempted, Then HTTP 423 Locked is returned.

#### REQ-F-007: Multi-Device Session Support
**Description:** The system shall allow each account to maintain up to 5 concurrent active sessions across devices.
**Rationale:** Customers use phone + tablet; admins use multiple workstations.
**Processing:** When a 6th session is created, revoke the oldest session (state = `revoked`).
**Priority:** Essential
**Source:** Account HAS Session (1:N).

#### REQ-F-008: Session Revocation and Logout
**Description:** The system shall support explicit logout (single session) and "logout all devices" (all sessions for the account).
**Outputs:** Session(s) marked `revoked`; subsequent requests with revoked tokens shall return 401.
**Priority:** Essential

#### REQ-F-009: Account Lifecycle State Transitions
**Description:** The system shall enforce the Account lifecycle states and transitions: `pending_verification` → `active` → (`locked` ↔ `active`) → `suspended` → `deleted`.
**Rationale:** Reflects security and operational events; aligns Account state names with REQ-F-001 to ensure consistent terminology across the SRS.
**Inputs:** State transition triggers (OTP verification success, login-failure threshold reached, admin suspension, scheduled deletion).
**Processing:**
1. `pending_verification` → `active`: triggered by successful OTP verification (REQ-F-004).
2. `active` → `locked`: triggered after 5 consecutive failed login attempts within 15 minutes; auto-unlocks after 30 minutes or admin override.
3. `locked` → `active`: triggered by successful password reset, admin unlock, or auto-unlock timer expiry.
4. `active`/`locked` → `suspended`: triggered by admin action (REQ-F-104) for policy violation.
5. `suspended` → `deleted`: triggered after 90 days in `suspended` state or upon GDPR/Decree-13 deletion request.
**Outputs:** Updated Account state; audit log entry per REQ-F-010; user notification on `suspended`/`deleted`.
**Error Handling:** Reject any transition not defined above with HTTP 409 and error code `INVALID_STATE_TRANSITION`.
**Priority:** Essential
**Source:** Account entity lifecycle; Security constraint.
**Acceptance Criteria:**
- AC1: Given an account in `suspended` state, When any authenticated action is attempted, Then HTTP 403 with code `ACCOUNT_SUSPENDED` is returned.
- AC2: Given an account in `pending_verification` state, When OTP verification succeeds, Then the account transitions to `active` within 1 second and an audit event is logged.
- AC3: Given an account in `active` state, When 5 failed login attempts occur within 15 minutes, Then the account transitions to `locked` and login is rejected with HTTP 423.

#### REQ-F-010: Audit Logging of Security Events
**Description:** The system shall write an audit log entry for the following account events: registration, login success, login failure, OTP failure burst, account lock, password change, session revocation, role change.
**Rationale:** Forensic traceability and compliance.
**Outputs:** `audit_log` record with entityType=`account`, action, actorId, timestamp, metadata.
**Priority:** Essential
**Source:** Account → Audit Log PRODUCES.

---

### 3.2 Restaurant Discovery & Browsing

#### REQ-F-011: Customer Address Management
**Description:** The system shall allow customers to create, list, update, soft-delete, and set a default delivery address with label, street, ward, district, city, and geographic coordinates.
**Inputs:** Address fields; coordinates from device GPS or map picker.
**Processing:** Validate coordinates via Map Service; persist Address.
**Priority:** Essential
**Source:** Customer MANAGES Address; Map Service VALIDATES Address.

#### REQ-F-012: Restaurant Discovery by Location
**Description:** The system shall return a paginated list of restaurants within a configurable delivery radius (default 5 km) of a customer's selected address, including name, image, cuisine tags, rating, deliveryFee, and current open/closed status.
**Inputs:** customerAddressId or coordinates; optional filters (cuisine, rating ≥ N, isOpen).
**Processing:**
1. Query restaurants where `isOpen = true` and within radius.
2. Apply filters and sort order (relevance, rating, deliveryFee).
3. Return paginated results (default 20 per page).
**Outputs:** List of restaurants with summary fields.
**Priority:** Essential
**Source:** Customer READS Restaurant.
**Acceptance Criteria:**
- AC1: Given 200 restaurants near a location, When the customer browses, Then the first page loads within 1.5 seconds (P95).

#### REQ-F-013: Restaurant Search
**Description:** The system shall support full-text search across restaurant name, cuisine tags, and menu item names, returning matching restaurants ranked by relevance.
**Rationale:** Enables customers to locate restaurants quickly using natural-language queries.
**Inputs:** searchQuery (1–100 chars, UTF-8), customerLocation (lat, lng), optional filters (cuisine, priceRange, minRating).
**Processing:**
1. Tokenize and normalize the query (lowercase, diacritic-folding for Vietnamese).
2. Execute full-text match against the search index (restaurant.name, restaurant.cuisineTags, menuItem.name).
3. Compute composite relevance score per result:
   `score = 0.45 × textRelevance + 0.25 × (1 / distanceKm) + 0.15 × averageRating + 0.10 × isOpenNow + 0.05 × popularity7d`
   where `textRelevance` is BM25, normalized to 0–1.
4. Filter out restaurants further than 10 km or in `closed`/`suspended` state.
5. Return top 50 results, paginated at 20 per page.
**Outputs:** Ranked list of restaurants with id, name, distance, rating, openStatus, ETA estimate.
**Error Handling:** Return empty list with HTTP 200 if no matches; return HTTP 400 if query is empty after trimming.
**Performance:** Search shall return results within **300 ms at the 95th percentile** under a load of 1,000 concurrent searches.
**Priority:** Essential
**Source:** Restaurant entity; Customer Discovery use case.
**Acceptance Criteria:**
- AC1: Given a customer issues query "pho", When the search executes, Then results are returned within 300 ms (p95) ordered by composite score.
- AC2: Given a query that matches no records, When executed, Then the system returns HTTP 200 with an empty list and a `NO_RESULTS` hint.
- AC3: Given two restaurants tie on text relevance, When ranked, Then the closer restaurant is ranked higher.

#### REQ-F-014: Cuisine Tag Filtering
**Description:** The system shall support filtering restaurants by one or more cuisine tags (localized in vi/en).
**Priority:** Essential
**Source:** Restaurant HAS Cuisine Tag (N:M).

#### REQ-F-015: Menu Item Browsing
**Description:** The system shall display all menu items for a selected restaurant grouped by category, including name, description, price, image, and availability flag.
**Outputs:** Menu items with `isAvailable` clearly indicated; unavailable items shall not be addable to cart.
**Priority:** Essential
**Source:** Restaurant HAS Menu Item; Customer READS Menu Item.

#### REQ-F-016: Operating Hours Enforcement
**Description:** The system shall display restaurants as `closed` when the current time is outside their operating hours and shall prevent new orders from closed restaurants.
**Priority:** Essential

---

### 3.3 Cart Management

#### REQ-F-017: Add Item to Cart
**Description:** The system shall allow a customer to add a menu item with a positive integer quantity and optional notes to a cart belonging to that menu item's restaurant.
**Processing:**
1. Locate or create active cart for (customerId, restaurantId).
2. Append cart_item; recompute subtotal.
**Outputs:** Updated cart state.
**Priority:** Essential
**Source:** Cart CONTAINS Cart Item.

#### REQ-F-018: Single-Restaurant Cart Constraint
**Description:** The system shall prevent a cart from containing items from more than one restaurant. When the customer adds an item from a different restaurant, the system shall prompt to discard the existing cart.
**Rationale:** Single-source delivery model.
**Outputs:** On confirmation, mark previous cart `abandoned` and create new cart.
**Priority:** Essential
**Source:** Cart constraint "items must belong to single restaurant".

#### REQ-F-019: Update Cart Item Quantity
**Description:** The system shall allow incrementing, decrementing (minimum 1), or removing items from an active cart and shall recompute subtotal in real time.
**Priority:** Essential

#### REQ-F-020: Cart Abandonment
**Description:** The system shall mark a cart as `abandoned` if it has not been modified or checked out within 24 hours.
**Priority:** Conditional

#### REQ-F-021: Checkout Precondition
**Description:** The system shall reject checkout when the cart contains zero items or when the associated restaurant is currently closed.
**Priority:** Essential
**Source:** Cart constraint "must contain ≥1 item to checkout".

---

### 3.4 Order Placement & Lifecycle

#### REQ-F-022: Idempotent Order Creation
**Description:** The system shall create an order from a cart only when a valid `Idempotency-Key` header is provided. Repeated requests with the same key within 24 hours shall return the original order without creating a duplicate.
**Rationale:** Network retries and double-tap prevention.
**Inputs:** cartId, addressId, paymentMethod, deliveryNotes, Idempotency-Key.
**Processing:**
1. Look up Idempotency-Key in idempotency store; if found, return cached response.
2. Snapshot cart_items into order_items with `unitPrice` captured at order time.
3. Compute subtotal, deliveryFee, tax, total.
4. Persist Order with state `pending`.
5. Cache idempotency response with 24-hour TTL.
**Outputs:** Order record.
**Error Handling:** Return 400 if Idempotency-Key missing; return cached 2xx response on replay.
**Priority:** Essential
**Source:** Order constraint "idempotent creation"; Lesson on idempotency keys with 24h replay window.
**Acceptance Criteria:**
- AC1: Given the same Idempotency-Key submitted twice within 24 hours, When the second request arrives, Then exactly one order exists and both responses are byte-equal.
- AC2: Given a request without Idempotency-Key on a state-mutating endpoint, When submitted, Then HTTP 400 with code `IDEMPOTENCY_KEY_REQUIRED` is returned.

#### REQ-F-023: Idempotency on All State-Mutating Endpoints
**Description:** The system shall require and honor `Idempotency-Key` headers on all state-mutating REST endpoints (POST, PUT, PATCH, DELETE) with a 24-hour replay window.
**Priority:** Essential
**Source:** Lesson on idempotency keys.

#### REQ-F-024: Delivery Range Validation
**Description:** The system shall reject order creation when the customer's delivery address is outside the restaurant's configured delivery radius.
**Outputs:** HTTP 400 with code `ADDRESS_OUT_OF_RANGE`.
**Priority:** Essential
**Source:** Order constraint "address must be in delivery range".

#### REQ-F-025: Order State Machine
**Description:** The system shall enforce the order lifecycle: `pending` → `confirmed` → `preparing` → `ready` → `picked_up` → `on_the_way` → `delivered`. Side states: `cancelled`, `rejected`. Only authorized actors per state may transition.
**Priority:** Essential
**Source:** Order lifecycle_states.
**Acceptance Criteria:**
- AC1: Given an order in `delivered` state, When any actor attempts a state change, Then HTTP 409 Conflict is returned.

#### REQ-F-026: Restaurant Order Acknowledgment
**Description:** The system shall require restaurant staff to acknowledge (confirm or reject) a `pending` order within 5 minutes of creation.
**Processing:** A timer is started on order creation; on acknowledgment, transition to `confirmed` or `rejected`.
**Priority:** Essential
**Source:** Restaurant Staff MODIFIES Order.

#### REQ-F-027: Auto-Cancellation on Restaurant Timeout
**Description:** The system shall automatically transition an order from `pending` to `cancelled` when the restaurant has not acknowledged within 5 minutes, and shall trigger a full refund (REQ-F-080) for prepaid orders.
**Outputs:** Cancellation record with `initiatedBy = system`, `reason = restaurant_timeout`, fee = 0.
**Priority:** Essential
**Source:** Order constraint "auto-cancel if restaurant doesn't ack in 5 min".

#### REQ-F-028: Order Item Snapshot
**Description:** The system shall capture `unitPrice` and item descriptors on each order_item at order creation, independent of subsequent menu price changes.
**Priority:** Essential
**Source:** Order Item constraint "unit price snapshot at order time".

#### REQ-F-029: ETA Calculation
**Description:** The system shall compute an estimated time of arrival upon order confirmation as `prep_time + travel_time + buffer`, persist it on the order, and recompute upon driver assignment and at every 60-second interval until `delivered`.
**Inputs:** Restaurant prepTime; map service travel time from restaurant to dropoff.
**Processing:** ETA Calculator queries Map Service; computation must complete in ≤ 500ms.
**Outputs:** `order.eta` (timestamp).
**Priority:** Essential
**Source:** ETA Calculator constraints; ETA Calculator MODIFIES Order; CONSUMES Map Service.
**Acceptance Criteria:**
- AC1: Given a confirmed order, When ETA is computed, Then computation completes in ≤ 500ms (P95).
- AC2: Given 100 sample completed orders, When measured, Then ≥ 90 shall have actual delivery time within ±3 minutes of the most recent ETA.

---

### 3.5 Payment Processing

#### REQ-F-030: Payment Method Selection
**Description:** The system shall support payment by credit/debit card, e-wallet (VNPay, Momo), and Cash on Delivery (COD).
**Priority:** Essential

#### REQ-F-031: COD Order Limit
**Description:** The system shall reject COD orders where `total > 2,000,000 VND`.
**Outputs:** HTTP 400 with code `COD_LIMIT_EXCEEDED`.
**Priority:** Essential
**Source:** Payment constraint "COD limit 2,000,000 VND per order".

#### REQ-F-032: No Card Data Storage
**Description:** The system shall NEVER persist primary account number (PAN), CVV, or expiration date in any database, log, or backup. All card payments shall be processed via gateway-hosted forms or tokenization.
**Priority:** Essential
**Source:** Payment constraint "no card data stored on platform"; PCI-DSS.

#### REQ-F-033: Payment Authorization
**Description:** The system shall request payment authorization from the gateway during order placement for non-COD methods, and shall transition the Payment record from `pending` → `authorized` upon success.
**Priority:** Essential

#### REQ-F-034: Payment Capture on Delivery Completion
**Description:** For digital (non-COD) payments, the system shall support two configurable capture models per region: (a) **auto-capture-on-delivery** — funds are authorized at order placement and captured when the order transitions to `delivered`; (b) **immediate-capture** — funds are captured at the time of authorization. The active model is configured by **Platform Operations Admins** via the Region Configuration service and stored in the `RegionPaymentPolicy` entity (key: regionCode, value: captureModel ∈ {AUTO_ON_DELIVERY, IMMEDIATE}).
**Rationale:** Different markets have different regulatory and merchant-acceptance norms; configuration per region is required.
**Inputs:** orderId, regionCode, paymentMethod, authorizedAmount.
**Processing:**
1. Resolve `captureModel` from `RegionPaymentPolicy` for the order's region.
2. If `paymentMethod = COD`, this requirement does not apply — see REQ-F-031 and REQ-F-036 (Payment State Machine), where COD follows the path `pending_cod → captured` upon driver receipt of cash, independently of the digital capture model.
3. If `captureModel = IMMEDIATE`: invoke gateway capture immediately after successful authorization.
4. If `captureModel = AUTO_ON_DELIVERY`: hold authorization; on order transition to `delivered`, invoke gateway capture for the authorized amount.
5. On capture success, transition Payment state to `captured`; on failure, follow REQ-F-036 fallback paths.
**Outputs:** Payment state update; gateway capture transaction id; audit log entry.
**Error Handling:** If capture fails after `delivered` (auto model), retry up to 3 times with exponential backoff (5s, 30s, 120s); if all retries fail, raise an `OPS_PAYMENT_CAPTURE_FAILED` alert and route the case to the finance team.
**Priority:** Essential
**Source:** Payment entity; Region constraint; PCI-DSS scope.
**Acceptance Criteria:**
- AC1: Given a region configured for `AUTO_ON_DELIVERY`, When an order is placed and later marked `delivered`, Then the gateway capture is invoked within 60 seconds of the `delivered` transition.
- AC2: Given a region configured for `IMMEDIATE`, When the gateway returns successful authorization, Then the capture is invoked within 5 seconds and the Payment state becomes `captured`.
- AC3: Given a COD order in any region, When the driver confirms cash receipt, Then the Payment transitions `pending_cod → captured` regardless of the regional `captureModel` setting.

#### REQ-F-035: HMAC-Verified Webhook Processing
**Description:** The system shall verify HMAC-SHA256 signatures on every inbound payment gateway webhook against the configured per-gateway secret before any state mutation. Webhooks failing verification shall be rejected with HTTP 401, logged to `audit_log`, and shall not modify any payment record.
**Inputs:** Webhook payload, `X-Signature` header, gatewayId.
**Processing:**
1. Look up HMAC secret for gatewayId.
2. Compute HMAC-SHA256 of raw request body.
3. Constant-time compare against header.
4. If equal, deduplicate by `transactionId` + event type, then process.
**Priority:** Essential
**Source:** Payment Gateway constraint; Lesson on HMAC-verified webhook processing.
**Acceptance Criteria:**
- AC1: Given a webhook with invalid signature, When received, Then HTTP 401 is returned and an audit log with action `WEBHOOK_SIGNATURE_INVALID` is recorded.
- AC2: Given the same valid webhook delivered twice, When processed, Then the payment state changes exactly once.

#### REQ-F-036: Payment State Machine
**Description:** The system shall enforce Payment lifecycle: `pending` → `authorized` → `captured` | `cancelled_by_user` | `declined`; `captured` → `refunded`; `pending_cod` → `captured` (on driver cash receipt) or `cancelled_by_user`. Suspect transactions shall be marked `suspect` for manual review.
**Priority:** Essential
**Source:** Payment lifecycle_states.

#### REQ-F-037: Payment Audit Logging
**Description:** The system shall write an `audit_log` entry for every payment state change, retained for ≥ 7 years.
**Priority:** Essential
**Source:** Payment PRODUCES Audit Log; constraint "≥7 years retention".

---

### 3.6 Order Dispatch & Delivery Tracking

#### REQ-F-040: Driver Availability Status
**Description:** The system shall allow drivers to set their availability among `offline`, `available`, `assigned`, `on_delivery`. Only `available` drivers participate in dispatch matching.
**Priority:** Essential

#### REQ-F-041: Order-to-Driver Matching
**Description:** When a restaurant transitions an order to `confirmed`, the Order Dispatcher shall identify the closest available driver within a configurable radius (default 5 km of the restaurant) and offer the assignment.
**Inputs:** Order pickup coordinates; available driver locations.
**Processing:** Rank by proximity (and optionally by rating); offer to top candidate; on rejection, offer to next.
**Outputs:** Delivery record with state `assigned`.
**Priority:** Essential
**Source:** Order Dispatcher CREATES Delivery; constraint "must respect driver availability and proximity".

#### REQ-F-042: Driver Acceptance Window
**Description:** The system shall give a driver 30 seconds to accept or reject an assignment offer before automatically reassigning to the next candidate.
**Priority:** Essential

#### REQ-F-043: Real-Time Driver Location Updates
**Description:** While a delivery is in `picked_up` or `en_route_dropoff` state, the driver app shall publish location updates at intervals not exceeding 5 seconds when the driver is moving (speed > 1 m/s).
**Outputs:** `Delivery.currentLocation` and `Delivery.lastLocationUpdate` updated; broadcast to subscribed customer client via WebSocket.
**Priority:** Essential
**Source:** Delivery constraint "driver location update ≤ 5 seconds when moving".

#### REQ-F-044: Customer Live Tracking
**Description:** The system shall allow the customer to view the driver's live location on a map from `picked_up` until `delivered`, with current ETA.
**Priority:** Essential

#### REQ-F-045: Masked Communication Channel
**Description:** The system shall provision a masked communication channel (virtual phone number and/or in-app chat) between customer and driver upon delivery assignment, and shall expire it within 30 minutes after `delivered`.
**Outputs:** `masked_communication` record; driver's real number is never exposed to customer.
**Priority:** Essential
**Source:** Order HAS Masked Communication; Driver constraint "phoneNumber masked when shared with customer".

#### REQ-F-046: Pickup Confirmation
**Description:** The driver shall confirm pickup, transitioning Delivery to `picked_up` and Order to `picked_up` / `on_the_way`.
**Priority:** Essential

#### REQ-F-047: Delivery Confirmation
**Description:** The driver shall confirm delivery via the app. The system shall transition Order to `delivered`, capture COD payment if applicable, and trigger the rating prompt.
**Priority:** Essential

---

### 3.7 Notifications

#### REQ-F-050: Order Lifecycle Notifications
**Description:** The system shall send notifications to the customer for the following Order state transitions: `confirmed`, `preparing`, `ready`, `picked_up`, `on_the_way`, `delivered`, `cancelled`, `rejected`.
**Priority:** Essential
**Source:** Order TRIGGERS Notification.

#### REQ-F-051: Driver Assignment Notifications
**Description:** The system shall send a push notification to a driver when offered a delivery assignment, including pickup and dropoff summaries.
**Priority:** Essential
**Source:** Notification TARGETS Driver.

#### REQ-F-052: Restaurant New-Order Notifications
**Description:** The system shall send an audible push notification to restaurant staff devices upon a new order in `pending` state, repeating every 30 seconds until acknowledged or auto-cancelled.
**Priority:** Essential

#### REQ-F-053: Multi-Channel Delivery
**Description:** Notifications shall be deliverable via push (FCM/APNs), SMS, and email. **Critical security events** shall be sent on at least two independent channels (one of which must be SMS or email — i.e., out-of-band from the app push channel).
**Rationale:** Out-of-band delivery for security-sensitive events ensures the user is reachable even if the app session is compromised or unavailable.
**Critical Security Events (enumerated):**
1. New-device login.
2. Successful password change.
3. Password-reset request and completion.
4. MFA/OTP credential change (phone number or email update).
5. Account locked due to failed-login threshold (REQ-F-009).
6. Account suspended or reactivated by admin.
7. Successful payment-method addition or removal.
8. Refund > 500,000 VND issued to the account.
9. Permanent account deletion confirmation.
**Inputs:** notificationEvent, recipientAccountId, channelPreferences.
**Processing:**
1. Look up the event's classification; if classified as a Critical Security Event, force fan-out to ≥ 2 channels.
2. Apply the channel-priority order: push → SMS → email; fall back to the next channel if the primary fails or is not registered.
**Outputs:** Notification delivery records per channel attempted, with status (sent/failed) and timestamp.
**Error Handling:** If all configured channels fail, log to the `notification_dlq` and raise a monitoring alert.
**Priority:** Essential
**Source:** Push/SMS/Email PRODUCES Notification; Security audit constraint.
**Acceptance Criteria:**
- AC1: Given a successful password change, When the notification fires, Then both an email and an SMS are dispatched within 30 seconds (in addition to optional push).
- AC2: Given an event not classified as critical, When dispatched, Then it is sent on the user's preferred single channel only.

#### REQ-F-054: Notification Latency
**Description:** The end-to-end notification latency from event occurrence to push delivery to device shall be ≤ 5 seconds (P95).
**Priority:** Essential
**Source:** Notification constraint.

---

### 3.8 Cancellation & Refund

#### REQ-F-060: Customer Cancellation Window
**Description:** The system shall allow customers to cancel an order only while in states `pending`, `confirmed`, or `preparing` (i.e., before pickup).
**Priority:** Essential
**Source:** Cancellation constraint "only allowed before pickup".

#### REQ-F-061: Restaurant Cancellation
**Description:** The system shall allow restaurant staff to reject an order during `pending` and to cancel during `confirmed` or `preparing` with a documented reason.
**Priority:** Essential

#### REQ-F-062: Cancellation Fee Policy
**Description:** The system shall calculate a cancellation fee per a configurable policy maintained by **Finance Operations Admins** in the `CancellationFeePolicy` configuration entity (per-region, versioned, with audit trail). The default policy is:
| Order State at Cancellation | Initiator | Fee |
|------------------------------|-----------|-----|
| `pending` (within 60 sec of placement) | Customer | 0 VND |
| `confirmed` | Customer | 0 VND |
| `confirmed` | Restaurant | 0 VND (customer is fully refunded) |
| `preparing` | Customer | **50% of order subtotal**, capped at 200,000 VND (default; configurable up to 100% of order subtotal) |
| `preparing` | Restaurant | 0 VND (customer is fully refunded) |
| `ready_for_pickup` or later | Customer | Cancellation not allowed (REQ-F-060) |
**Rationale:** Compensates restaurants for sunk preparation cost while protecting customers from arbitrary fees; configurability supports market and regulatory variation.
**Inputs:** orderId, cancellationInitiator, currentOrderState, regionCode.
**Processing:**
1. Load the active `CancellationFeePolicy` version for the order's region.
2. Look up the fee for the (state, initiator) tuple.
3. Compute fee as min(configuredPercent × subtotal, configuredCap).
4. Record the policy version id used in the cancellation audit record.
**Outputs:** feeAmount (VND), policyVersionId, refundAmount (= paidAmount − feeAmount).
**Priority:** Essential
**Source:** Cancellation constraint "fee per cancellation policy"; Finance Ops governance.
**Acceptance Criteria:**
- AC1: Given the default policy and a customer-initiated cancellation in `preparing` for a 300,000 VND order, When the fee is calculated, Then feeAmount = 150,000 VND and refundAmount = paidAmount − 150,000 VND.
- AC2: Given a finance admin updates the cap to 100,000 VND for region VN, When a new cancellation occurs, Then the fee is capped at 100,000 VND and the audit log records the new policyVersionId.

#### REQ-F-063: Cancellation Triggers Refund
**Description:** When a cancellation occurs for a prepaid order with a `captured` or `authorized` payment, the system shall initiate a Refund record within 60 seconds.
**Priority:** Essential
**Source:** Cancellation TRIGGERS Refund; Refund constraint "initiated ≤ 60 seconds".

#### REQ-F-080: Refund Initiation
**Description:** The system shall create a Refund record in state `initiated` and dispatch the refund request to the appropriate gateway, transitioning to `processing` upon dispatch.
**Priority:** Essential

#### REQ-F-081: Refund State Machine
**Description:** Refund states: `initiated` → `processing` → `completed` | `failed`. On `failed`, the refund shall transition to `manual_ticket` and create an admin task.
**Priority:** Essential
**Source:** Refund lifecycle_states.

#### REQ-F-082: Tiered Refund Authorization
**Description:** The system shall enforce a tiered authorization policy for refunds based on VND amount:
- **Auto-approve:** amount ≤ 200,000 VND (no human review)
- **L1 approval (Customer Service Agent):** 200,001 – 1,000,000 VND
- **L2 approval (Senior Agent / Lead):** 1,000,001 – 5,000,000 VND
- **Manager approval:** > 5,000,000 VND

Refunds requiring approval shall be parked in state `processing` (sub-state `awaiting_approval_<tier>`) and shall not dispatch to the gateway until the required approver acts.

**Inputs:** refundId, amount, reason, requesterId.
**Processing:**
1. Determine tier from amount.
2. If auto, dispatch to gateway.
3. Otherwise, route to approval queue for the required role; on approval, dispatch; on rejection, transition to `failed` with reason.
4. Record approver identity and decision in `audit_log`.
**Outputs:** Refund state; approval audit trail.
**Priority:** Essential
**Source:** Lesson on tiered refund authorization.
**Acceptance Criteria:**
- AC1: Given a refund of 150,000 VND, When initiated, Then it is dispatched to the gateway without human approval.
- AC2: Given a refund of 600,000 VND, When initiated by an L1 agent on their own ticket, Then the system shall require a different L1+ approver (separation of duties).
- AC3: Given a refund of 6,000,000 VND, When approved by a non-Manager, Then HTTP 403 is returned and the refund remains in `awaiting_approval_manager`.

---

### 3.9 Ratings, Reviews, and Disputes

#### REQ-F-090: Submit Rating
**Description:** After a delivery is `delivered`, the system shall allow the customer to submit star ratings (integer 1–5) for the restaurant and the driver, with one rating per (order, target).
**Priority:** Essential
**Source:** Rating constraints.

#### REQ-F-091: Submit Review with Profanity Filter
**Description:** The system shall allow a customer to submit a written review (text + tags + up to 5 photos) for a delivered order. The system shall apply a Vietnamese/English profanity filter to text and tags, route flagged content to `pending_moderation`, and submit clean content directly to `submitted` → `approved`.
**Inputs:** orderId, text, tags[], photos[].
**Processing:**
1. Validate ≤ 5 photos; compress each to ≤ 500KB.
2. Run profanity filter (vi + en).
3. Submit ≤ 2 seconds end-to-end.
**Priority:** Essential
**Source:** Review constraints.
**Acceptance Criteria:**
- AC1: Given a review with 5 photos averaging 3MB each, When submitted, Then the upload-and-compress pipeline completes within 2 seconds and stored photos are ≤ 500KB each.
- AC2: Given a review containing a profane Vietnamese word, When submitted, Then the review enters `pending_moderation` state.

#### REQ-F-092: Rating Targets
**Description:** A Rating shall reference exactly one target type (`restaurant` or `driver`) and exactly one target id, joined to a delivered order.
**Priority:** Essential
**Source:** Rating TARGETS Restaurant/Driver.

#### REQ-F-093: Customer Dispute Submission
**Description:** The system shall allow a customer to file a Dispute against a delivered or cancelled order, with category (e.g., `missing_item`, `incorrect_item`, `late`, `quality`), description, and optional photo evidence.
**Priority:** Essential
**Source:** Customer CREATES Dispute.

#### REQ-F-094: Admin Dispute Resolution
**Description:** The system shall allow admins to investigate, resolve (with resolution text), escalate, or close disputes. Resolution actions may include initiating a Refund (subject to REQ-F-082).
**Priority:** Essential
**Source:** Admin MANAGES Dispute.

#### REQ-F-095: Dispute State Machine
**Description:** Dispute states: `open` → `investigating` → `resolved` | `escalated` → `closed`.
**Priority:** Essential

---

### 3.10 Admin & Restaurant Operations

#### REQ-F-100: Restaurant Onboarding by Admin
**Description:** The system shall allow admins to create restaurants with name, image, address, coordinates, operating hours, deliveryFee, prepTime, cuisine tags, and assigned staff accounts.
**Priority:** Essential
**Source:** Admin MANAGES Restaurant.

#### REQ-F-101: Menu Item CRUD by Restaurant Staff
**Description:** Restaurant staff shall create, update (price, description, image, category), set availability, and discontinue menu items only for their associated restaurant.
**Priority:** Essential
**Source:** Restaurant Staff MODIFIES Menu Item; constraint "must be associated with one restaurant".

#### REQ-F-102: Menu Item Availability Toggle
**Description:** Staff shall toggle item `isAvailable` in real time; unavailable items shall not appear in customer cart additions but shall remain visible (greyed) on menu.
**Priority:** Essential

#### REQ-F-103: Restaurant Open/Close Toggle
**Description:** Staff shall manually mark the restaurant `closed` or `active` (open) outside automatic operating-hours rules.
**Priority:** Essential

#### REQ-F-104: Admin User Suspension
**Description:** Admins shall suspend or unsuspend any account; suspension shall revoke all sessions immediately and write an audit log.
**Priority:** Essential

#### REQ-F-105: Admin Reporting Dashboard
**Description:** The system shall provide an admin dashboard with daily, weekly, and monthly metrics, with explicit calculation methods and refresh frequencies.
**Metrics:**
| Metric | Calculation | Refresh Frequency |
|--------|-------------|-------------------|
| Order count | COUNT(orders WHERE created_at IN window) | Every 5 minutes (near-real-time) |
| GMV (Gross Merchandise Value) | SUM(order.totalAmount WHERE order.state = `delivered` AND created_at IN window) | Every 15 minutes |
| Avg ETA accuracy | AVG(abs(actualDeliveryTime − promisedETA) ≤ 3 min ? 1 : 0) over delivered orders in window | Hourly |
| Cancellation rate | COUNT(cancelled) / COUNT(orders placed) in window, × 100% | Hourly |
| Dispute rate | COUNT(disputes opened) / COUNT(delivered orders) in window, × 100% | Hourly |
| Top restaurants | Top 20 by GMV in window, with rank-change vs prior window | Daily at 02:00 local time |
| Driver utilization | SUM(driver.activeMinutes with assignment) / SUM(driver.activeMinutes) in window, × 100% | Every 30 minutes |
**Inputs:** dateRange (window), regionCode (optional), metricSelection.
**Processing:** Metrics are computed by the analytics pipeline against the read-replica reporting database; results are cached per (metric, window, region) tuple with the refresh frequency above.
**Outputs:** JSON payload to dashboard UI; CSV export option for any metric.
**Error Handling:** If a metric's pipeline lags > 2× its refresh frequency, the dashboard shall display a "stale data" warning with the lastUpdated timestamp.
**Performance:** Dashboard initial render shall complete within **2 seconds at p95** for a 30-day window.
**Priority:** Conditional
**Source:** Admin Operations use case; Operational Reporting requirement.
**Acceptance Criteria:**
- AC1: Given an admin opens the dashboard for the last 7 days, When the page loads, Then all metrics render within 2 seconds (p95) using cached values not older than each metric's refresh frequency.
- AC2: Given the analytics pipeline is delayed beyond 2× the refresh frequency, When the dashboard is opened, Then a "stale data" badge is shown next to the affected metric.

---

## 4. External Interface Requirements

### 4.1 User Interfaces

- **UI-1:** All client UIs shall conform to **WCAG 2.1 Level AA** for accessibility (color contrast ≥ 4.5:1, keyboard navigation, screen-reader labels for all interactive elements).
- **UI-2:** The system shall provide three distinct client applications: (a) Customer mobile app (iOS 14+ and Android 8+), (b) Restaurant staff web/tablet app (responsive, optimized for 10″ tablets in portrait), and (c) Driver mobile app (Android 8+ primary; iOS 14+ secondary).
- **UI-3:** All UIs shall support both Vietnamese (`vi`) and English (`en`) localization, switchable in user settings; locale shall persist per Account.
- **UI-4:** All monetary values shall be displayed in VND with thousands separators; all timestamps shall be displayed in the user's local time zone with the time zone abbreviation visible.
- **UI-5:** The Customer app shall complete the **first meaningful paint within 2 seconds** on a mid-tier 4G connection (≥ 5 Mbps) and a device representative of the 50th-percentile target market device.
- **UI-6:** All forms shall provide inline validation feedback within 200 ms of field-blur, with WCAG-compliant error indication (color + icon + text).
- **UI-7:** Loading states longer than 500 ms shall display a skeleton or progress indicator; operations longer than 5 seconds shall be cancellable.

### 4.2 Hardware Interfaces

- **HW-1:** The Driver app shall interface with the device GPS sensor at a sampling rate of **once every 5 seconds while on an active delivery**, falling back to once every 30 seconds while idle, to balance accuracy and battery consumption.
- **HW-2:** The Customer and Driver apps shall interface with the device camera for (a) profile photo capture and (b) delivery proof-of-photo capture (Driver only). Captured images shall be compressed to ≤ 500 KB before upload.
- **HW-3:** The Restaurant tablet app shall interface with **Bluetooth or USB-attached thermal receipt printers** (ESC/POS protocol, 80mm) for order ticket printing. Printer absence shall not block order acceptance.
- **HW-4:** All client apps shall interface with the device push-notification subsystem (APNs on iOS, FCM on Android) for inbound notification delivery.
- **HW-5:** The Customer and Driver apps shall request and use device location services with **foreground** and (Driver only) **background** location permissions, with clear in-app rationale screens before OS prompts.

### 4.3 Software Interfaces

- **SW-1: Payment Gateways** — The system shall integrate with VNPay, Momo, and Stripe via their respective REST APIs over HTTPS/TLS 1.3. Integration shall use a tokenization/redirect model (no raw PAN traverses FoodSwift servers — see REQ-F-032). All gateway responses shall be authenticated via HMAC-SHA256 signatures (REQ-F-035).
- **SW-2: Mapping & Routing** — The system shall integrate with Google Maps Platform (primary) and Mapbox (failover) for geocoding, reverse geocoding, ETA calculation, and route polyline retrieval, via REST/HTTPS. Failover to the secondary provider shall be automatic on > 2% error rate over a rolling 5-minute window.
- **SW-3: Push Notification Services** — The system shall integrate with Firebase Cloud Messaging (FCM) for Android and Apple Push Notification service (APNs) for iOS via their respective HTTPS APIs.
- **SW-4: SMS Gateway** — The system shall integrate with at least one regional SMS provider (Twilio or local equivalent) for OTP and critical-event delivery, via HTTPS REST API. The SMS provider shall be swappable via configuration without code change.
- **SW-5: Email Service** — The system shall integrate with a transactional email provider (e.g., SendGrid, Amazon SES) via HTTPS REST API or SMTP relay over TLS.
- **SW-6: Object Storage** — The system shall use S3-compatible object storage for menu images, profile photos, and proof-of-delivery photos, accessed via signed URLs with ≤ 15-minute expiry.
- **SW-7: Data Format** — All inter-service and external API exchanges shall use **JSON over HTTPS** with UTF-8 encoding. Date-time values shall be ISO 8601 in UTC with explicit `Z` suffix.

### 4.4 Communication Interfaces

- **COM-1:** All external client-to-server communication shall use **HTTPS with TLS 1.3** (TLS 1.2 permitted as a fallback for legacy clients with strong cipher suites only). Plain HTTP shall be redirected (HTTP 301) to HTTPS at the edge.
- **COM-2:** Real-time delivery tracking shall use **WebSocket Secure (WSS)** connections for driver-to-server location streaming and server-to-customer location push. Connections shall auto-reconnect with exponential backoff (1s, 2s, 4s, 8s, max 30s) on disconnect.
- **COM-3:** Webhooks received from payment gateways shall be authenticated via **HMAC-SHA256** (REQ-F-035), processed idempotently (REQ-F-023), and acknowledged within 5 seconds.
- **COM-4:** All API endpoints shall enforce per-account **rate limits** (default: 100 requests/minute for authenticated users, 20 requests/minute for unauthenticated endpoints such as registration/login). Limits shall be returned in `X-RateLimit-*` response headers.
- **COM-5:** Internal service-to-service communication shall use mutual TLS (mTLS) within the platform's private network; no internal service shall be reachable from the public internet.
- **COM-6:** All API requests and responses shall include a `X-Request-Id` header (UUID v4) for distributed-trace correlation; this id shall be logged at every hop.

---

## 5. Non-Functional Requirements

### 5.1 Performance

- **REQ-NF-001 (API Response Time):** 95% of authenticated REST API requests shall complete within **300 ms** server-side under nominal load (5,000 concurrent users); 99% shall complete within **800 ms**.
- **REQ-NF-002 (Order Placement Latency):** End-to-end order placement (customer tap → confirmation screen) shall complete within **30 seconds at p95**, including payment authorization round-trips.
- **REQ-NF-003 (ETA Computation):** ETA shall be computed and returned within **500 ms at p95** of being requested (REQ-F-029).
- **REQ-NF-004 (ETA Accuracy):** Promised ETA shall be within **±3 minutes of actual delivery time for ≥ 90% of delivered orders**, measured monthly.
- **REQ-NF-005 (Live Tracking Freshness):** Driver location displayed to the customer shall be no older than **10 seconds at p95** during active delivery (driver pings every 5 seconds per HW-1).
- **REQ-NF-006 (Search Latency):** Restaurant search shall return results within **300 ms at p95** (see REQ-F-013).
- **REQ-NF-007 (Notification Latency):** Push notifications shall be dispatched to the upstream provider within **2 seconds at p95** of the triggering event (see REQ-F-054).
- **REQ-NF-008 (Throughput):** The platform shall sustain **1,000 orders per minute** peak with no degradation of the latency targets above.

### 5.2 Scalability

- **REQ-NF-010 (Concurrent Users):** The system shall support **50,000 concurrent active users** (customers + drivers + restaurant staff combined) without violating the performance targets in §5.1.
- **REQ-NF-011 (Horizontal Scaling):** All stateless services shall be horizontally scalable; adding capacity shall not require code change or downtime.
- **REQ-NF-012 (Data Volume Growth):** The system shall accommodate **10 million orders per month** with linear cost scaling and no schema changes for at least 3 years from launch.
- **REQ-NF-013 (Geographic Expansion):** New regions shall be onboardable via configuration (regionCode, currency, locale, payment policy, cancellation policy) without code change.

### 5.3 Availability & Reliability

- **REQ-NF-020 (Uptime):** The platform shall achieve **99.9% monthly availability** for customer-facing order placement and tracking flows (≤ 43 minutes of downtime per 30-day month).
- **REQ-NF-021 (MTBF):** Mean Time Between Failures for any single critical service shall exceed **720 hours** (30 days).
- **REQ-NF-022 (MTTR):** Mean Time To Recovery for a Severity-1 incident shall be ≤ **30 minutes**.
- **REQ-NF-023 (RPO):** Recovery Point Objective shall be ≤ **5 minutes** for transactional data (orders, payments, accounts).
- **REQ-NF-024 (RTO):** Recovery Time Objective shall be ≤ **1 hour** for full-region failover.
- **REQ-NF-025 (Graceful Degradation):** When a non-critical dependency (e.g., recommendations, analytics) is unavailable, core flows (registration, ordering, payment, tracking) shall continue functioning.
- **REQ-NF-026 (Idempotency Window):** All idempotency keys shall be honored for **24 hours** (REQ-F-022, REQ-F-023).

### 5.4 Security

- **REQ-NF-030 (Authentication):** All authenticated endpoints shall require a valid bearer token (JWT, signed RS256) with ≤ 60-minute expiry; refresh tokens shall be rotated on each use.
- **REQ-NF-031 (Password Policy):** Passwords shall be ≥ 10 characters, contain mixed case, digit, and symbol; hashed with **Argon2id** (memory ≥ 64 MB, iterations ≥ 3, parallelism ≥ 2). See REQ-F-001.
- **REQ-NF-032 (Encryption at Rest):** All databases, object storage, and backups shall be encrypted at rest with **AES-256**; keys shall be managed in an HSM-backed KMS with annual rotation.
- **REQ-NF-033 (Encryption in Transit):** All data in transit shall use TLS 1.3 (TLS 1.2 minimum legacy), per COM-1 and COM-5.
- **REQ-NF-034 (PCI-DSS):** The system shall maintain **PCI-DSS v4.0 SAQ-A** compliance scope (no raw PAN handling); see REQ-F-032.
- **REQ-NF-035 (PII Protection):** PII (phone, email, address, payment tokens) shall be encrypted at rest, accessible only via least-privilege IAM, and access shall be audit-logged (REQ-F-010).
- **REQ-NF-036 (OWASP):** The system shall be free of OWASP Top 10 (2021) vulnerabilities at every release, verified by automated SAST/DAST and annual third-party penetration testing.
- **REQ-NF-037 (Authorization):** The system shall enforce **role-based access control (RBAC)** for all roles (Customer, Driver, RestaurantStaff, Admin, FinanceAdmin, OpsAdmin) with attribute-based extensions (ABAC) for region- and tenant-scoped operations.
- **REQ-NF-038 (Rate Limiting & Abuse Protection):** Per COM-4; in addition, suspicious patterns (credential stuffing, OTP brute force) shall trigger automated lockout per REQ-F-009.
- **REQ-NF-039 (Audit Retention):** Security and financial audit logs shall be retained for **≥ 7 years** in immutable (WORM) storage.
- **REQ-NF-040 (Regulatory Compliance):** The system shall comply with **GDPR (EU 2016/679)** and **Vietnam's Decree 13/2023/ND-CP** on personal-data protection, including right-to-access, right-to-erasure, and consent recording.

### 5.5 Usability & Accessibility

- **REQ-NF-050 (Accessibility):** Per UI-1, all client UIs shall meet **WCAG 2.1 Level AA**.
- **REQ-NF-051 (Localization):** All user-facing strings shall be externalized; the system shall support `vi` and `en` at launch with infrastructure for additional locales.
- **REQ-NF-052 (Learnability):** A new customer shall be able to place a first order within **5 minutes** of app install (registration → discovery → order → checkout), measured in usability testing with ≥ 80% success rate.
- **REQ-NF-053 (Error Messaging):** Every error visible to end users shall include (a) plain-language description, (b) suggested next action, and (c) a stable error code for support reference.

### 5.6 Maintainability & Portability

- **REQ-NF-060 (Modularity):** The system shall be implemented as bounded-context services (Account, Catalog, Order, Payment, Dispatch, Notification, Refund, Rating, Admin) with documented APIs.
- **REQ-NF-061 (Observability):** Every service shall emit structured logs (JSON), metrics (RED — Rate, Errors, Duration), and distributed traces correlated by `X-Request-Id` (COM-6).
- **REQ-NF-062 (Deployability):** Releases shall be deployable via blue-green or canary strategy with zero downtime; rollback shall be possible within **5 minutes**.
- **REQ-NF-063 (Cloud Portability):** The system shall avoid single-vendor cloud lock-in by using portable abstractions (Kubernetes for compute, S3-compatible storage, standard SQL).
- **REQ-NF-064 (Test Coverage):** Backend services shall maintain ≥ **80% line coverage** with unit + integration tests; payment, refund, and order state-machine code shall maintain ≥ **95% branch coverage**.

### 5.7 Compliance & Legal

- **REQ-NF-070 (Data Residency):** Vietnamese user PII shall be stored in data centers physically located in Vietnam, per Decree 53/2022/ND-CP.
- **REQ-NF-071 (Audit Logging):** All security-relevant events (REQ-F-010), all financial events (REQ-F-037), and all admin actions shall be audit-logged with 7-year retention (REQ-NF-039).
- **REQ-NF-072 (Right to Erasure):** Upon a verified deletion request, all PII for the requesting account shall be anonymized within **30 days**, except where retention is mandated by financial regulation (in which case PII is replaced with a tokenized reference).

---

## 6. Data Requirements

### 6.1 Logical Data Model (Core Entities)

The system manages the following core entities. All entities include the standard attributes `id` (UUID v4 primary key), `createdAt`, `updatedAt`, and `version` (optimistic-concurrency token) unless otherwise noted.

#### 6.1.1 Identity & Access

- **Account** — `id`, `phoneNumber` (unique, E.164), `email`, `passwordHash`, `state` ∈ {`pending_verification`, `active`, `locked`, `suspended`, `deleted`}, `preferredLanguage`, `roles[]`.
- **Customer** — `id`, `accountId` (FK Account, 1:1), `name`, `defaultAddressId` (FK Address, nullable).
- **Driver** — `id`, `accountId` (FK Account, 1:1), `name`, `licenseNumber`, `vehicleType`, `availabilityStatus` ∈ {`offline`, `available`, `on_delivery`}, `rating` (avg, denormalized).
- **RestaurantStaff** — `id`, `accountId` (FK Account, 1:1), `restaurantId` (FK Restaurant), `staffRole` ∈ {`owner`, `manager`, `clerk`}.
- **AdminUser** — `id`, `accountId` (FK Account, 1:1), `adminRole` ∈ {`platform_admin`, `finance_admin`, `ops_admin`, `support_agent`}.
- **Session** — `id`, `accountId` (FK), `deviceInfo`, `issuedAt`, `expiresAt`, `revokedAt` (nullable).
- **OtpChallenge** — `id`, `accountId` (FK), `codeHash`, `purpose`, `expiresAt`, `attempts`, `consumedAt` (nullable).
- **AuditEvent** — `id`, `accountId` (FK, nullable for system events), `eventType`, `payload` (JSON), `ipAddress`, `userAgent`, `timestamp`. **Append-only / WORM**.

#### 6.1.2 Catalog

- **Restaurant** — `id`, `name`, `address`, `geoLocation` (lat, lng), `cuisineTags[]`, `operatingHours` (JSON week schedule), `state` ∈ {`onboarding`, `open`, `closed`, `suspended`}, `averageRating`, `reviewCount`.
- **MenuItem** — `id`, `restaurantId` (FK Restaurant), `name`, `description`, `priceVnd`, `imageUrl`, `cuisineTags[]`, `isAvailable` (bool).
- **Address** — `id`, `customerId` (FK Customer), `label`, `line1`, `line2`, `ward`, `district`, `city`, `geoLocation` (lat, lng), `isDefault`.

#### 6.1.3 Ordering

- **Cart** — `id`, `customerId` (FK Customer, 1:1 active cart), `restaurantId` (FK Restaurant, nullable until first item), `state` ∈ {`active`, `abandoned`, `checked_out`}.
- **CartItem** — `id`, `cartId` (FK Cart), `menuItemId` (FK MenuItem), `quantity`, `unitPriceVndSnapshot`.
- **Order** — `id`, `customerId` (FK), `restaurantId` (FK), `addressId` (FK Address), `state` ∈ {`pending`, `confirmed`, `preparing`, `ready_for_pickup`, `picked_up`, `out_for_delivery`, `delivered`, `cancelled`}, `subtotalVnd`, `deliveryFeeVnd`, `discountVnd`, `totalVnd`, `idempotencyKey`, `placedAt`, `promisedEtaAt`, `actualDeliveredAt` (nullable), `cancellationReason` (nullable), `cancellationPolicyVersionId` (nullable).
- **OrderItem** — `id`, `orderId` (FK Order), `menuItemId` (FK MenuItem), `nameSnapshot`, `unitPriceVndSnapshot`, `quantity` (REQ-F-028 snapshot semantics).

#### 6.1.4 Payments & Refunds

- **Payment** — `id`, `orderId` (FK Order, 1:1), `method` ∈ {`vnpay`, `momo`, `card`, `cod`}, `state` ∈ {`pending`, `authorized`, `captured`, `failed`, `voided`, `pending_cod`}, `gatewayTxnId`, `authorizedVnd`, `capturedVnd`, `regionCode`, `captureModelUsed`.
- **RegionPaymentPolicy** — `regionCode` (PK), `captureModel` ∈ {`AUTO_ON_DELIVERY`, `IMMEDIATE`}, `effectiveFrom`, `version`.
- **Refund** — `id`, `paymentId` (FK Payment), `orderId` (FK Order), `amountVnd`, `reason`, `state` ∈ {`requested`, `approved`, `processing`, `succeeded`, `failed`, `rejected`}, `tier` ∈ {`auto`, `agent`, `supervisor`, `finance`}, `approverAccountId` (FK Account, nullable).
- **CancellationFeePolicy** — `regionCode`, `version`, `policyJson` (rules per state × initiator), `effectiveFrom`, `createdByAdminId` (FK).

#### 6.1.5 Dispatch & Delivery

- **DeliveryAssignment** — `id`, `orderId` (FK Order, 1:1), `driverId` (FK Driver, nullable until matched), `state` ∈ {`matching`, `offered`, `accepted`, `rejected`, `picked_up`, `delivered`, `failed`}, `offeredAt`, `acceptedAt` (nullable), `pickupAt` (nullable), `deliveredAt` (nullable).
- **DriverLocationPing** — `id`, `driverId` (FK Driver), `geoLocation`, `accuracyMeters`, `timestamp`. Time-series; retained 90 days hot, then archived.
- **MaskedCallSession** — `id`, `orderId` (FK Order), `customerProxyNumber`, `driverProxyNumber`, `expiresAt`.

#### 6.1.6 Engagement

- **Notification** — `id`, `accountId` (FK), `eventType`, `channel` ∈ {`push`, `sms`, `email`}, `payload`, `state` ∈ {`queued`, `sent`, `delivered`, `failed`}, `sentAt`.
- **Rating** — `id`, `orderId` (FK Order), `targetType` ∈ {`restaurant`, `driver`}, `targetId`, `customerId` (FK Customer), `stars` (1–5), `createdAt`.
- **Review** — `id`, `ratingId` (FK Rating, 1:1), `text`, `moderationState` ∈ {`pending`, `approved`, `rejected`}.
- **Dispute** — `id`, `orderId` (FK Order), `customerId` (FK Customer), `reason`, `state` ∈ {`open`, `under_review`, `resolved_refund`, `resolved_no_action`, `rejected`}, `assignedAdminId` (FK), `resolutionNote`, `openedAt`, `resolvedAt` (nullable).

### 6.2 Key Relationships & Cardinalities

| Relationship | Cardinality | Notes |
|--------------|-------------|-------|
| Account ↔ Customer / Driver / RestaurantStaff / AdminUser | 1 : 0..1 (each role) | Account may have multiple roles (REQ-F-002) |
| Customer → Address | 1 : N | One marked default |
| Customer → Cart | 1 : 1 active | Multiple historical (`abandoned`, `checked_out`) permitted |
| Cart → CartItem | 1 : N | All items must belong to a single Restaurant (REQ-F-018) |
| Restaurant → MenuItem | 1 : N | |
| Customer → Order | 1 : N | |
| Restaurant → Order | 1 : N | |
| Order → OrderItem | 1 : N | Snapshots at placement time |
| Order ↔ Payment | 1 : 1 | |
| Payment → Refund | 1 : N | Multiple partial refunds permitted |
| Order ↔ DeliveryAssignment | 1 : 1 | |
| Driver → DeliveryAssignment | 1 : N (over time) | One active assignment at a time |
| Driver → DriverLocationPing | 1 : N | Time-series |
| Order → Rating | 1 : 0..2 | One per target type (restaurant, driver) |
| Order → Dispute | 1 : 0..N | Multiple disputes per order possible |

### 6.3 Data Retention Policies

| Data Class | Retention | Rationale |
|------------|-----------|-----------|
| Order, Payment, Refund records | **7 years** | Tax & financial-audit obligations (REQ-NF-039) |
| AuditEvent | **7 years**, WORM | Security & regulatory (REQ-NF-039, REQ-NF-071) |
| DriverLocationPing | 90 days hot, then aggregated to per-trip polyline; raw discarded | Privacy + cost |
| Notification logs | 12 months | Operational debugging |
| Cart (`abandoned`) | 30 days | Recovery and analytics |
| OtpChallenge | Until expiry + 30 days for fraud analysis | Security |
| Session | Until `expiresAt` + 30 days | Audit |
| PII for `deleted` Accounts | Anonymized within 30 days; tokenized reference retained where mandated | REQ-NF-072 |

### 6.4 Data Integrity & Constraints

- **DI-1:** All foreign-key relationships shall be enforced at the database layer with `ON DELETE` policies that preserve audit trails (use soft-delete or anonymization, never hard-delete on entities referenced by financial records).
- **DI-2:** All monetary fields shall be stored as integer VND (no decimals); display formatting is a presentation concern.
- **DI-3:** All timestamps shall be stored as UTC with millisecond precision; time-zone conversion is a presentation concern.
- **DI-4:** All idempotency keys (REQ-F-022, REQ-F-023) shall be unique per (accountId, endpoint) for 24 hours and indexed accordingly.
- **DI-5:** All `*Snapshot` fields (price, name in OrderItem) shall be immutable after creation, regardless of subsequent edits to the source MenuItem.
- **DI-6:** Geo-coordinates shall be validated within plausible national bounds before persistence and indexed using a geospatial index (e.g., PostGIS GIST or equivalent) to support REQ-F-012 location queries.

---

## 7. Appendices

### 7.1 Appendix A — Open Issues / TBDs

| ID | Issue | Owner | Target Resolution |
|----|-------|-------|-------------------|
| TBD-1 | Final list of supported SMS providers per region beyond Vietnam | Ops Lead | Pre-launch of region 2 |
| TBD-2 | Surge-pricing algorithm and policy (currently out of scope for v1) | Product | v1.1 |
| TBD-3 | Driver tipping flow | Product | v1.1 |
| TBD-4 | Loyalty / referral program | Product | v2.0 |
| TBD-5 | Multi-restaurant cart support (currently disallowed by REQ-F-018) | Product | Post-v2.0 |

### 7.2 Appendix B — Numbering Reservation Note

Gaps in the REQ-F numbering sequence (REQ-F-038/039, 048/049, 055–059, 070–079) are **intentionally reserved** for forthcoming requirements within their parent feature group, to keep ID ranges aligned per group:
- REQ-F-038/039: reserved within §3.5 Payment Processing
- REQ-F-048/049: reserved within §3.6 Order Dispatch & Delivery Tracking
- REQ-F-055–059: reserved within §3.7 Notifications
- REQ-F-064–079: reserved within §3.8 Cancellation & Refund (between cancellation and refund subsections)

These reservations preserve traceability and avoid renumbering when additional requirements are added in subsequent revisions.

### 7.3 Appendix C — Inferred Requirements

The following requirements were inferred from domain best practices to fill gaps not explicitly stated in source interviews; they are marked **[INFERRED]** for traceability and shall be confirmed with stakeholders:

- [INFERRED] REQ-NF-031 specific Argon2id parameters (memory ≥ 64 MB, iterations ≥ 3) — based on OWASP password-storage guidance.
- [INFERRED] REQ-NF-070 data-residency under Decree 53/2022/ND-CP — assumed applicable to a Vietnam-launched product.
- [INFERRED] REQ-F-013 ranking-formula coefficients — assumed reasonable defaults; product/data team to tune post-launch.
- [INFERRED] Default cancellation-fee values in REQ-F-062 — derived from common industry practice; finance team to ratify.
- [INFERRED] Notification retention of 12 months in §6.3 — operational default; legal review pending.

### 7.4 Appendix D — Document Conventions

- "shall" — mandatory requirement.
- "should" — desirable but not mandatory.
- "may" — optional / permissive.
- "REQ-F-NNN" — Functional requirement identifier.
- "REQ-NF-NNN" — Non-functional requirement identifier.
- "UI-N", "HW-N", "SW-N", "COM-N", "DI-N" — Interface and data-integrity identifiers.
- "AC-N" — Acceptance Criterion.
- All timestamps in this document refer to UTC unless otherwise specified.

### 7.5 Appendix E — Traceability Matrix (Summary)

| Source / Constraint | Implementing Requirements |
|---------------------|---------------------------|
| Customer entity & account lifecycle | REQ-F-001..010, REQ-NF-030..031 |
| Restaurant discovery use case | REQ-F-011..016, REQ-NF-006 |
| Single-restaurant cart constraint | REQ-F-017..021 |
| Order lifecycle & idempotency | REQ-F-022..029, REQ-NF-026 |
| PCI-DSS scope (no PAN storage) | REQ-F-032, REQ-NF-034 |
| Payment capture & regional config | REQ-F-033..037 |
| Real-time dispatch & tracking | REQ-F-040..047, REQ-NF-005 |
| Multi-channel notifications | REQ-F-050..054, REQ-NF-007 |
| Cancellation & tiered refunds | REQ-F-060..063, REQ-F-080..082 |
| Rating, review, dispute | REQ-F-090..095 |
| Admin & restaurant operations | REQ-F-100..105 |
| 99.9% availability target | REQ-NF-020..025 |
| 7-year audit retention | REQ-NF-039, REQ-NF-071, §6.3 |
| WCAG 2.1 AA accessibility | UI-1, REQ-NF-050 |
| GDPR / Decree 13 compliance | REQ-NF-040, REQ-NF-072 |

---

*End of Document.*
