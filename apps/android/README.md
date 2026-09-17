# kitchCU Android store shells (P55)

Three **separate Play Store apps** (three downloads). Each is a Trusted Web Activity over the matching PWA. Product logic stays in `apps/website/`.

| Play listing name | Application id | Production host | Local debug |
|-------------------|----------------|-----------------|-------------|
| **kitchCU - customers** | `in.kitchcu.customer` | `https://customer.kitchcu.com` | `http://10.0.2.2:13001` |
| **kitchCU - kitchen owner** | `in.kitchcu.kitchen` | `https://kitchen.kitchcu.com` | `http://10.0.2.2:13002` |
| **kitchCU - admin** | `in.kitchcu.admin` | `https://admin.kitchcu.com` | `http://10.0.2.2:13003` |

Different `applicationId` = three Play Console apps, three store URLs, three install buttons.

## Build AABs (what Play accepts)

Requires Android Studio / JDK 17 + Android SDK. Create an **upload keystore** once and reuse it for all three (or one keystore per app — Play cares about the app id, not sharing the key).

```bash
cd apps/android
./gradlew :app:bundleCustomerRelease
./gradlew :app:bundleKitchenRelease
./gradlew :app:bundleAdminRelease
```

Outputs under `app/build/outputs/bundle/*Release/`.

Debug (emulator → host Vite):

```bash
./gradlew :app:installCustomerDebug
./gradlew :app:installKitchenDebug
./gradlew :app:installAdminDebug
```

## Publish on Google Play (three listings)

1. **Google Play Console** → create a developer account (one-time fee) if you do not have one.
2. Create **three** applications (Create app × 3):
   - kitchCU - customers
   - kitchCU - kitchen owner
   - kitchCU - admin
3. For **each** app: default language, app category, Free, declarations (ads = no, target audience, content rating questionnaire).
4. **Setup → App integrity / App signing**: enroll Play App Signing. Upload the first AAB; Play generates the **app signing certificate**.
5. Copy that app’s **SHA-256** of the **app signing cert** (not only the upload cert) into `apps/website/public/.well-known/assetlinks.json` for that package (`in.kitchcu.customer` / `.kitchen` / `.admin`). Deploy the website so `https://customer.kitchcu.com/.well-known/assetlinks.json` (and kitchen/admin hosts) serve the file. TWA will not verify without this.
6. **Store listing** per app: short/full description, screenshots (phone + 7" / 10" if you claim tablets), feature graphic 1024×500, icon 512×512. Point privacy policy at `https://kitchcu.com` (or a dedicated policy URL).
7. **Production** track → Create release → upload the matching AAB → review → Start rollout to Production.
8. Repeat steps 4–7 for the other two packages. Each gets its own Play URL, e.g. `https://play.google.com/store/apps/details?id=in.kitchcu.customer`.

Do not put JWT or API keys in this project. Updates to tutorials/sales/features ship by deploying the **website PWAs**; you only ship a new AAB when the shell or host URL changes.
