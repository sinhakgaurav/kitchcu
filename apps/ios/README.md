# kitchCU iOS store shells (P55)

Three **WKWebView** apps wrap the live PWAs. Product logic stays in `apps/website/`.

| App Store name | Bundle id | Production host | Simulator debug |
|----------------|-----------|-----------------|-----------------|
| **kitchCU - customers** | `in.kitchcu.customer` | `https://customer.kitchcu.com` | `http://127.0.0.1:13001` |
| **kitchCU - kitchen owner** | `in.kitchcu.kitchen` | `https://kitchen.kitchcu.com` | `http://127.0.0.1:13002` |
| **kitchCU - admin** | `in.kitchcu.admin` | `https://admin.kitchcu.com` | `http://127.0.0.1:13003` |

Create three iOS App targets in Xcode that compile `Shared/WebShellViewController.swift` plus the matching `Info.plist` and `LaunchURL.plist`.

`NSAppTransportSecurity` allows localhost only in Debug. Production ATS stays HTTPS.

Replace `TEAMID` in `apps/website/public/.well-known/apple-app-site-association` before App Store submission.

Do not put JWT or API keys in these targets.
