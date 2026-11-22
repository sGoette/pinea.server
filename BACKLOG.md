# Backlog

## Docker image (easy install for v1)

**Goal:** installing Pinea on a NAS, a mini PC or a Raspberry Pi is "paste a compose file in the NAS UI",
not a Debian VM with network shares, a network bridge, nftables and avahi. Running the container on the
machine that holds the media removes most of that: media folders are local read-only mounts and host
networking makes Bonjour work.

**Image**
- Built by CI for `linux/amd64` and `linux/arm64` (Raspberry Pi 4/5), published to the GitHub container
  registry. Python + `ffmpeg`/`ffprobe` + the built frontend, small base image.
- Fixed paths inside the container: data in `/data` (`PINEA_DATA_ROOT=/data`), media in `/media`.

**Compose file** (works in the container UIs of Synology, QNAP, UGREEN, TrueNAS Scale, Unraid, Proxmox, Raspberry Pi OS):
```yaml
services:
  pinea:
    image: ghcr.io/<owner>/pinea-server:latest
    network_mode: host          # needed for Bonjour, see below
    volumes:
      - ./data:/data
      - /path/to/media:/media:ro
    restart: unless-stopped
```

**Notes**
- **Bonjour only works with `network_mode: host`.** In the default bridge network the mDNS packets don't
  leave the container and the advertised IP would be the container's. With host networking the
  default-route detection in `services/bonjour.py` works as on Linux. Test on Synology/QNAP: their host
  already runs avahi, check that both mDNS stacks get along (and that AAAA lookups stay instant).
- **Self-update stays off** in the container (the updater already refuses without the `releases/` +
  `current` layout). Updates come from pulling the new image; the update panel should say that instead
  of showing the generic "not an installed server" message.
- **No port 80 forwarding, nftables or avahi** in the container. The web UI is reached on port 4000;
  the tvOS app finds the server via Bonjour anyway.
- **`MEDIA_ROOT_FOLDER`** is always `/media` inside the container: preselect it (or seed it) so the user
  never types a path. Paths in the DB stay relative to it, so the host path of the media mount can change.
- **Raspberry Pi:** fine for Pinea (direct play, frame grabs). The Pi 5 has no hardware video encoder,
  so real-time transcoding would never be an option there.
- **First-run setup in the web UI** to go with it: media folder (preselected), server name, first
  library, start the scan. The tvOS app can show the web UI address / a QR code when it finds a server
  without libraries.
- **TMDB API key:** the shipped scraper needs one and today every user has to get their own. For an
  App Store audience either ship a key (check TMDB's terms for distributed apps) or guide through it in
  the first-run setup.
- Keep `scripts/linux/install.sh` for bare-metal / VM installs.
- Later: an Unraid Community Apps template and the TrueNAS app catalog, both based on the same image.

## Creating a library for a folder that already has one

**Where:** `PUT /api/library` (`backend/app/api/library.py`, `create_library`)

`libraries.media_folder` is `UNIQUE`, so a second library for the same folder fails with an
`IntegrityError` and the web UI only gets a 500. Catch the conflict and answer with a clear error
(e.g. 409 "This folder already has a library"), and show it in the library dialog.

## Changing the media root folder

**Where:** `POST /api/settings` (`backend/app/api/settings.py`, setting `MEDIA_ROOT_FOLDER`)

All `libraries.media_folder` and `movies.file_location` paths are relative to `MEDIA_ROOT_FOLDER`.
Saving a different root today just changes the setting: existing libraries then point into the new
root, files are missing, and the orphan cleanup may delete movies (its safety guards usually stop it).
When libraries exist, a root change needs a decision: refuse it, or delete the libraries with all their
movies and posters first (ask the user in the UI).
