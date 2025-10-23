This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Performance & Memory Optimization

This project has been optimized to run on low-spec machines (minimum 2GB RAM). Key optimizations include:

### Memory-Efficient Development

For machines with limited RAM, you can run with a memory limit:

```bash
# Minimum (512MB - slower but works on potato computers)
NODE_OPTIONS='--max-old-space-size=512' npm run dev

# Recommended (1GB - good balance)
NODE_OPTIONS='--max-old-space-size=1024' npm run dev

# Default (uses system default, ~2GB)
npm run dev
```

### What's Been Optimized

1. **Icon Library (lucide-react)**: Tree-shaken via `optimizePackageImports` - only used icons are bundled
2. **Animations (framer-motion)**: Lazy-loaded to reduce initial bundle size
3. **Background Patterns**: Rewritten to use native SVG patterns instead of 1000+ animated elements
4. **UI Libraries**: All major dependencies configured for optimal tree-shaking

### Bundle Analysis

To check the bundle size and identify optimization opportunities:

```bash
npm run analyze
```

This will build the project with bundle analyzer and open an interactive report in your browser.

### Expected Memory Usage

- **Development**: 800 MB - 1.2 GB (down from 2.5 GB)
- **Production Build**: ~500 MB
- **Runtime**: Depends on browser and usage

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
