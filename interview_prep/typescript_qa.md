# TypeScript Interview Q&A

Questions that came up during the JS → TS migration of this project.

---

## Q1: What is the difference between `import type` and `import` in TypeScript?

**My answer:** import type is hard enforced in typescript while import is just a guideline in js.

**Correct answer:**
`import type` tells TypeScript that the import is used *only as a type* — it is **completely erased from the compiled JavaScript output** and never exists at runtime.

`import` (without `type`) imports the actual runtime value. It survives compilation and appears in the output JS.

**Why it matters in `tailwind.config.ts` specifically:**
`Config` is a TypeScript interface — it has no runtime value, it's purely a compile-time shape. Using `import type` guarantees the bundler (Vite/esbuild) strips it out entirely. A plain `import { Config }` might cause the bundler to include the tailwindcss module at runtime unnecessarily.

**Key mental model:** The distinction is **runtime existence vs. compile-time erasure**, not just strictness of enforcement.

---

## Q2: What is the difference between `??` (nullish coalescing) and `||` (logical OR)?

**My answer:** In `??` it can only be null whereas in OR condition it can be null.

**Correct answer:**
`??` falls back to the right side only when the left is `null` or `undefined` — nothing else.

`||` falls back to the right side for **any falsy value** — `null`, `undefined`, `0`, `''` (empty string), `false`, `NaN`.

```ts
const count = userInput || 10   // if userInput is 0 (valid!), wrongly falls back to 10
const count = userInput ?? 10   // if userInput is 0, keeps 0 — correct
```

**In our migration context (`buffer = parts.pop() ?? ''`):** Both would behave the same here since the fallback is `''`. But `??` is the more intentional choice — it says "I only want a fallback for missing values, not for empty strings."

**Key mental model:** `||` = "falsy fallback", `??` = "null/undefined fallback only".

---

## Q3: What does `[key: string]: unknown` mean in a TypeScript interface, and when do you need it?

**My answer:** Message is an interface we explicitly control, whereas ToolEvent comes from SSE and we don't know what the backend is going to return — so string and unknown.

**Correct answer:**
`[key: string]: unknown` is called an **index signature**. It means "this object can have any additional string keys beyond the ones explicitly defined, and their values are `unknown`."

- `Message` is fully constructed in frontend code — every field is known, no index signature needed.
- `ToolEvent` arrives from the backend via SSE. We define the known fields (`tool_name`, `type`, `id`, `timestamp`) but the backend can attach arbitrary extra fields depending on which tool ran. The index signature allows those extra keys without TypeScript erroring.

**Key mental model:** Use an index signature when you own some fields but the rest are open-ended (external data, dynamic payloads). Don't use it when you fully control the shape — explicit interfaces catch more bugs.

---

## Q4: As an EM reviewing a PR, what concern would you raise if `!` (non-null assertion) was used instead of an explicit null check?

**My answer:** We are tight coupling the app to only non-null values and not flexible enough to handle unknown contingencies — Option B is more flexible.

**Correct answer:**
The concern is about **debuggability and fail-fast behavior**, not flexibility.

`!` tells TypeScript "trust me, this won't be null" — but provides zero runtime protection. If `root` is ever null, the app crashes with a cryptic error:
```
Cannot read properties of null (reading 'render')
```
That points at React internals, not the actual problem. Hard to debug at 2am in production.

Option B (explicit throw) fails **fast and clearly**:
```
Error: Root element not found
```
Immediately actionable — one line tells you exactly what went wrong.

**The EM framing for a PR comment:** *"If `!` becomes a habit, we've defeated the purpose of TypeScript — we've moved crashes from compile time to runtime with no safety net. Team norm: `!` is only acceptable with a comment explaining why null is provably impossible here."*

**Key mental model:** Fail-fast — a well-engineered system should crash loudly and early with a clear message, not silently limp along and blow up somewhere unexpected.

---

## Q5: Why define separate `Auth` and `LoginData` interfaces instead of reusing one for both?

**My answer:** Auth can have failure scenarios where user is unauthenticated, whereas LoginData is only for authenticated users — separation of duties.

**Correct answer:**
Both types only represent authenticated states — the `null` in `useState<Auth | null>` already handles the unauthenticated case, not a separate type.

The real reason is **API contract vs application state are two different concerns**:

- `LoginData` (DTO) = raw server response shape: `{ access_token, token_type, user }`
- `Auth` (Domain Model) = what the app actually stores: `{ token, user }` — `token_type` dropped, `access_token` renamed to `token`

If `LoginData` was used as app state, we'd carry a useless `token_type` field everywhere and write `auth.access_token` instead of the cleaner `auth.token`.

