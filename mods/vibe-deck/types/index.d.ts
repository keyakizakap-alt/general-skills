export type ThemeId = 'mocha' | 'tokyo' | 'rose' | 'ember' | 'latte'

export type Prefs = { band: boolean; chat: boolean; prompts: boolean }

export type Stats = {
  startedAt: number
  turns: number
  tools: number
  edits: number
  turnStartedAt: number
  lastTurnMs: number | null
}

declare module 'claude-code' {
  interface PluginState {
    'vibe-deck': {
      theme: ThemeId
      prefs: Prefs
      stats: Stats | null
      now: number
    }
  }
}
