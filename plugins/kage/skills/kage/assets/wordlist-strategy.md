# Wordlist Generation Strategy Reference

Detailed rules for the wordlist-generator agent. Read this file before generating any wordlist.

## Core Principle

Every word in the AI wordlist should have a REASON to be there. Static wordlists guess blindly. Your wordlist is informed by:
1. What industry the target operates in
2. What technology they use
3. What naming patterns their existing subdomains follow
4. What companies they've acquired
5. What regions they operate in

## Pattern Analysis Rules

When reading `passive/all_passive.txt`, extract these patterns:

### Separator Detection
```
dev-api.example.com    -> hyphen separator
devapi.example.com     -> no separator (concatenated)
dev.api.example.com    -> dot separator (multi-level subdomain)
```
Use the MOST COMMON separator found. If no multi-word subdomains exist, default to hyphen.

### Service Name Extraction
Strip the domain and any known prefixes (dev-, staging-, etc.) to find base service names:
```
dev-api.example.com      -> service: api
staging-portal.example.com -> service: portal
us-east-dashboard.example.com -> service: dashboard
app2.example.com         -> service: app
```

### Environment Prefix Detection
Common environments to look for:
```
dev, development, staging, stg, stage, uat, qa, test, testing,
beta, alpha, canary, preview, demo, sandbox, preprod, pre-prod,
prod, production, live, dr, disaster-recovery, backup, training,
perf, performance, load, stress
```

### Geographic Pattern Detection
Look for region indicators:
```
us, eu, ap, na, sa, af, me, oc
us-east, us-west, us-central, eu-west, eu-central, eu-north,
ap-south, ap-southeast, ap-northeast, ap-east
us-east-1, us-west-2, eu-west-1 (AWS-style)
eastus, westus, northeurope, westeurope (Azure-style)
```

### Version Pattern Detection
```
api2, api3           -> numeric suffix
api-v2, api-v3       -> version with v-prefix
v2-api, v3-api       -> version as prefix
api-new, api-old     -> lifecycle suffix
api-legacy           -> legacy marker
```

## Cross-Product Generation Rules

### Service x Environment Matrix
For N services and M environments, generate N*M combinations using the detected separator:
```
Separator: hyphen
Services: [api, portal, dashboard]
Environments: [dev, staging, uat, beta, sandbox]

Output:
dev-api, dev-portal, dev-dashboard,
staging-api, staging-portal, staging-dashboard,
uat-api, uat-portal, uat-dashboard,
beta-api, beta-portal, beta-dashboard,
sandbox-api, sandbox-portal, sandbox-dashboard
```

Also generate reverse patterns if detected:
```
api-dev, portal-dev, dashboard-dev, ...
```

### Service x Region Matrix
Only generate if geographic patterns were detected in passive results:
```
Separator: hyphen
Services: [api, portal]
Regions: [us-east, us-west, eu-west, ap-south]

Output:
us-east-api, us-west-api, eu-west-api, ap-south-api,
us-east-portal, us-west-portal, eu-west-portal, ap-south-portal
```

### Version Expansion
For each discovered service, generate using the detected version pattern:
```
Pattern: numeric suffix
Services: [api, app, portal]

Output: api2, api3, app2, app3, portal2, portal3
```

```
Pattern: v-prefix suffix
Services: [api, app]

Output: api-v2, api-v3, api-v4, app-v2, app-v3, app-v4
```

## Industry-Specific Deep Dives

### Fintech / Banking
```
payments, pay, checkout, billing, invoice, ledger, accounting,
merchant, seller, vendor, partner, affiliate,
kyc, aml, compliance, fraud, risk, underwriting,
wallet, balance, transfer, transaction, settlement, payout,
card, debit, credit, prepaid, virtual-card,
loan, lending, mortgage, interest, amortization,
insurance, policy, claim, premium,
sandbox, test-payments, payment-gateway, acquiring,
plaid, stripe, adyen, braintree (common integrations)
```

### SaaS / Cloud Software
```
app, dashboard, portal, console, admin, manage, settings,
tenant, workspace, organization, team, user,
api, graphql, rest, webhook, callback, integration,
auth, sso, saml, oauth, idp, login, signup, register,
analytics, metrics, reports, insights, data,
notifications, email, push, sms, alerts,
marketplace, plugins, extensions, addons,
docs, documentation, help, support, status, changelog,
onboarding, trial, demo, showcase
```

### Healthcare / HealthTech
```
ehr, emr, patient, provider, clinician, physician,
fhir, hl7, dicom, icd, cpt, ndc,
telehealth, telemedicine, virtual-care, video-visit,
pharmacy, rx, prescription, medication, formulary,
claims, billing, coding, revenue-cycle,
lab, laboratory, results, orders, specimens,
imaging, radiology, pacs, viewer,
scheduling, appointments, availability, calendar,
hipaa, consent, authorization, audit-log,
clinical, research, trials, registry
```

### E-commerce / Retail
```
cart, basket, checkout, payment, order, confirmation,
catalog, products, categories, search, browse, filter,
inventory, stock, warehouse, fulfillment, shipping, tracking,
returns, refunds, exchange, rma,
customer, account, profile, wishlist, favorites, lists,
reviews, ratings, recommendations, personalization,
sellers, merchants, marketplace, vendors,
promotions, coupons, discounts, deals, flash-sale,
cms, content, landing, campaign, banner,
analytics, conversion, funnel, attribution
```

## Quality Guidelines

1. **No duplicates**: Every word should appear exactly once
2. **Lowercase only**: All words must be lowercase
3. **Prefix only**: Write `api` not `api.example.com`
4. **Valid DNS characters**: Only `a-z`, `0-9`, and `-` (no underscores, no spaces)
5. **No trailing hyphens**: `dev-api` is valid, `dev-api-` is not
6. **Reasonable length**: Skip words longer than 63 characters (DNS label limit)
7. **Target 1000-2500 total**: After merging with the base wordlist

## Output Checklist

Before writing the final wordlist, verify:
- [ ] Pattern analysis was performed on passive results
- [ ] All 7 strategies were applied
- [ ] Cross-product expansions used the correct separator
- [ ] Industry-specific terms match the target's actual industry
- [ ] Tech stack terms match the target's actual stack
- [ ] Acquisition/brand terms were included (if any found)
- [ ] Standard infrastructure terms are present
- [ ] All words are lowercase, valid DNS, no duplicates