**The pattern:** DTO (Data Transfer Object) vs Domain Model.
- DTO = shape of data as it travels over the wire. Belongs to the transport layer — the server owns it.
- Domain Model = shape your app thinks in. You own this. Optimized for UI and business logic, not the API contract.

The `handleLogin` function is the translation boundary — DTO in, Domain Model out:
```ts
function handleLogin(data: LoginData) {
  setAuth({ token: data.access_token, user: data.user })
}
```
Everything else in the app only ever sees `Auth`, never `LoginData`.

**EM framing:** *"Don't let API response shapes leak directly into app state — you'll regret it when the API changes."*

---

## Q6: What's the risk of putting all TypeScript interfaces in a single `types.ts`, and how would you organize them at scale?

**My answer:** Segregate them based on Redux commonality type (guessing).

**Correct answer:**
A single `types.ts` becomes a **dumping ground** — grows to hundreds of lines, unrelated types get imported together, creating hidden coupling between features.

The right approach is **co-location** — types live next to the code that owns them:

```
src/
  api/
    types.ts        ← DTO layer: LoginData, API response shapes
  hooks/
    useChat.ts      ← Message, ToolEvent exported from here (domain types)
  components/
    LoginModal.tsx  ← DemoUser stays here, only used locally
  types.ts          ← only truly shared cross-cutting types
```

**The rules:**
- Local to one component → define in that file, don't export
- Shared within a feature → `feature/types.ts`
- Shared across the whole app → `src/types.ts`

**EM principle:** *"Types should be as close to their usage as possible — only promote them upward when genuinely needed by multiple unrelated parts of the app."*

---

## Q7: `typeof null === 'object'` in JavaScript — does `typeof toolInput === 'object'` correctly guard against null?

**My answer:** No, we have to explicitly separate out null with `??`.

**Correct answer:**
`??` is the wrong tool — it provides fallback values, not conditional guards.

Our actual check is:
```ts
toolInput && typeof toolInput === 'object' && Object.keys(toolInput).length > 0
```

The `toolInput &&` truthiness check already eliminates null because `null` is falsy — the expression short-circuits before reaching `typeof`. So the code IS correct as written.

The dangerous pattern is `typeof` without a prior null guard:
```ts
// WRONG — null passes typeof check, then Object.keys(null) crashes at runtime
if (typeof toolInput === 'object' && Object.keys(toolInput).length > 0)
```

The safe patterns:
```ts
toolInput && typeof toolInput === 'object'       // truthiness guard
toolInput !== null && typeof toolInput === 'object'  // explicit null guard
```

**Key mental model:** Always null-guard before `typeof x === 'object'` — either with `x &&` or `x !== null`. The `typeof` check alone is not enough because `typeof null === 'object'`.

---

## Q8: Why can't you render `unknown` in JSX, but you can render `string`, `number`, and `boolean`?

**My answer:** Because unknown can be any object type.

**Correct answer:**
`ReactNode` is a specific union type React defines:
```ts
type ReactNode = string | number | boolean | null | undefined | ReactElement | ReactFragment
```
React knows how to render all of these — strings/numbers become text, `null`/`undefined`/`false` are silently skipped.

`unknown` is not in that union. TypeScript refuses it because at compile time there's no guarantee the value will be one of those safe types at runtime — it could be a plain `{}`, a `Date`, a `Function`, a `Symbol` — none of which React can render.

The fix: extract the condition into a `boolean` variable. `boolean` IS in `ReactNode` (React skips `false`), so the `&&` short-circuit produces a `boolean` instead of `unknown`.

**Key mental model:** `unknown` means "could be anything, including things React cannot render." TypeScript refuses anything not provably in the `ReactNode` union.

---

## Q9: We forgot to update `index.html` when renaming `main.jsx` → `main.tsx`. Why didn't Vite or the browser throw an error?

**My answer:** Because `index.html` is not a TypeScript file.

**Correct answer — two parts:**

1. **TypeScript can't see `index.html`** — correct. `tsc --noEmit` only checks files in `src/` per `tsconfig.json`. `index.html` is a static file outside TypeScript's scope.

2. **Vite has a silent fallback** — when Vite's dev server can't find `main.jsx`, it tries `main.tsx` in the same directory before giving up. The app worked by accident, relying on an undocumented fallback.

**The EM lesson:** Silence is not always correctness. If Vite ever removed that fallback, the app would break with no TypeScript warning, no compile error — just a 404 at runtime in the browser.

**Static config files like `index.html` are blind spots in your type safety net.** The only way to catch this class of bug is a proper integration test or `vite build` (which is stricter than the dev server).

---
