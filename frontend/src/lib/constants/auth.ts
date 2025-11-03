export const AUTH_STEPS = [
  {
    title: "Validating request",
    description: "Confirming everything matches the original login.",
  },
  {
    title: "Exchanging tokens",
    description: "Talking to Spotify to complete the secure handshake.",
  },
  {
    title: "Finalizing session",
    description: "Saving your session and preparing your Moodlist dashboard.",
  },
] as const;
