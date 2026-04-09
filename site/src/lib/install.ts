export const repoOwner = "Takhoffman";
export const repoName = "ankicli";
export const repoUrl = `https://github.com/${repoOwner}/${repoName}`;
export const releasesUrl = `${repoUrl}/releases`;
export const issuesUrl = `${repoUrl}/issues`;
export const rawBaseUrl = `https://raw.githubusercontent.com/${repoOwner}/${repoName}/main`;

export type PlatformCard = {
  id: "macos" | "linux" | "windows";
  label: string;
  installCommand: string;
  verifyCommand: string;
  manualCommand: string;
};

export const installerScripts = {
  shell: `${rawBaseUrl}/scripts/install.sh`,
  powershell: `${rawBaseUrl}/scripts/install.ps1`,
};

export const platformCards: PlatformCard[] = [
  {
    id: "macos",
    label: "macOS",
    installCommand: `curl -fsSL ${installerScripts.shell} | sh`,
    verifyCommand: "ankicli --version\nankicli --json doctor backend",
    manualCommand: "pipx install anki-agent-toolkit",
  },
  {
    id: "linux",
    label: "Linux",
    installCommand: `curl -fsSL ${installerScripts.shell} | sh`,
    verifyCommand: "ankicli --version\nankicli --json doctor backend",
    manualCommand: "pipx install anki-agent-toolkit",
  },
  {
    id: "windows",
    label: "Windows",
    installCommand: `irm ${installerScripts.powershell} | iex`,
    verifyCommand: "ankicli --version\r\nankicli --json doctor backend",
    manualCommand: "pipx install anki-agent-toolkit",
  },
];
