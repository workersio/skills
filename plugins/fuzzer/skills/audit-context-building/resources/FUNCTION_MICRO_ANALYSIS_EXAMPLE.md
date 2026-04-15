# Function Micro-Analysis Example

## Target: `createUser(email, password, orgId)` in auth/users.ts

**Purpose:**
Creates a new user account within an organization. Core user provisioning operation that validates input, hashes the password, stores the user record with org association, and sends a verification email. Critical identity primitive affecting authentication, authorization boundaries, and multi-tenant data isolation.

---

**Inputs & Assumptions:**

*Parameters:*
- `email` (string): Untrusted user input from registration form.
- `password` (string): Plaintext password. Must be hashed before storage.
- `orgId` (string): Could come from invite link (semi-trusted) or user input (untrusted).

*Implicit Inputs:*
- `db`: Database connection. Assumed valid and open.
- `emailService`: External email service. Assumed available but may fail.
- `config.bcryptRounds`: Hash cost factor. Assumed >= 12.

*Trust Assumptions:*
- bcrypt library correctly implements hashing
- Database enforces unique constraint on email
- Email service does not log plaintext tokens

---

**Outputs & Effects:**

- Returns `User` object (id, email, orgId, createdAt) -- never includes password hash
- Writes to `users` table (id, email, passwordHash, orgId, emailVerified=false)
- Writes to `audit_log` table (userId, action="user_created")
- Calls `emailService.sendVerification(email, token)` externally
- Postcondition: plaintext password NOT stored anywhere

---

**Block-by-Block Analysis:**

```typescript
// L12-15: Input validation
const validEmail = validateEmail(email);
if (!validEmail) throw new ValidationError("Invalid email format");
if (password.length < 8) throw new ValidationError("Password too short");
```
- **What:** Validates email format and minimum password length
- **Why here:** Fail fast before any database or crypto operations
- **Assumption:** `validateEmail` implements RFC 5322 correctly
- **First Principles:** Input validation at system boundary prevents downstream errors
- **5 Whys:** Why validate? -> Prevent invalid records. Why here? -> Fail fast. Why min 8? -> NIST SP 800-63B.

---

```typescript
// L22: Password hashing
const passwordHash = await bcrypt.hash(password, config.bcryptRounds);
```
- **What:** Hashes plaintext password with bcrypt
- **Why here:** After validation passes; expensive operation (~250ms at rounds=12)
- **Invariant:** After this line, plaintext `password` must never be stored or logged
- **5 Hows:** How to protect? -> bcrypt (slow, salted). How many rounds? -> config (12+).

---

```typescript
// L25-30: User insertion (transaction)
const user = await db.transaction(async (tx) => {
  const newUser = await tx.query(
    "INSERT INTO users (email, password_hash, org_id) VALUES ($1, $2, $3) RETURNING ...",
    [validEmail, passwordHash, orgId]
  );
  await tx.query("INSERT INTO audit_log ...", [newUser.id]);
  return newUser;
});
```
- **What:** Inserts user and audit log atomically
- **Why here:** After all validation; point of no return
- **Invariant:** User + audit log created together or not at all
- **5 Whys:** Why transaction? -> Audit log must exist for every user (compliance). Why parameterized? -> Prevent SQL injection.

---

**Cross-Function Dependencies:**

- `validateEmail(email)`: Pure validation, no state
- `generateToken(userId)`: Creates verification token, stores in `verification_tokens` table
- Called by: `POST /api/auth/register`, `POST /api/admin/users`, `acceptInvite()`
- Shares state with: `loginUser()` (reads users), `verifyEmail()` (reads tokens), `deleteUser()` (cascades)
- **Invariant coupling:** Every user MUST have org_id (NOT NULL + FK), every creation MUST have audit_log (transaction)
