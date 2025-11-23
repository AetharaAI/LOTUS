  aetherai-ui git:(main) ✗ ./audit.sh
=== PROJECT STRUCTURE ===
.
├── app
│   ├── api
│   │   └── chat
│   │       └── completions
│   ├── compliance
│   │   └── page.tsx
│   ├── globals.css
│   ├── layout.tsx
│   └── page.tsx
├── audit.sh
├── components
│   ├── auth
│   │   └── ProfileButton.tsx
│   ├── chat
│   │   ├── ChatInterface.tsx
│   │   ├── InputBar.tsx
│   │   ├── MessageList.tsx
│   │   ├── Message.tsx
│   │   ├── Sidebar.tsx
│   │   └── ThinkingBlock.tsx
│   ├── settings
│   │   └── SettingsPanel.tsx
│   └── shared
│       ├── Button.tsx
│       ├── ComplianceFooter.tsx
│       ├── Logo.tsx
│       ├── MarkdownRenderer.tsx
│       └── ModelBadge.tsx
├── lib
│   ├── api
│   │   ├── streaming.ts
│   │   └── streaming.ts.bak
│   └── stores
│       ├── authStore.ts
│       ├── chatStore.ts
│       └── settingsStore.ts
├── next.config.js
├── next-env.d.ts
├── niginx-junk
│   ├── apriel-api.conf
│   └── lotus_api.nginx.conf
├── package.json
├── package-lock.json
├── postcss.config.js
├── tailwind.config.ts
├── tsconfig.json
├── types
│   └── prismjs.d.ts
└── types.d.ts

15 directories, 34 files

=== PACKAGE.JSON ===
{
  "name": "aetherai-ui",
  "version": "1.0.0",
  "description": "AetherAI - The American Standard for Sovereign AI",
  "private": true,
  "scripts": {
    "dev": "next dev -p 3000",
    "build": "next build",
    "start": "next start -p 3000",
    "lint": "next lint"
  },
  "dependencies": {
    "lucide-react": "^0.554.0",
    "next": "14.0.4",
    "prismjs": "^1.29.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-draggable": "^4.5.0",
    "react-markdown": "^9.0.1",
    "remark-gfm": "^4.0.0",
    "zustand": "^4.4.7"
  },
  "devDependencies": {
    "@types/node": "^20",
    "@types/prismjs": "^1.26.3",
    "@types/react": "^18",
    "@types/react-dom": "^18",
    "autoprefixer": "^10.0.1",
    "postcss": "^8",
    "tailwindcss": "^3.3.0",
    "typescript": "^5"
  }
}

=== TSCONFIG.JSON ===
{
  "compilerOptions": {
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [
      {
        "name": "next"
      }
    ],
    "paths": {
      "@/*": ["./*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}

=== NEXT.CONFIG ===
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080',
  },
};

module.exports = nextConfig;

=== APP DIRECTORY STRUCTURE ===
total 32
drwxrwxr-x 4 cory cory 4096 Nov 23 00:11 .
drwxrwxr-x 9 cory cory 4096 Nov 23 01:03 ..
drwxrwxr-x 3 cory cory 4096 Nov 23 00:12 api
drwxrwxr-x 2 cory cory 4096 Nov 16 20:33 compliance
-rw-rw-r-- 1 cory cory 4130 Nov 16 20:33 globals.css
-rw-rw-r-- 1 cory cory 1200 Nov 18 03:17 layout.tsx
-rw-rw-r-- 1 cory cory  769 Nov 22 11:19 page.tsx

=== LIB DIRECTORY STRUCTURE ===
total 16
drwxrwxr-x 4 cory cory 4096 Nov 16 20:33 .
drwxrwxr-x 9 cory cory 4096 Nov 23 01:03 ..
drwxrwxr-x 2 cory cory 4096 Nov 23 00:13 api
drwxrwxr-x 2 cory cory 4096 Nov 18 03:17 stores

=== COMPONENTS DIRECTORY ===
total 24
drwxrwxr-x 6 cory cory 4096 Nov 18 03:17 .
drwxrwxr-x 9 cory cory 4096 Nov 23 01:03 ..
drwxrwxr-x 2 cory cory 4096 Nov 18 03:17 auth
drwxrwxr-x 2 cory cory 4096 Nov 18 03:17 chat
drwxrwxr-x 2 cory cory 4096 Nov 18 03:17 settings
drwxrwxr-x 2 cory cory 4096 Nov 16 20:33 shared

=== CURRENT ENV VARS (sanitized) ===
AI_GATEWAY_API_KEY=***REDACTED***
AETHER_UPSTREAM_URL=***REDACTED***
AETHER_API_KEY=***REDACTED***

#AETHER_BASE_URL=***REDACTED***

# MODEL ID (Must match what you launched in Docker)
NEXT_PUBLIC_MODEL_ID=***REDACTED***


=== VERCEL ENV VARS (from vercel.json if exists) ===
No vercel.json
End of Audit.