# iOS test distribution plan

## Recommended path

For a real iPhone, the practical path is an Expo EAS internal iOS build:

1. Register/sign the app with an Apple Developer account.
2. Run the GitHub Actions workflow **Build iOS app** with profile `preview`.
3. Open the GitHub Release created by the workflow.
4. Use the EAS download/install URL in the release notes on the registered iPhone.

This produces a signed `.ipa` suitable for development testing on physical devices. iOS will not install an arbitrary unsigned `.ipa` downloaded from GitHub.

## What is already configured

- `mobile/eas.json`
  - `preview`: internal distribution for real iPhone testing.
  - `simulator`: iOS Simulator-only build.
  - `production`: production/TestFlight-ready build profile.
- `apps/mygardenos/.github/workflows/ios-build.yml`
  - Legacy workflow from the former standalone repository. It is retained as a reference after migration, but GitHub will not trigger it from this nested path. Move/adapt it under the repository root `.github/workflows/` before using it in PointCloudTT.
- `mobile/package.json`
  - `npm run build:ios:preview`
  - `npm run build:ios:simulator`
  - `npm run build:ios:production`

## Required GitHub/Expo setup

Add this repository secret in GitHub:

- `EXPO_TOKEN`: Expo access token from https://expo.dev/accounts/[account]/settings/access-tokens

Then connect the project to Expo/EAS once from a trusted machine:

```bash
cd apps/mygardenos/mobile
npx eas-cli login
npx eas-cli build:configure
```

For physical iPhone installs, EAS also needs Apple Developer signing credentials. You can let EAS manage them during the first local interactive build:

```bash
cd apps/mygardenos/mobile
npm run build:ios:preview
```

After credentials are stored in EAS, GitHub Actions can run non-interactively.

## Profiles

### `preview` — best for your requested phone test

- Real iPhone install.
- Requires Apple Developer account and registered device/provisioning.
- Output: signed iOS app install URL / `.ipa` artifact via EAS.

### `simulator` — easiest no-Apple-account build

- Runs only on iOS Simulator on Mac.
- Cannot be installed on a physical iPhone.

### `production` — TestFlight/App Store

- Best once the app is ready for broader testing.
- Requires App Store Connect setup.

## Backend URL note

The current preview build uses `EXPO_PUBLIC_API_URL=http://localhost:8000`. That is useful for simulator/local development, but a real iPhone cannot reach your laptop's `localhost`.

Before distributing to a phone, set the preview profile URL to a reachable backend, for example:

- a deployed HTTPS FastAPI endpoint, or
- your LAN IP, e.g. `http://192.168.1.23:8000`, while the phone is on the same Wi-Fi.
