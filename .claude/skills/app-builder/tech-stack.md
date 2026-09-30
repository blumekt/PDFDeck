# Tech Stack Selection

> Default and alternative technology choices for web applications. Use the current stable release of each (current LTS for runtimes); in an existing project the lockfile decides.

## Default Stack (Web App)

```yaml
Frontend:
  framework: Next.js (App Router)
  language: TypeScript
  styling: Tailwind CSS
  state: React Actions / Server Components
  bundler: Turbopack

Backend:
  runtime: Node.js (current LTS)
  framework: Next.js Route Handlers / Hono (for Edge)
  validation: Zod / TypeBox

Database:
  primary: PostgreSQL
  orm: Prisma / Drizzle
  hosting: Supabase / Neon

Auth:
  provider: Auth.js / Clerk

Monorepo:
  tool: Turborepo
```

## Alternative Options

| Need | Default | Alternative |
|------|---------|-------------|
| Real-time | - | Supabase Realtime, Socket.io |
| File storage | - | Cloudinary, S3 |
| Payment | Stripe | LemonSqueezy, Paddle |
| Email | - | Resend, SendGrid |
| Search | - | Algolia, Typesense |
