This is a [Next.js](https://nextjs.org/) project bootstrapped with [`create-next-app`](https://github.com/vercel/next.js/tree/canary/packages/create-next-app).

## Getting Started

### Initial Setup

```bash
npm install --legacy-peer-deps
cp example.env .env.local
```

### Run Development Server

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

### Enabling Login with NextAuth and Google Drive Integration

Set `NEXT_PUBLIC_GOOGLE_CLIENT_ID` and `NEXT_PUBLIC_GOOGLE_CLIENT_SECRET` in .env.local from a Google Cloud project with Drive integration and test user enabled. If you don't already have access to this, follow these steps starting at https://console.cloud.google.com/:

* Create a new project from project menu, open the new project
* Open Main Menu (upper-left) -> APIs & Services -> Library
* Open "Google Drive API" in center card view, then click "Enable" button
* Open "Oauth consent screen" in left menu, click "get started"
* Enter App name, User support email, pick Audience -> External, ..., create
* Under "Test users" click "+ Add users" and add your Gmail account
* Open "Clients" in left menu, add Web Application type
* Add `http://localhost:3000` to "Authorized JavaScript origins"
* Add `http://localhost:3000/api/auth/callback/google` to "Authorized Redirect URIs"
* Copy the "Client ID" and "Client secret" to the variables in `.env.local`

### Setting Up Firebase Credentials (Local & CI)

To allow both your Next.js application and the Playwright test suite to communicate with Firebase, you need to configure your environment variables.

**Phase 1: Generate Your Firebase Configuration**
If you do not already have a Firebase app configured, follow these steps starting at [https://console.firebase.google.com/](https://console.firebase.google.com/):

* Create a new project from the project menu, give it a name, and complete the setup wizard.
* Open the Project Overview dashboard, click "Add app", then click the Web platform icon (`</>`).
* Enter a web app nickname (e.g., `linked-creds-client-1234`), leave hosting unchecked, and click "Register app".
* Keep the generated `firebaseConfig` object on your screen (you will need values like `apiKey`, `authDomain`, and `projectId` for the next steps).

**Phase 2: Local Development Setup**
To run the app or Playwright tests on your local machine:

* Create a file named `.env.local` in the root of your project directory.
* Copy the following template into the file and populate it with the raw values from your Firebase configuration:
```env
NEXT_PUBLIC_FIREBASE_API_KEY=your_api_key_here
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=your_auth_domain_here
NEXT_PUBLIC_FIREBASE_PROJECT_ID=your_project_id_here
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=your_storage_bucket_here
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=your_sender_id_here
NEXT_PUBLIC_FIREBASE_APP_ID=your_app_id_here

```


* Note: `.env.local` is intentionally ignored by Git to keep your credentials secure. In higher environments, these values can be injected via Cloud Providers, Vaults, or IaC like Terraform.

**Phase 3: GitHub Actions (CI) Setup**
To allow Playwright to build and test your application in CI, you must securely provide these same variables to GitHub.

* Navigate to your project repository on [https://github.com/](https://github.com/).
* Open Repository Settings (gear icon) -> Secrets and variables -> Actions.
* Click the "New repository secret" button to create an entry for each variable.
* Name the secret exactly as it appears above (e.g., `NEXT_PUBLIC_FIREBASE_API_KEY`) and paste the corresponding raw value, then click "Add secret".
* Open your project's `.github/workflows/playwright.yml` file.
* Map the GitHub secrets to job-level environment variables inside the `env:` block so they are securely baked in during the `npm run build` step.

  
### Custom Font

This project uses [`next/font`](https://nextjs.org/docs/basic-features/font-optimization) to automatically optimize and load Inter, a custom Google Font.

### Setting up Google Cloud Project with Drive Integration

Create a project 

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js/) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/deployment) for more details.
