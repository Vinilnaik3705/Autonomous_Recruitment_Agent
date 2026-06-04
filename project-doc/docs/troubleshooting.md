# Troubleshooting

## Docker or service startup issues

Symptoms:

- Containers do not start
- API or frontend unreachable

Checks:

1. Confirm Docker Desktop is running
2. Rebuild and restart stack
3. Inspect container logs for postgres, fastapi, and n8n

## Port conflicts

If 3000, 5433, 5678, or 8000 are already in use:

1. Stop conflicting local processes
2. Bring compose stack down
3. Start compose stack again

## Database connectivity errors

Verify database settings used by fastapi:

- host: postgres
- port: 5432 (inside compose network)
- DB_NAME: hr_db
- DB_USER: hr_user

## Workflow trigger failures

Symptoms:

- scheduling or feedback automation not triggered

Checks:

1. Confirm n8n is reachable at port 5678
2. Verify webhook environment variables in fastapi service
3. Re-import private workflow JSON if workflows are missing

## Feedback form not loading

The backend serves the feedback form from frontend/public/feedback-form.html first,
with fallback to backend/feedback-form.html.
If unavailable, verify both files are present in source and container image.

## OAuth / Better Auth & Social Sign-In Issues

### 1. 405 Method Not Allowed on `/api/auth/sign-in/social`
*   **Cause**: Next.js App Router requires route handlers to explicitly export HTTP methods (`GET`, `POST`). Standard `auth.handler` from Better Auth is a raw request handler and doesn't map directly to Next.js route exports.
*   **Solution**: Ensure your catch-all route at `src/app/api/auth/[...better-auth]/route.ts` wraps the handler using `toNextJsHandler` from `better-auth/next-js`:
    ```typescript
    import { auth } from "@/lib/auth";
    import { toNextJsHandler } from "better-auth/next-js";
    export const { GET, POST } = toNextJsHandler(auth);
    ```

### 2. 500 Internal Server Error (Missing Database Tables)
*   **Cause**: Better Auth relies on dynamic server-side adapters and expects target database tables (`user`, `session`, `account`, `verification`, `jwks`) to exist.
*   **Solution**: Run the Better Auth schema migrations using the CLI to generate the tables on your PostgreSQL database:
    ```bash
    npx @better-auth/cli migrate --config ./src/lib/auth.ts -y
    ```

### 3. Hydration Mismatches (SSR & Password Manager conflicts)
*   **Cause**: Client-side browser extensions (such as Dashlane, 1Password, or Bitwarden) inject elements/attributes (like `fdprocessedid`) into interactive form elements before React hydrates the page, throwing a hydration mismatch error.
*   **Solution**: Apply `suppressHydrationWarning` on all interactive buttons, select dropdowns, and form inputs in client components.

### 4. 404 Not Found on `/dashboard` after Social Login Redirect
*   **Cause**: Better Auth's standard `user` table schema doesn't contain a `role` column, making `session.user.role` return `undefined`. Because of role checks, users were directed to `/dashboard` which is an abstract route that lacked its own page.
*   **Solution**:
    1.  **Extend User Schema**: Set `role` in the additional fields configuration in `src/lib/auth.ts` and infer it client-side inside `src/lib/auth-client.ts` using `inferAdditionalFields`.
    2.  **Alter DB Table**: Add the `role` column to the `public.user` table in PostgreSQL:
        ```sql
        ALTER TABLE public.user ADD COLUMN IF NOT EXISTS role VARCHAR(50) DEFAULT 'recruiter';
        ```
    3.  **Setup Safe Landing Router**: Create `src/app/dashboard/page.tsx` as a fallback routing container that loads user sessions and automatically routes users to `/dashboard/recruiter`, `/dashboard/student`, or `/dashboard/admin` depending on their role.

