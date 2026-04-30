# Welcome to your Expo app 👋

This is an [Expo](https://expo.dev) project created with [`create-expo-app`](https://www.npmjs.com/package/create-expo-app).

## Get started

1. Install dependencies

   ```bash
   npm install
   ```

2. Configure environment

   ```bash
   cp .env.example .env.local
   # Then edit .env.local to set EXPO_PUBLIC_API_BASE_URL for your environment.
   ```

3. Start the app

   ```bash
   npx expo start
   ```

In the output, you'll find options to open the app in a

- [development build](https://docs.expo.dev/develop/development-builds/introduction/)
- [Android emulator](https://docs.expo.dev/workflow/android-studio-emulator/)
- [iOS simulator](https://docs.expo.dev/workflow/ios-simulator/)
- [Expo Go](https://expo.dev/go), a limited sandbox for trying out app development with Expo

You can start developing by editing the files inside the **app** directory. This project uses [file-based routing](https://docs.expo.dev/router/introduction).

## API Base URL

The mobile app calls the FastAPI backend directly (no Next.js proxy). The base URL must be configured via `EXPO_PUBLIC_API_BASE_URL` in `.env.local`.

| Environment       | Value                                      | Notes                                     |
|-------------------|--------------------------------------------|-------------------------------------------|
| iOS Simulator     | `http://localhost:8001`                    | Same machine, `localhost` works           |
| Android Emulator  | `http://10.0.2.2:8001`                     | `10.0.2.2` = host machine from emulator   |
| Physical device   | `http://<your-LAN-IP>:8001`                | e.g. `http://192.168.0.42:8001`. Same Wi-Fi as your dev machine. Find LAN IP with `ifconfig` (Mac/Linux) or `ipconfig` (Windows). |
| Production        | `https://api.opad.example.com`             | Set at EAS Build time                     |

Use the `apiUrl` helper from `lib/api.ts` to build full URLs:

```ts
import { apiUrl } from '@/lib/api'

const res = await fetch(apiUrl('/articles'))
```

> CORS does **not** apply to native mobile calls (only browsers enforce CORS). The FastAPI server's `CORS_ORIGINS` setting is irrelevant for the mobile app, except when running via Expo Web.

## Get a fresh project

When you're ready, run:

```bash
npm run reset-project
```

This command will move the starter code to the **app-example** directory and create a blank **app** directory where you can start developing.

## Learn more

To learn more about developing your project with Expo, look at the following resources:

- [Expo documentation](https://docs.expo.dev/): Learn fundamentals, or go into advanced topics with our [guides](https://docs.expo.dev/guides).
- [Learn Expo tutorial](https://docs.expo.dev/tutorial/introduction/): Follow a step-by-step tutorial where you'll create a project that runs on Android, iOS, and the web.

## Join the community

Join our community of developers creating universal apps.

- [Expo on GitHub](https://github.com/expo/expo): View our open source platform and contribute.
- [Discord community](https://chat.expo.dev): Chat with Expo users and ask questions.
